"""Binary sensor platform for Beestat occupancy and comfort-profile usage."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

from .const import DOMAIN
from .data import (
    extract_remote_sensors,
    extract_thermostat_sensor,
    find_thermostat,
    remote_sensor_id,
    remote_sensor_in_use,
    remote_sensor_name,
    remote_sensor_occupancy,
    thermostat_fan_is_running,
    thermostat_id,
    thermostat_is_in_hold,
    thermostat_name,
)


@dataclass(frozen=True)
class BeestatBinarySensorDescription(BinarySensorEntityDescription):
    """Describe a Beestat binary sensor.

    We subclass HA's BinarySensorEntityDescription so HA has translation_key,
    entity_registry_* defaults, etc.
    """

    value_fn: Callable[[dict[str, Any]], bool | None] = lambda _data: None


BINARY_SENSOR_DESCRIPTIONS: tuple[BeestatBinarySensorDescription, ...] = (
    BeestatBinarySensorDescription(
        key="in_use",
        name="In Use",
        device_class=None,
        value_fn=lambda sensor: remote_sensor_in_use(sensor),
    ),
    BeestatBinarySensorDescription(
        key="occupancy",
        name="Presence",
        device_class=BinarySensorDeviceClass.OCCUPANCY,
        value_fn=lambda sensor: remote_sensor_occupancy(sensor),
    ),
)

THERMOSTAT_BINARY_SENSOR_DESCRIPTIONS: tuple[BeestatBinarySensorDescription, ...] = (
    *BINARY_SENSOR_DESCRIPTIONS,
    BeestatBinarySensorDescription(
        key="hold_active",
        name="Hold Active",
        device_class=None,
        value_fn=lambda thermostat_sensor: thermostat_is_in_hold(thermostat_sensor),
    ),
    BeestatBinarySensorDescription(
        key="fan_running",
        name="Fan Running",
        device_class=None,
        value_fn=lambda thermostat_sensor: thermostat_fan_is_running(thermostat_sensor),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Beestat binary sensors based on a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    entities: list[BinarySensorEntity] = []

    for thermostat in coordinator.data:
        # Thermostat-level presence / in-use (extracted from the ecobee "thermostat" sensor entry).
        thermostat_sensor = extract_thermostat_sensor(thermostat)
        if thermostat_sensor is not None:
            for description in THERMOSTAT_BINARY_SENSOR_DESCRIPTIONS:
                # Some thermostat-level values come from the special thermostat remote_sensor
                # entry (presence/in-use), others come from the thermostat dict itself (events).
                source = thermostat_sensor if description.key in {"in_use", "occupancy"} else thermostat
                value = description.value_fn(source)
                if value is None:
                    continue
                entities.append(
                    BeestatThermostatBinarySensor(
                        coordinator=coordinator,
                        thermostat=thermostat,
                        description=description,
                    )
                )

        # Remote sensor presence / in-use.
        for remote_sensor in extract_remote_sensors(thermostat):
            for description in BINARY_SENSOR_DESCRIPTIONS:
                if description.value_fn(remote_sensor) is None:
                    continue
                entities.append(
                    BeestatRemoteBinarySensor(
                        coordinator=coordinator,
                        thermostat=thermostat,
                        remote_sensor=remote_sensor,
                        description=description,
                    )
                )

    async_add_entities(entities)


class BeestatThermostatBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Representation of a Beestat thermostat-level binary sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator,
        thermostat: dict[str, Any],
        description: BeestatBinarySensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._thermostat_id = thermostat_id(thermostat)
        self._thermostat_name = thermostat_name(thermostat)
        self._attr_unique_id = f"{self._thermostat_id}_{description.key}"
        self._attr_suggested_object_id = f"beestat_{slugify(self._thermostat_name)}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._thermostat_id)},
            name=self._thermostat_name,
            manufacturer="Beestat",
            model="Thermostat",
        )
        self._attr_device_class = description.device_class

    @property
    def name(self) -> str:
        return self.entity_description.name

    @property
    def is_on(self) -> bool | None:
        thermostat = find_thermostat(self.coordinator.data, self._thermostat_id)
        if thermostat is None:
            return None
        thermostat_sensor = extract_thermostat_sensor(thermostat)
        if thermostat_sensor is None:
            return None

        source = thermostat_sensor if self.entity_description.key in {"in_use", "occupancy"} else thermostat
        return self.entity_description.value_fn(source)


class BeestatRemoteBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Representation of a Beestat remote sensor binary sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator,
        thermostat: dict[str, Any],
        remote_sensor: dict[str, Any],
        description: BeestatBinarySensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._thermostat_id = thermostat_id(thermostat)
        self._remote_sensor_id = remote_sensor_id(remote_sensor, self._thermostat_id)
        self._remote_sensor_name = remote_sensor_name(remote_sensor)
        self._attr_unique_id = f"{self._remote_sensor_id}_{description.key}"
        self._attr_suggested_object_id = f"beestat_{slugify(self._remote_sensor_name)}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._remote_sensor_id)},
            name=self._remote_sensor_name,
            manufacturer="Beestat",
            model="Remote Sensor",
            via_device=(DOMAIN, self._thermostat_id),
        )
        self._attr_device_class = description.device_class

    @property
    def name(self) -> str:
        return self.entity_description.name

    @property
    def is_on(self) -> bool | None:
        thermostat = find_thermostat(self.coordinator.data, self._thermostat_id)
        if thermostat is None:
            return None
        for sensor in extract_remote_sensors(thermostat):
            if remote_sensor_id(sensor, self._thermostat_id) == self._remote_sensor_id:
                return self.entity_description.value_fn(sensor)
        return None

"""Binary sensor platform for Beestat remote occupancy."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .data import (
    extract_remote_sensors,
    find_thermostat,
    remote_sensor_id,
    remote_sensor_name,
    remote_sensor_occupancy,
    thermostat_id,
)


@dataclass(frozen=True)
class BeestatBinarySensorDescription:
    """Describe a Beestat binary sensor."""

    key: str
    name: str
    device_class: BinarySensorDeviceClass | None
    value_fn: Callable[[dict[str, Any]], bool | None]


BINARY_SENSOR_DESCRIPTIONS: tuple[BeestatBinarySensorDescription, ...] = (
    BeestatBinarySensorDescription(
        key="occupancy",
        name="Occupancy",
        device_class=BinarySensorDeviceClass.OCCUPANCY,
        value_fn=lambda sensor: remote_sensor_occupancy(sensor),
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
        for remote_sensor in extract_remote_sensors(thermostat):
            for description in BINARY_SENSOR_DESCRIPTIONS:
                if description.value_fn(remote_sensor) is None:
                    continue
                entities.append(
                    BeestatRemoteOccupancySensor(
                        coordinator=coordinator,
                        thermostat=thermostat,
                        remote_sensor=remote_sensor,
                        description=description,
                    )
                )
    async_add_entities(entities)


class BeestatRemoteOccupancySensor(CoordinatorEntity, BinarySensorEntity):
    """Representation of a Beestat remote occupancy sensor."""

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

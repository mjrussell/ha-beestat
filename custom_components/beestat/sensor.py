"""Sensor platform for Beestat."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

from .const import DOMAIN
from .data import (
    extract_remote_sensors,
    find_thermostat,
    pick_air_quality_value,
    pick_first_nested_value,
    pick_first_value,
    remote_sensor_humidity,
    remote_sensor_id,
    remote_sensor_name,
    remote_sensor_temperature,
    thermostat_id,
    thermostat_name,
)


@dataclass(frozen=True)
class BeestatSensorDescription(SensorEntityDescription):
    """Describe a Beestat sensor.

    We subclass HA's SensorEntityDescription so we automatically satisfy HA's
    expected attributes (translation_key, entity_registry_* defaults, etc.).

    We add our own callbacks for pulling values and dynamic units.
    """

    unit_fn: Callable[[HomeAssistant], str | None] = lambda _hass: None
    value_fn: Callable[[dict[str, Any]], Any] = lambda _data: None
    optional: bool = False


SENSOR_DESCRIPTIONS: tuple[BeestatSensorDescription, ...] = (
    BeestatSensorDescription(
        key="temperature",
        name="Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        unit_fn=lambda hass: hass.config.units.temperature_unit,
        value_fn=lambda thermostat: pick_first_value(
            thermostat,
            "temperature",
            "temp",
            "current_temperature",
        ),
    ),
    BeestatSensorDescription(
        key="humidity",
        name="Humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        unit_fn=lambda hass: PERCENTAGE,
        value_fn=lambda thermostat: pick_first_value(
            thermostat,
            "humidity",
            "current_humidity",
        ),
    ),
    BeestatSensorDescription(
        key="hvac_mode",
        name="HVAC Mode",
        device_class=None,
        state_class=None,
        unit_fn=lambda _hass: None,
        value_fn=lambda thermostat: pick_first_value(
            thermostat,
            "hvac_mode",
            "mode",
            "hvacMode",
            "thermostat_mode",
        )
        or pick_first_nested_value(thermostat, ("runtime", "hvacMode")),
        optional=True,
    ),
    BeestatSensorDescription(
        key="hvac_state",
        name="HVAC State",
        device_class=None,
        state_class=None,
        unit_fn=lambda _hass: None,
        value_fn=lambda thermostat: pick_first_value(
            thermostat,
            "hvac_state",
            "hvacState",
            "equipmentStatus",
            "equipment_status",
            "state",
        )
        or pick_first_nested_value(thermostat, ("runtime", "equipmentStatus")),
        optional=True,
    ),
    BeestatSensorDescription(
        key="co2",
        name="CO2",
        device_class=SensorDeviceClass.CO2,
        state_class=SensorStateClass.MEASUREMENT,
        unit_fn=lambda _hass: "ppm",
        value_fn=lambda thermostat: pick_air_quality_value(
            thermostat,
            runtime_key="actualCO2",
            fallback_keys=("co2", "CO2", "co2_ppm", "air_quality_co2"),
        ),
        optional=True,
    ),
    BeestatSensorDescription(
        key="voc",
        name="VOC",
        device_class=SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS,
        state_class=SensorStateClass.MEASUREMENT,
        unit_fn=lambda _hass: "ppb",
        value_fn=lambda thermostat: pick_air_quality_value(
            thermostat,
            runtime_key="actualVOC",
            fallback_keys=("voc", "VOC", "voc_ppb", "air_quality_voc"),
        ),
        optional=True,
    ),
    BeestatSensorDescription(
        key="aq_score",
        name="Air Quality Score",
        device_class=SensorDeviceClass.AQI,
        state_class=SensorStateClass.MEASUREMENT,
        unit_fn=lambda _hass: None,
        value_fn=lambda thermostat: pick_air_quality_value(
            thermostat,
            runtime_key="actualAQScore",
            fallback_keys=("aq_score", "aqScore", "air_quality_score", "AQScore"),
        ),
        optional=True,
    ),
    BeestatSensorDescription(
        key="aq_accuracy",
        name="Air Quality Accuracy",
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        unit_fn=lambda _hass: None,
        value_fn=lambda thermostat: pick_air_quality_value(
            thermostat,
            runtime_key="actualAQAccuracy",
            fallback_keys=("aq_accuracy", "aqAccuracy", "air_quality_accuracy", "AQAccuracy"),
        ),
        optional=True,
    ),
)

REMOTE_SENSOR_DESCRIPTIONS: tuple[BeestatSensorDescription, ...] = (
    BeestatSensorDescription(
        key="temperature",
        name="Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        unit_fn=lambda hass: hass.config.units.temperature_unit,
        value_fn=lambda sensor: remote_sensor_temperature(sensor),
    ),
    BeestatSensorDescription(
        key="humidity",
        name="Humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        unit_fn=lambda _hass: PERCENTAGE,
        value_fn=lambda sensor: remote_sensor_humidity(sensor),
        optional=True,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Beestat sensors based on a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    entities: list[SensorEntity] = []
    for thermostat in coordinator.data:
        for description in SENSOR_DESCRIPTIONS:
            if description.optional and description.value_fn(thermostat) is None:
                continue
            entities.append(
                BeestatThermostatSensor(
                    coordinator=coordinator,
                    thermostat=thermostat,
                    description=description,
                    hass=hass,
                )
            )
        for remote_sensor in extract_remote_sensors(thermostat):
            for description in REMOTE_SENSOR_DESCRIPTIONS:
                if description.optional and description.value_fn(remote_sensor) is None:
                    continue
                entities.append(
                    BeestatRemoteSensor(
                        coordinator=coordinator,
                        thermostat=thermostat,
                        remote_sensor=remote_sensor,
                        description=description,
                        hass=hass,
                    )
                )
    async_add_entities(entities)


class BeestatThermostatSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Beestat thermostat sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator,
        thermostat: dict[str, Any],
        description: BeestatSensorDescription,
        hass: HomeAssistant,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._thermostat_id = _thermostat_id(thermostat)
        self._thermostat_name = _thermostat_name(thermostat)
        self._hass = hass
        self._attr_unique_id = f"{self._thermostat_id}_{description.key}"
        self._attr_suggested_object_id = f"beestat_{slugify(self._thermostat_name)}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._thermostat_id)},
            name=self._thermostat_name,
            manufacturer="Beestat",
            model=pick_first_value(thermostat, "model", "thermostat_model") or "Thermostat",
        )

    @property
    def name(self) -> str:
        return self.entity_description.name

    @property
    def native_value(self) -> Any:
        thermostat = _find_thermostat(self.coordinator.data, self._thermostat_id)
        if thermostat is None:
            return None
        return self.entity_description.value_fn(thermostat)

    @property
    def native_unit_of_measurement(self) -> str | None:
        return self.entity_description.unit_fn(self._hass)

def _thermostat_id(thermostat: dict[str, Any]) -> str:
    return thermostat_id(thermostat)


def _thermostat_name(thermostat: dict[str, Any]) -> str:
    return thermostat_name(thermostat)


def _find_thermostat(thermostats: list[dict[str, Any]], thermostat_id: str) -> dict[str, Any] | None:
    return find_thermostat(thermostats, thermostat_id)


class BeestatRemoteSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Beestat remote sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator,
        thermostat: dict[str, Any],
        remote_sensor: dict[str, Any],
        description: BeestatSensorDescription,
        hass: HomeAssistant,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._thermostat_id = _thermostat_id(thermostat)
        self._remote_sensor_id = remote_sensor_id(remote_sensor, self._thermostat_id)
        self._remote_sensor_name = remote_sensor_name(remote_sensor)
        self._hass = hass
        self._attr_unique_id = f"{self._remote_sensor_id}_{description.key}"
        self._attr_suggested_object_id = f"beestat_{slugify(self._remote_sensor_name)}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._remote_sensor_id)},
            name=self._remote_sensor_name,
            manufacturer="Beestat",
            model=pick_first_value(remote_sensor, "type", "model") or "Remote Sensor",
            via_device=(DOMAIN, self._thermostat_id),
        )

    @property
    def name(self) -> str:
        return self.entity_description.name

    @property
    def native_value(self) -> Any:
        thermostat = _find_thermostat(self.coordinator.data, self._thermostat_id)
        if thermostat is None:
            return None
        for sensor in extract_remote_sensors(thermostat):
            if remote_sensor_id(sensor, self._thermostat_id) == self._remote_sensor_id:
                return self.entity_description.value_fn(sensor)
        return None

    @property
    def native_unit_of_measurement(self) -> str | None:
        return self.entity_description.unit_fn(self._hass)

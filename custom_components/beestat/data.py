"""Data extraction helpers for Beestat entities."""
from __future__ import annotations

from typing import Any


def pick_first_value(data: dict[str, Any], *keys: str) -> Any:
    """Return the first non-None value from a dict for the provided keys."""
    for key in keys:
        value = data.get(key)
        if value is not None:
            return value
    return None


def pick_first_nested_value(data: dict[str, Any], *paths: tuple[str, ...]) -> Any:
    """Return the first non-None value from nested dict paths."""
    for path in paths:
        current: Any = data
        for key in path:
            if not isinstance(current, dict) or key not in current:
                current = None
                break
            current = current[key]
        if current is not None:
            return current
    return None


def pick_air_quality_value(
    thermostat: dict[str, Any],
    runtime_key: str,
    fallback_keys: tuple[str, ...],
) -> Any:
    """Return air quality value, preferring runtime values over fallbacks."""
    runtime_value = pick_first_nested_value(thermostat, ("runtime", runtime_key))
    if runtime_value is not None:
        return runtime_value

    types = {runtime_key.lower(), *(key.lower() for key in fallback_keys)}
    for container_key in (
        "capabilities",
        "capability",
        "settings",
        "equipment",
        "air_quality",
        "airQuality",
    ):
        container = thermostat.get(container_key)
        if isinstance(container, dict):
            value = pick_first_value(container, runtime_key, *fallback_keys)
            if value is not None:
                return value
        elif isinstance(container, list):
            for item in container:
                if not isinstance(item, dict):
                    continue
                cap_type = str(
                    item.get("type") or item.get("name") or item.get("capability") or ""
                ).lower()
                if cap_type in types:
                    value = item.get("value")
                    if value is None:
                        value = item.get("val")
                    if value is not None:
                        return value

    return pick_first_value(thermostat, runtime_key, *fallback_keys)


def thermostat_id(thermostat: dict[str, Any]) -> str:
    """Return a stable thermostat id string."""
    return str(
        pick_first_value(
            thermostat,
            "id",
            "thermostat_id",
            "identifier",
            "uuid",
        )
        or "unknown"
    )


def thermostat_name(thermostat: dict[str, Any]) -> str:
    """Return a thermostat display name."""
    return str(
        pick_first_value(
            thermostat,
            "name",
            "thermostat_name",
            "label",
        )
        or "Thermostat"
    )


def find_thermostat(
    thermostats: list[dict[str, Any]],
    thermostat_identifier: str,
) -> dict[str, Any] | None:
    """Find a thermostat dict by id."""
    for thermostat in thermostats:
        if thermostat_id(thermostat) == thermostat_identifier:
            return thermostat
    return None


def extract_remote_sensors(thermostat: dict[str, Any]) -> list[dict[str, Any]]:
    """Return a normalized list of remote sensor dicts from a thermostat payload.

    Note: ecobee payloads often include a "remote_sensors" entry for the thermostat
    itself (type="thermostat"). We filter those out since we already expose
    thermostat-level entities separately.
    """
    sensors: list[dict[str, Any]] = []
    for key in (
        "remoteSensors",
        "remote_sensors",
        "remoteSensor",
        "remote_sensor",
        "sensors",
        "roomSensors",
        "rooms",
    ):
        value = thermostat.get(key)
        if isinstance(value, list):
            sensors.extend([item for item in value if isinstance(item, dict)])
        elif isinstance(value, dict):
            nested_list = value.get("sensors") or value.get("items")
            if isinstance(nested_list, list):
                sensors.extend([item for item in nested_list if isinstance(item, dict)])
            elif all(isinstance(v, dict) for v in value.values()):
                sensors.extend(list(value.values()))

    filtered: list[dict[str, Any]] = []
    for sensor in sensors:
        if str(sensor.get("type") or "").lower() == "thermostat":
            continue
        filtered.append(sensor)

    return filtered


def remote_sensor_id(sensor: dict[str, Any], thermostat_identifier: str) -> str:
    """Return a stable remote sensor id string."""
    sensor_id = pick_first_value(
        sensor,
        "id",
        "sensor_id",
        "identifier",
        "uuid",
        "remoteSensorId",
    )
    if sensor_id is not None:
        return str(sensor_id)
    return f"{thermostat_identifier}_{remote_sensor_name(sensor)}"


def remote_sensor_name(sensor: dict[str, Any]) -> str:
    """Return a remote sensor display name."""
    return str(
        pick_first_value(
            sensor,
            "name",
            "sensorName",
            "label",
            "room",
            "displayName",
        )
        or "Remote Sensor"
    )


def remote_sensor_temperature(sensor: dict[str, Any]) -> float | int | None:
    """Return the remote sensor temperature if available."""
    value = _extract_remote_sensor_value(
        sensor,
        direct_keys=("temperature", "temp", "current_temperature"),
        nested_paths=(("data", "temperature"), ("runtime", "temperature")),
        capability_types=("temperature", "temp"),
    )
    return _coerce_number(value)


def remote_sensor_humidity(sensor: dict[str, Any]) -> float | int | None:
    """Return the remote sensor humidity if available."""
    value = _extract_remote_sensor_value(
        sensor,
        direct_keys=("humidity", "current_humidity"),
        nested_paths=(("data", "humidity"), ("runtime", "humidity")),
        capability_types=("humidity",),
    )
    return _coerce_number(value)


def remote_sensor_occupancy(sensor: dict[str, Any]) -> bool | None:
    """Return the remote sensor occupancy/presence if available."""
    value = _extract_remote_sensor_value(
        sensor,
        direct_keys=("occupancy", "presence", "occupied"),
        nested_paths=(("data", "occupancy"), ("data", "presence")),
        capability_types=("occupancy", "presence", "occupied"),
    )
    return _coerce_bool(value)


def _extract_remote_sensor_value(
    sensor: dict[str, Any],
    *,
    direct_keys: tuple[str, ...],
    nested_paths: tuple[tuple[str, ...], ...],
    capability_types: tuple[str, ...],
) -> Any:
    value = pick_first_value(sensor, *direct_keys)
    if value is not None:
        return value

    value = pick_first_nested_value(sensor, *nested_paths)
    if value is not None:
        return value

    return _extract_capability_value(sensor, capability_types)


def _extract_capability_value(sensor: dict[str, Any], capability_types: tuple[str, ...]) -> Any:
    types = {cap.lower() for cap in capability_types}
    for list_key in ("capability", "capabilities", "capabilityList"):
        caps = sensor.get(list_key)
        if isinstance(caps, list):
            for cap in caps:
                if not isinstance(cap, dict):
                    continue
                cap_type = str(
                    cap.get("type") or cap.get("name") or cap.get("capability") or ""
                ).lower()
                if cap_type in types:
                    value = cap.get("value")
                    if value is None:
                        value = cap.get("val")
                    if value is not None:
                        return value
        elif isinstance(caps, dict):
            for cap_key, cap_value in caps.items():
                if str(cap_key).lower() in types:
                    if isinstance(cap_value, dict):
                        value = cap_value.get("value")
                        if value is None:
                            value = cap_value.get("val")
                        if value is not None:
                            return value
                    else:
                        return cap_value
    return None


def _coerce_number(value: Any) -> float | int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if stripped == "":
            return None
        try:
            if "." in stripped:
                return float(stripped)
            return int(stripped)
        except ValueError:
            return None
    return None


def _coerce_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "on", "yes", "occupied", "present", "1"}:
            return True
        if lowered in {"false", "off", "no", "unoccupied", "not present", "away", "0"}:
            return False
    return None

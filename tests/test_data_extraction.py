from custom_components.beestat.data import (
    extract_remote_sensors,
    pick_air_quality_value,
    remote_sensor_humidity,
    remote_sensor_occupancy,
    remote_sensor_temperature,
)


def test_pick_air_quality_prefers_runtime():
    thermostat = {
        "runtime": {"actualCO2": 900},
        "capabilities": {"actualCO2": 450},
    }
    assert (
        pick_air_quality_value(thermostat, "actualCO2", ("co2",)) == 900
    )


def test_pick_air_quality_fallbacks_to_capabilities():
    thermostat = {
        "capabilities": [
            {"type": "actualVOC", "value": 120},
        ],
    }
    assert (
        pick_air_quality_value(thermostat, "actualVOC", ("voc",)) == 120
    )


def test_extract_remote_sensors_from_list():
    thermostat = {
        "remoteSensors": [{"id": "r1", "name": "Living"}],
    }
    sensors = extract_remote_sensors(thermostat)
    assert len(sensors) == 1
    assert sensors[0]["name"] == "Living"


def test_remote_sensor_values_from_capabilities():
    sensor = {
        "capability": [
            {"type": "temperature", "value": "72.5"},
            {"type": "humidity", "value": "45"},
            {"type": "occupancy", "value": "true"},
        ]
    }
    assert remote_sensor_temperature(sensor) == 72.5
    assert remote_sensor_humidity(sensor) == 45
    assert remote_sensor_occupancy(sensor) is True

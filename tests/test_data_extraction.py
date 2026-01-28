from tests._load_module import load_module

data = load_module("beestat_data", "custom_components/beestat/data.py")


def test_pick_air_quality_prefers_runtime():
    thermostat = {
        "runtime": {"actualCO2": 900},
        "capabilities": {"actualCO2": 450},
    }
    assert (
        data.pick_air_quality_value(thermostat, "actualCO2", ("co2",)) == 900
    )


def test_pick_air_quality_fallbacks_to_capabilities():
    thermostat = {
        "capabilities": [
            {"type": "actualVOC", "value": 120},
        ],
    }
    assert (
        data.pick_air_quality_value(thermostat, "actualVOC", ("voc",)) == 120
    )


def test_extract_remote_sensors_from_list():
    thermostat = {
        "remoteSensors": [{"id": "r1", "name": "Living"}],
    }
    sensors = data.extract_remote_sensors(thermostat)
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
    assert data.remote_sensor_temperature(sensor) == 72.5
    assert data.remote_sensor_humidity(sensor) == 45
    assert data.remote_sensor_occupancy(sensor) is True

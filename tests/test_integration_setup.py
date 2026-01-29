from __future__ import annotations

import pytest

from homeassistant.helpers import entity_registry as er

from custom_components.beestat.const import API_ENDPOINT


@pytest.mark.asyncio
async def test_setup_creates_entities(
    hass, mock_config_entry, enable_custom_integrations, aioclient_mock
):
    """Basic smoke test: integration sets up without throwing and registers sensors."""

    fake_thermostats = [
        {
            "id": "t1",
            "name": "Upstairs",
            "ecobee_thermostat_id": "e1",
            "temperature": 72,
            "humidity": 40,
            "setpoint_heat": 68,
            "weather": {"temperature": 45.3, "humidity_relative": 92},
        }
    ]

    fake_ecobee_thermostats = {
        "e1": {
            "ecobee_thermostat_id": "e1",
            "runtime": {
                "actualCO2": 900,
                "actualVOC": 120,
                "actualAQScore": 85,
                "actualAQAccuracy": 2,
            },
            "remote_sensors": [
                {
                    "id": "ei:0",
                    "name": "Upstairs",
                    "type": "thermostat",
                    "inUse": True,
                    "capability": [
                        {"type": "occupancy", "value": "false"},
                    ],
                },
                {
                    "id": "rs2:100",
                    "name": "Living",
                    "type": "ecobee3_remote_sensor",
                    "inUse": True,
                    "capability": [
                        {"type": "temperature", "value": "712"},
                        {"type": "humidity", "value": "44"},
                        {"type": "occupancy", "value": "true"},
                    ],
                },
            ],
        }
    }

    from pytest_homeassistant_custom_component.test_util.aiohttp import (
        AiohttpClientMockResponse,
    )

    async def _handler(method, url, data):
        # pytest-homeassistant-custom-component may hand us either the payload directly,
        # or a wrapper like {"json": payload}.
        if isinstance(data, dict) and "json" in data and isinstance(data["json"], dict):
            body = data["json"]
        elif isinstance(data, dict):
            body = data
        else:
            body = {}

        resource = body.get("resource")
        api_method = body.get("method")

        if resource == "thermostat" and api_method == "read_id":
            return AiohttpClientMockResponse(
                method=method,
                url=url,
                json={"success": True, "data": fake_thermostats},
            )

        if resource == "ecobee_thermostat" and api_method == "read_id":
            return AiohttpClientMockResponse(
                method=method,
                url=url,
                json={"success": True, "data": fake_ecobee_thermostats},
            )

        if api_method == "sync":
            return AiohttpClientMockResponse(
                method=method,
                url=url,
                json={"success": True, "data": {}},
            )

        return AiohttpClientMockResponse(
            method=method,
            url=url,
            status=400,
            json={
                "success": False,
                "data": {"error_code": 999, "error_message": f"Unexpected {resource}/{api_method}"},
            },
        )

    aioclient_mock.post(API_ENDPOINT, side_effect=_handler)

    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    registry = er.async_get(hass)
    entities = [e for e in registry.entities.values() if e.platform == "beestat"]

    # Base thermostat sensors.
    assert any(e.unique_id == "t1_temperature" for e in entities)
    assert any(e.unique_id == "t1_humidity" for e in entities)

    # Binary sensors should exist (would have caught the EntityDescription subclass issue).
    assert any(e.unique_id == "t1_occupancy" for e in entities)
    assert any(e.unique_id == "t1_in_use" for e in entities)

    # Remote sensor entities should exist (namespaced unique_ids).
    assert any(e.unique_id == "t1:rs2:100_temperature" for e in entities)
    assert any(e.unique_id == "t1:rs2:100_occupancy" for e in entities)
    assert any(e.unique_id == "t1:rs2:100_in_use" for e in entities)

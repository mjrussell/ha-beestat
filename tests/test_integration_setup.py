from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from homeassistant.helpers import entity_registry as er


@pytest.mark.asyncio
async def test_setup_creates_entities(hass, mock_config_entry, enable_custom_integrations):
    """Basic smoke test: integration sets up without throwing and registers sensors."""

    fake_thermostats = [
        {
            "id": "t1",
            "name": "Upstairs",
            "temperature": 72,
            "humidity": 40,
            # Include runtime AQ keys to ensure optional sensors can be created safely.
            "runtime": {"actualCO2": 900, "actualVOC": 120, "actualAQScore": 85, "actualAQAccuracy": 2},
            "remoteSensors": [
                {"id": "r1", "name": "Living", "capability": [{"type": "temperature", "value": "71"}]}
            ],
        }
    ]

    with (
        patch(
            "custom_components.beestat.api.BeestatApiClient.async_validate_key",
            new=AsyncMock(return_value=None),
        ),
        patch(
            "custom_components.beestat.api.BeestatApiClient.request",
            new=AsyncMock(return_value=fake_thermostats),
        ),
    ):
        mock_config_entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    registry = er.async_get(hass)
    entities = [e for e in registry.entities.values() if e.platform == "beestat"]

    # We should at least have the base thermostat temperature/humidity sensors.
    assert any(e.unique_id == "t1_temperature" for e in entities)
    assert any(e.unique_id == "t1_humidity" for e in entities)

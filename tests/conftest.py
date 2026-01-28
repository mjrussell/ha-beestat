from __future__ import annotations

import pytest

from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant

from custom_components.beestat.const import CONF_API_KEY, DOMAIN


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    return MockConfigEntry(domain=DOMAIN, data={CONF_API_KEY: "test-key"})


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable custom integrations for tests."""
    return


@pytest.fixture
async def setup_integration(hass: HomeAssistant, mock_config_entry: MockConfigEntry) -> MockConfigEntry:
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    return mock_config_entry

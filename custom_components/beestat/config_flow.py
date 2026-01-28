"""Config flow for Beestat integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import voluptuous as vol

from .api import BeestatApiClient, BeestatApiError
from .const import (
    CONF_API_KEY,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL_MINUTES,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


async def _validate_api_key(hass: HomeAssistant, api_key: str) -> None:
    session = async_get_clientsession(hass)
    client = BeestatApiClient(api_key, session, _LOGGER)
    await client.async_validate_key()


class BeestatConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Beestat."""

    VERSION = 1

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        return BeestatOptionsFlowHandler(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            api_key = user_input[CONF_API_KEY]
            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()

            try:
                await _validate_api_key(self.hass, api_key)
            except BeestatApiError as err:
                # Note: HA's UI log viewer often hides DEBUG; log auth failures at WARNING so they show up.
                _LOGGER.warning("Beestat API key validation failed: %s", err)
                errors["base"] = "invalid_auth"
            except Exception:  # noqa: BLE001 - surfaced to user as unknown
                _LOGGER.exception("Unexpected error validating Beestat API key")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title="Beestat", data={CONF_API_KEY: api_key})

        data_schema = vol.Schema({vol.Required(CONF_API_KEY): str})
        return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)


class BeestatOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle Beestat options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = self._config_entry.options.get(
            CONF_UPDATE_INTERVAL,
            DEFAULT_UPDATE_INTERVAL_MINUTES,
        )
        data_schema = vol.Schema(
            {
                vol.Optional(CONF_UPDATE_INTERVAL, default=current): vol.All(
                    vol.Coerce(int), vol.Range(min=1)
                )
            }
        )
        return self.async_show_form(step_id="init", data_schema=data_schema)

"""Constants for the Beestat integration."""
from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "beestat"

CONF_API_KEY = "api_key"
CONF_UPDATE_INTERVAL = "update_interval"

DEFAULT_UPDATE_INTERVAL_SECONDS = 300
DEFAULT_UPDATE_INTERVAL_MINUTES = DEFAULT_UPDATE_INTERVAL_SECONDS // 60

API_ENDPOINT = "https://api.beestat.io/"

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]

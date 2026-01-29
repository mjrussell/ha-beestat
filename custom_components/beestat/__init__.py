"""The Beestat integration."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import BeestatApiClient, BeestatApiError
from .const import (
    CONF_API_KEY,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL_MINUTES,
    DOMAIN,
    PLATFORMS,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Beestat from a config entry."""
    session = async_get_clientsession(hass)
    client = BeestatApiClient(entry.data[CONF_API_KEY], session, _LOGGER)

    # Sync is heavier than polling. We poll frequently (default 5 min) but only
    # request Beestat/ecobee sync on a slower cadence (default 1 hour).
    sync_interval = timedelta(hours=1)

    async def _async_update_data():
        try:
            now = datetime.now(timezone.utc)  # noqa: UP017
            last_sync: datetime | None = hass.data.get(DOMAIN, {}).get(entry.entry_id, {}).get("last_sync")
            if last_sync is None or (now - last_sync) >= sync_interval:
                _LOGGER.debug("Triggering Beestat sync (interval=%s)", sync_interval)
                await client.async_sync_thermostats()
                await client.async_sync_sensors()
                hass.data.setdefault(DOMAIN, {}).setdefault(entry.entry_id, {})["last_sync"] = now

            thermostats = await client.async_get_thermostats()
            ecobee_thermostats = await client.async_get_ecobee_thermostats()
        except BeestatApiError as err:
            raise UpdateFailed(str(err)) from err

        if not thermostats:
            raise UpdateFailed("No thermostat data returned from Beestat API")

        # Attach ecobee runtime (contains air quality fields) onto the thermostat dict.
        for thermostat in thermostats:
            ecobee_id = thermostat.get("ecobee_thermostat_id")
            if ecobee_id is None:
                continue
            ecobee = ecobee_thermostats.get(str(ecobee_id))
            if isinstance(ecobee, dict):
                runtime = ecobee.get("runtime")
                if isinstance(runtime, dict):
                    thermostat["runtime"] = runtime

                remote_sensors = ecobee.get("remote_sensors")
                if isinstance(remote_sensors, list):
                    thermostat["remote_sensors"] = remote_sensors

        return thermostats

    update_minutes = entry.options.get(
        CONF_UPDATE_INTERVAL,
        DEFAULT_UPDATE_INTERVAL_MINUTES,
    )
    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
        update_method=_async_update_data,
        update_interval=timedelta(minutes=update_minutes),
    )

    try:
        await coordinator.async_config_entry_first_refresh()
    except UpdateFailed as err:
        raise ConfigEntryNotReady from err

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "client": client,
        "coordinator": coordinator,
        "last_sync": hass.data.get(DOMAIN, {}).get(entry.entry_id, {}).get("last_sync"),
    }

    entry.async_on_unload(entry.add_update_listener(_async_options_updated))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)

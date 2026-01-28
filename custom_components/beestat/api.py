"""Beestat API client."""
from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any

import aiohttp

from .const import API_ENDPOINT


class BeestatApiError(Exception):
    """Beestat API error."""


def build_payload(
    api_key: str,
    resource: str,
    method: str,
    arguments: dict[str, Any] | None,
) -> dict[str, Any]:
    """Build a Beestat API payload."""
    return {
        "api_key": api_key,
        "resource": resource,
        "method": method,
        "arguments": json.dumps(arguments or {}),
    }


@dataclass
class BeestatApiClient:
    """Simple Beestat API client."""

    api_key: str
    session: aiohttp.ClientSession
    logger: Any

    async def request(self, resource: str, method: str, arguments: dict[str, Any] | None = None) -> Any:
        """POST to the Beestat API and return JSON data."""
        payload = build_payload(self.api_key, resource, method, arguments)

        try:
            async with self.session.post(API_ENDPOINT, json=payload) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise BeestatApiError(f"HTTP {resp.status}: {text}")
                data = await resp.json()
        except aiohttp.ClientError as err:
            raise BeestatApiError(f"Client error: {err}") from err
        except aiohttp.ContentTypeError as err:
            raise BeestatApiError("Invalid response from Beestat API") from err

        if isinstance(data, dict):
            if data.get("error"):
                raise BeestatApiError(str(data["error"]))
            if data.get("success") is False:
                message = data.get("error") or data.get("data") or "Beestat API returned success=false"
                raise BeestatApiError(str(message))
            if "success" in data:
                return data.get("data")

        return data

    async def async_get_thermostats(self) -> list[dict[str, Any]]:
        """Fetch thermostat data from Beestat."""
        data = await self.request("thermostat", "read", {})
        return _normalize_thermostats(data)

    async def async_validate_key(self) -> None:
        """Validate the API key by attempting a lightweight call."""
        await self.request("thermostat", "read", {})


def _normalize_thermostats(data: Any) -> list[dict[str, Any]]:
    """Normalize thermostat data into a list of dicts."""
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        for key in ("thermostats", "thermostat", "data", "items"):
            value = data.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
        if all(isinstance(v, dict) for v in data.values()):
            return list(data.values())
    return []

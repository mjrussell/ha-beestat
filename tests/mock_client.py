"""Mock Beestat API client for testing."""
from __future__ import annotations

from typing import Any


class BeestatApiError(Exception):
    """Beestat API error."""


class MockBeestatApiClient:
    """Mock Beestat API client for testing without network calls.

    Usage:
        client = MockBeestatApiClient(api_key="test_key")
        client.set_thermostats_response([{"id": "t1", "name": "Test"}])
        client.set_error_response("API key invalid")

    This class mirrors the interface of BeestatApiClient but doesn't require
    network access or Home Assistant dependencies.
    """

    def __init__(self, api_key: str = "test_key") -> None:
        """Initialize mock client."""
        self.api_key = api_key
        self._thermostats_response: list[dict[str, Any]] | None = None
        self._error_response: str | None = None
        self._call_count: int = 0
        self._last_request: dict[str, Any] | None = None

    def set_thermostats_response(self, thermostats: list[dict[str, Any]]) -> None:
        """Set the response for async_get_thermostats."""
        self._thermostats_response = thermostats

    def set_error_response(self, error_message: str) -> None:
        """Set an error to raise on the next request."""
        self._error_response = error_message

    def reset(self) -> None:
        """Reset call count and last request."""
        self._call_count = 0
        self._last_request = None
        self._error_response = None

    @property
    def call_count(self) -> int:
        """Get the number of requests made."""
        return self._call_count

    @property
    def last_request(self) -> dict[str, Any] | None:
        """Get the last request payload."""
        return self._last_request

    async def request(self, resource: str, method: str, arguments: dict[str, Any] | None = None) -> Any:
        """Return mock data based on configuration."""
        self._call_count += 1
        self._last_request = {"resource": resource, "method": method, "arguments": arguments}

        if self._error_response:
            raise BeestatApiError(self._error_response)

        if resource == "thermostat" and method == "read_id":
            if self._thermostats_response is not None:
                return self._thermostats_response
            return []

        return None

    async def async_get_thermostats(self) -> list[dict[str, Any]]:
        """Return mock thermostat data."""
        return await self.request("thermostat", "read_id")

    async def async_validate_key(self) -> None:
        """Validate key - mock version."""
        await self.request("thermostat", "read_id")

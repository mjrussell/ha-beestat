"""Tests for the mock API client - standalone without HA dependencies."""
from __future__ import annotations

import pytest

from tests.mock_client import MockBeestatApiClient, BeestatApiError


@pytest.mark.asyncio
async def test_mock_client_returns_configured_thermostats():
    """Test that mock client returns configured thermostat data."""
    client = MockBeestatApiClient()
    thermostats = [{"id": "t1", "name": "Upstairs", "temperature": 72}]
    client.set_thermostats_response(thermostats)

    result = await client.async_get_thermostats()

    assert result == thermostats
    assert client.call_count == 1


@pytest.mark.asyncio
async def test_mock_client_default_empty_list():
    """Test that mock client returns empty list by default."""
    client = MockBeestatApiClient()

    result = await client.async_get_thermostats()

    assert result == []


@pytest.mark.asyncio
async def test_mock_client_error_response():
    """Test that mock client raises error when configured."""
    client = MockBeestatApiClient()
    client.set_error_response("API key invalid")

    with pytest.raises(BeestatApiError, match="API key invalid"):
        await client.async_get_thermostats()


@pytest.mark.asyncio
async def test_mock_client_tracks_last_request():
    """Test that mock client tracks the last request."""
    client = MockBeestatApiClient()
    client.set_thermostats_response([{"id": "t1"}])

    await client.request("thermostat", "read_id", {"limit": 10})

    assert client.last_request == {
        "resource": "thermostat",
        "method": "read_id",
        "arguments": {"limit": 10},
    }


@pytest.mark.asyncio
async def test_mock_client_call_count():
    """Test that mock client tracks call count."""
    client = MockBeestatApiClient()
    client.set_thermostats_response([])

    assert client.call_count == 0
    await client.async_get_thermostats()
    assert client.call_count == 1
    await client.async_get_thermostats()
    assert client.call_count == 2


@pytest.mark.asyncio
async def test_mock_client_reset():
    """Test that mock client can be reset."""
    client = MockBeestatApiClient()
    client.set_thermostats_response([{"id": "t1"}])
    await client.async_get_thermostats()

    client.reset()

    assert client.call_count == 0
    assert client.last_request is None

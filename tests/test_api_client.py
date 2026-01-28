from tests._load_module import load_module

api = load_module("custom_components.beestat.api", "custom_components/beestat/api.py")


def test_build_payload_includes_required_fields():
    payload = api.build_payload("key123", "thermostat", "read", {"limit": 1})
    assert payload == {
        "api_key": "key123",
        "resource": "thermostat",
        "method": "read",
        "arguments": "{\"limit\": 1}",
    }


def test_build_payload_omits_arguments_when_none():
    payload = api.build_payload("key123", "thermostat", "read", None)
    assert "arguments" not in payload

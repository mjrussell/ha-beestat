from custom_components.beestat.api import build_payload


def test_build_payload_includes_required_fields():
    payload = build_payload("key123", "thermostat", "read", {"limit": 1})
    assert payload == {
        "api_key": "key123",
        "resource": "thermostat",
        "method": "read",
        "arguments": "{\"limit\": 1}",
    }


def test_build_payload_defaults_arguments():
    payload = build_payload("key123", "thermostat", "read", None)
    assert payload["arguments"] == "{}"

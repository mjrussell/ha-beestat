# Beestat Home Assistant Integration

[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Integration-41BDF5.svg)](https://www.home-assistant.io/)
[![CI](https://github.com/mjrussell/ha-beestat/actions/workflows/ci.yml/badge.svg)](https://github.com/mjrussell/ha-beestat/actions/workflows/ci.yml)

[![Add to Home Assistant](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=beestat)

A custom Home Assistant integration that connects to the Beestat API and creates devices and sensors for each thermostat and remote sensor (room).

## Install via HACS (manual repo)
1. In HACS, go to **Integrations**.
2. Open the menu (three dots) and choose **Custom repositories**.
3. Add the repository URL `https://github.com/mjrussell/ha-beestat` and select **Integration**.
4. Install **Beestat**.
5. Restart Home Assistant.

## Configuration
1. In Home Assistant, go to **Settings -> Devices & Services -> Add Integration**.
2. Search for **Beestat**.
3. Enter your Beestat API key.

## Options
- Update interval (minutes), default 5.

## Entities created
Per thermostat, the integration creates sensors for:
- Temperature
- Humidity
- HVAC mode (if available)
- HVAC state (if available)
- CO2 (if present in the API response)
- VOC in ppb (if present in the API response)
- Air Quality Score (if present in the API response)
- Air Quality Accuracy (if present in the API response)

Per remote sensor (room), the integration creates:
- Temperature
- Humidity (if present)
- Occupancy (if present)

## Development notes
- API client uses a POST to `https://api.beestat.io/` with `api_key`, `resource`, `method`, and `arguments`.
- Data is fetched with `thermostat/read` and normalized into a list of thermostat dictionaries.
- Polling interval defaults to 5 minutes (configurable via Options).

## Security / secrets
- Your Beestat API key is stored by Home Assistant in the config entry (standard HA behavior).
- Do not commit real API keys to this repository.

## Local testing
1. Copy `custom_components/beestat` into your Home Assistant config directory.
2. Restart Home Assistant.
3. Add the **Beestat** integration and enter your API key.

### Dev environment (optional)
This repo includes a simple CI workflow (hassfest + ruff + pytest). If you want to run the same checks locally, use a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
ruff check .
pytest -q
```


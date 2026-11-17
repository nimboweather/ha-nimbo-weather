"""Config flow and entities in a test Home Assistant (pytest-homeassistant-custom-component)."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import patch

import pytest

pytest.importorskip("pytest_homeassistant_custom_component")

from homeassistant import config_entries  # noqa: E402
from homeassistant.const import CONF_API_KEY, CONF_LATITUDE, CONF_LONGITUDE, CONF_NAME  # noqa: E402
from homeassistant.core import HomeAssistant  # noqa: E402
from homeassistant.data_entry_flow import FlowResultType  # noqa: E402
from pytest_homeassistant_custom_component.common import MockConfigEntry  # noqa: E402

from custom_components.nimbo_weather.const import CONF_UPDATE_MINUTES, DOMAIN  # noqa: E402

BASE = "https://nimboweather.com"
KEY = "nimbo_test"
USAGE = {
    "key_prefix": "nimbo_te",
    "plan": "free",
    "monthly_quota": 20000,
    "created": "2026-11-13",
    "used_this_month": 1,
    "resets": 1764547200,
}
NOW = datetime(2026, 11, 12, 17, 17, tzinfo=UTC)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


async def test_flow_defaults_to_home_and_creates_entry(hass: HomeAssistant, aioclient_mock, nowcast_answer) -> None:
    hass.config.latitude, hass.config.longitude, hass.config.location_name = 48.85, 2.35, "Home"
    aioclient_mock.get(f"{BASE}/v1/keys/me", json=USAGE)
    aioclient_mock.get(f"{BASE}/v1/nowcast", json=nowcast_answer)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.FORM and result["step_id"] == "user"
    defaults = {str(k): k.default() for k in result["data_schema"].schema if callable(getattr(k, "default", None))}
    assert defaults == {CONF_NAME: "Home", CONF_LATITUDE: 48.85, CONF_LONGITUDE: 2.35}

    with patch("custom_components.nimbo_weather.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_API_KEY: KEY, CONF_NAME: "Home", CONF_LATITUDE: 48.85, CONF_LONGITUDE: 2.35}
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_API_KEY: KEY, CONF_LATITUDE: 48.85, CONF_LONGITUDE: 2.35}
    assert aioclient_mock.mock_calls[0][3]["X-API-Key"] == KEY


@pytest.mark.parametrize(
    ("status", "body", "error"),
    [
        (401, {"error": "invalid_api_key", "message": "x"}, "invalid_auth"),
        (404, {"error": "out_of_coverage", "message": "x"}, "out_of_coverage"),
        (429, {"error": "monthly_quota_exceeded", "message": "x"}, "rate_limited"),
        (500, None, "cannot_connect"),
    ],
)
async def test_flow_errors(hass: HomeAssistant, aioclient_mock, status, body, error) -> None:
    aioclient_mock.get(f"{BASE}/v1/keys/me", json=USAGE)
    aioclient_mock.get(f"{BASE}/v1/nowcast", status=status, json=body)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_API_KEY: KEY, CONF_NAME: "X", CONF_LATITUDE: 10.0, CONF_LONGITUDE: 10.0}
    )
    assert result["type"] is FlowResultType.FORM and result["errors"] == {"base": error}


async def test_entities(hass: HomeAssistant, aioclient_mock, nowcast_answer) -> None:
    aioclient_mock.get(f"{BASE}/v1/nowcast", json=nowcast_answer)
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Home",
        unique_id="48.8500_2.3500",
        data={CONF_API_KEY: KEY, CONF_LATITUDE: 48.85, CONF_LONGITUDE: 2.35},
    )
    entry.add_to_hass(hass)
    with patch("custom_components.nimbo_weather.coordinator.dt_util.utcnow", return_value=NOW):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert hass.states.get("sensor.home_precipitation_now").state == "0.0"
    rain = hass.states.get("sensor.home_rain_starts_in")
    assert rain.state == "23" and rain.attributes["summary"].startswith("Light rain")
    assert "Nimbo Weather" in rain.attributes["attribution"] and "Radar credit line" in rain.attributes["attribution"]
    assert hass.states.get("sensor.home_rain_stops_in").state == "unknown"
    assert float(hass.states.get("sensor.home_precipitation_next_hour").state) == pytest.approx(0.8)
    assert hass.states.get("sensor.home_forecast_issued").state == "2026-11-12T17:10:00+00:00"
    assert hass.states.get("binary_sensor.home_rain_within_30_minutes").state == "on"
    params = aioclient_mock.mock_calls[0][1].query
    assert params["lat"] == "48.8500" and params["step"] == "5"

    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_invalid_key_starts_reauth(hass: HomeAssistant, aioclient_mock) -> None:
    aioclient_mock.get(f"{BASE}/v1/nowcast", status=401, json={"error": "invalid_api_key", "message": "x"})
    entry = MockConfigEntry(domain=DOMAIN, title="Home", data={CONF_API_KEY: KEY, CONF_LATITUDE: 1.0, CONF_LONGITUDE: 1.0})
    entry.add_to_hass(hass)
    assert not await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is config_entries.ConfigEntryState.SETUP_ERROR
    flows = hass.config_entries.flow.async_progress()
    assert [f["context"]["source"] for f in flows] == ["reauth"]


async def test_quota_backs_off(hass: HomeAssistant, aioclient_mock, nowcast_answer) -> None:
    aioclient_mock.get(f"{BASE}/v1/nowcast", json=nowcast_answer)
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Home",
        data={CONF_API_KEY: KEY, CONF_LATITUDE: 1.0, CONF_LONGITUDE: 1.0},
        options={CONF_UPDATE_MINUTES: 10},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    coordinator = entry.runtime_data
    assert coordinator.update_interval.total_seconds() == 600
    aioclient_mock.clear_requests()
    aioclient_mock.get(
        f"{BASE}/v1/nowcast",
        status=429,
        json={"error": "monthly_quota_exceeded", "message": "x"},
        headers={"Retry-After": "1209600"},
    )
    await coordinator.async_refresh()
    assert not coordinator.last_update_success
    assert coordinator.update_interval.total_seconds() == 6 * 3600


async def test_options_flow(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(domain=DOMAIN, title="Home", data={CONF_API_KEY: KEY, CONF_LATITUDE: 1.0, CONF_LONGITUDE: 1.0})
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    with patch("custom_components.nimbo_weather.async_setup_entry", return_value=True):
        result = await hass.config_entries.options.async_configure(result["flow_id"], {CONF_UPDATE_MINUTES: 15})
    assert result["type"] is FlowResultType.CREATE_ENTRY and entry.options == {CONF_UPDATE_MINUTES: 15}

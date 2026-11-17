"""The mapping from a /v1/nowcast answer to entity values (pure Python)."""

from __future__ import annotations

import importlib.util
import pathlib
import sys
from datetime import UTC, datetime

import pytest

# Loaded by path so this test runs without Home Assistant installed.
_spec = importlib.util.spec_from_file_location(
    "nimbo_data", pathlib.Path(__file__).parents[1] / "custom_components/nimbo_weather/data.py"
)
data = importlib.util.module_from_spec(_spec)
sys.modules["nimbo_data"] = data
_spec.loader.exec_module(data)

NOW = datetime(2026, 11, 12, 17, 17, tzinfo=UTC)


def test_rain_coming(nowcast_answer):
    d = data.from_nowcast(nowcast_answer, NOW)
    assert d.has_radar and not d.stale
    assert d.precipitation_now == 0.0  # the observation
    assert d.minutes_until_rain == 23 and d.minutes_until_dry is None
    assert d.rain_soon is True
    assert d.issue_time == datetime(2026, 11, 12, 17, 10, tzinfo=UTC)
    # 1.2 mm/h from entries 17:40 to 18:15 (8 steps of 5 min) inside (17:17, 18:17]: 1.2 * 40/60 = 0.8 mm
    assert d.precipitation_next_60 == pytest.approx(0.8)
    assert d.summary.startswith("Light rain") and d.attribution == ["Radar credit line"]


def test_rain_later_than_30_min(nowcast_answer):
    nowcast_answer["summary"]["minutes_until_rain"] = 45
    assert data.from_nowcast(nowcast_answer, NOW).rain_soon is False


def test_raining_now(nowcast_answer):
    nowcast_answer["summary"].update(rain_now=True, minutes_until_rain=0, rain_starts_at="2026-11-12T17:10:00Z")
    nowcast_answer["observed_now"] = {"time": "2026-11-12T17:15:00Z", "precip_mm_h": 2.4}
    d = data.from_nowcast(nowcast_answer, NOW)
    assert d.precipitation_now == 2.4 and d.minutes_until_rain == 0 and d.rain_soon is True
    assert d.minutes_until_dry == 63  # 17:17 -> 18:20
    nowcast_answer["summary"]["rain_ends_at"] = None
    d = data.from_nowcast(nowcast_answer, NOW)
    assert d.minutes_until_dry is None and d.rain_lasts_past_forecast


def test_no_rain(nowcast_answer):
    nowcast_answer["summary"].update(
        rain_now=False,
        rain_starts_at=None,
        rain_ends_at=None,
        minutes_until_rain=None,
        text="No rain expected in the next 3 hours",
    )
    for m in nowcast_answer["minutely"]:
        m["precip_mm_h"] = 0.0
    d = data.from_nowcast(nowcast_answer, NOW)
    assert d.minutes_until_rain is None and d.minutes_until_dry is None and d.rain_soon is False
    assert d.precipitation_next_60 == 0.0


def test_now_interpolated_without_observation(nowcast_answer):
    nowcast_answer["observed_now"] = None
    nowcast_answer["minutely"][0]["precip_mm_h"] = 1.0  # 17:15
    nowcast_answer["minutely"][1]["precip_mm_h"] = 2.0  # 17:20
    assert data.from_nowcast(nowcast_answer, NOW).precipitation_now == pytest.approx(1.4)


def test_no_radar(nowcast_answer):
    nowcast_answer.update(coverage="no_radar", summary=None, observed_now=None, radar_source=None)
    for m in nowcast_answer["minutely"]:
        m.update(precip_mm_h=None, precip_probability=None)
    d = data.from_nowcast(nowcast_answer, NOW)
    assert not d.has_radar and d.precipitation_now is None and d.precipitation_next_60 is None
    assert d.minutes_until_rain is None and d.rain_soon is None and d.summary is None


def test_stale(nowcast_answer):
    nowcast_answer["stale"] = True
    nowcast_answer["summary"] = {
        "text": "Forecast delayed: radar data is 27 min old",
        "rain_now": None,
        "rain_starts_at": None,
        "rain_ends_at": None,
        "minutes_until_rain": None,
        "max_intensity": None,
        "now_source": None,
    }
    d = data.from_nowcast(nowcast_answer, NOW)
    assert d.stale and d.rain_soon is None and d.minutes_until_rain is None
    assert d.summary.startswith("Forecast delayed")

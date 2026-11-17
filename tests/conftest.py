"""Shared fixtures. The integration tests need pytest-homeassistant-custom-component (see requirements_test.txt)."""

from __future__ import annotations

import pytest

NOWCAST = {
    "lat": 48.85,
    "lon": 2.35,
    "issue_time": "2026-11-12T17:10:00Z",
    "data_age_s": 420,
    "stale": False,
    "notice": None,
    "coverage": "radar",
    "radar_source": "opera",
    "summary": {
        "text": "Light rain starting in 23 min, for about 40 min",
        "rain_now": False,
        "rain_starts_at": "2026-11-12T17:40:00Z",
        "rain_ends_at": "2026-11-12T18:20:00Z",
        "minutes_until_rain": 23,
        "max_intensity": "light",
        "now_source": "radar",
    },
    "minutely": [
        {
            "time": f"2026-11-12T{17 + (10 + 5 * i) // 60}:{(10 + 5 * i) % 60:02d}:00Z",
            "precip_mm_h": 1.2 if 30 <= 5 * i < 70 else 0.0,
            "precip_probability": 0.8 if 30 <= 5 * i < 70 else 0.0,
            "precip_probability_1mm_h": 0.0,
            "precip_probability_5mm_h": 0.0,
            "precip_type": "rain",
        }
        for i in range(1, 37)
    ],
    "observed_now": {"time": "2026-11-12T17:15:00Z", "precip_mm_h": 0.0},
    "horizon_skill": [],
    "horizon_skill_label": None,
    "confidence_notes": [],
    "grid": "EUROPE_2K",
    "attribution": ["Radar credit line"],
}


@pytest.fixture
def nowcast_answer() -> dict:
    import copy

    return copy.deepcopy(NOWCAST)

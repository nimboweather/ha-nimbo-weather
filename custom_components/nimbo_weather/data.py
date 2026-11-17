"""From a /v1/nowcast answer to the values the entities show. Pure Python (no Home Assistant import), so it can be
tested on its own."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

RAIN_MM_H = 0.2  # the API's rain threshold


def parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    return datetime.fromisoformat(value[:-1] + "+00:00" if value.endswith("Z") else value)


@dataclass
class NimboData:
    """What the sensors read. None means unknown (no radar at the point, or a late forecast)."""

    issue_time: datetime | None
    has_radar: bool
    stale: bool
    precipitation_now: float | None  # mm/h
    minutes_until_rain: int | None  # 0 when it rains now; None when no rain is expected in the forecast
    minutes_until_dry: int | None  # while it rains: until it stops; None when dry or past the forecast
    precipitation_next_60: float | None  # mm over the next 60 minutes
    rain_soon: bool | None  # rain now or within rain_soon_minutes
    summary: str | None
    rain_lasts_past_forecast: bool = False
    notice: str | None = None
    data_age_s: int | None = None
    attribution: list[str] = field(default_factory=list)


def _minutes_between(start: datetime, end: datetime) -> int:
    return max(0, math.ceil((end - start).total_seconds() / 60))


def _rate_now(minutely: list[dict[str, Any]], now: datetime) -> float | None:
    """The forecast rate at ``now``, linearly between the two entries around it."""
    points = [(t, m.get("precip_mm_h")) for m in minutely if (t := parse_time(m.get("time"))) is not None]
    points = [(t, float(r)) for t, r in points if r is not None]
    if not points:
        return None
    if now <= points[0][0]:
        return points[0][1]
    for (t0, r0), (t1, r1) in zip(points, points[1:], strict=False):
        if t0 <= now <= t1:
            span = (t1 - t0).total_seconds()
            return round(r0 + (r1 - r0) * ((now - t0).total_seconds() / span if span else 0.0), 2)
    return points[-1][1]


def _amount_next(minutely: list[dict[str, Any]], now: datetime, minutes: int) -> float | None:
    """mm in (now, now + minutes]: each entry's rate held over the step before it."""
    end = now + timedelta(minutes=minutes)
    total = 0.0
    seen = False
    prev: datetime | None = None
    for m in minutely:
        t = parse_time(m.get("time"))
        rate = m.get("precip_mm_h")
        if t is None:
            continue
        start = prev if prev is not None else t - timedelta(minutes=5)
        prev = t
        lo, hi = max(start, now), min(t, end)
        if hi <= lo:
            continue
        if rate is None:
            return None
        seen = True
        total += float(rate) * (hi - lo).total_seconds() / 3600
    return round(total, 2) if seen else None


def from_nowcast(answer: dict[str, Any], now: datetime, rain_soon_minutes: int = 30) -> NimboData:
    """Map a /v1/nowcast answer (asked with step=5) to the entity values, as seen at ``now`` (timezone-aware)."""
    minutely: list[dict[str, Any]] = answer.get("minutely") or []
    has_radar = answer.get("coverage", "radar") == "radar"
    stale = bool(answer.get("stale"))
    summary: dict[str, Any] = answer.get("summary") or {}
    observed = answer.get("observed_now")

    precipitation_now: float | None = None
    if has_radar:
        if observed and observed.get("precip_mm_h") is not None:
            precipitation_now = float(observed["precip_mm_h"])
        else:
            precipitation_now = _rate_now(minutely, now)

    minutes_until_rain: int | None = None
    minutes_until_dry: int | None = None
    lasts_past = False
    rain_now = summary.get("rain_now")
    if has_radar and not stale and rain_now is not None:
        starts = parse_time(summary.get("rain_starts_at"))
        ends = parse_time(summary.get("rain_ends_at"))
        if rain_now:
            minutes_until_rain = 0
            minutes_until_dry = _minutes_between(now, ends) if ends else None
            lasts_past = ends is None
        elif summary.get("minutes_until_rain") is not None:
            minutes_until_rain = int(summary["minutes_until_rain"])
        elif starts is not None:
            minutes_until_rain = _minutes_between(now, starts)

    rain_soon: bool | None = None
    if has_radar and not stale and rain_now is not None:
        rain_soon = minutes_until_rain is not None and minutes_until_rain <= rain_soon_minutes

    return NimboData(
        issue_time=parse_time(answer.get("issue_time")),
        has_radar=has_radar,
        stale=stale,
        precipitation_now=precipitation_now,
        minutes_until_rain=minutes_until_rain,
        minutes_until_dry=minutes_until_dry,
        precipitation_next_60=_amount_next(minutely, now, 60) if has_radar else None,
        rain_soon=rain_soon,
        summary=(answer.get("summary") or {}).get("text"),
        rain_lasts_past_forecast=lasts_past,
        notice=answer.get("notice"),
        data_age_s=answer.get("data_age_s"),
        attribution=list(answer.get("attribution") or []),
    )

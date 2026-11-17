"""Sensors: rain now, minutes until rain starts / stops, rain in the next hour, forecast issue time."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UnitOfPrecipitationDepth, UnitOfTime, UnitOfVolumetricFlux
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import NimboConfigEntry
from .data import NimboData
from .entity import NimboEntity


@dataclass(frozen=True, kw_only=True)
class NimboSensorDescription(SensorEntityDescription):
    value_fn: Callable[[NimboData], float | int | datetime | None]


SENSORS: tuple[NimboSensorDescription, ...] = (
    NimboSensorDescription(
        key="precipitation_now",
        device_class=SensorDeviceClass.PRECIPITATION_INTENSITY,
        native_unit_of_measurement=UnitOfVolumetricFlux.MILLIMETERS_PER_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda d: d.precipitation_now,
    ),
    NimboSensorDescription(
        key="minutes_until_rain",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        value_fn=lambda d: d.minutes_until_rain,
    ),
    NimboSensorDescription(
        key="minutes_until_dry",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        value_fn=lambda d: d.minutes_until_dry,
    ),
    NimboSensorDescription(
        key="precipitation_next_hour",
        device_class=SensorDeviceClass.PRECIPITATION,
        native_unit_of_measurement=UnitOfPrecipitationDepth.MILLIMETERS,
        suggested_display_precision=1,
        value_fn=lambda d: d.precipitation_next_60,
    ),
    NimboSensorDescription(
        key="issue_time",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda d: d.issue_time,
    ),
)


async def async_setup_entry(hass: HomeAssistant, entry: NimboConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = entry.runtime_data
    async_add_entities(NimboSensor(coordinator, description) for description in SENSORS)


class NimboSensor(NimboEntity, SensorEntity):
    entity_description: NimboSensorDescription

    def __init__(self, coordinator: Any, description: NimboSensorDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> float | int | datetime | None:
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        d = self.coordinator.data
        key = self.entity_description.key
        if key == "minutes_until_rain":
            return {"summary": d.summary, "stale": d.stale, "radar_coverage": d.has_radar, "notice": d.notice}
        if key == "minutes_until_dry":
            return {"rain_lasts_past_forecast": d.rain_lasts_past_forecast}
        if key == "issue_time":
            return {"data_age_s": d.data_age_s, "stale": d.stale}
        return None

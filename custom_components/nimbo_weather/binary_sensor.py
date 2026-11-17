"""Binary sensor: rain now or expected within 30 minutes."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import NimboConfigEntry
from .entity import NimboEntity


async def async_setup_entry(hass: HomeAssistant, entry: NimboConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    async_add_entities([NimboRainSoon(entry.runtime_data)])


class NimboRainSoon(NimboEntity, BinarySensorEntity):
    def __init__(self, coordinator: Any) -> None:
        super().__init__(coordinator, "rain_soon")

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.data.rain_soon

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        d = self.coordinator.data
        return {"minutes_until_rain": d.minutes_until_rain, "summary": d.summary}

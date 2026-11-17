"""Polls the point forecast every few minutes (5 by default)."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, CONF_LATITUDE, CONF_LONGITUDE
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import NimboApi, NimboApiError, NimboAuthError, NimboRateLimited
from .const import CONF_UPDATE_MINUTES, DEFAULT_UPDATE_MINUTES, DOMAIN, RAIN_SOON_MINUTES
from .data import NimboData, from_nowcast

_LOGGER = logging.getLogger(__name__)

# After a 429, wait as the API asks, within these bounds (the monthly quota's Retry-After runs to the month's end).
MIN_BACKOFF = timedelta(minutes=5)
MAX_BACKOFF = timedelta(hours=6)


class NimboCoordinator(DataUpdateCoordinator[NimboData]):
    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.normal_interval = timedelta(minutes=entry.options.get(CONF_UPDATE_MINUTES, DEFAULT_UPDATE_MINUTES))
        super().__init__(hass, _LOGGER, name=f"{DOMAIN} {entry.title}", update_interval=self.normal_interval, config_entry=entry)
        self.api = NimboApi(async_get_clientsession(hass), entry.data[CONF_API_KEY])
        self.latitude: float = entry.data[CONF_LATITUDE]
        self.longitude: float = entry.data[CONF_LONGITUDE]

    async def _async_update_data(self) -> NimboData:
        try:
            answer = await self.api.nowcast(self.latitude, self.longitude)
        except NimboAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except NimboRateLimited as err:
            wait = timedelta(seconds=err.retry_after or 0)
            self.update_interval = min(max(wait, MIN_BACKOFF), MAX_BACKOFF)
            raise UpdateFailed(f"Rate limited, next try in {self.update_interval}: {err}") from err
        except NimboApiError as err:
            raise UpdateFailed(str(err)) from err
        self.update_interval = self.normal_interval
        return from_nowcast(answer, dt_util.utcnow(), RAIN_SOON_MINUTES)

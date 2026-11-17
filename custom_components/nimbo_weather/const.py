"""Constants for the Nimbo Weather integration."""

from __future__ import annotations

DOMAIN = "nimbo_weather"
API_BASE_URL = "https://nimboweather.com"

CONF_UPDATE_MINUTES = "update_minutes"
DEFAULT_UPDATE_MINUTES = 5
MIN_UPDATE_MINUTES = 5
MAX_UPDATE_MINUTES = 60

RAIN_SOON_MINUTES = 30
ATTRIBUTION = "Rain forecast: Nimbo Weather (nimboweather.com)"

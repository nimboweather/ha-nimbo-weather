"""Config flow: an API key and a place (Home Assistant's home by default); options: the update interval."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_API_KEY, CONF_LATITUDE, CONF_LONGITUDE, CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import NimboApi, NimboApiError, NimboAuthError, NimboOutOfCoverage, NimboRateLimited
from .const import CONF_UPDATE_MINUTES, DEFAULT_UPDATE_MINUTES, DOMAIN, MAX_UPDATE_MINUTES, MIN_UPDATE_MINUTES


class NimboConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def _validate(self, api_key: str, lat: float | None, lon: float | None) -> str | None:
        """None when fine, else an error key. Checks the key (not counted), then the place (one counted call)."""
        api = NimboApi(async_get_clientsession(self.hass), api_key)
        try:
            await api.key_usage()
            if lat is not None and lon is not None:
                await api.nowcast(lat, lon)
        except NimboAuthError:
            return "invalid_auth"
        except NimboOutOfCoverage:
            return "out_of_coverage"
        except NimboRateLimited:
            return "rate_limited"
        except NimboApiError:
            return "cannot_connect"
        return None

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            lat, lon = user_input[CONF_LATITUDE], user_input[CONF_LONGITUDE]
            await self.async_set_unique_id(f"{lat:.4f}_{lon:.4f}")
            self._abort_if_unique_id_configured()
            error = await self._validate(user_input[CONF_API_KEY], lat, lon)
            if error is None:
                return self.async_create_entry(
                    title=user_input[CONF_NAME],
                    data={CONF_API_KEY: user_input[CONF_API_KEY], CONF_LATITUDE: lat, CONF_LONGITUDE: lon},
                )
            errors["base"] = error

        schema = vol.Schema(
            {
                vol.Required(CONF_API_KEY): str,
                vol.Required(CONF_NAME, default=self.hass.config.location_name): str,
                vol.Required(CONF_LATITUDE, default=self.hass.config.latitude): cv.latitude,
                vol.Required(CONF_LONGITUDE, default=self.hass.config.longitude): cv.longitude,
            }
        )
        if user_input is not None:
            schema = self.add_suggested_values_to_schema(schema, user_input)
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            error = await self._validate(user_input[CONF_API_KEY], None, None)
            if error is None:
                return self.async_update_reload_and_abort(
                    self._get_reauth_entry(), data_updates={CONF_API_KEY: user_input[CONF_API_KEY]}
                )
            errors["base"] = error
        return self.async_show_form(
            step_id="reauth_confirm", data_schema=vol.Schema({vol.Required(CONF_API_KEY): str}), errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return NimboOptionsFlow()


class NimboOptionsFlow(OptionsFlow):
    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        current = self.config_entry.options.get(CONF_UPDATE_MINUTES, DEFAULT_UPDATE_MINUTES)
        schema = vol.Schema(
            {
                vol.Required(CONF_UPDATE_MINUTES, default=current): vol.All(
                    vol.Coerce(int), vol.Range(min=MIN_UPDATE_MINUTES, max=MAX_UPDATE_MINUTES)
                )
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)

"""Config flow for the Vklass integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.selector import SelectSelector, SelectSelectorConfig

from .const import (
    CONF_ACTION_CONTINUE_MANUAL_COOKIE,
    CONF_ACTION_EDIT_AUTH_URL,
    CONF_UNSUPPORTED_AUTH_URL_ACTION,
    DOMAIN,
    VKLASS_CONFKEY_AUTH_URL,
    VKLASS_CONFKEY_NAME,
    VKLASS_CONFKEY_PASSWORD,
    VKLASS_CONFKEY_PERSONNO,
    VKLASS_CONFKEY_USERNAME,
)
from .vklassgateway import get_auth_adapter


def _build_name_schema(user_input: dict[str, Any] | None = None) -> vol.Schema:
    user_input = user_input or {}

    return vol.Schema(
        {
            vol.Required(
                VKLASS_CONFKEY_NAME,
                default=user_input.get(VKLASS_CONFKEY_NAME, ""),
            ): cv.string,
        }
    )


def _build_auth_schema(user_input: dict[str, Any] | None = None) -> vol.Schema:
    user_input = user_input or {}

    return vol.Schema(
        {
            vol.Required(
                VKLASS_CONFKEY_AUTH_URL,
                default=user_input.get(VKLASS_CONFKEY_AUTH_URL, ""),
            ): cv.string,
            vol.Optional(
                VKLASS_CONFKEY_USERNAME,
                default=user_input.get(VKLASS_CONFKEY_USERNAME, ""),
            ): cv.string,
            vol.Optional(
                VKLASS_CONFKEY_PASSWORD,
                default=user_input.get(VKLASS_CONFKEY_PASSWORD, ""),
            ): cv.string,
            vol.Optional(
                VKLASS_CONFKEY_PERSONNO,
                default=user_input.get(VKLASS_CONFKEY_PERSONNO, ""),
            ): cv.string,
        }
    )


def _build_manual_cookie_warning_schema() -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_UNSUPPORTED_AUTH_URL_ACTION): SelectSelector(
                SelectSelectorConfig(
                    options=[
                        CONF_ACTION_EDIT_AUTH_URL,
                        CONF_ACTION_CONTINUE_MANUAL_COOKIE,
                    ],
                    translation_key=CONF_UNSUPPORTED_AUTH_URL_ACTION,
                )
            ),
        }
    )


class VklassConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Vklass."""

    VERSION = 1

    def __init__(self) -> None:
        self._name_input: dict[str, Any] | None = None
        self._pending_input: dict[str, Any] | None = None

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        return VklassOptionsFlow(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ):
        errors: dict[str, str] = {}

        if user_input is not None:
            name = user_input[VKLASS_CONFKEY_NAME].strip()

            if not name:
                errors[VKLASS_CONFKEY_NAME] = "required"
            elif any(
                existing_entry.title == name
                for existing_entry in self._async_current_entries()
            ):
                errors[VKLASS_CONFKEY_NAME] = "name_exists"
            else:
                self._name_input = {VKLASS_CONFKEY_NAME: name}
                return await self.async_step_auth()

        return self.async_show_form(
            step_id="user",
            data_schema=_build_name_schema(user_input),
            errors=errors,
        )

    async def async_step_auth(
        self, user_input: dict[str, Any] | None = None
    ):
        if self._name_input is None:
            return await self.async_step_user()

        errors: dict[str, str] = {}

        if user_input is not None:
            auth_url = user_input[VKLASS_CONFKEY_AUTH_URL].strip()
            cleaned_input = {
                key: value.strip() if isinstance(value, str) else value
                for key, value in user_input.items()
            }
            cleaned_input[VKLASS_CONFKEY_AUTH_URL] = auth_url
            cleaned_input.update(self._name_input)

            if not auth_url:
                errors[VKLASS_CONFKEY_AUTH_URL] = "required"
            else:
                adapter = get_auth_adapter(auth_url)
                if adapter is None:
                    self._pending_input = cleaned_input
                    return await self.async_step_manual_cookie_warning()

                return self.async_create_entry(
                    title=self._name_input[VKLASS_CONFKEY_NAME],
                    data=cleaned_input,
                )

        return self.async_show_form(
            step_id="auth",
            data_schema=_build_auth_schema(user_input or self._pending_input),
            errors=errors,
            description_placeholders={
                "name": self._name_input[VKLASS_CONFKEY_NAME],
            },
        )

    async def async_step_manual_cookie_warning(
        self, user_input: dict[str, Any] | None = None
    ):
        if self._pending_input is None:
            return await self.async_step_user()

        errors: dict[str, str] = {}

        if user_input is not None:
            if (
                user_input.get(CONF_UNSUPPORTED_AUTH_URL_ACTION)
                == CONF_ACTION_CONTINUE_MANUAL_COOKIE
            ):
                return self.async_create_entry(
                    title=self._pending_input[VKLASS_CONFKEY_NAME],
                    data=self._pending_input,
                )

            return await self.async_step_auth()

        return self.async_show_form(
            step_id="manual_cookie_warning",
            data_schema=_build_manual_cookie_warning_schema(),
            errors=errors,
            description_placeholders={
                "auth_url": self._pending_input[VKLASS_CONFKEY_AUTH_URL],
            },
        )


class VklassOptionsFlow(config_entries.OptionsFlow):
    """Handle Vklass options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry
        self._pending_input: dict[str, Any] | None = None

    def _get_defaults(self) -> dict[str, Any]:
        return {
            VKLASS_CONFKEY_AUTH_URL: self._config_entry.options.get(
                VKLASS_CONFKEY_AUTH_URL,
                self._config_entry.data.get(VKLASS_CONFKEY_AUTH_URL, ""),
            ),
            VKLASS_CONFKEY_USERNAME: self._config_entry.options.get(
                VKLASS_CONFKEY_USERNAME,
                self._config_entry.data.get(VKLASS_CONFKEY_USERNAME, ""),
            ),
            VKLASS_CONFKEY_PASSWORD: self._config_entry.options.get(
                VKLASS_CONFKEY_PASSWORD,
                self._config_entry.data.get(VKLASS_CONFKEY_PASSWORD, ""),
            ),
            VKLASS_CONFKEY_PERSONNO: self._config_entry.options.get(
                VKLASS_CONFKEY_PERSONNO,
                self._config_entry.data.get(VKLASS_CONFKEY_PERSONNO, ""),
            ),
        }

    def _update_entry_data(self, updated_values: dict[str, Any]) -> None:
        merged_data = {**self._config_entry.data, **updated_values}
        self.hass.config_entries.async_update_entry(
            self._config_entry,
            data=merged_data,
            options={},
        )

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ):
        errors: dict[str, str] = {}

        if user_input is not None:
            auth_url = user_input[VKLASS_CONFKEY_AUTH_URL].strip()
            cleaned_input = {
                key: value.strip() if isinstance(value, str) else value
                for key, value in user_input.items()
            }
            cleaned_input[VKLASS_CONFKEY_AUTH_URL] = auth_url

            if not auth_url:
                errors[VKLASS_CONFKEY_AUTH_URL] = "required"
            else:
                adapter = get_auth_adapter(auth_url)
                if adapter is None:
                    self._pending_input = cleaned_input
                    return await self.async_step_manual_cookie_warning()

                self._update_entry_data(cleaned_input)
                return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="init",
            data_schema=_build_auth_schema(
                user_input or self._pending_input or self._get_defaults()
            ),
            errors=errors,
            description_placeholders={
                "name": self._config_entry.title,
            },
        )

    async def async_step_manual_cookie_warning(
        self, user_input: dict[str, Any] | None = None
    ):
        if self._pending_input is None:
            return await self.async_step_init()

        errors: dict[str, str] = {}

        if user_input is not None:
            if (
                user_input.get(CONF_UNSUPPORTED_AUTH_URL_ACTION)
                == CONF_ACTION_CONTINUE_MANUAL_COOKIE
            ):
                self._update_entry_data(self._pending_input)
                return self.async_create_entry(title="", data={})

            return await self.async_step_init()

        return self.async_show_form(
            step_id="manual_cookie_warning",
            data_schema=_build_manual_cookie_warning_schema(),
            errors=errors,
            description_placeholders={
                "auth_url": self._pending_input[VKLASS_CONFKEY_AUTH_URL],
            },
        )

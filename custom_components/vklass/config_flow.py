"""Config flow for the Vklass integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    AUTH_ADAPTER_ATTR_TITLE,
    DOMAIN,
    VKLASS_CONFKEY_AUTHADAPTER,
    VKLASS_CONFKEY_NAME,
)
from .vklassgateway import get_auth_adapters


def _get_adapter_options() -> list[dict[str, str]]:
    options: list[dict[str, str]] = []

    for adapter_key, adapter in sorted(
        (get_auth_adapters() or {}).items(),
        key=lambda item: str(item[1].get(AUTH_ADAPTER_ATTR_TITLE, item[0])).casefold(),
    ):
        options.append(
            {
                "value": adapter_key,
                "label": str(adapter.get(AUTH_ADAPTER_ATTR_TITLE, adapter_key)),
            }
        )

    return options


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


def _build_config_schema(user_input: dict[str, Any] | None = None) -> vol.Schema:
    user_input = user_input or {}
    adapter_options = _get_adapter_options()

    default_adapter = user_input.get(VKLASS_CONFKEY_AUTHADAPTER)
    if default_adapter is None and adapter_options:
        default_adapter = adapter_options[0]["value"]

    return vol.Schema(
        {
            vol.Required(
                VKLASS_CONFKEY_AUTHADAPTER,
                default=default_adapter,
            ): SelectSelector(
                SelectSelectorConfig(
                    options=adapter_options,
                    mode=SelectSelectorMode.DROPDOWN,
                )
            ),
        }
    )


class VklassConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Vklass."""

    VERSION = 1

    def __init__(self) -> None:
        self._name_input: dict[str, Any] | None = None

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
                return await self.async_step_config()

        return self.async_show_form(
            step_id="user",
            data_schema=_build_name_schema(user_input),
            errors=errors,
        )

    async def async_step_config(
        self, user_input: dict[str, Any] | None = None
    ):
        if self._name_input is None:
            return await self.async_step_user()

        errors: dict[str, str] = {}

        if user_input is not None:
            cleaned_input = {
                VKLASS_CONFKEY_AUTHADAPTER: user_input[VKLASS_CONFKEY_AUTHADAPTER],
                **self._name_input,
            }
            return self.async_create_entry(
                title=self._name_input[VKLASS_CONFKEY_NAME],
                data=cleaned_input,
            )

        return self.async_show_form(
            step_id="config",
            data_schema=_build_config_schema(user_input),
            errors=errors,
            description_placeholders={
                "name": self._name_input[VKLASS_CONFKEY_NAME],
            },
        )


class VklassOptionsFlow(config_entries.OptionsFlow):
    """Handle Vklass options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    def _get_defaults(self) -> dict[str, Any]:
        return {
            VKLASS_CONFKEY_AUTHADAPTER: self._config_entry.options.get(
                VKLASS_CONFKEY_AUTHADAPTER,
                self._config_entry.data.get(VKLASS_CONFKEY_AUTHADAPTER),
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
            cleaned_input = {
                VKLASS_CONFKEY_AUTHADAPTER: user_input[VKLASS_CONFKEY_AUTHADAPTER],
            }
            self._update_entry_data(cleaned_input)
            return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="init",
            data_schema=_build_config_schema(user_input or self._get_defaults()),
            errors=errors,
            description_placeholders={
                "name": self._config_entry.title,
            },
        )

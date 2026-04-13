"""Auth sensor entity for Vklass."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.util import dt as dt_util
from homeassistant.util import slugify

from .auth_state import STORAGE_KEY_CREDENTIALS
from .const import (
    AUTH_ADAPTER_ATTR_METHOD,
    AUTH_ADAPTER_ATTR_NAME,
    AUTH_ADAPTER_ATTR_TITLE,
    AUTH_METHOD_USERPASS,
    AUTH_STATUS_FAIL,
    AUTH_STATUS_INPROGRESS,
    AUTH_STATUS_SUCCESS,
    CONF_SAVE_CREDENTIALS,
    DATA_AUTH_STATE,
    DATA_CALLBACKS,
    DATA_GATEWAY,
    DOMAIN,
    HA_ENTITYNAME_AUTH,
    VKLASS_CREDKEY_PASSWORD,
    VKLASS_CREDKEY_PERSONNO,
    VKLASS_CREDKEY_USERNAME,
    VKLASS_CONFKEY_NAME,
    VKLASS_HANDLER_ON_AUTH_EVENT,
    VKLASS_HANDLER_ON_AUTH_QRCODE_UPDATE,
)
from .vklassgateway import VklassGateway


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities,
) -> None:
    runtime_data = hass.data[DOMAIN][entry.entry_id]
    gateway: VklassGateway = runtime_data[DATA_GATEWAY]
    async_add_entities([VklassAuthSensor(entry, gateway, runtime_data)])


class VklassAuthSensor(SensorEntity):
    """Represent the Vklass authentication status."""

    _attr_icon = "mdi:shield-account"
    _attr_should_poll = False

    def __init__(
        self,
        entry: ConfigEntry,
        gateway: VklassGateway,
        runtime_data: dict[str, Any],
    ) -> None:
        self._entry = entry
        self._gateway = gateway
        self._runtime_data = runtime_data
        self._config = {**entry.data, **entry.options}
        self._name = entry.title or self._config.get(VKLASS_CONFKEY_NAME, "Vklass")
        self._state = AUTH_STATUS_FAIL
        self._message: str | None = None
        self._qr_code: str | None = None
        self._last_success: str | None = None
        self._handlers_registered = False
        self._runtime_callback_registered = False

        self._attr_unique_id = f"{entry.entry_id}_auth"
        self._attr_name = HA_ENTITYNAME_AUTH
        self.entity_id = f"sensor.vklass_{slugify(self._name)}_auth"

    @property
    def native_value(self) -> str:
        return self._state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        auth_adapter = self._gateway.getAuthAdapter()
        auth_state = self._runtime_data.get(DATA_AUTH_STATE, {})
        credentials = auth_state.get(STORAGE_KEY_CREDENTIALS, {})
        user = ""

        if self._state == AUTH_STATUS_SUCCESS:
            try:
                user = self._gateway.getUserName()
            except RuntimeError:
                user = ""

        attributes: dict[str, Any] = {
            "device_name": self._name,
            "user": user,
            "auth_adapter": auth_adapter.get(AUTH_ADAPTER_ATTR_NAME),
            "auth_adapter_title": auth_adapter.get(AUTH_ADAPTER_ATTR_TITLE),
            "auth_method": auth_adapter.get(AUTH_ADAPTER_ATTR_METHOD),
            "save_credentials": bool(auth_state.get(CONF_SAVE_CREDENTIALS, False)),
        }

        if auth_adapter.get(AUTH_ADAPTER_ATTR_METHOD) == AUTH_METHOD_USERPASS:
            attributes["persisted_password"] = bool(
                credentials.get(VKLASS_CREDKEY_PASSWORD)
            )

        if username := credentials.get(VKLASS_CREDKEY_USERNAME):
            attributes["username"] = username
        if personno := credentials.get(VKLASS_CREDKEY_PERSONNO):
            attributes["personno"] = personno
        if self._qr_code is not None:
            attributes["qr_code"] = self._qr_code
        if self._message is not None:
            attributes["message"] = self._message
        if self._last_success is not None:
            attributes["last_success"] = self._last_success

        return attributes

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=self._name,
            manufacturer="Vklass",
            model="Vklass",
        )

    async def async_added_to_hass(self) -> None:
        if not self._handlers_registered:
            self._gateway.registerHandler(
                VKLASS_HANDLER_ON_AUTH_EVENT,
                self._async_on_auth_event,
            )
            self._gateway.registerHandler(
                VKLASS_HANDLER_ON_AUTH_QRCODE_UPDATE,
                self._async_on_qr_code_update,
            )
            self._handlers_registered = True

        if not self._runtime_callback_registered:
            callbacks = self._runtime_data.setdefault(DATA_CALLBACKS, [])
            callbacks.append(self._async_on_runtime_update)
            self._runtime_callback_registered = True

            def _remove_runtime_callback() -> None:
                if self._async_on_runtime_update in callbacks:
                    callbacks.remove(self._async_on_runtime_update)

            self.async_on_remove(_remove_runtime_callback)

    async def _async_on_auth_event(
        self,
        state: str,
        message: str | None = None,
    ) -> None:
        self._state = state
        self._message = message

        if state == AUTH_STATUS_INPROGRESS:
            self._qr_code = None
        if state == AUTH_STATUS_SUCCESS:
            self._last_success = dt_util.utcnow().isoformat()

        self.async_write_ha_state()

    async def _async_on_qr_code_update(self, qr_code: str) -> None:
        self._qr_code = qr_code
        self.async_write_ha_state()

    async def _async_on_runtime_update(self) -> None:
        self.async_write_ha_state()

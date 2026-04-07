"""Auth sensor entity for Vklass."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.util import dt as dt_util
from homeassistant.util import slugify

from .const import (
    AUTH_STATUS_FAIL,
    AUTH_STATUS_INPROGRESS,
    AUTH_STATUS_SUCCESS,
    DATA_GATEWAY,
    DOMAIN,
    HA_ENTITYNAME_AUTH,
    VKLASS_CONFKEY_AUTH_URL,
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
    gateway: VklassGateway = hass.data[DOMAIN][entry.entry_id][DATA_GATEWAY]
    async_add_entities([VklassAuthSensor(entry, gateway)])


class VklassAuthSensor(SensorEntity):
    """Represent the Vklass authentication status."""

    _attr_icon = "mdi:shield-account"
    _attr_should_poll = False

    def __init__(self, entry: ConfigEntry, gateway: VklassGateway) -> None:
        self._entry = entry
        self._gateway = gateway
        self._config = {**entry.data, **entry.options}
        self._name = entry.title or self._config.get(VKLASS_CONFKEY_NAME, "Vklass")
        self._state = AUTH_STATUS_FAIL
        self._message: str | None = None
        self._qr_code: str | None = None
        self._last_success: str | None = None
        self._auth_method, self._auth_interactive = gateway.getAuthMethod()
        self._handlers_registered = False

        self._attr_unique_id = f"{entry.entry_id}_auth"
        self._attr_name = HA_ENTITYNAME_AUTH
        self.entity_id = f"sensor.vklass_{slugify(self._name)}_auth"

    @property
    def native_value(self) -> str:
        return self._state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        attributes: dict[str, Any] = {
            "auth_url": self._config.get(VKLASS_CONFKEY_AUTH_URL),
            "auth_method": self._auth_method,
            "auth_interactive": self._auth_interactive,
        }

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
        if self._handlers_registered:
            return

        self._gateway.registerHandler(
            VKLASS_HANDLER_ON_AUTH_EVENT,
            self._async_on_auth_event,
        )
        self._gateway.registerHandler(
            VKLASS_HANDLER_ON_AUTH_QRCODE_UPDATE,
            self._async_on_qr_code_update,
        )
        self._handlers_registered = True

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

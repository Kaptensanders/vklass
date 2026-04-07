"""The Vklass integration."""

from __future__ import annotations

from collections.abc import Mapping
import logging
from io import BytesIO
from pathlib import Path
from typing import Any

from aiohttp import web
import voluptuous as vol

from homeassistant.components import frontend
from homeassistant.components.http import HomeAssistantView, StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.const import Platform
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.storage import Store

from .const import (
    DATA_CONFIG_STORE,
    DATA_GATEWAY,
    DATA_SERVICES_REGISTERED,
    DEFAULT_KEEPALIVE_MINUTES,
    DOMAIN,
    SERVICE_ATTR_AUTH_COOKIE,
    SERVICE_AUTHENTICATE,
    SERVICE_LOGOUT,
    SERVICE_SET_AUTH_COOKIE,
    STORAGE_KEY,
    STORAGE_VERSION,
    VKLASS_HANDLER_ON_AUTHCOOKIE_UPDATE,
    VKLASS_CONFKEY_KEEPALIVE_MIN,
    VKLASS_CONFKEY_NAME,
    VERSION,
)
from .vklassgateway import VklassGateway

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR]
FRONTEND_URL_BASE = "/vklass"
FRONTEND_MODULE_URL = f"{FRONTEND_URL_BASE}/vklass-auth-card.js?v={VERSION}"
FRONTEND_REGISTERED = "frontend_registered"


def _render_qr_svg(data: str) -> bytes:
    import qrcode
    from qrcode.image.svg import SvgPathImage

    image = qrcode.make(
        data,
        image_factory=SvgPathImage,
        box_size=8,
        border=2,
    )
    output = BytesIO()
    image.save(output)
    return output.getvalue()


class VklassQrCodeView(HomeAssistantView):
    """Render QR images for the Vklass auth card."""

    url = "/api/vklass/qr"
    name = "api:vklass:qr"
    requires_auth = True

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass

    async def get(self, request: web.Request) -> web.Response:
        data = request.query.get("data", "").strip()
        if not data:
            return web.Response(status=400, text="Missing QR data")

        svg = await self.hass.async_add_executor_job(_render_qr_svg, data)
        return web.Response(body=svg, content_type="image/svg+xml")


def _get_entry_data(hass: HomeAssistant, entry_id: str) -> dict[str, Any]:
    domain_data = hass.data.setdefault(DOMAIN, {})
    return domain_data.setdefault(entry_id, {})


def _get_store(hass: HomeAssistant) -> Store:
    domain_data = hass.data.setdefault(DOMAIN, {})
    store = domain_data.get(DATA_CONFIG_STORE)
    if store is None:
        store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        domain_data[DATA_CONFIG_STORE] = store
    return store


async def _async_load_stored_data(hass: HomeAssistant) -> dict[str, Any]:
    stored_data = await _get_store(hass).async_load()
    if isinstance(stored_data, dict):
        return stored_data
    return {}


async def _async_save_entry_storage(
    hass: HomeAssistant,
    entry_id: str,
    *,
    auth_cookie: str | None = None,
) -> None:
    stored_data = await _async_load_stored_data(hass)
    entry_storage = dict(stored_data.get(entry_id, {}))

    if auth_cookie is None:
        entry_storage.pop("auth_cookie", None)
    else:
        entry_storage["auth_cookie"] = auth_cookie

    if entry_storage:
        stored_data[entry_id] = entry_storage
    else:
        stored_data.pop(entry_id, None)

    await _get_store(hass).async_save(stored_data)


async def _async_resolve_entry_from_entity(
    hass: HomeAssistant, service_data: Mapping[str, Any]
) -> ConfigEntry:
    entity_ids = service_data.get(ATTR_ENTITY_ID)
    if entity_ids is None:
        raise ValueError("Service call must target exactly one Vklass auth entity")

    if isinstance(entity_ids, str):
        entity_id = entity_ids
    elif isinstance(entity_ids, list) and len(entity_ids) == 1:
        entity_id = entity_ids[0]
    else:
        raise ValueError("Service call must target exactly one Vklass auth entity")

    if not entity_id.startswith("sensor.") or not entity_id.endswith("_auth"):
        raise ValueError(f"Entity is not a Vklass auth sensor: {entity_id}")

    entity_registry = er.async_get(hass)
    entity_entry = entity_registry.async_get(entity_id)
    if entity_entry is None:
        raise ValueError(f"Unknown entity: {entity_id}")

    entry = hass.config_entries.async_get_entry(entity_entry.config_entry_id)
    if entry is None or entry.domain != DOMAIN:
        raise ValueError(f"Entity does not belong to the Vklass integration: {entity_id}")

    return entry


async def _async_handle_authenticate(hass: HomeAssistant, call: ServiceCall) -> None:
    entry = await _async_resolve_entry_from_entity(hass, call.data)
    gateway: VklassGateway = hass.data[DOMAIN][entry.entry_id][DATA_GATEWAY]

    try:
        await gateway.authenticate(force=True, allow_interactive=True)
    except RuntimeError as err:
        raise HomeAssistantError(str(err)) from None


async def _async_handle_set_auth_cookie(hass: HomeAssistant, call: ServiceCall) -> None:
    entry = await _async_resolve_entry_from_entity(hass, call.data)
    gateway: VklassGateway = hass.data[DOMAIN][entry.entry_id][DATA_GATEWAY]
    auth_cookie = call.data[SERVICE_ATTR_AUTH_COOKIE]

    await gateway.setAuthCookie(auth_cookie)


async def _async_handle_logout(hass: HomeAssistant, call: ServiceCall) -> None:
    entry = await _async_resolve_entry_from_entity(hass, call.data)
    gateway: VklassGateway = hass.data[DOMAIN][entry.entry_id][DATA_GATEWAY]

    await gateway.logout()


async def _async_register_services(hass: HomeAssistant) -> None:
    domain_data = hass.data.setdefault(DOMAIN, {})
    if domain_data.get(DATA_SERVICES_REGISTERED):
        return

    async def async_authenticate_service(call: ServiceCall) -> None:
        await _async_handle_authenticate(hass, call)

    async def async_set_auth_cookie_service(call: ServiceCall) -> None:
        await _async_handle_set_auth_cookie(hass, call)

    async def async_logout_service(call: ServiceCall) -> None:
        await _async_handle_logout(hass, call)

    hass.services.async_register(
        DOMAIN,
        SERVICE_AUTHENTICATE,
        async_authenticate_service,
        schema=vol.Schema(
            {
                vol.Required(ATTR_ENTITY_ID): vol.Any(str, [str]),
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_AUTH_COOKIE,
        async_set_auth_cookie_service,
        schema=vol.Schema(
            {
                vol.Required(ATTR_ENTITY_ID): vol.Any(str, [str]),
                vol.Required(SERVICE_ATTR_AUTH_COOKIE): str,
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_LOGOUT,
        async_logout_service,
        schema=vol.Schema(
            {
                vol.Required(ATTR_ENTITY_ID): vol.Any(str, [str]),
            }
        ),
    )

    domain_data[DATA_SERVICES_REGISTERED] = True


async def _async_unregister_services_if_unused(hass: HomeAssistant) -> None:
    domain_data = hass.data.setdefault(DOMAIN, {})
    has_loaded_entries = any(
        isinstance(value, dict) and DATA_GATEWAY in value
        for value in domain_data.values()
    )
    if has_loaded_entries:
        return

    hass.services.async_remove(DOMAIN, SERVICE_AUTHENTICATE)
    hass.services.async_remove(DOMAIN, SERVICE_LOGOUT)
    hass.services.async_remove(DOMAIN, SERVICE_SET_AUTH_COOKIE)
    domain_data[DATA_SERVICES_REGISTERED] = False
    if domain_data.get(FRONTEND_REGISTERED):
        frontend.remove_extra_js_url(hass, FRONTEND_MODULE_URL)
        domain_data[FRONTEND_REGISTERED] = False


async def _async_register_frontend(hass: HomeAssistant) -> None:
    domain_data = hass.data.setdefault(DOMAIN, {})
    if domain_data.get(FRONTEND_REGISTERED):
        return

    frontend_path = Path(__file__).parent / "frontend"
    await hass.http.async_register_static_paths(
        [StaticPathConfig(FRONTEND_URL_BASE, str(frontend_path), cache_headers=False)]
    )
    frontend.add_extra_js_url(hass, FRONTEND_MODULE_URL)
    hass.http.register_view(VklassQrCodeView(hass))
    domain_data[FRONTEND_REGISTERED] = True


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    hass.data.setdefault(DOMAIN, {})
    await _async_register_frontend(hass)
    await _async_register_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    await _async_register_services(hass)

    runtime_data = _get_entry_data(hass, entry.entry_id)

    async def async_on_auth_cookie_update(auth_cookie: str) -> None:
        await _async_save_entry_storage(
            hass,
            entry.entry_id,
            auth_cookie=auth_cookie,
        )

    gateway_config = {**entry.data, **entry.options}
    gateway_config.setdefault(VKLASS_CONFKEY_KEEPALIVE_MIN, DEFAULT_KEEPALIVE_MINUTES)

    gateway = VklassGateway(gateway_config)
    gateway.registerHandler(
        VKLASS_HANDLER_ON_AUTHCOOKIE_UPDATE,
        async_on_auth_cookie_update,
    )
    runtime_data[DATA_GATEWAY] = gateway

    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.title or entry.data.get(VKLASS_CONFKEY_NAME),
        manufacturer="Vklass",
        model="Vklass",
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    stored_data = await _async_load_stored_data(hass)
    stored_entry_data = stored_data.get(entry.entry_id, {})
    stored_auth_cookie = stored_entry_data.get("auth_cookie")
    if stored_auth_cookie:
        await gateway.setAuthCookie(stored_auth_cookie)
        _LOGGER.info("Restored stored Vklass auth cookie for entry %s", entry.entry_id)

    gateway.startKeepAlive()
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    runtime_data = hass.data.setdefault(DOMAIN, {}).get(entry.entry_id)
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if not unload_ok:
        return False

    if runtime_data and (gateway := runtime_data.get(DATA_GATEWAY)):
        await gateway.shutdown()

    hass.data.setdefault(DOMAIN, {}).pop(entry.entry_id, None)
    await _async_unregister_services_if_unused(hass)
    return True

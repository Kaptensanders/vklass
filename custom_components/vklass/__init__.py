"""The Vklass integration."""

from __future__ import annotations

from collections.abc import Mapping
from io import BytesIO
import logging
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from aiohttp import web
import voluptuous as vol

from homeassistant.components.http import HomeAssistantView, StaticPathConfig
from homeassistant.components.lovelace.const import CONF_RESOURCE_TYPE_WS, LOVELACE_DATA, MODE_STORAGE
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ENTITY_ID, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .auth_state import (
    STORAGE_KEY_AUTH_COOKIE,
    STORAGE_KEY_CREDENTIALS,
    can_entity_fetch,
    credentials_can_seed,
    get_auth_method,
    get_auth_state,
    load_stored_data,
    next_auth_state_after_login,
    next_auth_state_with_cookie,
    notify_runtime_listeners,
    resolve_login_credentials,
    sanitize_auth_state,
    save_entry_storage,
)
from .const import (
    AUTH_STATUS_FAIL,
    AUTH_STATUS_INPROGRESS,
    AUTH_STATUS_SUCCESS,
    AUTH_METHOD_MANUAL_COOKIE,
    CONF_SAVE_CREDENTIALS,
    DATA_AUTH_STATE,
    DATA_AUTH_STATUS,
    DATA_CALLBACKS,
    DATA_GATEWAY,
    DATA_SERVICES_REGISTERED,
    DEFAULT_KEEPALIVE_MINUTES,
    DOMAIN,
    SERVICE_LOGIN,
    SERVICE_LOGOUT,
    VKLASS_CREDKEY_COOKIE,
    VKLASS_CREDKEY_PASSWORD,
    VKLASS_CREDKEY_PERSONNO,
    VKLASS_CREDKEY_USERNAME,
    VKLASS_HANDLER_ON_AUTH_EVENT,
    VKLASS_HANDLER_ON_AUTHCOOKIE_UPDATE,
    VKLASS_CONFKEY_KEEPALIVE_MIN,
    VKLASS_CONFKEY_NAME,
    VERSION,
)
from .vklassgateway import VklassGateway

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR]
FRONTEND_URL_BASE = "/vklass"
FRONTEND_MODULE_PATH = f"{FRONTEND_URL_BASE}/vklass-auth-card.js"
FRONTEND_MODULE_URL = f"{FRONTEND_MODULE_PATH}?v={VERSION}"
FRONTEND_REGISTERED = "frontend_registered"
FRONTEND_RESOURCE_SYNCED = "frontend_resource_synced"


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


def can_entry_fetch(hass: HomeAssistant, entry_id: str) -> bool:
    runtime_data = _get_entry_data(hass, entry_id)
    gateway: VklassGateway = runtime_data[DATA_GATEWAY]
    return can_entity_fetch(runtime_data, gateway)


def _strip_url_query(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


async def _async_ensure_lovelace_resource(hass: HomeAssistant) -> None:
    domain_data = hass.data.setdefault(DOMAIN, {})
    if domain_data.get(FRONTEND_RESOURCE_SYNCED) == FRONTEND_MODULE_URL:
        return

    lovelace_data = hass.data.get(LOVELACE_DATA)
    if lovelace_data is None:
        return

    if lovelace_data.resource_mode != MODE_STORAGE:
        return

    resources = lovelace_data.resources
    if not resources.loaded:
        await resources.async_load()
        resources.loaded = True

    matching_items = [item for item in resources.async_items() if _strip_url_query(item["url"]) == FRONTEND_MODULE_PATH]
    if len(matching_items) > 1:
        _LOGGER.warning(
            "Multiple Lovelace resources exist for %s. Fixing by removing all and re-adding only one correct entry.", FRONTEND_MODULE_PATH
        )
        for item in matching_items:
            await resources.async_delete_item(item["id"])
        matching_items = []

    primary_item = matching_items[0] if matching_items else None

    if primary_item is None:
        _LOGGER.info("Creating Lovelace resource for Vklass card %s", FRONTEND_MODULE_PATH)
        await resources.async_create_item({CONF_RESOURCE_TYPE_WS: "module", "url": FRONTEND_MODULE_URL})
    elif primary_item.get("url") != FRONTEND_MODULE_URL or primary_item.get("type") != "module":
        _LOGGER.info("Updating Lovelace resource for Vklass card to version %s", VERSION)
        await resources.async_update_item(primary_item["id"], {CONF_RESOURCE_TYPE_WS: "module", "url": FRONTEND_MODULE_URL})

    domain_data[FRONTEND_RESOURCE_SYNCED] = FRONTEND_MODULE_URL


async def _async_resolve_entry_from_entity(hass: HomeAssistant, service_data: Mapping[str, Any]) -> ConfigEntry:
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


async def _async_handle_login(hass: HomeAssistant, call: ServiceCall) -> None:
    entry = await _async_resolve_entry_from_entity(hass, call.data)
    runtime_data = _get_entry_data(hass, entry.entry_id)
    gateway: VklassGateway = runtime_data[DATA_GATEWAY]
    auth_method = get_auth_method(gateway)
    auth_state = get_auth_state(runtime_data)

    save_credentials = bool(call.data.get(CONF_SAVE_CREDENTIALS, auth_state.get(CONF_SAVE_CREDENTIALS, False)))
    if auth_method == AUTH_METHOD_MANUAL_COOKIE:
        save_credentials = False
    persisted_credentials = auth_state.get(STORAGE_KEY_CREDENTIALS, {})
    credentials = resolve_login_credentials(auth_method, call.data, persisted_credentials)

    try:
        await gateway.login(credentials, reuse_credentials=save_credentials)
    except Exception as err:
        raise HomeAssistantError(str(err)) from None

    # Login may trigger auth-cookie update handlers before control returns here,
    # so re-read runtime state to preserve the latest persisted session cookie.
    auth_state = get_auth_state(runtime_data)
    runtime_data[DATA_AUTH_STATE] = next_auth_state_after_login(
        auth_method,
        auth_state,
        save_credentials=save_credentials,
        credentials=credentials,
    )
    auth_state = runtime_data[DATA_AUTH_STATE]

    await save_entry_storage(
        hass,
        entry.entry_id,
        auth_method,
        save_credentials=auth_state[CONF_SAVE_CREDENTIALS],
        credentials=auth_state[STORAGE_KEY_CREDENTIALS],
        auth_cookie=auth_state.get(STORAGE_KEY_AUTH_COOKIE),
    )
    await notify_runtime_listeners(hass, entry.entry_id)


async def _async_handle_logout(hass: HomeAssistant, call: ServiceCall) -> None:
    entry = await _async_resolve_entry_from_entity(hass, call.data)
    runtime_data = _get_entry_data(hass, entry.entry_id)
    gateway: VklassGateway = runtime_data[DATA_GATEWAY]
    auth_method = get_auth_method(gateway)

    await gateway.logout()
    runtime_data[DATA_AUTH_STATE] = sanitize_auth_state(auth_method, None)
    runtime_data[DATA_AUTH_STATUS] = AUTH_STATUS_FAIL
    await save_entry_storage(
        hass,
        entry.entry_id,
        auth_method,
        save_credentials=False,
        credentials={},
        auth_cookie=None,
    )
    await notify_runtime_listeners(hass, entry.entry_id)


async def _async_register_services(hass: HomeAssistant) -> None:
    domain_data = hass.data.setdefault(DOMAIN, {})
    if domain_data.get(DATA_SERVICES_REGISTERED):
        return

    async def async_login_service(call: ServiceCall) -> None:
        await _async_handle_login(hass, call)

    async def async_logout_service(call: ServiceCall) -> None:
        await _async_handle_logout(hass, call)

    hass.services.async_register(
        DOMAIN,
        SERVICE_LOGIN,
        async_login_service,
        schema=vol.Schema(
            {
                vol.Required(ATTR_ENTITY_ID): vol.Any(str, [str]),
                vol.Optional(VKLASS_CREDKEY_USERNAME): str,
                vol.Optional(VKLASS_CREDKEY_PASSWORD): str,
                vol.Optional(VKLASS_CREDKEY_PERSONNO): str,
                vol.Optional(VKLASS_CREDKEY_COOKIE): str,
                vol.Optional(CONF_SAVE_CREDENTIALS): cv.boolean,
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
    has_loaded_entries = any(isinstance(value, dict) and DATA_GATEWAY in value for value in domain_data.values())
    if has_loaded_entries:
        return

    hass.services.async_remove(DOMAIN, SERVICE_LOGIN)
    hass.services.async_remove(DOMAIN, SERVICE_LOGOUT)
    domain_data[DATA_SERVICES_REGISTERED] = False
    if domain_data.get(FRONTEND_REGISTERED):
        domain_data[FRONTEND_REGISTERED] = False


async def _async_register_frontend(hass: HomeAssistant) -> None:
    domain_data = hass.data.setdefault(DOMAIN, {})
    if domain_data.get(FRONTEND_REGISTERED):
        return

    frontend_path = Path(__file__).parent / "frontend"
    await hass.http.async_register_static_paths([StaticPathConfig(FRONTEND_URL_BASE, str(frontend_path), cache_headers=False)])
    hass.http.register_view(VklassQrCodeView(hass))
    domain_data[FRONTEND_REGISTERED] = True


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    hass.data.setdefault(DOMAIN, {})
    await _async_register_frontend(hass)
    await _async_register_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    await _async_register_services(hass)
    await _async_ensure_lovelace_resource(hass)

    runtime_data = _get_entry_data(hass, entry.entry_id)
    runtime_data[DATA_CALLBACKS] = []

    gateway_config = {**entry.data, **entry.options}
    gateway_config.setdefault(VKLASS_CONFKEY_KEEPALIVE_MIN, DEFAULT_KEEPALIVE_MINUTES)
    gateway = VklassGateway(gateway_config)
    runtime_data[DATA_GATEWAY] = gateway

    auth_method = get_auth_method(gateway)
    stored_data = await load_stored_data(hass)
    runtime_data[DATA_AUTH_STATE] = sanitize_auth_state(
        auth_method,
        stored_data.get(entry.entry_id),
    )
    runtime_data[DATA_AUTH_STATUS] = AUTH_STATUS_FAIL

    async def async_on_auth_cookie_update(auth_cookie: str | None) -> None:
        await gateway._dumpoToFile(
            auth_cookie or "",
            "/workspaces/vklass/test/data/cookie.txt",
        )

        auth_state = get_auth_state(runtime_data)
        runtime_data[DATA_AUTH_STATE] = next_auth_state_with_cookie(
            auth_method,
            auth_state,
            auth_cookie,
        )
        saved_state = runtime_data[DATA_AUTH_STATE]
        await save_entry_storage(
            hass,
            entry.entry_id,
            auth_method,
            save_credentials=saved_state[CONF_SAVE_CREDENTIALS],
            credentials=saved_state[STORAGE_KEY_CREDENTIALS],
            auth_cookie=saved_state.get(STORAGE_KEY_AUTH_COOKIE),
        )

        await notify_runtime_listeners(hass, entry.entry_id)

    async def async_on_auth_event(state: str, message: str | None) -> None:
        runtime_data[DATA_AUTH_STATUS] = state

        if state in (AUTH_STATUS_SUCCESS, AUTH_STATUS_INPROGRESS):
            await notify_runtime_listeners(hass, entry.entry_id)
            return

        if state != AUTH_STATUS_FAIL:
            return

        auth_state = get_auth_state(runtime_data)
        if auth_state.get(STORAGE_KEY_AUTH_COOKIE) is None:
            return

        runtime_data[DATA_AUTH_STATE] = next_auth_state_with_cookie(
            auth_method,
            auth_state,
            None,
        )
        saved_state = runtime_data[DATA_AUTH_STATE]
        await save_entry_storage(
            hass,
            entry.entry_id,
            auth_method,
            save_credentials=saved_state[CONF_SAVE_CREDENTIALS],
            credentials=saved_state[STORAGE_KEY_CREDENTIALS],
            auth_cookie=saved_state.get(STORAGE_KEY_AUTH_COOKIE),
        )

        await notify_runtime_listeners(hass, entry.entry_id)

    gateway.registerHandler(
        VKLASS_HANDLER_ON_AUTH_EVENT,
        async_on_auth_event,
    )
    gateway.registerHandler(
        VKLASS_HANDLER_ON_AUTHCOOKIE_UPDATE,
        async_on_auth_cookie_update,
    )

    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.title or entry.data.get(VKLASS_CONFKEY_NAME),
        manufacturer="Vklass",
        model="Vklass",
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    auth_state = get_auth_state(runtime_data)
    stored_auth_cookie = auth_state.get(STORAGE_KEY_AUTH_COOKIE)
    credentials = auth_state.get(STORAGE_KEY_CREDENTIALS, {})
    resumed_session = False

    if stored_auth_cookie:
        try:
            resumed_session = await gateway.resumeLoggedInSession(stored_auth_cookie)
        except Exception as err:
            _LOGGER.warning(
                "Could not resume persisted Vklass session for entry %s: %s",
                entry.entry_id,
                err,
            )

    if not resumed_session and auth_state.get(CONF_SAVE_CREDENTIALS) and credentials_can_seed(auth_method, credentials):
        try:
            await gateway.login(credentials, reuse_credentials=True)
        except Exception as err:
            _LOGGER.warning(
                "Could not restore persisted Vklass credentials for entry %s: %s",
                entry.entry_id,
                err,
            )

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

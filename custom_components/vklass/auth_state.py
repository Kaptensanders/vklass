"""Persisted auth/session state helpers for the Vklass integration."""

from __future__ import annotations

from collections.abc import Mapping
from inspect import isawaitable
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import (
    AUTH_STATUS_FAIL,
    AUTH_STATUS_INPROGRESS,
    AUTH_STATUS_SUCCESS,
    AUTH_ADAPTER_ATTR_METHOD,
    AUTH_METHOD_CUSTOM,
    AUTH_METHOD_BANKID_PERSONNO,
    AUTH_METHOD_BANKID_QR,
    AUTH_METHOD_MANUAL_COOKIE,
    AUTH_METHOD_USERPASS,
    CONF_SAVE_CREDENTIALS,
    DATA_AUTH_STATE,
    DATA_AUTH_STATUS,
    DATA_CALLBACKS,
    DATA_CONFIG_STORE,
    DOMAIN,
    PERSISTED_SECRET_SENTINEL,
    STORAGE_KEY,
    STORAGE_VERSION,
    VKLASS_CREDKEY_COOKIE,
    VKLASS_CREDKEY_PASSWORD,
    VKLASS_CREDKEY_PERSONNO,
    VKLASS_CREDKEY_USERNAME,
)

STORAGE_KEY_AUTH_COOKIE = "auth_cookie"
STORAGE_KEY_CREDENTIALS = "credentials"
UNSET = object()


def empty_auth_state() -> dict[str, Any]:
    return {
        CONF_SAVE_CREDENTIALS: False,
        STORAGE_KEY_CREDENTIALS: {},
        STORAGE_KEY_AUTH_COOKIE: None,
    }


def get_auth_state(runtime_data: dict[str, Any]) -> dict[str, Any]:
    return runtime_data.setdefault(DATA_AUTH_STATE, empty_auth_state())


def get_auth_status(runtime_data: dict[str, Any]) -> str:
    return str(runtime_data.setdefault(DATA_AUTH_STATUS, AUTH_STATUS_FAIL))


def get_callbacks(runtime_data: dict[str, Any]) -> list:
    return runtime_data.setdefault(DATA_CALLBACKS, [])


def get_auth_method(gateway: Any) -> str:
    return gateway.getAuthAdapter()[AUTH_ADAPTER_ATTR_METHOD]


def can_entity_fetch(runtime_data: dict[str, Any], gateway: Any) -> bool:
    auth_status = get_auth_status(runtime_data)
    if auth_status == AUTH_STATUS_INPROGRESS:
        return False
    if auth_status == AUTH_STATUS_SUCCESS:
        return bool(gateway.hasLoadedContext())

    if gateway.hasLoadedContext():
        return True

    auth_method = get_auth_method(gateway)
    auth_state = get_auth_state(runtime_data)

    if not gateway.canAutoLogin():
        return False

    return bool(auth_state.get(CONF_SAVE_CREDENTIALS)) and credentials_can_seed(
        auth_method,
        auth_state.get(STORAGE_KEY_CREDENTIALS),
    )


def normalize_optional_text(value: Any) -> str | None:
    if value is None:
        return None

    text = str(value).strip()
    return text or None


def method_credentials(
    auth_method: str, credentials: Mapping[str, Any] | None
) -> dict[str, str]:
    credentials = dict(credentials or {})

    if auth_method == AUTH_METHOD_BANKID_PERSONNO:
        value = normalize_optional_text(credentials.get(VKLASS_CREDKEY_PERSONNO))
        return {VKLASS_CREDKEY_PERSONNO: value} if value else {}

    if auth_method == AUTH_METHOD_USERPASS:
        username = normalize_optional_text(credentials.get(VKLASS_CREDKEY_USERNAME))
        password = normalize_optional_text(credentials.get(VKLASS_CREDKEY_PASSWORD))
        result: dict[str, str] = {}
        if username:
            result[VKLASS_CREDKEY_USERNAME] = username
        if password:
            result[VKLASS_CREDKEY_PASSWORD] = password
        return result

    return {}


def sanitize_auth_state(
    auth_method: str, auth_state: Mapping[str, Any] | None
) -> dict[str, Any]:
    auth_state = dict(auth_state or {})
    save_credentials = bool(auth_state.get(CONF_SAVE_CREDENTIALS, False))
    credentials = method_credentials(
        auth_method,
        auth_state.get(STORAGE_KEY_CREDENTIALS),
    )
    auth_cookie = normalize_optional_text(auth_state.get(STORAGE_KEY_AUTH_COOKIE))

    if auth_method in (AUTH_METHOD_MANUAL_COOKIE, AUTH_METHOD_CUSTOM):
        save_credentials = False
        credentials = {}

    if not save_credentials:
        credentials = {}

    return {
        CONF_SAVE_CREDENTIALS: save_credentials,
        STORAGE_KEY_CREDENTIALS: credentials,
        STORAGE_KEY_AUTH_COOKIE: auth_cookie,
    }


def credentials_can_seed(
    auth_method: str, credentials: Mapping[str, Any] | None
) -> bool:
    credentials = dict(credentials or {})

    if auth_method == AUTH_METHOD_BANKID_QR:
        return False
    if auth_method == AUTH_METHOD_CUSTOM:
        return False
    if auth_method == AUTH_METHOD_BANKID_PERSONNO:
        return bool(credentials.get(VKLASS_CREDKEY_PERSONNO))
    if auth_method == AUTH_METHOD_USERPASS:
        return bool(credentials.get(VKLASS_CREDKEY_USERNAME)) and bool(
            credentials.get(VKLASS_CREDKEY_PASSWORD)
        )
    return False


def resolve_login_credentials(
    auth_method: str,
    service_data: Mapping[str, Any],
    persisted_credentials: Mapping[str, Any] | None,
) -> dict[str, str] | None:
    persisted_credentials = dict(persisted_credentials or {})
    missing = object()

    def _raw_value(key: str):
        return service_data[key] if key in service_data else missing

    def _visible_value(key: str) -> str | None:
        value = _raw_value(key)
        if value is missing:
            return normalize_optional_text(persisted_credentials.get(key))
        return normalize_optional_text(value)

    def _secret_value(key: str) -> str | None:
        value = _raw_value(key)
        if value is missing:
            return normalize_optional_text(persisted_credentials.get(key))

        normalized = normalize_optional_text(value)
        if normalized == PERSISTED_SECRET_SENTINEL:
            return normalize_optional_text(persisted_credentials.get(key))
        return normalized

    if auth_method == AUTH_METHOD_BANKID_QR:
        return None

    if auth_method == AUTH_METHOD_CUSTOM:
        return None

    if auth_method == AUTH_METHOD_BANKID_PERSONNO:
        personno = _visible_value(VKLASS_CREDKEY_PERSONNO)
        return {VKLASS_CREDKEY_PERSONNO: personno} if personno else {}

    if auth_method == AUTH_METHOD_USERPASS:
        username = _visible_value(VKLASS_CREDKEY_USERNAME)
        password = _secret_value(VKLASS_CREDKEY_PASSWORD)
        credentials: dict[str, str] = {}
        if username:
            credentials[VKLASS_CREDKEY_USERNAME] = username
        if password:
            credentials[VKLASS_CREDKEY_PASSWORD] = password
        return credentials

    if auth_method == AUTH_METHOD_MANUAL_COOKIE:
        cookie = normalize_optional_text(service_data.get(VKLASS_CREDKEY_COOKIE))
        return {VKLASS_CREDKEY_COOKIE: cookie} if cookie else {}

    return {}


def next_auth_state_after_login(
    auth_method: str,
    current_state: Mapping[str, Any] | None,
    *,
    save_credentials: bool,
    credentials: Mapping[str, Any] | None,
) -> dict[str, Any]:
    return sanitize_auth_state(
        auth_method,
        {
            CONF_SAVE_CREDENTIALS: save_credentials,
            STORAGE_KEY_CREDENTIALS: credentials if save_credentials else {},
            STORAGE_KEY_AUTH_COOKIE: dict(current_state or {}).get(STORAGE_KEY_AUTH_COOKIE),
        },
    )


def next_auth_state_with_cookie(
    auth_method: str,
    current_state: Mapping[str, Any] | None,
    auth_cookie: str | None,
) -> dict[str, Any]:
    updated_state = dict(current_state or {})
    updated_state[STORAGE_KEY_AUTH_COOKIE] = auth_cookie
    return sanitize_auth_state(auth_method, updated_state)


def get_store(hass: HomeAssistant) -> Store:
    domain_data = hass.data.setdefault(DOMAIN, {})
    store = domain_data.get(DATA_CONFIG_STORE)
    if store is None:
        store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        domain_data[DATA_CONFIG_STORE] = store
    return store


async def load_stored_data(hass: HomeAssistant) -> dict[str, Any]:
    stored_data = await get_store(hass).async_load()
    if isinstance(stored_data, dict):
        return stored_data
    return {}


async def save_entry_storage(
    hass: HomeAssistant,
    entry_id: str,
    auth_method: str,
    *,
    save_credentials: bool | object = UNSET,
    credentials: Mapping[str, Any] | None | object = UNSET,
    auth_cookie: str | None | object = UNSET,
) -> dict[str, Any]:
    stored_data = await load_stored_data(hass)
    entry_storage = dict(stored_data.get(entry_id, {}))

    if save_credentials is not UNSET:
        entry_storage[CONF_SAVE_CREDENTIALS] = bool(save_credentials)

    if credentials is not UNSET:
        entry_storage[STORAGE_KEY_CREDENTIALS] = dict(credentials or {})

    if auth_cookie is not UNSET:
        entry_storage[STORAGE_KEY_AUTH_COOKIE] = auth_cookie

    sanitized = sanitize_auth_state(auth_method, entry_storage)

    if (
        sanitized[CONF_SAVE_CREDENTIALS]
        or sanitized[STORAGE_KEY_CREDENTIALS]
        or sanitized[STORAGE_KEY_AUTH_COOKIE]
    ):
        stored_data[entry_id] = sanitized
    else:
        stored_data.pop(entry_id, None)

    await get_store(hass).async_save(stored_data)
    return sanitized


async def notify_runtime_listeners(hass: HomeAssistant, entry_id: str) -> None:
    runtime_data = hass.data.setdefault(DOMAIN, {}).setdefault(entry_id, {})
    for fn in list(get_callbacks(runtime_data)):
        result = fn()
        if isawaitable(result):
            await result

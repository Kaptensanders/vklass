import importlib
import pkgutil
from logging import getLogger


from .const import (
    VKLASS_CONFKEY_ASYNC_ON_QR_UPDATE,
    VKLASS_CONFKEY_AUTH_URL,
)

log = getLogger(__name__)

def _load_auth_adapters():
    adapters = []

    package_name = f"{__package__}.auth_adapters"
    package = importlib.import_module(package_name)

    for _, module_name, _ in pkgutil.iter_modules(package.__path__):
        module = importlib.import_module(f"{package_name}.{module_name}")

        can_handle = getattr(module, "can_handle", None)
        authenticate = getattr(module, "authenticate", None)

        if callable(can_handle) and callable(authenticate):
            adapters.append({
                "name": module_name,
                "can_handle": can_handle,
                "authenticate": authenticate,
            })

    return adapters

_ADAPTERS = _load_auth_adapters()

async def authenticate(aiohttp_session, config):

    url = config.get(VKLASS_CONFKEY_AUTH_URL)

    for adapter in _ADAPTERS:
        if adapter["can_handle"](url):
            log.info(f"Initializing Vklass authentication using adapter: {adapter['name']}")
            return await adapter["authenticate"](aiohttp_session, config)

    raise RuntimeError(f"No auth adapter found for {url}")


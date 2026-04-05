import importlib
import importlib.util
import os
import sys
import types

def _ensure_path(path: str) -> None:
    if path not in sys.path:
        sys.path.insert(0, path)


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

_ensure_path(ROOT)
_ensure_path(os.path.join(ROOT, "custom_components", "vklass"))
_ensure_path(os.path.join(ROOT, "test"))

try:
    gateway_module = importlib.import_module("custom_components.vklass.vklassgateway")
except ModuleNotFoundError:
    custom_components_path = os.path.join(ROOT, "custom_components")
    vklass_path = os.path.join(custom_components_path, "vklass")

    custom_components_pkg = sys.modules.get("custom_components")
    if custom_components_pkg is None:
        custom_components_pkg = types.ModuleType("custom_components")
        custom_components_pkg.__path__ = [custom_components_path]
        sys.modules["custom_components"] = custom_components_pkg

    vklass_pkg = sys.modules.get("custom_components.vklass")
    if vklass_pkg is None:
        vklass_pkg = types.ModuleType("custom_components.vklass")
        vklass_pkg.__path__ = [vklass_path]
        sys.modules["custom_components.vklass"] = vklass_pkg

    if "dateutil" not in sys.modules:
        dateutil_module = types.ModuleType("dateutil")
        dateutil_module.tz = types.SimpleNamespace()
        dateutil_module.parser = types.SimpleNamespace()
        sys.modules["dateutil"] = dateutil_module

    if "bs4" not in sys.modules:
        bs4_module = types.ModuleType("bs4")

        class _BeautifulSoup:  # pragma: no cover - test bootstrap fallback only
            def __init__(self, *_args, **_kwargs):
                pass

            def select(self, *_args, **_kwargs):
                return []

        bs4_module.BeautifulSoup = _BeautifulSoup
        sys.modules["bs4"] = bs4_module

    if "aiohttp" not in sys.modules:
        aiohttp_module = types.ModuleType("aiohttp")

        class _ClientError(Exception):
            pass

        aiohttp_module.ClientError = _ClientError
        sys.modules["aiohttp"] = aiohttp_module

    const_spec = importlib.util.spec_from_file_location(
        "custom_components.vklass.const", os.path.join(vklass_path, "const.py")
    )
    const_module = importlib.util.module_from_spec(const_spec)
    sys.modules["custom_components.vklass.const"] = const_module
    const_spec.loader.exec_module(const_module)

    gateway_spec = importlib.util.spec_from_file_location(
        "custom_components.vklass.vklassgateway", os.path.join(vklass_path, "vklassgateway.py")
    )
    gateway_module = importlib.util.module_from_spec(gateway_spec)
    sys.modules["custom_components.vklass.vklassgateway"] = gateway_module
    gateway_spec.loader.exec_module(gateway_module)

sys.modules.setdefault("vklassgateway", gateway_module)

####################################################################
# adapters must define:
# 
# AUTH_ADAPTERS = {
#   "adapter1": {
#       AUTH_ADAPTER_ATTR_TITLE : "Göteborgs stad UBF - Vårdnadshavare",
#       AUTH_ADAPTER_ATTR_METHOD: AUTH_METHOD_MANUAL_COOKIE,
#       AUTH_ADAPTER_ATTR_AUTH_FUNCTION: "authenticate"
#   },
#   "anotherAdapter": {
#       ...
#   }
# }
#


from yarl import URL
from http.cookies import SimpleCookie

from ..const import (
    AUTH_ADAPTER_ATTR_TITLE,
    AUTH_ADAPTER_ATTR_METHOD,
    VKLASS_CREDKEY_COOKIE,
    AUTH_ADAPTER_ATTR_AUTH_FUNCTION,
    AUTH_METHOD_MANUAL_COOKIE,
    VKLASS_URL_BASE,
    AUTH_COOKIE_NAME,
    AUTH_COOKIE_DOMAIN
)

AUTH_ADAPTERS = {
    "manual_cookie" : {
        AUTH_ADAPTER_ATTR_TITLE : "Ange Vklass cookie manuellt",
        AUTH_ADAPTER_ATTR_METHOD: AUTH_METHOD_MANUAL_COOKIE,
        AUTH_ADAPTER_ATTR_AUTH_FUNCTION: "authenticate"
    }
}

async def authenticate(aiohttp_session, asyncQrNotifyHandler, credentials:dict|None) -> bool:

    if not credentials or not (cookieValue := credentials.get(VKLASS_CREDKEY_COOKIE, None)):
        raise  RuntimeError("No cookie supplied for authentication")

    cookie = SimpleCookie()
    cookie[AUTH_COOKIE_NAME] = cookieValue.strip()
    c = cookie[AUTH_COOKIE_NAME]
    c["domain"] = AUTH_COOKIE_DOMAIN
    c["path"] = "/"
    c["secure"] = True
    c["httponly"] = True

    aiohttp_session.cookie_jar.update_cookies(
        cookie,
        response_url=URL(VKLASS_URL_BASE),
    )
    return True

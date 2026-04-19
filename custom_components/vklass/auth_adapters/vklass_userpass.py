##
## This adpter is completly untested and may not work
## The flow is from
## https://community.home-assistant.io/t/vklass-scrape-sensor/939402) by @fatuuse
##
##

import re

from ..const import (
    AUTH_ADAPTER_ATTR_AUTH_FUNCTION,
    AUTH_ADAPTER_ATTR_METHOD,
    AUTH_ADAPTER_ATTR_TITLE,
    AUTH_METHOD_USERPASS,
    VKLASS_CREDKEY_PASSWORD,
    VKLASS_CREDKEY_USERNAME,
)

AUTH_ADAPTERS = {
    "vklass_userpass": {
        AUTH_ADAPTER_ATTR_TITLE: "Untested - Vklass inloggning med användarnamn och lösenord",
        AUTH_ADAPTER_ATTR_METHOD: AUTH_METHOD_USERPASS,
        AUTH_ADAPTER_ATTR_AUTH_FUNCTION: "authenticate",
    }
}


_LOGIN_PAGE = "https://auth.vklass.se/credentials"
_LOGIN_PAGE_SIGNIN = f"{_LOGIN_PAGE}/signin"
_REQUEST_VERIFICATION_TOKEN_RE = re.compile(r'<input name="__RequestVerificationToken" type="hidden" value="([^"]*)" ?/?>')

async def authenticate(aiohttp_session, asyncQrNotifyHandler, credentials: dict | None) -> bool:
    del asyncQrNotifyHandler

    if not credentials:
        raise ValueError("Username and password needed for authentication")

    if not (username := credentials.get(VKLASS_CREDKEY_USERNAME)):
        raise ValueError("Username needed for authentication")

    if not (password := credentials.get(VKLASS_CREDKEY_PASSWORD)):
        raise ValueError("Password needed for authentication")

    async with aiohttp_session.get(_LOGIN_PAGE, allow_redirects=True) as response:
        html = await response.text()
        if response.status != 200:
            raise RuntimeError("Could not fetch RequestVerificationToken from Vklass")

    if not (tokens := _REQUEST_VERIFICATION_TOKEN_RE.findall(html)):
        raise RuntimeError("Could not fetch RequestVerificationToken from Vklass")

    async with aiohttp_session.post(
        _LOGIN_PAGE_SIGNIN,
        data={
            "__RequestVerificationToken": tokens[0],
            "Username": username,
            "Password": password,
            "RememberMe": "false",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        allow_redirects=False,
    ) as response:
        if response.status == 302:
            return True
        if response.status == 200:
            raise PermissionError("Could not log in to Vklass, wrong username or password?")
        raise RuntimeError(f"Could not log in to Vklass, unexpected response code {response.status}")

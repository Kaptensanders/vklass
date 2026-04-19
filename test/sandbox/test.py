import asyncio
import json
import logging
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, ROOT)

from test.tests.helpers import bootstrap  # noqa: E402, F401

from custom_components.vklass.vklassgateway import (  # noqa: E402
    VklassGateway,
    VKLASS_CREDKEY_COOKIE,
    VKLASS_CONFKEY_KEEPALIVE_MIN,
    VKLASS_HANDLER_ON_AUTH_EVENT,
    VKLASS_HANDLER_ON_AUTH_QRCODE_UPDATE,
    VKLASS_HANDLER_ON_AUTHCOOKIE_UPDATE,
    
    VKLASS_CONFKEY_AUTHADAPTER,

)

logging.basicConfig(level=logging.INFO)

DATA_DIR = "/workspaces/vklass/test/data"
AUT_COOKIE = "__DISABLED__"
COOKIE_FILE = f"{DATA_DIR}/cookie.txt"

async def onAuthUpdate(state: str, message: str | None = None):
    print(f"onAuthUpdate callback: {state}, {message}")


async def onCookieUpdate(cookie):
    # save to cookie file, for use on load
    with open(COOKIE_FILE, "w") as f:
        f.write(cookie)
    print("onCookieUpdate callback, new cookie saved to file")


async def onQrUpdate(qrCode: str, qrType: str):
    print(f"QR code update: type={qrType}, data={qrCode}")


async def loadCookieFromFile():
    if not os.path.exists(COOKIE_FILE):
        raise FileNotFoundError(f"Cookie file not found: {COOKIE_FILE}")

    with open(COOKIE_FILE, "r") as f:
        return f.read().strip()

def formatObject(data) -> str:
    return json.dumps(data, indent=4, ensure_ascii=False)


"""
config = {

    VKLASS_CONFKEY_PERSONNO                 # personal number (VKLASS_AUTH_BANKID_PERSONALNO)
    VKLASS_CONFKEY_USERNAME                 # username (VKLASS_AUTH_USERNAME_PASSWORD)
    VKLASS_CONFKEY_PASSWORD                 # password (VKLASS_AUTH_USERNAME_PASSWORD)
    VKLASS_CONFKEY_KEEPALIVE_MIN            # minutes between keepalive calls
}
"""

configs = {
    "manual": {
        VKLASS_CONFKEY_AUTHADAPTER: "manual_cookie.manual_cookie",
        VKLASS_CONFKEY_KEEPALIVE_MIN: 1
    },
}

default_config = "manual"



async def main():

    global configs
    keepalive = False

    confName = default_config

    if len(sys.argv) > 1:
        if sys.argv[1] == "keepalive":
            keepalive = True
        else:
            confName = sys.argv[1]

    gw = None

    try:
        gw = VklassGateway(configs[confName])
        gw.registerHandler(VKLASS_HANDLER_ON_AUTH_QRCODE_UPDATE, onQrUpdate)
        gw.registerHandler(VKLASS_HANDLER_ON_AUTHCOOKIE_UPDATE, onCookieUpdate)
        gw.registerHandler(VKLASS_HANDLER_ON_AUTH_EVENT, onAuthUpdate)

        gw.DEBUG = True
        gw.DUMP_TO_FILE = True
        gw.DUMP_FILE_PATH = DATA_DIR
        cookie = await loadCookieFromFile()
        if not await gw.resumeLoggedInSession(authCookieValue=cookie):
            await gw.login(credentials={VKLASS_CREDKEY_COOKIE: cookie})

        year = 2026
        month = 9

        await gw.getCalendar(year=year, month=month)

        print(f"Calendar events for {year}.{month}")
#        print(formatObject(calendar))

        if keepalive:
            while True:
                await asyncio.sleep(1)


    except asyncio.CancelledError:
        return
    finally:
        if gw:
            await gw.shutdown()


asyncio.run(main())

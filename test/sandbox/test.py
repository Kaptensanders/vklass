import sys, os, json, aiohttp, asyncio, logging
from datetime import date, timedelta
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, ROOT)

from test.tests.helpers import bootstrap  # noqa: F401

from custom_components.vklass.vklassgateway import ( # noqa: E402
    VklassGateway,
    VKLASS_CONFKEY_PERSONNO,
    VKLASS_CONFKEY_USERNAME,
    VKLASS_CONFKEY_PASSWORD,
    VKLASS_CONFKEY_KEEPALIVE_MIN,

    VKLASS_HANDLER_ON_AUTH_EVENT,
    VKLASS_HANDLER_ON_AUTH_QRCODE_UPDATE,
    VKLASS_HANDLER_ON_AUTHCOOKIE_UPDATE,

    VKLASS_CONFKEY_AUTHADAPTER_MODULENAME,
    VKLASS_CONFKEY_AUTHADAPTER_ADAPTERNAME
)

logging.basicConfig(level=logging.INFO)
    
AUT_COOKIE = "__DISABLED__"
COOKIE_FILE = "/workspaces/vklass/test/sandbox/cookie.txt"

async def onAuthUpdate(state:str, message:str|None = None):
    print (f"onAuthUpdate callback: {state}, {message}")

async def onCookieUpdate (cookie):
    # save to cookie file, for use on load
    with open(COOKIE_FILE, "w") as f:
        f.write(cookie)
    print ("onCookieUpdate callback, new cookie saved to file")

async def onQrUpdate (qrCode:str):
    print (f"QR code update: {qrCode}")


async def loadCookieFromFile():
    if not os.path.exists(COOKIE_FILE):
        return None

    with open(COOKIE_FILE, "r") as f:
        return f.read().strip()

'''
config = {

    VKLASS_CONFKEY_PERSONNO                 # personal number (VKLASS_AUTH_BANKID_PERSONALNO)
    VKLASS_CONFKEY_USERNAME                 # username (VKLASS_AUTH_USERNAME_PASSWORD)
    VKLASS_CONFKEY_PASSWORD                 # password (VKLASS_AUTH_USERNAME_PASSWORD)
    VKLASS_CONFKEY_KEEPALIVE_MIN            # minutes between keepalive calls
}
'''

configs = {
    "manual" : {
        VKLASS_CONFKEY_AUTHADAPTER_MODULENAME:      "manual_cookie",
        VKLASS_CONFKEY_AUTHADAPTER_ADAPTERNAME:     "manual_cookie",
        VKLASS_CONFKEY_USERNAME                     : None,
        VKLASS_CONFKEY_PASSWORD                     : None,
        VKLASS_CONFKEY_KEEPALIVE_MIN                : 1
    },
}

default_config = "manual"

async def main ():

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
        gw.registerHandler (VKLASS_HANDLER_ON_AUTH_QRCODE_UPDATE, onQrUpdate)
        gw.registerHandler (VKLASS_HANDLER_ON_AUTHCOOKIE_UPDATE, onCookieUpdate)
        gw.registerHandler (VKLASS_HANDLER_ON_AUTH_EVENT, onAuthUpdate)

        gw.DEBUG = True
        gw.DUMP_TO_FILE = True
        if cookie := await loadCookieFromFile():
            print(f"Loaded cookie from file {COOKIE_FILE}")
            await gw.authenticate(data=cookie)
        else:
            await gw.authenticate(data=AUT_COOKIE)

        if keepalive:
            gw.startKeepAlive()

        calStartDate = date.today().isoformat()
        calEndDate = (date.today() + timedelta(weeks=4)).isoformat()
        calendar = await gw.getCalendar(calStartDate, calEndDate)


    except asyncio.CancelledError:
        return
    finally:
        if gw:
            await gw.shutdown()    



asyncio.run(main())

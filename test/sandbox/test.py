import sys, os, json, aiohttp, asyncio, logging
from datetime import date, timedelta
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(ROOT, "test"))

from tests.helpers import bootstrap  # noqa: F401

from vklassgateway import ( # noqa: E402
    VklassGateway,
    VKLASS_CONFKEY_AUTH_URL,
    VKLASS_CONFKEY_PERSONNO,
    VKLASS_CONFKEY_USERNAME,
    VKLASS_CONFKEY_PASSWORD,
    VKLASS_CONFKEY_KEEPALIVE_MIN,
    VKLASS_CONFKEY_ASYNC_ON_QR_UPDATE,
    VKLASS_CONFKEY_ASYNC_ON_AUTH_UPDATE,
    VKLASS_CONFKEY_ASYNC_ON_AUTH_COOKIE_UPDATE
)

logging.basicConfig(level=logging.INFO)
    
AUT_COOKIE = "__DISABLED__"
COOKIE_FILE = "/workspaces/vklass/tests/sandbox/cookie.txt"

async def onAuthUpdate(state:str, message:str|None = None):
    print (f"onAuthUpdate callback {state}: {message}")

async def onCookieUpdate (cookie):
    # save to cookie file, for use on load
    with open(COOKIE_FILE, "w") as f:
        f.write(cookie)
    print ("onCookieUpdate callback, new cookie saved to file")

async def onQrUpdate (qrCode:str):
    print (f"QR code update: {qrCode}")


def loadCookieFromFile():
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
    VKLASS_CONFKEY_ASYNC_ON_AUTH_UPDATE     # async callback called on auth events
    VKLASS_CONFKEY_ASYNC_ON_AUTH_COOKIE_UPDATE # async callback function to notify when the vklass cookies was updated due to a server set-cookie response, plaintext cookie as input parameter
}
'''

configs = {
    "manual" : {
        VKLASS_CONFKEY_AUTH_URL                     : "https://authpub.goteborg.se/sp/sps/eidpub/saml20/logininitial?RequestBinding=HTTPPost&ResponseBinding=HTTPPost&Target=https%3A%2F%2Fauthpub.goteborg.se%2Fidp%2Fsps%2Fauth%3FFedId%3Duuidc69b10fc-018d-1e46-bd45-84b46fd723a9",
        VKLASS_CONFKEY_USERNAME                     : None,
        VKLASS_CONFKEY_PASSWORD                     : None,
        VKLASS_CONFKEY_KEEPALIVE_MIN                : 1,
        VKLASS_CONFKEY_ASYNC_ON_QR_UPDATE           : onQrUpdate,
        VKLASS_CONFKEY_ASYNC_ON_AUTH_UPDATE         : onAuthUpdate,
        VKLASS_CONFKEY_ASYNC_ON_AUTH_COOKIE_UPDATE  : onCookieUpdate,
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

    async with aiohttp.ClientSession() as session:
        gw = VklassGateway(configs[confName], session)
        gw.DEBUG = True
        gw.DUMP_TO_FILE = True
        if cookie := loadCookieFromFile():
            print(f"Loaded cookie from file {COOKIE_FILE}")
            await gw.setAuthCookie(cookie)
        else:
            await gw.setAuthCookie(AUT_COOKIE)

        stop_event = None 

        calStartDate = date.today().isoformat()
        calEndDate = (date.today() + timedelta(weeks=4)).isoformat()
        calendar = await gw.getCalendar(calStartDate, calEndDate)
        exit(0)

        if keepalive:
            stop_event = asyncio.Event()
            gw.startKeepAlive()


        calendar = await gw.getCalendar(calStartDate, calEndDate)

        if keepalive:
            try:
                await stop_event.wait()
            except asyncio.CancelledError:
                return
            finally:
                await gw.stopKeepAlive()
            




asyncio.run(main())

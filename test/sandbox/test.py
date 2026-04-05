import sys, os, json, aiohttp, asyncio, logging
from datetime import date, timedelta
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(ROOT, "test"))

from tests.helpers import bootstrap  # noqa: F401

from vklassgateway import ( # noqa: E402
    VklassGateway,
    VKLASS_AUTH_USERNAME_PASSWORD,
    VKLASS_AUTH_BANKID_QR,
    VKLASS_AUTH_BANKID_PERSONALNO,

    VKLASS_CONFKEY_AUTH_METHOD,
    VKLASS_CONFKEY_PERSONNO,
    VKLASS_CONFKEY_USERNAME,
    VKLASS_CONFKEY_PASSWORD,
    VKLASS_CONFKEY_KEEPALIVE_MIN,
    VKLASS_CONFKEY_ASYNC_ON_AUTH_FAIL_CB,
    VKLASS_CONFKEY_ASYNC_ON_AUTH_COOKIE_UPDATE
)

logging.basicConfig(level=logging.INFO)
    
AUT_COOKIE = "CfDJ8AF1v64zmWNJt9xTu8U9aMq0MxPGTrxvUicvW-6_vnAF7PkQJsd0pifUef3dpk-1cItGJkGclLLcYoYuyaqcOnziGoJE_tHOP5VOYgRQnrA0f6nSVQSi1k3ZLOpoVlWYQ6UsahiVObDevX7E8w_nSaS9fVXFRDtMTBuveI5O5owbo9k-9e_r-aueZYm78z5GJxdIQNF0t6_qBN3Gs0IpklnQXkEvTbOHRszfdnoTUMLm0ZsI9IDf0T7D_JJjsmWodp1UrWGB1etvZYaXYXTV3eEGpNipLwKfa0ANcH-JUAT73_jMgZ3zayDEJzdVCRqfJBuLmcbSHwuJnAuXTLNZyhRSVxS51qmidbALZF7M48F55H07EtWy49sW4suKqh2bgqvo5s9PQD4Jxswkk3ZVURFO8TThVohazxEam-3eJTsNa5WVDRfekFKb26iPQeH5EEVjO-jiIESzzzaUFdTlMvMiyNoCr9y6op6mVdHBxFUy8HMuAOQzEO2mKgsD8VDx3c-tsn7GjBS4gFKR82c4dMoeqlMCgzARRQaaAMPCvhD27LxLIittA6qKr9YbWPyq1s1ybRFDuomOUMjNQiBPAZEjsNEzWEPkX5EKBJM_6sqr1dFCGR-MHAyk8Qwy9brEb-NjFf00I9hNDH3WpfrGs9CPCwF6zPEDFdEbSsNnGHgyaX9G641oW-aIrMKFRvX2ADJ1n7Z_ZGQpDFb1KyV9nkwt_9MBtTnwkG3acQqjAq-aiOJ2zoe2zIGSZcSjd3qkJkkLzjlUooCXDTO15I2XUL7JS830IggEX4DL10ka4pTSlg0DfphSNcQvmR0n5xrq84o6iYBPeaj5jA4C8rq9NhYu7vF-ym35sylOwXzINzgKKD1N9X-v4DX7Pp5xdftUdNtLrFJ4b6yVw-ogYIvNavjs73ogaJrtlptBK9qbbELesckRFSGiSiiU4jrkYQHoiwfcvLw3aS5CtH4p8AyhT4aockCRTUrJBwqSU5Om0mgL8DG8T_3NCW0Nz9Wtw7rw1rkT4FA08jVhm0AxYJEA1exFGIj1clxDONR23iMC2dcN0J6dpaRAbQVenHp6DgKilHCiQGQz20DwOImj8abCXN2Inr9wZ9rxWpl14T5cgeA1DBIJUkzdlHpUbqE4mYjrTFDsetZ7jSK0DeRVM6jzS8BuXM2L-9DJCRHTdT6DWF0SqssPc4Tx6J1zmhOc54t3pPpGzsMfX3UuUHgc24wVVurjZE5AU4DkndOyPOw9IAmh8ZYk6zPo-ZbaSbkEMWO3-IAgVdYj9ip9V8GvTIvShgTiF4UZ0mS_LjqK2BH55i0PQBIXQohnyh06_RjK-gy_-BtLldrCrlIABcKAXuVnABhGco3NhSu4gSzPhkghXMXap0TQkb-wcymwYD2hHbQgjeQflRL_5KNcrCInEGL-rHLK4wtFXnrBxALcx-4UgzLuwuNiO5iD-aE-47uxQ4NDGu0n-BDtBXGhnVL4K14Ycql4Pte8aovPyqXi6vMwZUtfFBwwknjYRk2XqbRJyirt7CYziE7vM8nd-yqtqZzu8MKoyxSxJW7fORRUxS1UKGqwzgs7fyIYqC4TKN8SSdY3E-bvIAaDaoc_HLB-OCTqWic"
COOKIE_FILE = "/workspaces/vklass/tests/sandbox/cookie.txt"

async def onAuthFail(msg:str = None):
    print (f"onAuthFail callback {msg}")


async def onCookieUpdate (cookie):
    # save to cookie file, for use on load
    with open(COOKIE_FILE, "w") as f:
        f.write(cookie)
    print ("onCookieUpdate callback, new cookie saved to file")


def loadCookieFromFile():
    if not os.path.exists(COOKIE_FILE):
        return None

    with open(COOKIE_FILE, "r") as f:
        return f.read().strip()


'''
config = {

    VKLASS_CONFKEY_AUTH_METHOD              # VKLASS_AUTH_USERNAME_PASSWORD | VKLASS_AUTH_BANKID_QR | VKLASS_AUTH_BANKID_PERSONALNO
    VKLASS_CONFKEY_PERSONNO                 # personal number (VKLASS_AUTH_BANKID_PERSONALNO)
    VKLASS_CONFKEY_USERNAME                 # username (VKLASS_AUTH_USERNAME_PASSWORD)
    VKLASS_CONFKEY_PASSWORD                 # password (VKLASS_AUTH_USERNAME_PASSWORD)
    VKLASS_CONFKEY_KEEPALIVE_MIN            # minutes between keepalive calls
    VKLASS_CONFKEY_ASYNC_ON_AUTH_FAIL_CB    # async callback function to notify when Authentication has failed, and the VKLASS_CONFKEY_COOKIE_RETRIVAL_METHOD did not resolve auth (manual action needed, BankId login etc)
    VKLASS_CONFKEY_ASYNC_ON_AUTH_COOKIE_UPDATE # async callback function to notify when the vklass cookies was updated due to a server set-cookie response, plaintext cookie as input parameter
}
'''

configs = {
    "manual" : {
        VKLASS_CONFKEY_AUTH_METHOD                  : VKLASS_AUTH_BANKID_QR,
        VKLASS_CONFKEY_USERNAME                     : None,
        VKLASS_CONFKEY_PASSWORD                     : None,
        VKLASS_CONFKEY_KEEPALIVE_MIN                : 1,
        VKLASS_CONFKEY_ASYNC_ON_AUTH_FAIL_CB        : onAuthFail,
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
            gw.setAuthCookie(cookie)
        else:
            gw.setAuthCookie(AUT_COOKIE)

        stop_event = None 

        if keepalive:
            stop_event = asyncio.Event()
            gw.startKeepAlive()

        calStartDate = date.today().isoformat()
        calEndDate = (date.today() + timedelta(weeks=4)).isoformat()

        calendar = await gw.getCalendar(calStartDate, calEndDate)

        if keepalive:
            try:
                await stop_event.wait()
            except asyncio.CancelledError:
                return
            finally:
                await gw.stopKeepAlive()
            




asyncio.run(main())

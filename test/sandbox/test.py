import sys, os, json, aiohttp, asyncio, logging
from datetime import date, timedelta
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(ROOT, "test"))

from tests.helpers import bootstrap  # noqa: F401

from vklassgateway import ( # noqa: E402
    VklassGateway,
    VKLASS_CONFKEY_COOKIE_RETRIVAL_METHOD,
    VKLASS_CONFKEY_ASYNC_COOKIE_CB,
    VKLASS_CONFKEY_USERNAME,
    VKLASS_CONFKEY_PASSWORD,
    VKLASS_CONFKEY_COOKIEFILE,
    VKLASS_CONFKEY_COOKIEFILE_TYPE,
    VKLASS_CONFKEY_KEEPALIVE_MIN,
    VKLASS_ASYNC_ON_AUTH_FAIL_CB,
    VKLASS_ASYNC_ON_AUTH_COOKIE_UPDATE,

    VKLASS_COOKIE_RETRIVAL_METHOD_MANUAL,
    VKLASS_COOKIE_RETRIVAL_METHOD_FUNCTION,
    VKLASS_COOKIE_RETRIVAL_METHOD_FILE,
    VKLASS_COOKIE_RETRIVAL_METHOD_LOGIN,

    VKLASS_CONFKEY_COOKIEFILE_TYPE_CHROMIUM,
    VKLASS_CONFKEY_COOKIEFILE_TYPE_FIREFOX
)

logging.basicConfig(level=logging.INFO)
    
AUTH_COUNT = 0

async def getCookie():
    global AUTH_COUNT
    AUTH_COUNT += 1
    print (f"Cookie retrieval count = {AUTH_COUNT}")
    if AUTH_COUNT == 1:
        return "se.vklass.authentication=CfDJ8AF1v64zmWNJt9xTu8U9aMol4Jg-E-Wm2s6uauTG7gH7zhcTtn5xP_IVZyvss6tzlSIIifpyDkw53JzUHtbXYkq_xvVNdlhGx6zZtMul7kTn72NRfHPE2P1tl2D-cOewN9-rE1QmBmL2jBSAbWmuua4j_KpiH9n59GZ02zZeEya7sTv49iOWTY2TpFMusKZZX7dVc5z_6TED3aDliGjEAOX1rrgRYilbfaIV2myQ7CiJRFKTial3T5RfGmn9eH94seKMAIh7auhKwPKcWcdLanGWq0uPn3npay2TQTH_WO-FrEYwxumkmIQuCySGcRo0oXjgqw0RCFDtKMXvB50K5b3Ia9_0w2T0445RT4V-T2qTwNqdMA7YYM-dnSIAiNrN4nCAgq63EMCHz6GtLilTMbDvvPyx0_bcxwweKQRX3-Jq0NmTk24U8xouhgNiWcBgwB1Hs8bS77Z1BBMTSMNVmu7oeXg5GDAJKhUMATj6LBvmiulwO9P7oASAkf0hWhEf6t8eUw28-wZiRqAuT7oUz-08e4eD4CqCnqDjQHea0H7-DPdLghVK30b-KoLkWZQ2tl0wVtaYBiW5nlbwC_W6_8Mp-fd5MX2DW5eSQGOaMjAPV0Hzt-uHCC0y2Fxs6pCTdEtixp46w_T9_DUj4B_h3vQqjJjNZJub9l8EH2vL-jgAKb9VsZKNtFNkcx1ASV-AuR1-B-tcnG1PWefy6igA1hrPQJQ5f4gNsnyG02G8OVyOBtwkjfCxrsjpoi7nct6A6LTQOaTLMNuvf_5E3iiG1FoKYW5djs2Mmod3M6ugCCKc59Eb5O19WZImLOzLwRVy9AkHu5iki5LjYY81E7CHWZbVV2BHvgY-tQjOnLflbt1_319F_0cQEM4aYENB5WIa6Y2rGweMAGlWf4lXFhe-FWZqys-GtaasyeuG9M3o1uo9Ox3kDm7V_m2CH1J2kYgKn4pxCKzS9g6VlXglaXthKkh3Ocslu2oB7wb3QLMjEnBS5Akc0Ha6Fsp1tzwXI9BHbwViH2-Zs54Itv9Iw2Psr4DXomCjhTAWBwIB_W7znLaiR1GGb-tKam-DVDWcM0XPKDX1ACTSS1r5dIkB8KFe8NmrLnmAVODjZ5o_9uXut3-XhIV8fbSwsjBaxXcUbtT_xzECgrMLBM2DvkDbcAmt5PucQDNLRug6weJVQoxinj9BmxvmR6JnBOzJ2J_ITzybvMckHPNG-eiIG4Mhfj3jFYgHWrMMIBT2wAlgr21Gk9-n6tdeASJn7LvqjR2_gPnJYYvxovCgsN2upU34INN_UNia-VoyzaFQ9hVsL5l_xavnVbo0xW9j4EMrS_SvWV1mqPc-eQrGkrIjXXTxIj9cyV0JGd6OIgR1jP56eTVn1ae_mL736bCztmg2UE5xiKPdRljRZKA94N63PQ7PhC2CKed0JV_gOkCAD64TDjgABIzBxFMGjM-rzQ5mO0VoySS6fiMADRz50AC0GsBks6kkw5AWuzpOj2UFqTszd2CKYZWBa1K0hUK_yJNq5RMWiA3GwHJDf1aIzSs1JPt6wI-fKN0uHD6V0WC0_oSCVqupkcxY57_cYA6Uf6TCQi5pf2kTq_wvHC8x7hiTnDDTtVs6Qik; LogoutRedirectURL=%2Fsaml%2Fsignout; vhvklass.ASPXAUTH=49A33F4438C1363D633296E74D95555C70AAEAB6B7445C622B4D73D22B13A7A4BBCB2B43B175F2085CB9376F9E8A6F536FC9AE37935BC563D795A6F82B9EDC5CF5CCA8E941069F555E81168F2AF855F827BB968746FF9B7D030D3906CF1BBF374C102E9B18F4C2CAB85DDE4BA4A01950ABA8C71576B59FF5540569F0D0392382400F07E8; vk.vh.localization=c%3Dsv-SE%7Cuic%3Dsv-SE; vk-pointer=mouse"
    return "se.vklass.authentication=CfDJ8AF1v64zmWNJt9xTu8U9aMqtp6AXX_nULCYPFPFxok9u4pUrSFZ5_X-q6ggJZDIrffD5X-G01xTAYt3Wobu2v7P9nSRIdzVFBwlSfgq5SAxZMOwG4QdFfCSsxjJ_FcmcNhvkMV8HjQzN0RHkjID8ojkf74by9wxRwtKSikjRF9MLQSV7M3c8Ol8rQKu0P0uXUVEd3lS8vHiYEpEcutnvnIHq8b6MJw1Qd2psNmtZvOWLRpGR4eTURyu-4d4lWVwKQJ79iCoJoDXIP4vT85pH_c2X7vgn7JnGADZ9U1b3m6q95y0b7OLq2wDYWipaFAKivR_exRr5Xrs2vPujFULpc4ubczLN3e5WhVxKi7fci8wrs3T1Bf0duxp94UdPQne_riFjdj55C2IOj7_UXyLgNMbZ6zxs5-Gi5NcgXBkvwtSxAyTOjYSmHZFJ4ue7ehLJyVi5objjnwd8dVgaQ5h71ipXwu7EdU1WryG4KnW0sQNAQboXuI4rLFaMu2maAhTAKTZAt-X0bkRZKYqFwkasbxe98r_gLBl2fENJFSuv6TNW09N808-G_5qPdHz5EcIOIkBhsmupDeHFroF2rLUzEW9WeqBZ7Q_Qibii9kS_WbARXtVSZPusOxxsS9XeDo-rurCOd_avvxBprLcWGElQeMH5BFCoqXD-XcJkrLvpMhkMYmoNNZgRkpJs2RWVPO56e0TbIAdI9Bql8RJztPTFxiamFhM4E4LFy2FReOfROvbSS532HqJBX47Ydc7MbWhfxkb1lz7zSyMisFBVVpLMCVu-vn5Ts9-3mLj2yzDCIpV_u5oXUy3_-Qpl4HxUx7HvC9Ec_jxLTJ2XrFz3-xsZ3ROuq-qZHMfd6lrjS7ZTUvuqIIz87O0A67vsM-U38UizdGMH6HT0A8X2FHVDjqCiX7OZ9DWH7taLDQEzcSVQAPs7OttBY5KZKluf09RlpYIvHbjOqw_Oagi1aYTLHyd9-yzcjvG24BJquq9vwg-IbtzcMRtGgDJiO62miD2iHIzPd1652V3iV9SkpXoZc08Ac-sTZjXv7EWNWVw9z23tu9kMR9dX9JVRSBd3-4AMM034bfV_0lUyeNmQH91b1pc2gVdsIvwkaO9fFzVEctDQhaObYKdBORQ2PaP3Q00IdMhXI7n5KEkh5mXS7fJzGclgFgZsBliZPNUsBx26h2TbxejwIULKnebyEUKOWbS_O41kYnJ8BzzIcIpt_l_YzmXXu9XZNevrHqVQiF3Azs1RIeCUMtnM5EfQn9H64wkmnrveL2C8Dh9drVN5wjGaWECb_evSwJRI26BP_-4RN_GAp91YYu0-I8_TRFR5qNT3yTJ2gXMWw2c5vLQ38zEJ949gjV1M9KCmeyBgcA02zN17R0LiOMnNzIZILNJnNKtKsLMo3Q79hsL3yyAUiRYvd1VtdHproRZTeMpXMFvR7ARGBzuf3GMo4HzHlj_KehDPDW8xfa1-kwlLb0QHTmTBUyV3D4o1GTMOzJZF7WlVE3peIOKgxDkNBUqh0I8yhHmLrZXRIVWM5-3qn8fPuCf6EYAfwU3heJwIMyFCDYKC2cp6Vx98Jf_Z3GpLPjqUZAITZl4q4V_ApdV1bQEZMwwfMBk-5Eo"
    
async def onAuthFail(msg:str = None):
    print (f"onAuthFail callback {msg}")


async def onCookieUpdate (cookie):
    cstr = "; ".join(f"{k}={v}" for k, v in cookie.items())
    print (f"New cookie: {cstr}")

# override default with script argument "p test.py mashie4b"

'''
config = {

    VKLASS_CONFKEY_COOKIE_RETRIVAL_METHOD   # VKLASS_COOKIE_RETRIVAL_METHOD_MANUAL | VKLASS_COOKIE_RETRIVAL_METHOD_FUNCTION | VKLASS_COOKIE_RETRIVAL_METHOD_FILE | VKLASS_COOKIE_RETRIVAL_METHOD_LOGIN
    VKLASS_CONFKEY_ASYNC_COOKIE_CB          # async function to retrieve auth cookies (VKLASS_COOKIE_RETRIVAL_METHOD_FUNCTION)
    VKLASS_CONFKEY_USERNAME                 # username (VKLASS_COOKIE_RETRIVAL_METHOD_LOGIN)
    VKLASS_CONFKEY_PASSWORD                 # password (VKLASS_COOKIE_RETRIVAL_METHOD_LOGIN)
    VKLASS_CONFKEY_COOKIEFILE               # cookie file path (VKLASS_COOKIE_RETRIVAL_METHOD_FILE)
    VKLASS_CONFKEY_COOKIEFILE_TYPE          # cookie file type: VKLASS_CONFKEY_COOKIEFILE_TYPE_CHROMIUM | VKLASS_CONFKEY_COOKIEFILE_TYPE_FIREFOX
    VKLASS_CONFKEY_KEEPALIVE_MIN            # minutes between keepalive calls
    VKLASS_ASYNC_ON_AUTH_FAIL_CB            # async callback function to notify when Authentication has failed, and the VKLASS_CONFKEY_COOKIE_RETRIVAL_METHOD did not resolve auth (manual action needed, BankId login etc)
    VKLASS_ASYNC_ON_AUTH_COOKIE_UPDATE      # async callback function to notify when the vklass cookies was updated due to a server set-cookie response, plaintext cookie as input parameter
}
'''

configs = {
    "manual" : {
        VKLASS_CONFKEY_COOKIE_RETRIVAL_METHOD   : VKLASS_COOKIE_RETRIVAL_METHOD_FUNCTION,
        VKLASS_CONFKEY_ASYNC_COOKIE_CB          : getCookie,
        VKLASS_CONFKEY_USERNAME                 : None,
        VKLASS_CONFKEY_PASSWORD                 : None,
        VKLASS_CONFKEY_COOKIEFILE               : None,
        VKLASS_CONFKEY_COOKIEFILE_TYPE          : None,
        VKLASS_CONFKEY_KEEPALIVE_MIN            : 1,
        VKLASS_ASYNC_ON_AUTH_FAIL_CB            : onAuthFail,
        VKLASS_ASYNC_ON_AUTH_COOKIE_UPDATE      : onCookieUpdate,
    },
    "win-chrome" : {
        VKLASS_CONFKEY_COOKIE_RETRIVAL_METHOD   : VKLASS_COOKIE_RETRIVAL_METHOD_FILE,
        VKLASS_CONFKEY_ASYNC_COOKIE_CB          : None,
        VKLASS_CONFKEY_USERNAME                 : None,
        VKLASS_CONFKEY_PASSWORD                 : None,
        VKLASS_CONFKEY_COOKIEFILE               : VKLASS_CONFKEY_COOKIEFILE_TYPE_CHROMIUM,
        VKLASS_CONFKEY_COOKIEFILE_TYPE          : None,
        VKLASS_CONFKEY_KEEPALIVE_MIN            : 1,
        VKLASS_ASYNC_ON_AUTH_FAIL_CB            : onAuthFail,
        VKLASS_ASYNC_ON_AUTH_COOKIE_UPDATE      : onCookieUpdate,
    }
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
        gw = VklassGateway(asyncio.to_thread, session, configs[confName])
        gw.DEBUG = True
        gw.DUMP_TO_FILE = True
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

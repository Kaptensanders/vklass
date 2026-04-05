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
    return "se.vklass.authentication=CfDJ8AF1v64zmWNJt9xTu8U9aMobtK_Sjg8i2SfsiDdgqBqNC89cygX_W_hlnLezBf-riC6lKkYKUUggwAVL02OyWWCIFjMbXL6CLMT80bd0-IJ3bbnwz6CQpssu1VtoC-ZRkUfi-u8INTFFhG_ZfQuDgeruPZYdZkYKAzij_fCT2b7_XvHLzwWF9-FAbrPiNz7EoMaKVUSYpmTaFNEy3ysIsdG4LeKo0SdxhesnDZoLTgmFalqrK0aOUvDBDePCqYWJ150Gp20k840ZGBtrrkFtOrH4Vx3jB6n2ZIppiEdEZRLqPOF90w4AuJIZhOrm0unobRJ3QkoFmT7LtiApUOhOdAVv7oFjMpMzXwyTOAtMkzbiOGBCeck8_D-Qs69TR_PEm5os3G50uCZqemAwLaBsF4ObtgRggvKkh1qsmTCLxfVC67CF18mwIcC5fdVhQZ3tNuM6KNDGtB0feja7G3n5cHs9SBZGgQzma4X4mRSoOQLpanXjOQMVfJEQs-jhPJRcT4Ml2asYsNK15SKzpCVuxPmO1ABB8td7WxGbu7p2ASQFTWBhH_WW9zivdmFNnB1w99b2uxxnJiq85eb8x_xgDwkyRaKkz_Bi2qkP36T89Z2lQN8Ac-C_Y46qTnW2rT3f48bjAsOT6Fcn79qdXnVv3TbKudLtB5yll3o5psEnqR3jKbKFvhOUORwuA0dIUnzv3oWcq0Ni3rdvnHuJ2fM2B5Kg5RoojEShVN1b34VZlP_0YLw2cXgTni3ud6R1LphcT_3uXJgUBbOl70W__k6cxML5WZ613h8ign-Og30Oe32A7OX2A-ePDIBMp8eAob_K9WU1juiUzKBnQE2s1yGgstwde-2ZaVyUg4zJuacZB9EFEdGXpJl_5PhKQLBr8LYI1x1bZCItHX8he_s3CiEXJ2c77QYf-8ibuc-E0XdLh20xF12uxJhv7NA37Neie4BbEXa-JsliKGOuXa9jjeVS9Y2k_aS8MzoQau7-JWo0SoMq6osMyH4fTqmj7XFfUEH6WthmHouNiajhe1wuh-3X8xhlODgFtbEd1gWjO4yDrTRGZ1Y1LBrs_OZNuCmYLq9SDhGtGD-3qpVqS1bgeIJ1yU6hs8RqYV6xm5wnMimxqytw0jtyoJALRoEsbWWjZKlxR0ON-crpNW_UzxjEp_X-uZR5kt2KtwuJsPpm84DgJTOf2V2k_vTdxxJMtfwCJH0SjEHQb2UIIOfMi2T7U8Lpj1ooX_OcIztUL5Rz21zb3H7VtSW0i16mL1eO0Tf0hopTZQFVY1mLPxhGD215ZTEFaNkhj4tquol8TsCtZHc5ZLOddaAQpxX-kvVTPvKoZI63c3vi8zNpminfSMcH6Q7LhEPmkYsQMUr4THePskdwsSDpE1bLgSyK9hQjB8zlLWL_-elsu7YjGPcvKsFuEvrvAnsyBtR4de0NBP-SEa8qfUCkyj3-j5JHW1VDUUNfbS7XEtryAv7-4MjGubVxIaqrGinu1WGW6NiQ71XW7nB1yuQr4bruzvj2Isb3vOfIlvjY8k_acTTG35OOt52mfk20bAO_o_ZUeCcUEbkB35FoGHaG6RmZEdU--oDRCgUF7vw2dSvLuH-gMyHALHhGMlz_6KA; LogoutRedirectURL=%2Fsaml%2Fsignout; vhvklass.ASPXAUTH=418D3C1CBE653FA694BA45DB43DD986EC81D37414217D6FD264F926A76CDBCCBD489F085352713D9E54211B0A2143169DB3B6D6FAED6B54FDF4D7791F316F579F8CA88345A556940115F521A6BC2C40918E1C73688733D80D95633EFE00922DD969A82587C523A1160ECB685F2FB5D09E44B46837652371D8B130F6DEED90BDDCE4EE1D0; vk.vh.localization=c%3Dsv-SE%7Cuic%3Dsv-SE; vk-pointer=mouse"
    
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

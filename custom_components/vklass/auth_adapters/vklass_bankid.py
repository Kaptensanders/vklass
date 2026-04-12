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


from ..const import (
    AUTH_ADAPTER_ATTR_TITLE,
    AUTH_ADAPTER_ATTR_METHOD,
    AUTH_ADAPTER_ATTR_AUTH_FUNCTION,
    AUTH_METHOD_BANKID_PERSONNO,
)

AUTH_ADAPTERS = {
    "manual_cookie" : {
        AUTH_ADAPTER_ATTR_TITLE : "Vklass BankID, inloggning med personnummer",
        AUTH_ADAPTER_ATTR_METHOD: AUTH_METHOD_BANKID_PERSONNO,
        AUTH_ADAPTER_ATTR_AUTH_FUNCTION: "authenticate"
    }
}

async def authenticate(aiohttp_session, asyncQrNotifyHandler, credentials:dict|None) -> bool:
    raise NotImplementedError("vklass bankid login not implemented")



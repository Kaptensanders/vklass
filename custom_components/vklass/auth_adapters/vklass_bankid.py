# stub for vklass bankid login
# interactive

####################################################################
# adapters must define:
# 
# AUTH_METHOD = AUTH_METHOD_BANKID_QR | AUTH_METHOD_BANKID_PERSONNO | AUTH_METHOD_USERPASS
# AUTH_INTERACTIVE = True | False
# ADAPTER_DESCRIPTION = description of use case. Shown in config flow if multiple adapters match the auth url
# def can_handle(url) -> bool
# async def authenticate(aiohttp_session, authUrl, asyncQrNotifyHandler) -> bool
#

from ..const import AUTH_METHOD_BANKID_PERSONNO

ADAPTER_DESCRIPTION = "Vklass BankID inloggning med personnummer"
ADAPTER_AUTH_METHOD = AUTH_METHOD_BANKID_PERSONNO
ADAPTER_AUTH_INTERACTIVE = True


def can_handle(url:str) -> bool:
    return "auth.vklass.se/bankid" in url

async def authenticate(aiohttp_session, authUrl, asyncQrNotifyHandler) -> bool:
    raise NotImplementedError("vklass bankid login not implemented")

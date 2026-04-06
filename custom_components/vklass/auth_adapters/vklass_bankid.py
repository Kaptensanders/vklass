# stub for vklass bankid login
# interractive

def can_handle(url:str) -> bool:
    return "auth.vklass.se/bankid" in url

def is_interractive() -> bool:
    return True

def authenticate(url:str, aiohttp_session, config) -> bool:
    raise NotImplementedError("vklass bankid login not implemented")

# stub for vklass user credentials login
# non-interractive

def can_handle(url:str) -> bool:
    return "auth.vklass.se/credentials" in url

def is_interractive() -> bool:
    return False

def authenticate(url:str, aiohttp_session, config) -> bool:
    raise NotImplementedError("vklass username and password login not implemented")

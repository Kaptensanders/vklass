
def can_handle(url:str) -> bool:
    return "auth.vklass.se/credentials" in url


def authenticate(url:str, aiohttp_session, config) -> bool:
    raise NotImplementedError("vklass username and password login not implemented")

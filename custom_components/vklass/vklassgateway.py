from abc import ABC, abstractmethod
import inspect
from logging import getLogger
from bs4 import BeautifulSoup
from http.cookies import SimpleCookie
from yarl import URL
import importlib
import pkgutil
import re
import json
import asyncio
import aiohttp
from contextlib import suppress
from .const import (
    VKLASS_CONFKEY_AUTH_URL,
    VKLASS_CONFKEY_PERSONNO,
    VKLASS_CONFKEY_USERNAME,
    VKLASS_CONFKEY_PASSWORD,
    VKLASS_CONFKEY_KEEPALIVE_MIN,

    VKLASS_HANDLER_ON_AUTH_EVENT,
    VKLASS_HANDLER_ON_AUTHCOOKIE_UPDATE,
    VKLASS_HANDLER_ON_AUTH_QRCODE_UPDATE,

    AUTH_STATUS_INPROGRESS,
    AUTH_STATUS_SUCCESS,
    AUTH_STATUS_FAIL,

    AUTH_METHOD_BANKID_QR,
    AUTH_METHOD_BANKID_PERSONNO,
    AUTH_METHOD_USERPASS,
    AUTH_METHOD_MANUAL_COOKIE    
)

log = getLogger(__name__)

'''
config = {

    VKLASS_CONFKEY_PERSONNO                     # personal number      
    VKLASS_CONFKEY_USERNAME                     # username (VKLASS_COOKIE_RETRIVAL_METHOD_LOGIN)
    VKLASS_CONFKEY_PASSWORD                     # password (VKLASS_COOKIE_RETRIVAL_METHOD_LOGIN)
    VKLASS_CONFKEY_KEEPALIVE_MIN                # minutes between keepalive calls
}
'''

_EPKEY_URL              = "url"
_EPKEY_SUCCCESS_CODE    = "success_code"
_EPKEY_CONTENTTYPE      = "contenttype"
_EPKEY_ALLOWREDIRECTS   = "allow_redirects"

_EPTYPE_JSON            = "application/json"
_EPTYPE_HTML            = "text/html"

_AUTH_COOKIE_NAME       = "se.vklass.authentication"
_AUTH_COOKIE_DOMAIN     = ".vklass.se"

_VKLASS_URL_BASE        = "https://custodian.vklass.se"
_EP_LOGIN               = "login"
_EP_LOGIN_AUTH          = "login_auth"
_EP_VKLASS_HOME         = "home"
_EP_VKLASS_CLASSLIST    = "classlist"
_EP_VKLASS_CALENDAR     = "calendar"

_ENDPOINTS = {
    _EP_LOGIN : {
        _EPKEY_URL              : "https://auth.vklass.se/credentials",  
        _EPKEY_SUCCCESS_CODE    : 200,
        _EPKEY_CONTENTTYPE      : _EPTYPE_HTML,
        _EPKEY_ALLOWREDIRECTS   : False
    },
    _EP_LOGIN_AUTH : {
        _EPKEY_URL              : "https://auth.vklass.se/credentials/signin",  
        _EPKEY_SUCCCESS_CODE    : 301,
        _EPKEY_CONTENTTYPE      : _EPTYPE_HTML,
        _EPKEY_ALLOWREDIRECTS   : True
    },
    _EP_VKLASS_HOME : {
        _EPKEY_URL              : "/Home/Welcome",  
        _EPKEY_SUCCCESS_CODE    : 200,
        _EPKEY_CONTENTTYPE      : _EPTYPE_HTML,
        _EPKEY_ALLOWREDIRECTS   : False
    },
    _EP_VKLASS_CLASSLIST : {
        _EPKEY_URL              : "/ClassList/Index",  
        _EPKEY_SUCCCESS_CODE    : 200,
        _EPKEY_CONTENTTYPE      : _EPTYPE_HTML,
        _EPKEY_ALLOWREDIRECTS   : False
    },
    _EP_VKLASS_CALENDAR : {
        _EPKEY_URL              : "/Events/FullCalendar",  
        _EPKEY_SUCCCESS_CODE    : 200,
        _EPKEY_CONTENTTYPE      : _EPTYPE_JSON,
        _EPKEY_ALLOWREDIRECTS   : False
    },
}

def _get_ep_url (endpoint:str):
    ep = _ENDPOINTS[endpoint]
    if ep[_EPKEY_URL].startswith("/"):
        return _VKLASS_URL_BASE + ep[_EPKEY_URL]
    return ep[_EPKEY_URL]

log = getLogger(__name__)

_ADAPTER_ATTR_NAME="name"
_ADAPTER_ATTR_CAN_HANDLE="can_handle"
_ADAPTER_ATTR_DESCRIPTION="ADAPTER_DESCRIPTION"
_ADAPTER_ATTR_AUTH_INTERACTIVE="ADAPTER_AUTH_INTERACTIVE"
_ADAPTER_ATTR_AUTH_METHOD="ADAPTER_AUTH_METHOD"
_ADAPTER_ATTR_AUTHENTICATE="authenticate"

def load_auth_adapters() -> list | None:

    adapters = []
    package_name = f"{__package__}.auth_adapters"
    package = importlib.import_module(package_name)

    for _, module_name, _ in pkgutil.iter_modules(package.__path__):
        module = importlib.import_module(f"{package_name}.{module_name}")

        adapters.append ({
            _ADAPTER_ATTR_NAME              : module_name,
            _ADAPTER_ATTR_DESCRIPTION       : getattr(module, _ADAPTER_ATTR_DESCRIPTION),
            _ADAPTER_ATTR_CAN_HANDLE        : getattr(module, _ADAPTER_ATTR_CAN_HANDLE),
            _ADAPTER_ATTR_AUTH_METHOD       : getattr(module, _ADAPTER_ATTR_AUTH_METHOD),
            _ADAPTER_ATTR_AUTH_INTERACTIVE  : getattr(module, _ADAPTER_ATTR_AUTH_INTERACTIVE),
            _ADAPTER_ATTR_AUTHENTICATE      : getattr(module, _ADAPTER_ATTR_AUTHENTICATE)
        })

    return adapters

_AUTH_ADAPTERS = load_auth_adapters()

def get_auth_adapter(auth_url: str | None) -> dict | None:
    """Return the first auth adapter that can handle the configured URL."""        
    for adapter in _AUTH_ADAPTERS:
        if adapter["can_handle"](auth_url):
            return adapter
    return None


class ObjBase(ABC):
    DEBUG = False
    DUMP_TO_FILE = False

    async def _dumpData(self, data, fileName = None):
        if not self.DEBUG: 
            return

        dump = "" if data is None else str(data)
        ext = "txt"

        if isinstance(data, (dict, list)):
            dump = json.dumps(data, indent=4, ensure_ascii=False)
            ext = "json"

        if self.DUMP_TO_FILE:
            fn = fileName or f"data_dump.{ext}"
            with open(fn, "w", encoding="utf-8") as f:
                f.write(dump)
        else:
            log.info(dump)


class VklassSession(ObjBase):

    def __init__(self, config):
        super().__init__()
        self._config = config
        self._reAuth = False
        self._authFail = False
        self._students = {}
        self._keepAliveTask = None
        self._auth_adapter = self._load_auth_adapter()
        self._async_handlers = {}
        self._aiohttp_session = self._initAioHttpSession()


    def _initAioHttpSession (self):
        timeout = aiohttp.ClientTimeout(total=15)
        return aiohttp.ClientSession(
            cookie_jar=aiohttp.CookieJar(quote_cookie=False),
            requote_redirect_url=False,
            timeout=timeout,
            raise_for_status=False,
            headers={
                "accept": "*/*",
                "content-type": "application/x-www-form-urlencoded",
                "origin": _VKLASS_URL_BASE,
                "referer": f"{_VKLASS_URL_BASE}/",
                "user-agent": "Mozilla/5.0",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }
        )

    # call for graceful unload
    async def shutdown (self):
        await self.stopKeepAlive()
        if not self._aiohttp_session.closed:
            await self._aiohttp_session.close()


    def _load_auth_adapter(self):
        authUrl = self._config.get(VKLASS_CONFKEY_AUTH_URL)
        adapter = get_auth_adapter(authUrl)
        if not adapter:
            log.warning(f"No Vklass auth adapter found for {authUrl}")   

        return adapter

    # returns auth_method, is_interactive
    def getAuthMethod (self):
        
        if not self._auth_adapter:
            return AUTH_METHOD_MANUAL_COOKIE, True 

        return self._auth_adapter[_ADAPTER_ATTR_AUTH_METHOD], self._auth_adapter[_ADAPTER_ATTR_AUTH_INTERACTIVE]


    def registerHandler (self, handlerKey:str, coroutine):

        if not inspect.iscoroutinefunction(coroutine):
            raise ValueError("registerHandler: argument must be coroutine")

        if handlerKey not in [VKLASS_HANDLER_ON_AUTH_EVENT, VKLASS_HANDLER_ON_AUTHCOOKIE_UPDATE, VKLASS_HANDLER_ON_AUTH_QRCODE_UPDATE]:
            raise KeyError(f"handlerKey: {handlerKey} not recognized")

        if handlerKey not in self._async_handlers:
            self._async_handlers[handlerKey] = []

        self._async_handlers[handlerKey].append(coroutine)

    def getHandlers(self, handlerKey:str) -> list:
        
        if handlerKey not in self._async_handlers:
            return []
        return self._async_handlers[handlerKey]


    async def setAuthCookie(self, value:str):

        if not value:
            return

        # update the self._aiohttp_session cookie jar with the new cookie, so that it is included in subsequent requests, and also update the internal cookie dict 
        cookie = SimpleCookie()
        cookie[_AUTH_COOKIE_NAME] = value
        c = cookie[_AUTH_COOKIE_NAME]
        c["domain"] = _AUTH_COOKIE_DOMAIN
        c["path"] = "/"
        c["secure"] = True
        c["httponly"] = True

        self._aiohttp_session.cookie_jar.update_cookies(
            cookie,
            response_url=URL(_VKLASS_URL_BASE),
        )

        self._setAuthSuccess()
        await self._notifyAuthCookieUpdate()
        await self._onAuthUpdate(AUTH_STATUS_SUCCESS, "Auth cookie set manually")


    def isAuthFail (self) -> bool:
        return self._authFail

    async def _onAuthUpdate(self, state:str, message:str|None = None):
        log.info(message)
        handlers = self.getHandlers(VKLASS_HANDLER_ON_AUTH_EVENT)
        for fn in handlers:
            await fn(state, message)

    async def _setAuthFail(self):
        self._authFail = True

    def _setAuthSuccess(self):
        self._authFail = False


    async def authenticate (self, force:bool = False, allow_interactive:bool = False) -> bool:

        # callback helper auth adaptors that need to propagate qr codes
        async def _notifyQrCodeUpdate(qrCode:str):
            handlers = self.getHandlers(VKLASS_HANDLER_ON_AUTH_QRCODE_UPDATE)
            if not handlers:
                return
            
            for fn in handlers:
                await fn(qrCode)

        if not force and self._aiohttp_session.cookie_jar.filter_cookies(URL(_VKLASS_URL_BASE)).get(_AUTH_COOKIE_NAME):
            return True

        if not self._auth_adapter:
            msg = "No authentication adapter available, cannot authenticate"
            await self._onAuthUpdate(AUTH_STATUS_FAIL, msg)
            raise RuntimeError(msg)

        if self._auth_adapter[_ADAPTER_ATTR_AUTH_INTERACTIVE] and not allow_interactive:
            msg = f"Authentication adapter {self._auth_adapter[_ADAPTER_ATTR_NAME]} requires interactive authentication"
            await self._onAuthUpdate(AUTH_STATUS_FAIL, msg)
            raise RuntimeError(msg)

        await self._onAuthUpdate(AUTH_STATUS_INPROGRESS, "Authentication process started")

        try:
            # clear all cookies before this, so we dont have any legacy attemps
            # causing issues
            self._aiohttp_session.cookie_jar.clear()
            if not await self._auth_adapter[_ADAPTER_ATTR_AUTHENTICATE](self._aiohttp_session, self._config[VKLASS_CONFKEY_AUTH_URL], _notifyQrCodeUpdate):
                raise PermissionError("Vklass authentication failed")
        except Exception as err:
            await self._onAuthUpdate(AUTH_STATUS_FAIL, str(err))
            await self._setAuthFail()
            raise

        # verify auth successful
        cookie = self._aiohttp_session.cookie_jar.filter_cookies(URL(_VKLASS_URL_BASE)).get(_AUTH_COOKIE_NAME)
        if not cookie:
            msg = f"Authentication failed, {_AUTH_COOKIE_NAME} cookie not found in aiohttp session"
            await self._onAuthUpdate(AUTH_STATUS_FAIL, msg)
            await self._setAuthFail()
            raise PermissionError(msg)


        await self._notifyAuthCookieUpdate()
        await self._onAuthUpdate(AUTH_STATUS_SUCCESS, "Vklass authentication successful")
        return True

    async def logout (self):
        self._aiohttp_session.cookie_jar.clear()
        await self._onAuthUpdate(AUTH_STATUS_FAIL, "Logged out")
        await self._setAuthFail()

    async def _notifyAuthCookieUpdate(self, response_cookies = None) -> None:

        handlers = self.getHandlers(VKLASS_HANDLER_ON_AUTHCOOKIE_UPDATE)
        if not handlers:
            return

        if isinstance(response_cookies, str) and response_cookies == "logout":
            for handler in handlers:
                await handler(None)
            return

        # get from response_cookies
        if response_cookies:
            for cookies in response_cookies:
                for name, morsel in cookies.items():
                    if name == _AUTH_COOKIE_NAME:
                        for handler in handlers:
                            await handler(morsel.value)
                        return
            return
        
        # get from session
        cookie = self._aiohttp_session.cookie_jar.filter_cookies(URL(_VKLASS_URL_BASE)).get(_AUTH_COOKIE_NAME)
        if not cookie:
            log.error (f"_notifyAuthCookieUpdate: {_AUTH_COOKIE_NAME} cookie not found in aiohttp session")
            return

        for handler in handlers:
            if not cookie.value:
                await handler(None)
            else:
                await handler(cookie.value)
        return



    async def _fetch (self, ep_key:str, data = None) -> str | dict :

        ep = _ENDPOINTS[ep_key]

        await self.authenticate(force=self._reAuth)
        request_method = self._aiohttp_session.get if data is None else self._aiohttp_session.post
        request_kwargs = {
            "allow_redirects": ep[_EPKEY_ALLOWREDIRECTS],
            "raise_for_status": False,
            "timeout": 30,
        }
        if data is not None:
            request_kwargs["data"] = data

        response_cookies = []

        if self.DEBUG:
            _data = "" if not data else data
            log.info(f"Requested: {ep[_EPKEY_URL]}, {_data}")

        try:
            uri = _get_ep_url(ep_key)
            async with request_method(uri, **request_kwargs) as response:

                if response.status != ep[_EPKEY_SUCCCESS_CODE]:

                    if response.status in (302, 401, 403):
                        if not self._reAuth:
                            self._reAuth = True
                            log.info("Authentication failed, renewing auth cookies and retrying")
                            return await self._fetch(ep_key, data)

                        await self._setAuthFail()
                        raise ConnectionError(f"Authentication failed when fetching {uri}: HTTP {response.status}")

                    raise ConnectionError(f"Unexpected response fetching {ep[_EPKEY_URL]}: HTTP {response.status}, expected {ep[_EPKEY_SUCCCESS_CODE]}")

                # successful request, proceed...
                
                response_cookies = [
                    response_item.cookies.copy()
                    for response_item in [*response.history, response]
                    if response_item.cookies
                ]

                if ep[_EPKEY_CONTENTTYPE] == _EPTYPE_JSON:
                    content = await response.json()
                else:
                    content = await response.text()

        except asyncio.TimeoutError as err:
            raise ConnectionError(f"Timed out fetching {uri}") from err
        except aiohttp.ClientError as err:
            raise ConnectionError(f"Request to {uri} failed: {err}") from err

        self._reAuth = False
        self._setAuthSuccess()
        await self._notifyAuthCookieUpdate(response_cookies)

        if self.DEBUG:
            if ep[_EPKEY_CONTENTTYPE] == _EPTYPE_JSON:
                await self._dumpData(content, f"{ep_key}.json")
            else:
                await self._dumpData(content, f"{ep_key}.html")

        return content

    async def _keepAliveLoop(self, loopLen:int):
        interval_seconds = int(loopLen) * 60
        if self.DEBUG:
            log.info (f"Keepalive starting, {interval_seconds} second intervals")
        
        while True:
            try:
                await asyncio.sleep(interval_seconds)

                if not self._students:
                    await self._mapStudents()
                else:
                    await self._fetch(_EP_VKLASS_HOME)

            except asyncio.CancelledError:
                raise
            except Exception as err:
                log.warning("Vklass keepalive failed: %s", err)

    def startKeepAlive(self):        
        
        if self._keepAliveTask and not self._keepAliveTask.done():
            return

        loopLen = self._config.get(VKLASS_CONFKEY_KEEPALIVE_MIN, 10)
        self._keepAliveTask = asyncio.create_task(self._keepAliveLoop(loopLen))

    async def stopKeepAlive(self):
        task = self._keepAliveTask
        if task is None:
            return

        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
        self._keepAliveTask = None
        log.info ("Keepalive gracefully stopped")

    async def _mapStudents (self):

        html = await self._fetch (_EP_VKLASS_CLASSLIST)
        soup = BeautifulSoup(html, "html.parser")
        students = {}

        select_el = soup.select_one("#SelectedClassIdAndStudentId")
        if select_el is None:
            self._students = {}
            if self.DEBUG:
                log.info("Students found:\n{}")
            return

        for option_el in select_el.select("option"):
            value = option_el.get("value", "").strip()
            if not value:
                continue

            match = re.fullmatch(r"\d+:(\d+)", value)
            if not match:
                continue

            name = option_el.get_text(strip=True)
            if not name:
                continue

            student_id = match.group(1)
            students.setdefault(student_id, name)

        self._students = students
        if self.DEBUG:
            log.info(f"Students found:\n{json.dumps(self._students, indent=4, ensure_ascii=False)}")

        if not students:
            raise RuntimeError("No students found, cannot proceed")


    async def getStudents(self, name=None) -> dict | str:
        if not self._students:
            await self._mapStudents()
        
        return self._students

    async def getStudentIds (self, studentNames:list|None = None) -> list:

        if studentNames is not None and not isinstance(studentNames, list):
            raise TypeError (f"studentNames must be list or None, not {type(studentNames)}")
        
        students = await self.getStudents()

        if studentNames is None:
            return list(students.keys())

        requested_ids = []
        students_by_name = {
            student_name.strip().casefold(): student_id
            for student_id, student_name in students.items()
        }

        for student_name in studentNames:
            normalized_name = str(student_name).strip().casefold()
            student_id = students_by_name.get(normalized_name)
            if student_id is None:
                raise ValueError(f"Student name: {student_name} was not found")
            requested_ids.append(student_id)

        return requested_ids


    async def getStudentNames (self, studentIds:list|None = None ) -> list:

        if studentIds is not None and not isinstance(studentIds, list):
            raise TypeError (f"studentIds must be list or None, not {type(studentIds)}")
        students = await self.getStudents()

        if studentIds is None:
            return list(students.values())

        requested_names = []

        for student_id in studentIds:
            normalized_id = str(student_id)
            student_name = students.get(normalized_id)
            if student_name is None:
                raise ValueError(f"Student id: {student_id} was not found")
            requested_names.append(student_name)

        return requested_names


class VklassGateway(VklassSession):

    def __init__(self, config):
        super().__init__(config)


    async def getCalendar(self, dateBegin:str, dateEnd:str, childIds:list|None=None):

        if not childIds:
            childIds = await self.getStudentIds()

        students = ",".join(str(child_id) for child_id in childIds)
        if not students:
            return []

        data = {
            "students": students,
            "start": dateBegin,
            "end": dateEnd,
        }

        return await self._fetch(_EP_VKLASS_CALENDAR, data)

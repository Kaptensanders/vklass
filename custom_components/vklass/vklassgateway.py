from abc import ABC, abstractmethod
from datetime import date
import inspect
from logging import getLogger
from typing import AsyncIterator
from bs4 import BeautifulSoup
from http.cookies import Morsel
from yarl import URL
import json
import asyncio
import aiohttp
from contextlib import asynccontextmanager, suppress

from .gateway_helpers import (
    vklass_date_to_timestring,
    calendar_parse_events,
    MANUAL_COOKIE_ADAPTER,
    auth_adapter_get,
)

from .const import (
    
    VKLASS_URL_BASE,
    
    VKLASS_CONFKEY_KEEPALIVE_MIN,
    VKLASS_CONFKEY_AUTHADAPTER,
    VKLASS_CREDKEY_PERSONNO,
    VKLASS_CREDKEY_USERNAME,
    VKLASS_CREDKEY_PASSWORD,
    VKLASS_CREDKEY_COOKIE,
    
    VKLASS_HANDLER_ON_AUTH_EVENT,
    VKLASS_HANDLER_ON_AUTHCOOKIE_UPDATE,
    VKLASS_HANDLER_ON_AUTH_QRCODE_UPDATE,
    
    AUTH_STATUS_INPROGRESS,
    AUTH_STATUS_SUCCESS,
    AUTH_STATUS_FAIL,
    
    AUTH_METHOD_BANKID_QR,
    AUTH_METHOD_BANKID_PERSONNO,
    AUTH_METHOD_USERPASS,
    AUTH_METHOD_MANUAL_COOKIE,
    
    AUTH_COOKIE_NAME,

    AUTH_ADAPTER_ATTR_METHOD,
    AUTH_ADAPTER_ATTR_AUTH_FUNCTION,
    
    VKLASS_CONTEXT_USER,
    VKLASS_CONTEXT_SCHOOL,
    VKLASS_CONTEXT_STUDENTS,

)

log = getLogger(__name__)


"""
config = {

    VKLASS_CREDKEY_PERSONNO                     # personal number      
    VKLASS_CREDKEY_USERNAME                     # username (VKLASS_COOKIE_RETRIVAL_METHOD_LOGIN)
    VKLASS_CREDKEY_PASSWORD                     # password (VKLASS_COOKIE_RETRIVAL_METHOD_LOGIN)
    VKLASS_CREDKEY_KEEPALIVE_MIN                # minutes between keepalive calls
}
"""

_AUTH_MAX_FAILS = 3
_AUTH_RETRY_DELAY = 5

_EPKEY_URL = "url"
_EPKEY_SUCCCESS_CODE = "success_code"
_EPKEY_CONTENTTYPE = "contenttype"
_EPKEY_ALLOWREDIRECTS = "allow_redirects"

_EPTYPE_JSON = "application/json"
_EPTYPE_HTML = "text/html"

_EP_VKLASS_HOME = "welcome"
_EP_VKLASS_CUSTODIAN = "custodian"
_EP_VKLASS_STUDENTS = "students"
_EP_VKLASS_CLASSLIST = "classlist"
_EP_VKLASS_CALENDAR = "calendar"


_ENDPOINTS = {
    _EP_VKLASS_HOME: {_EPKEY_URL: "/Home/Welcome", _EPKEY_SUCCCESS_CODE: 200, _EPKEY_CONTENTTYPE: _EPTYPE_HTML, _EPKEY_ALLOWREDIRECTS: False},
    _EP_VKLASS_CUSTODIAN: {_EPKEY_URL: VKLASS_URL_BASE, _EPKEY_SUCCCESS_CODE: 200, _EPKEY_CONTENTTYPE: _EPTYPE_HTML, _EPKEY_ALLOWREDIRECTS: False},
    _EP_VKLASS_STUDENTS: {
        _EPKEY_URL: "/StudyOverview/Student",
        _EPKEY_SUCCCESS_CODE: 200,
        _EPKEY_CONTENTTYPE: _EPTYPE_HTML,
        _EPKEY_ALLOWREDIRECTS: False,
    },
    _EP_VKLASS_CLASSLIST: {_EPKEY_URL: "/ClassList/Index", _EPKEY_SUCCCESS_CODE: 200, _EPKEY_CONTENTTYPE: _EPTYPE_HTML, _EPKEY_ALLOWREDIRECTS: False},
    _EP_VKLASS_CALENDAR: {
        _EPKEY_URL: "/Events/FullCalendar",
        _EPKEY_SUCCCESS_CODE: 200,
        _EPKEY_CONTENTTYPE: _EPTYPE_JSON,
        _EPKEY_ALLOWREDIRECTS: False,
    },
}

def _get_ep_url(endpoint: str):
    ep = _ENDPOINTS[endpoint]
    if ep[_EPKEY_URL].startswith("/"):
        return VKLASS_URL_BASE + ep[_EPKEY_URL]
    return ep[_EPKEY_URL]



class VklassBase(ABC):
    DEBUG = False
    DUMP_TO_FILE = False
    DUMP_FILE_PATH = "./"
    def __init__(self):

        self._async_handlers: dict = {}
        self._aiohttp_session = self._initAioHttpSession()

    @abstractmethod
    async def _notifyAuthCookieUpdate(self, cookie: Morsel | str | None = None) -> bool:
        raise NotImplementedError

    def registerHandler(self, handlerKey: str, coroutine):

        if not inspect.iscoroutinefunction(coroutine):
            raise ValueError("registerHandler: argument must be coroutine")

        if handlerKey not in [VKLASS_HANDLER_ON_AUTH_EVENT, VKLASS_HANDLER_ON_AUTHCOOKIE_UPDATE, VKLASS_HANDLER_ON_AUTH_QRCODE_UPDATE]:
            raise KeyError(f"handlerKey: {handlerKey} not recognized")

        if handlerKey not in self._async_handlers:
            self._async_handlers[handlerKey] = []

        self._async_handlers[handlerKey].append(coroutine)

    async def _notifyHandlers(self, handlerKey: str, *args, **kwargs):

        if not (handlers := self._async_handlers.get(handlerKey, None)):
            return

        for fn in handlers:
            await fn(*args, **kwargs)

    def _initAioHttpSession(self):
        timeout = aiohttp.ClientTimeout(total=15)
        return aiohttp.ClientSession(
            cookie_jar=aiohttp.CookieJar(quote_cookie=False),
            requote_redirect_url=False,
            timeout=timeout,
            raise_for_status=False,
            headers={
                "accept": "*/*",
                "content-type": "application/x-www-form-urlencoded",
                "origin": VKLASS_URL_BASE,
                "referer": f"{VKLASS_URL_BASE}/",
                "user-agent": "Mozilla/5.0",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            },
        )

    @asynccontextmanager
    async def _vklassRequest(self, ep_key: str, data=None) -> AsyncIterator[aiohttp.ClientResponse]:

        ep = _ENDPOINTS[ep_key]
        uri = _get_ep_url(ep_key)

        request_method = self._aiohttp_session.get if data is None else self._aiohttp_session.post
        request_kwargs = {
            "allow_redirects": ep[_EPKEY_ALLOWREDIRECTS],
            "raise_for_status": False,
            "timeout": 30,
        }
        if data is not None:
            request_kwargs["data"] = data

        if self.DEBUG:
            _data = "" if not data else data
            log.info(f"Requested: {ep[_EPKEY_URL]}, {_data}")

        try:
            async with request_method(uri, **request_kwargs) as response:
                # successful request, proceed...
                if authCookie := response.cookies.get(AUTH_COOKIE_NAME):
                    await self._notifyAuthCookieUpdate(authCookie)

                yield response

        except asyncio.TimeoutError as err:
            raise ConnectionError(f"Timed out fetching {uri}") from err
        except aiohttp.ClientError as err:
            raise ConnectionError(f"Request to {uri} failed: {err}") from err

    async def _dumpData(self, data, fileName=None):
        if not self.DEBUG:
            return

        dump = "" if data is None else str(data)

        if isinstance(data, (dict, list)):
            dump = json.dumps(data, indent=4, ensure_ascii=False)

        if self.DUMP_TO_FILE:
            await self._dumpoToFile(dump, fileName)
        else:
            log.info(dump)

    async def _dumpoToFile(self, data: str, fileName=None):

        ext = "html"
        if isinstance(data, (dict, list)):
            ext = "json"

        fn = fileName or f"data_dump.{ext}"
        if not fn.startswith("/"):
            if self.DUMP_FILE_PATH.endswith("/"):
                fn = self.DUMP_FILE_PATH + fn
            fn = f"{self.DUMP_FILE_PATH}/{fn}"

        with open(fn, "w", encoding="utf-8") as f:
            f.write(data)


class VklassSession(VklassBase):

    def __init__(self, config):
        super().__init__()
        self._config: dict = config
        self._context = {}
        self._credentials: dict | None = None
        self._keepAliveTask = None
        self._auth_adapter = auth_adapter_get(config.get(VKLASS_CONFKEY_AUTHADAPTER))
        self._authFails = 0

    # call for graceful unload
    async def shutdown(self):
        await self._stopKeepAlive()
        if not self._aiohttp_session.closed:
            await self._aiohttp_session.close()

    def getVklassContext(self) -> dict:
        """
        context format:
        {
            VKLASS_CONTEXT_USER: {
                <user id> : <user full name>
            },
            VKLASS_CONTEXT_SCHOOL: {
                <school id>: <school name>,
                ... },
            VKLASS_CONTEXT_STUDENTS: {
                <student id>: <student name>,
                ... }
        }
        """

        if not self._context:
            raise RuntimeError("Vklass context not loaded, login first")

        return self._context

    def hasLoadedContext(self) -> bool:
        return bool(self._context)

    def getAuthAdapter(self):
        return self._auth_adapter

    def canAutoLogin(self) -> bool:
        return self._auth_adapter[AUTH_ADAPTER_ATTR_METHOD] in [AUTH_METHOD_USERPASS, AUTH_METHOD_MANUAL_COOKIE]

    async def _onAuthUpdate(self, state: str, message: str | None = None):
        await self._notifyHandlers(VKLASS_HANDLER_ON_AUTH_EVENT, state, message)

    async def _notifyAuthCookieUpdate(self, cookie: Morsel | str | None = None) -> bool:

        if cookie and isinstance(cookie, str) and cookie == "logout":
            await self._notifyHandlers(VKLASS_HANDLER_ON_AUTHCOOKIE_UPDATE, None)
            return True

        if cookie and not isinstance(cookie, Morsel):
            raise ValueError(f"_notifyAuthCookieUpdate: cookie must be of type Morsel or str, not {type(cookie)}")

        if not cookie:
            cookie = self._aiohttp_session.cookie_jar.filter_cookies(URL(VKLASS_URL_BASE)).get(AUTH_COOKIE_NAME)

        if not cookie:
            log.error(f"_notifyAuthCookieUpdate: No cookie provided and {AUTH_COOKIE_NAME} cookie not found in session")
            return False

        await self._notifyHandlers(VKLASS_HANDLER_ON_AUTHCOOKIE_UPDATE, cookie.value)
        return True

    async def login(self, credentials: dict | None, reuse_credentials: bool = False):
        """
        AUTH_METHOD_BANKID_QR:          credentials:None = None
        AUTH_METHOD_BANKID_PERSONNO     credentials:dict = {"personno": <"personal number">}
        AUTH_METHOD_USERPASS            credentials:dict = {"username": <"username">, "password":<"password">}
        AUTH_METHOD_MANUAL_COOKIE       credentials:dict = {"cookie":   <"cookie value">}
        AUTH_METHOD_CUSTOM:             credentials:None = None
        """

        self._credentials = credentials
        try:
            self._authFails = 0
            return await self._authenticate(True, True)
        except Exception:
            self._credentials = None
            raise
        finally:
            if not reuse_credentials:
                self._credentials = None

    async def resumeLoggedInSession(self, authCookieValue: str) -> bool:
        log.info("Attempting to resume session with persisted cookie value")
        # set the cookie using the manual cookie adapter
        manual_adapter = auth_adapter_get(MANUAL_COOKIE_ADAPTER)
        self._aiohttp_session.cookie_jar.clear()
        await manual_adapter[AUTH_ADAPTER_ATTR_AUTH_FUNCTION](self._aiohttp_session, None, {VKLASS_CREDKEY_COOKIE: authCookieValue})
        try:
            await self._verifyAuth()
        except Exception:
            msg = "Failed to resume session with persisted cookie, could not access vklass using stored cookie"
            log.error(msg)
            await self._onAuthUpdate(AUTH_STATUS_FAIL, msg)
            return False

        self._context = {}
        await self._loadSessionContext()
        self._startKeepAlive()
        await self._onAuthUpdate(AUTH_STATUS_SUCCESS, "Vklass session resumed successfully")
        return True

    async def logout(self):
        # Also delete stored credentials if any, to prevent auto login
        self._credentials = None
        self._aiohttp_session.cookie_jar.clear()
        await self._notifyAuthCookieUpdate("logout")
        await self._onAuthUpdate(AUTH_STATUS_FAIL, "Logged out")
        await self._stopKeepAlive()
        self._context = {}

    def _hasAuthCookie(self):
        cookie = self._aiohttp_session.cookie_jar.filter_cookies(URL(VKLASS_URL_BASE)).get(AUTH_COOKIE_NAME)
        return cookie is not None

    async def _verifyAuth(self):

        # verify auth successful
        if not self._hasAuthCookie():
            raise RuntimeError(f"Authentication failed: {AUTH_COOKIE_NAME} cookie not found after authentication")

        ep = _ENDPOINTS[_EP_VKLASS_HOME]
        async with self._vklassRequest(_EP_VKLASS_HOME) as response:
            if response.status != ep[_EPKEY_SUCCCESS_CODE]:
                raise PermissionError(
                    f"Authentication failed: unexpected response code {response.status} from {_EP_VKLASS_HOME}, expected {ep[_EPKEY_SUCCCESS_CODE]}"
                )

        return True

    # return True or raise
    async def _authenticate(self, force: bool = False, isInteractive: bool = False) -> bool:

        # callback helper auth adaptors that need to propagate qr codes
        async def _notifyQrCodeUpdate(qrCode: str, qrType: str):
            await self._notifyHandlers(VKLASS_HANDLER_ON_AUTH_QRCODE_UPDATE, qrCode, qrType)

        if not force and self._hasAuthCookie():
            return True

        # check if we are already authenticated and can access protected resources
        # if so, skip auth process regardeless of force flag. If client/consumer wants to re-authenticate, they should call logout first
        try:
            if await self._verifyAuth():
                return True
        except Exception:
            pass

        # can we authenticate?
        authMethod = self._auth_adapter[AUTH_ADAPTER_ATTR_METHOD]
        try:
            if authMethod == AUTH_METHOD_MANUAL_COOKIE:
                if not self._credentials or VKLASS_CREDKEY_COOKIE not in self._credentials:
                    raise ValueError(f"Cookie '{AUTH_COOKIE_NAME}' value needed for authentication")

            elif authMethod == AUTH_METHOD_BANKID_QR:
                if not isInteractive:
                    raise RuntimeError("Bankid authentication is interactive")

            elif authMethod == AUTH_METHOD_BANKID_PERSONNO:
                if not self._credentials or VKLASS_CREDKEY_PERSONNO not in self._credentials:
                    raise ValueError("Personal number needed for authentication")
                if not isInteractive:
                    raise RuntimeError("Bankid authentication is interactive")

            elif authMethod == AUTH_METHOD_USERPASS:
                if not self._credentials or VKLASS_CREDKEY_USERNAME not in self._credentials or VKLASS_CREDKEY_PASSWORD not in self._credentials:
                    raise ValueError("Username and password needed for authentication")

            # handle failed attempts
            if self._authFails >= _AUTH_MAX_FAILS:
                raise RuntimeError(f"Authentication blocked after {_AUTH_MAX_FAILS} failed attempts")
            elif self._authFails > 0 and self._authFails < _AUTH_MAX_FAILS:
                # Add a small delay before retrying
                log.info(
                    f"Retrying authentication in {self._authFails * _AUTH_RETRY_DELAY} seconds. Previous authentication attempt failed, retrying... (attempt {self._authFails + 1} of {_AUTH_MAX_FAILS})"
                )
                await asyncio.sleep(self._authFails * _AUTH_RETRY_DELAY)

            await self._onAuthUpdate(AUTH_STATUS_INPROGRESS, "Authentication process started")

            # clear all cookies before this, so we dont have any legacy attemps causing issues
            self._aiohttp_session.cookie_jar.clear()
            if not await self._auth_adapter[AUTH_ADAPTER_ATTR_AUTH_FUNCTION](self._aiohttp_session, _notifyQrCodeUpdate, self._credentials):
                raise PermissionError("Vklass authentication failed")

            # validate that we are actually authenticated and can access protected resources
            await self._verifyAuth()

        except Exception as err:
            await self._stopKeepAlive()
            await self._onAuthUpdate(AUTH_STATUS_FAIL, str(err))
            self._authFails += 1
            raise

        self._context = {}
        await self._loadSessionContext()

        # we are live
        await self._notifyAuthCookieUpdate()
        self._startKeepAlive()
        await self._onAuthUpdate(AUTH_STATUS_SUCCESS, "Vklass authentication successful")

        self._authFails = 0
        return True

    async def _fetch(self, ep_key: str, data=None, forceAuthenticate: bool = False) -> str | dict:

        await self._authenticate(force=forceAuthenticate, isInteractive=False)

        ep = _ENDPOINTS[ep_key]

        async with self._vklassRequest(ep_key, data) as response:
            if response.status != ep[_EPKEY_SUCCCESS_CODE]:
                if response.status in (302, 401, 403):
                    if forceAuthenticate:  # we have already tried and succeded with authentication, still no dice
                        raise RuntimeError(
                            f"Unexpected response fetching {ep[_EPKEY_URL]}: HTTP {response.status}, expected {ep[_EPKEY_SUCCCESS_CODE]} even after successful authentication"
                        )

                    return await self._fetch(ep_key, data, forceAuthenticate=True)

                raise ConnectionError(f"Unexpected response fetching {ep[_EPKEY_URL]}: HTTP {response.status}, expected {ep[_EPKEY_SUCCCESS_CODE]}")

            if ep[_EPKEY_CONTENTTYPE] == _EPTYPE_JSON:
                content = await response.json()
            else:
                content = await response.text()

        if self.DEBUG:
            if ep[_EPKEY_CONTENTTYPE] == _EPTYPE_JSON:
                await self._dumpData(content, f"{ep_key}.json")
            else:
                await self._dumpData(content, f"{ep_key}.html")

        return content

    async def _keepAliveLoop(self, loopLen: int):
        interval_seconds = int(loopLen) * 60
        if self.DEBUG:
            log.info(f"Keepalive starting, {interval_seconds} second intervals")

        while True:
            try:
                await asyncio.sleep(interval_seconds)
                await self._fetch(_EP_VKLASS_CUSTODIAN)

            except asyncio.CancelledError:
                raise
            except Exception as err:
                log.warning("Vklass keepalive failed: %s", err)

    def _startKeepAlive(self):

        if self._keepAliveTask and not self._keepAliveTask.done():
            return
        loopLen = self._config.get(VKLASS_CONFKEY_KEEPALIVE_MIN, 10)
        log.info("Keepalive starting, interval: %s minutes", loopLen)
        self._keepAliveTask = asyncio.create_task(self._keepAliveLoop(loopLen))

    async def _stopKeepAlive(self):
        task = self._keepAliveTask
        if task is None:
            return

        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
        self._keepAliveTask = None
        log.info("Keepalive stopped")

    async def _loadSessionContext(self):

        if self._context:
            return self._context

        context = {}

        # load custodian data for user
        html = await self._fetch(_EP_VKLASS_CUSTODIAN)
        soup = BeautifulSoup(html, "html.parser")
        script = soup.find("script", string=lambda s: s and "window['appData']" in s)
        raw = script.string.split("=", 1)[1].strip().rstrip(";")
        raw = raw.strip("'")
        data = json.loads(raw)
        user_id = data.get("userId", None)
        user_name = data.get("userFullName", None)
        if not user_id or not user_name:
            raise RuntimeError("Failed to load session context, user information not found in custodian data")

        context[VKLASS_CONTEXT_USER] = {user_id: user_name}

        # load students page for students and schools
        html = await self._fetch(_EP_VKLASS_STUDENTS)

        # schools
        soup = BeautifulSoup(html, "html.parser")
        schools = {}
        for opt in soup.select("#SchoolId option"):
            schools[opt["value"]] = opt.get_text(strip=True)

        if not schools:
            raise RuntimeError("Failed to load session context, school information not found in students page")

        context[VKLASS_CONTEXT_SCHOOL] = schools

        #  students
        students = {}
        for item in soup.select("vkau-checkable-list-item"):
            inp = item.find("input", {"type": "radio"})
            students[inp["value"]] = item.get("text")

        if not students:
            raise RuntimeError("Failed to load session context, no students found in students page")
        context[VKLASS_CONTEXT_STUDENTS] = students

        self._context = context
        log.info(f"Session context loaded, user: {user_name}, schools: {len(schools)}, students: {len(students)}")


class VklassGateway(VklassSession):
    def __init__(self, config):
        super().__init__(config)

    def getUserName(self) -> str:
        context = self.getVklassContext()
        return next(iter(context[VKLASS_CONTEXT_USER].values()))

    def getUserId(self) -> str:
        context = self.getVklassContext()
        return next(iter(context[VKLASS_CONTEXT_USER].keys()))

    def getStudents(self, name=None) -> dict | str:
        context = self.getVklassContext()
        return context[VKLASS_CONTEXT_STUDENTS]

    def getStudentIds(self, studentNames: list | None = None) -> list:

        if studentNames is not None and not isinstance(studentNames, list):
            raise TypeError(f"studentNames must be list or None, not {type(studentNames)}")

        students = self.getStudents()

        if studentNames is None:
            return list(students.keys())

        requested_ids = []
        students_by_name = {student_name.strip().casefold(): student_id for student_id, student_name in students.items()}

        for student_name in studentNames:
            normalized_name = str(student_name).strip().casefold()
            student_id = students_by_name.get(normalized_name)
            if student_id is None:
                raise ValueError(f"Student name: {student_name} was not found")
            requested_ids.append(student_id)

        return requested_ids

    def getStudentNames(self, studentIds: list | None = None) -> list:

        if studentIds is not None and not isinstance(studentIds, list):
            raise TypeError(f"studentIds must be list or None, not {type(studentIds)}")

        students = self.getStudents()

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

    async def getCalendar(self, year:int, month:int, studentIds: list | None = None) -> list[dict]:
        
        """
        the timespan for the returned data seem to be less than 2 months maximum. So we can fetch only one month
        at the time, thus the year, month design

        returns:

        [
            {
                "context": <str | None>,
                "event_type": <int | None>,    # raw event type from vklass
                "name": <str>,                 # "<context> - <event type label>" or "Vklass Helgdagar"
                "events": [
                    {
                        "uid": <str>,              # stable id derived from detailUrl
                        "detail_url": <str>,       # original detailUrl
                        "start": <str>,            # ISO date for all-day, ISO datetime for timed
                        "end": <str>,              # exclusive end, same type as start
                        "summary": <str>,          # title
                        "description": <str | None>,
                        "location": <str | None>,
                        "cancelled": <bool>,
                    },
                    ...
                ],
            },
        ...
        ]
        
        """

        if not studentIds:
            studentIds = self.getStudentIds()

        students = ",".join(str(student_id) for student_id in studentIds)
        if not students:
            raise RuntimeError("Invalid context, login first.")

        dateBegin = date(year, month, 1)
        if month == 12:
            dateEnd = date(year + 1, 1, 1)
        else:
            dateEnd = date(year, month + 1, 1)

        data = {
            "students": students,
            "start": vklass_date_to_timestring(dateBegin),
            "end": vklass_date_to_timestring(dateEnd),
        }

        raw_calendar = await self._fetch(_EP_VKLASS_CALENDAR, data)
        if not isinstance(raw_calendar, list):
            raise RuntimeError(f"Unexpected calendar payload type: {type(raw_calendar)}")

        return calendar_parse_events(raw_calendar)

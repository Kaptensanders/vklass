from abc import ABC, abstractmethod
from datetime import datetime, date, timezone, timedelta
from dateutil import tz, parser
from logging import getLogger
from collections.abc import Callable
from typing import TypedDict, TypeAlias, Any
from pathlib import Path
from bs4 import BeautifulSoup
from http.cookies import SimpleCookie
from yarl import URL
import re
import json
import asyncio
import aiohttp
from contextlib import suppress
from .const import (
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


'''
config = {

    VKLASS_CONFKEY_AUTH_METHOD                  # VKLASS_AUTH_USERNAME_PASSWORD | VKLASS_AUTH_BANKID_QR | VKLASS_AUTH_BANKID_PERSONALNO
    VKLASS_CONFKEY_PERSONNO                     # personal number (VKLASS_AUTH_BANKID_PERSONALNO)      
    VKLASS_CONFKEY_USERNAME                     # username (VKLASS_COOKIE_RETRIVAL_METHOD_LOGIN)
    VKLASS_CONFKEY_PASSWORD                     # password (VKLASS_COOKIE_RETRIVAL_METHOD_LOGIN)
    VKLASS_CONFKEY_KEEPALIVE_MIN                # minutes between keepalive calls
    VKLASS_CONFKEY_ASYNC_ON_AUTH_FAIL_CB        # async callback function to notify when Authentication has failed, and the VKLASS_CONFKEY_COOKIE_RETRIVAL_METHOD did not resolve auth (manual action needed, BankId login etc)
    VKLASS_CONFKEY_ASYNC_ON_AUTH_COOKIE_UPDATE  # async callback function to notify when the vklass cookies was updated due to a server set-cookie response, cookie value as input parameter    
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
    


'''
config = {

    VKLASS_CONFKEY_AUTH_METHOD                  # VKLASS_AUTH_USERNAME_PASSWORD | VKLASS_AUTH_BANKID_QR | VKLASS_AUTH_BANKID_PERSONALNO
    VKLASS_CONFKEY_PERSONNO                     # personal number (VKLASS_AUTH_BANKID_PERSONALNO)      
    VKLASS_CONFKEY_USERNAME                     # username (VKLASS_COOKIE_RETRIVAL_METHOD_LOGIN)
    VKLASS_CONFKEY_PASSWORD                     # password (VKLASS_COOKIE_RETRIVAL_METHOD_LOGIN)
    VKLASS_CONFKEY_KEEPALIVE_MIN                # minutes between keepalive calls
    VKLASS_CONFKEY_ASYNC_ON_AUTH_FAIL_CB        # async callback function to notify when Authentication has failed, and the VKLASS_CONFKEY_COOKIE_RETRIVAL_METHOD did not resolve auth (manual action needed, BankId login etc)
    VKLASS_CONFKEY_ASYNC_ON_AUTH_COOKIE_UPDATE  # async callback function to notify when the vklass cookies was updated due to a server set-cookie response, cookie value as input parameter    
}
'''

class VklassSession(ObjBase):

    def __init__(self, config, aiohttp_session):
        super().__init__()
        self._config = config
        self._aiohttp_session = aiohttp_session
        self._reAuth = False
        self._authFail = False
        self._students = {}
        self._keepAliveTask = None
        self._headers = {
            "accept": "*/*",
            "content-type": "application/x-www-form-urlencoded",
            "origin": _VKLASS_URL_BASE,
            "referer": f"{_VKLASS_URL_BASE}/",
            "user-agent": "Mozilla/5.0",
        }

    def setAuthCookie(self, value:str):

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

    def isAuthFail (self) -> bool:
        return self._authFail

    async def _setAuthFail(self):
        self._authFail = True
        if fn := self._config.get(VKLASS_CONFKEY_ASYNC_ON_AUTH_FAIL_CB, None):
            await fn()

    def _setAuthSuccess(self):
        self._authFail = False

    async def _handleResponseCookies(self, response_cookies) -> None:

        cb = self._config.get(VKLASS_CONFKEY_ASYNC_ON_AUTH_COOKIE_UPDATE, None)
        if not cb:
            return

        for cookies in response_cookies:
            for name, morsel in cookies.items():
                if name == _AUTH_COOKIE_NAME:
                    await cb(morsel.value)
                    return


    async def _fetch (self, ep_key:str, data = None) -> str | dict :

        ep = _ENDPOINTS[ep_key]

        await self._authenticate(force=self._reAuth)
        request_method = self._aiohttp_session.get if data is None else self._aiohttp_session.post
        request_kwargs = {
            "headers": self._headers,
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
        await self._handleResponseCookies(response_cookies)

        if self.DEBUG:
            if ep[_EPKEY_CONTENTTYPE] == _EPTYPE_JSON:
                await self._dumpData(content, f"{ep_key}.json")
            else:
                await self._dumpData(content, f"{ep_key}.html")

        return content

    async def _authenticate (self, force:bool = False):
        return True


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

    def __init__(self, config, aiohttp_session):
        super().__init__(config, aiohttp_session)


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

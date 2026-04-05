from abc import ABC, abstractmethod
from datetime import datetime, date, timezone, timedelta
from dateutil import tz, parser
from logging import getLogger
from collections.abc import Callable
from bs4 import BeautifulSoup
import re
import json
import asyncio
import aiohttp
from contextlib import suppress
from .const import (
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
    VKLASS_CONFKEY_COOKIEFILE_TYPE_FIREFOX,
)

async def authenticate_bankid_qr(url:str, qrCallback) -> bool:
    ...


async def authenticate_bankid_stub(url:str) -> bool:
    import requests
    from bs4 import BeautifulSoup
    from urllib.parse import urlparse, parse_qs

    session = requests.Session()

    # STEP 1 — load login page
    url = "https://authpub.goteborg.se/sp/sps/eidpub/saml20/logininitial"
    params = {
        "RequestBinding": "HTTPPost",
        "ResponseBinding": "HTTPPost",
        "Target": "https://authpub.goteborg.se/idp/sps/auth?FedId=uuidc69b10fc-018d-1e46-bd45-84b46fd723a9"
    }

    r1 = session.get(url, params=params)
    r1.raise_for_status()

    # STEP 2 — simulate BankID button click
    r2 = session.get(url, params={
        **params,
        "ITFIM_WAYF_IDP": "https://eid-connect.funktionstjanster.se/saml2/65ca0c705a557fb525eb8789"
    })
    r2.raise_for_status()

    # STEP 3 — parse auto-submit form
    soup = BeautifulSoup(r2.text, "html.parser")
    form = soup.find("form")

    action = form["action"]
    payload = {
        inp["name"]: inp.get("value", "")
        for inp in form.find_all("input")
        if inp.get("name")
    }

    # STEP 4 — POST SAML request
    r3 = session.post(action, data=payload, allow_redirects=False)
    r3.raise_for_status()

    # STEP 5 — extract AID
    location = r3.headers["Location"]
    aid = parse_qs(urlparse(location).query)["aid"][0]

    print("AID:", aid)

    # STEP 6 — start BankID
    session.get(
        "https://eid-connect.funktionstjanster.se/id/bankid/auth",
        params={"aid": aid, "id": "631992d934c51e4f39e150b9", "lang": "sv"}
    )

    # STEP 7 — fetch QR
    qr = session.get(
        "https://eid-connect.funktionstjanster.se/id/bankid/qr",
        params={"aid": aid}
    ).text

    print("QR string:", qr)

    # STEP 8 — poll status
    status = session.get(
        "https://eid-connect.funktionstjanster.se/id/bankid/status",
        params={"aid": aid}
    ).json()

    print(status)


async def authenticate_bankid_peronno(url:str, qrCallback) -> bool:
    ...

async def authenticate_userpass(url:str, username:str, password:str) -> bool:
    ... 








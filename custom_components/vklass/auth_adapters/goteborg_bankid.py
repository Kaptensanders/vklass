import json, asyncio # noqa: E401
from logging import getLogger
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
from ..const import VKLASS_CONFKEY_ASYNC_ON_QR_UPDATE

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "sv-SE,sv;q=0.9,en-SE;q=0.8,en;q=0.7,en-US;q=0.6",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}

_AUTH_URL = "https://authpub.goteborg.se/sp/sps/eidpub/saml20/logininitial"
_AUTH_TARGET = "https://authpub.goteborg.se/idp/sps/auth"
_BANKID_BASE = "https://eid-connect.funktionstjanster.se"

log = getLogger(__name__)

def can_handle(url:str) -> bool:
    return "authpub.goteborg.se" in url


def _snippet(value, limit: int = 240) -> str:
    text = str(value).replace("\n", "\\n").replace("\r", "\\r")
    if len(text) <= limit:
        return text
    return f"{text[:limit]}..."


async def authenticate(aiohttp_session, config) -> bool:
    """
    Full BankID QR authentication flow.

    :param session: aiohttp ClientSession (HA: async_get_clientsession)
    :param auth_url: initial login URL
    :param qr_callback: async function(qr_string)
    :return: True if success, False otherwise
    """
    authData = {}

    await _step0_extract_saml_url(aiohttp_session, _AUTH_URL, authData)
    await _step1_get_saml_form(aiohttp_session, authData)
    await _step2_post_saml_and_extract(aiohttp_session, authData)
    await _step3_init(aiohttp_session, authData)
    await _step3_start_bankid_auth(aiohttp_session, authData)
    result = await _step3_poll_qr(aiohttp_session, authData, config.get(VKLASS_CONFKEY_ASYNC_ON_QR_UPDATE))
    # finalization TODO
    # if result:
    #     await _step4_finalize(aiohttp_session, authData)

    return result

# ------------------------------------------------------------
# STEP 0 — get SAML provider URL
# ------------------------------------------------------------

async def _step0_extract_saml_url(session, start_url, authData):
    async with session.get(start_url, headers=_HEADERS) as resp:
        response_status = resp.status
        response_url = str(resp.url)
        response_content_type = resp.headers.get("Content-Type")
        html = await resp.text()

    if response_status != 200:
        raise Exception(f"Failed fetching login page: http_status={response_status}, url={response_url}, content_type={response_content_type}, body={_snippet(html)}")

    soup = BeautifulSoup(html, "html.parser")

    buttons = soup.find_all("button", attrs={"name": "ITFIM_WAYF_IDP"})

    if not buttons:
        raise Exception(f"Found no ITFIM_WAYF_IDP buttons in response from {response_url}, body={_snippet(html)}")

    for btn in buttons:
        value = btn.get("value", "")

        if "bankid" in btn.text.lower() or "bankid" in value.lower():
            authData["saml_url"] = value
            return

    raise Exception(f"BankID SAML URL not found in response from {response_url}, button_values={[btn.get('value', '') for btn in buttons]}")


async def _step1_get_saml_form(session, authData):

    params = {
        "RequestBinding": "HTTPPost",
        "ResponseBinding": "HTTPPost",
        "NameIdFormat": "Transient",
        "Target": _AUTH_TARGET,
        "ITFIM_WAYF_IDP": authData["saml_url"],
    }

    async with session.get(_AUTH_URL, params=params, headers=_HEADERS) as resp:
        response_status = resp.status
        response_url = str(resp.url)
        response_content_type = resp.headers.get("Content-Type")
        html = await resp.text()

    if response_status != 200:
        raise Exception(f"SAML form fetching failed: http_status={response_status}, url={response_url}, content_type={response_content_type}, body={_snippet(html)}")

    if not html.strip():
        raise Exception(f"SAML form returned empty response body from {response_url}")

    soup = BeautifulSoup(html, "html.parser")

    form = soup.find("form")
    if not form:
        raise Exception(f"SAML form not found in response from {response_url}, body={_snippet(html)}")

    action = form.get("action")
    if not action:
        raise Exception(f"SAML form missing action in response from {response_url}, body={_snippet(html)}")

    inputs = form.find_all("input")
    data = {
        inp.get("name"): inp.get("value")
        for inp in inputs
        if inp.get("name")
    }

    if not data:
        raise Exception(f"SAML form contained no named inputs in response from {response_url}, form_action={action}, body={_snippet(html)}")

    if "SAMLRequest" not in data:
        raise Exception(f"SAMLRequest missing in form from {response_url}, form_action={action}, input_names={sorted(data.keys())}")

    if not data.get("RelayState"):
        raise Exception(f"RelayState missing in form from {response_url}, form_action={action}, input_names={sorted(data.keys())}")

    authData["action"] = action
    authData["data"] = data


async def _step2_post_saml_and_extract(session, authData):

    async with session.post(
        authData["action"],
        data=authData["data"],
        headers=_HEADERS,
        allow_redirects=False
    ) as resp:
        response_status = resp.status
        response_url = str(resp.url)
        response_content_type = resp.headers.get("Content-Type")
        final_url = resp.headers.get("Location") or str(resp.url)
        response_body = await resp.text()

    if response_status not in (302, 303):
        raise Exception(
            f"Step2 expected redirect after SAML post but got http_status={response_status}, url={response_url}, content_type={response_content_type}, body={_snippet(response_body)}"
        )

    if not final_url:
        raise Exception(
            f"Step2 missing redirect location after SAML post from {response_url}"
        )

    if not final_url.startswith(f"{_BANKID_BASE}/web/app/v2/"):
        raise Exception(
            f"Step2 unexpected redirect location={final_url}, expected BankID app URL"
        )

    parsed = urlparse(final_url)
    qs = parse_qs(parsed.query)

    aid = qs.get("aid", [None])[0]

    parts = parsed.path.strip("/").split("/")
    if len(parts) < 5:
        raise Exception(f"Step2 unexpected redirect path structure in {final_url}")

    spId = parts[-1] if parts[-1] else parts[-2]
    app_id = parts[-2] if parts[-1] else parts[-3]

    if not aid or not spId:
        raise Exception(f"Step2 failed extracting aid/spId from {final_url}")

    authData["aid"] = aid
    authData["spId"] = spId
    authData["app_id"] = app_id
    authData["app_url"] = final_url


async def _step3_init(session, authData):
    async with session.get(
        f"{_BANKID_BASE}/web/res/api/methods",
        params={
            "aid": authData["aid"],
            "spId": authData["spId"],
            "lang": "sv"
        },
        headers=_HEADERS
    ) as resp:
        init_status = resp.status
        init_content_type = resp.headers.get("Content-Type")
        init_text = await resp.text()

    try:
        init_data = json.loads(init_text)
    except json.JSONDecodeError:
        log.error(
            "BankID init: methods response was not valid JSON. http_status=%s content_type=%s body=%s",
            init_status,
            init_content_type,
            _snippet(init_text),
        )
        raise

    authData["bankid_methods"] = init_data


async def _step3_start_bankid_auth(session, authData):
    methods = authData.get("bankid_methods") or []

    if not methods:
        raise Exception("No BankID methods found in methods response")

    selected_method = methods[0]

    authData["bankid_method"] = selected_method

    async with session.post(
        f"{_BANKID_BASE}/id/bankid/auth",
        params={
            "aid": authData["aid"],
            "id": selected_method["id"],
            "lang": "sv",
        },
        data="",
        headers={
            **_HEADERS,
            "Accept": "*/*",
            "Content-Type": "application/json",
            "Origin": _BANKID_BASE,
            "Referer": authData["app_url"],
        },
    ) as resp:
        auth_status = resp.status
        auth_text = (await resp.text()).strip()

    authData["bankid_auth_token"] = auth_text

    if auth_status != 200:
        raise Exception(f"BankID auth failed with http_status={auth_status}, body={_snippet(auth_text)}")


# ------------------------------------------------------------
# STEP 3 — QR + STATUS loop
# ------------------------------------------------------------

async def _step3_poll_qr(session, auth, qr_callback):
    aid = auth["aid"]

    qr_url = f"{_BANKID_BASE}/id/bankid/qr"
    status_url = f"{_BANKID_BASE}/id/bankid/status"
    poll_count = 0
    fail_count = 0
    previous_status = None
    while True:

        await asyncio.sleep(1)
        poll_count += 1

        # --- get status ---
        async with session.get(status_url, params={"aid": aid}, headers=_HEADERS) as resp:
            status_status = resp.status
            status_content_type = resp.headers.get("Content-Type")
            status_text = await resp.text()

        if status_status != 200:
            fail_count += 1
            if fail_count < 10:
                continue
            raise Exception(f"BankID status request failed: http_status={status_status}, content_type={status_content_type}, body={_snippet(status_text)}")

        try:
            data = json.loads(status_text)
        except json.JSONDecodeError:
            log.error(
                "BankID QR poll %s: status response was not valid JSON. http_status=%s content_type=%s body=%s",
                poll_count,
                status_status,
                status_content_type,
                _snippet(status_text),
            )
            raise

        status = data.get("status")
        hint_code = data.get("hintCode")
        message = data.get("message")
        substatus = data.get("substatus")

        if status != "pending":
            log.info (f"BankID auth completed with status={status}, hintCode={hint_code}, message={message}, substatus={substatus}")
            return

        if status != previous_status:
            log.info ("Awaiting BankID app authentication... ")

        # get QR
        async with session.get(qr_url, params={"aid": aid}, headers=_HEADERS) as resp:
            qr_text = (await resp.text()).strip()
            qr_status = resp.status
            qr_content_type = resp.headers.get("Content-Type")
            qr_response_url = str(resp.url)
            qr_response_headers = dict(resp.headers)

        if qr_status != 200:
            log.error(
                "QR request failed: status=%s url=%s content_type=%s headers=%s body=%s",
                qr_status,
                qr_response_url,
                qr_content_type,
                qr_response_headers,
                _snippet(qr_text),
            )
            continue

        if qr_callback:
            try:
                await qr_callback(qr_text)
            except Exception:
                log.exception(
                    "BankID QR poll %s: qr_callback failed for qr_text=%s",
                    poll_count,
                    qr_text,
                )
                raise


        previous_status = status


# ------------------------------------------------------------
# STEP 4 — finalize (IMPORTANT)
# ------------------------------------------------------------

async def _step4_finalize(session, auth):
    """
    Many providers require this call to finalize login
    and propagate session cookies.
    """

    await session.get(
        f"{_BANKID_BASE}/web/res/api/complete",
        params={"aid": auth["aid"]},
        headers=_HEADERS
    )

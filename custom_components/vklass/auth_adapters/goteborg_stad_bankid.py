import json, asyncio # noqa: E401
from html import unescape
from logging import getLogger
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs, urlunparse
from ..http_helper import (
    setDebug, 
    handleResponse, 
    decodeURL, 
    prettyObject, 
    snippet
)

from ..const import (
    AUTH_ADAPTER_ATTR_TITLE,
    AUTH_ADAPTER_ATTR_METHOD,
    AUTH_METHOD_BANKID_QR,
    AUTH_ADAPTER_ATTR_AUTH_FUNCTION,
    QR_CODE_TYPE_SEED
)

AUTH_ADAPTERS = {
    
    "auth189" : {
        AUTH_ADAPTER_ATTR_TITLE:            "Göteborgs stad UBF - Vårdnadshavare",
        AUTH_ADAPTER_ATTR_METHOD:           AUTH_METHOD_BANKID_QR,
        AUTH_ADAPTER_ATTR_AUTH_FUNCTION:    "auth189"
    },
    "auth190" : {
        AUTH_ADAPTER_ATTR_TITLE :           "Göteborgs stad GSF - Vårdnadshavare",
        AUTH_ADAPTER_ATTR_METHOD:           AUTH_METHOD_BANKID_QR,
        AUTH_ADAPTER_ATTR_AUTH_FUNCTION:    "auth190"
    }
}

log = getLogger(__name__)
setDebug(False)


async def auth189 (aiohttp_session, asyncQrNotifyHandler, credentials) -> bool:
    return await authenticate(aiohttp_session, asyncQrNotifyHandler, "189")

async def auth190 (aiohttp_session, asyncQrNotifyHandler, credentials) -> bool:
    return await authenticate(aiohttp_session, asyncQrNotifyHandler, "190")


async def authenticate(aiohttp_session, asyncQrNotifyHandler, org) -> bool:

    authData = {"vklass_org": org}

    # auth.vklass.se init steps
    await _init1_bootstrap_auth (aiohttp_session, authData)
    await _init2_start_bankidqr (aiohttp_session, authData)
        
    # bankid qr flow with https://eid-connect.funktionstjanster.se
    await _bankid1_init_app (aiohttp_session, authData)
    if not await _bankid1_poll_qr (aiohttp_session, authData, asyncQrNotifyHandler):
        return False

    # handshake bankid authentication with https://authpub.goteborg.se, 
    # to in the end, get the se.vklass.authentication cookie
    await _handshake1_handover (aiohttp_session, authData)

    return True


async def _init1_bootstrap_auth(aiohttp_session, authData):
    

    # https://auth.vklass.se/saml/initiate 
    # 302 => redirects
    #  -> https://authpub.goteborg.se/idp/sps/idppub/saml20/login?SAMLRequest=... &SigAlg=... &Signature
    #  -> https://authpub.goteborg.se/idp/sps/auth?FedId=...&PartnerId=https://auth.vklass.se/saml/1/0&FedName=idppub
    #  -> https://authpub.goteborg.se/mga/sps/authsvc/policy/lrr?TAM_OP=login&ERROR_CODE=0x00000000&HOSTNAME=authpub.goteborg.se&AUTHNLEVEL=8&URL=https://authpub.goteborg.se/idp/sps/auth?FedId=...&FedName=idppub
    #  -> https://authpub.goteborg.se/sp/sps/eidpub/saml20/logininitial?RequestBinding=HTTPPost&ResponseBinding=HTTPPost&Target=https%3A%2F%2Fauthpub.goteborg.se%2Fidp%2Fsps%2Fauth%3FFedId=...
    
    # this is the page with the bankID/Freja+ buttons in a html form  

    async with aiohttp_session.get(
        "https://auth.vklass.se/saml/initiate", 
        params={
        "idp": "https://authpub.goteborg.se/idp/sps/idppub/saml20",
        "org": authData["vklass_org"]},
        allow_redirects=True

    ) as response:
        responseData = await handleResponse(response, expectedRetCode=200, expectedLocation="authpub.goteborg.se/sp/sps/eidpub/saml20/logininitial")
    
    html = responseData["content"]

    # save Target and ITFIM_WAYF_IDP (from bankID button), 
    # to request the updated form that we can post
    
    # Target
    decodedUrl = decodeURL(responseData["url"])
    authData["Target"] = decodedUrl["params"]["Target"]

    # ITFIM_WAYF_IDP (saml_url)
    saml_url = None
    soup = BeautifulSoup(html, "html.parser")
    buttons = soup.find_all("button", attrs={"name": "ITFIM_WAYF_IDP"})
    for btn in buttons:
        value = btn.get("value", "")
        if "bankid" in btn.text.lower() or "bankid" in value.lower():
            saml_url = value

    if not saml_url:
        err = "BankID SAML URL not found in response"
        log.error (f"{err} - name='ITFIM_WAYF_IDP' attribute or 'BankId' text not found in form buttons"
                   f"\n{html}") 
        raise ValueError(err)

    authData["saml_url"] = saml_url


async def _init2_start_bankidqr (aiohttp_session, authData):

    # previous step landed us on https://authpub.goteborg.se/sp/sps/eidpub/saml20/logininitial
    # eg, the initial form with the bankid/freja+ buttons
    # 1. re-load the form again with values from thi form, to get updated form data,
    # 2. post into eid-connect.funktionstjanster.se to start the bankid qr flow

    async with aiohttp_session.get(
        "https://authpub.goteborg.se/sp/sps/eidpub/saml20/logininitial", 
        params={
            "ResponseBinding":  "HTTPPost",
            "RequestBinding":   "HTTPPost",
            "NameIdFormat":     "Transient",
            "ITFIM_WAYF_IDP":   authData["saml_url"],
            "Target":           authData["Target"]          
        },
        allow_redirects=False
    ) as response:
      responseData = await handleResponse(response, expectedRetCode=200, expectedLocation="authpub.goteborg.se/sp/sps/eidpub/saml20/logininitial")


    html = responseData["content"]

    # extract form data needed for the POST
    soup = BeautifulSoup(html, "html.parser")
    form = soup.find("form")
    if form:
        formAction = form.get("action")
        relay_state_input = form.find("input", {"name": "RelayState"})
        saml_request_input = form.find("input", {"name": "SAMLRequest"})

        RelayState = relay_state_input.get("value") if relay_state_input else None
        SAMLRequest = saml_request_input.get("value") if saml_request_input else None


    if not form or not formAction or not RelayState or not SAMLRequest:
        err = "SAML request data not found in html"
        log.error (f"{err} - form, action, RelayState, or SAMLRequest not found on page"
                   f"\n{html}")
        raise ValueError(err)

    # hand over to eid-connect.funktionstjanster.se for the bankid qr flow
    # after 302 redirects, will land us on:
	# https://eid-connect.funktionstjanster.se/web/app/v2/<someid>/<someid>/?lang=sv&aid=<value>

    async with aiohttp_session.post(
        formAction,
        headers= {
            "Origin": "https://authpub.goteborg.se",
            "Referer": "https://authpub.goteborg.se/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={
            "RelayState":       RelayState,
            "SAMLRequest":      SAMLRequest
        },
        allow_redirects=True
    ) as response:
      responseData = await handleResponse(response, expectedRetCode=200, expectedLocation="eid-connect.funktionstjanster.se/web/app/v2")

    #  we need the aid, spId, app_id, and app_url from the URL of the landing page
    # https://eid-connect.funktionstjanster.se/web/app/v2/<app_id>/<spId>/?aid=<aid>

    app_url = responseData["url"]


    parsed = urlparse(responseData["url"])
    app_url = urlunparse(parsed._replace(query=""))

    qs = parse_qs(parsed.query)
    aid = qs.get("aid", [None])[0]

    parts = parsed.path.strip("/").split("/")
    if len(parts) < 5:
        err = "Unexpected URL format"
        log.error (f"{err} - eid-connect app url: {responseData["url"]}")
        raise ValueError(err)

    spId = parts[-1] if parts[-1] else parts[-2]

    if not aid or not spId:
        err = "Failed to parse BankId app URL, unexpected format"
        log.error (f"{err} - expected format: https://eid-connect.funktionstjanster.se/web/app/v2/<appId>/<spId>/?aid=<aid>\nGot: {responseData["url"]}")
        raise ValueError(err)

    authData["bankid_aid"] = aid
    authData["bankid_spId"] = spId
    authData["bankid_app_url"] = app_url


async def _bankid1_init_app (aiohttp_session, authData):

    headers = {
        "Accept":   "*/*",
        "Origin": "https://eid-connect.funktionstjanster.se",
        "Referer":  f"{authData['bankid_app_url']}?lang=sv&aid={authData["bankid_aid"]}",
        "Content-Type": "application/json"
    }

    # first get the method id for "bankidBankID annan enhet"    
    async with aiohttp_session.get(
        "https://eid-connect.funktionstjanster.se/web/res/api/methods",
        headers = headers,
        params={
            "lang":             "sv",
            "aid":              authData["bankid_aid"],
            "spId":             authData["bankid_spId"],
        },
        allow_redirects=False
    ) as response:
      responseData = await handleResponse(response, expectedRetCode=200)

    methods = responseData["content"]
    methodId = None
    if isinstance (methods, list) and isinstance(methods[0], dict):
        methodId = methods[0].get("id", None)
    
    if not methodId:
        err = "Could not get BankID method"
        content = "unknown content"
        if isinstance(methods, (dict, list)):
            content = prettyObject(methods)
        elif isinstance(methods, str):
            content = methods
        log.error (f"{err} - unexpected json format:\n{content}")
        raise ValueError(err)

    authData["bankid_methodId"] = methodId
    
    # authenticate with the eid-connect.funktionstjanster.se to start the bankid flow
    # https://eid-connect.funktionstjanster.se/id/bankid/auth?aid=hcy1bwryc&id=631992d934c51e4f39e150b9&lang=sv
    async with aiohttp_session.post(
        "https://eid-connect.funktionstjanster.se/id/bankid/auth",
        headers = headers,
        params={
            "lang":             "sv",
            "aid":              authData["bankid_aid"],
            "id":               authData["bankid_methodId"]
        },
        data="",
        allow_redirects=False
    ) as response:
      responseData = await handleResponse(response, expectedRetCode=200)

    # auth returns 200 even on fail, with html instead of plain auth token 
    auth_token = (responseData["content"]).strip()
    if auth_token.startswith("<html>"):
        err = "BankID auth page did not return a token"
        log.error (f"{err} - return content:\n{auth_token}")
        raise ValueError(err)


async def _bankid1_poll_qr(session, authData, asyncQrNotifyHandler):

    # status: https://eid-connect.funktionstjanster.se/id/bankid/status?aid=hcy1bwryc
    # qr: https://eid-connect.funktionstjanster.se/id/bankid/qr?aid=hcy1bwryc

    headers = {
        "Accept":   "*/*",
        "Origin": "https://eid-connect.funktionstjanster.se",        
        "Referer":  f"{authData['bankid_app_url']}?lang=sv&aid={authData["bankid_aid"]}",
    }

    poll_count = 0
    fail_count = 0
    while True:

        await asyncio.sleep(1)
        poll_count += 1

        if poll_count >= 90:  # roughly 1.5 min 
            err = f"BankID QR retrieval was aborted after {poll_count} QR fetched due to inactivity"
            log.error (err)
            raise TimeoutError(err)

        # --- get status ---
        async with session.get(
            "https://eid-connect.funktionstjanster.se/id/bankid/status",
            params={"aid": authData["bankid_aid"]},
            headers=headers,
        ) as resp:
            
            status_status = resp.status
            status_text = await resp.text()

        if status_status != 200:
            fail_count += 1
            if fail_count < 10:
                continue
            raise Exception(f"BankID status request failed: http_status={status_status}, body={snippet(status_text)}")

        data = json.loads(status_text)
        status = data.get("status")
        hint_code = data.get("hintCode")
        message = data.get("message")
        substatus = data.get("substatus")

        if status == "complete":
            log.info("BankID auth successfully completed")
            return True

        if status != "pending":
            err = "BankID QR retrieval was aborted"
            log.error (f"{err} - BankID status status={status}, hintCode={hint_code}, message={message}, substatus={substatus}")
            raise ValueError(err)

        # get QR
        async with session.get(
            "https://eid-connect.funktionstjanster.se/id/bankid/qr",
            params={"aid": authData["bankid_aid"]},
            headers=headers
        ) as resp:
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
                snippet(qr_text),
            )
            continue

        try:
            await asyncQrNotifyHandler(qr_text, QR_CODE_TYPE_SEED)
        except Exception:
            log.exception(f"BankID QR code notify callback failed for QR code={qr_text}")
            raise


async def _handshake1_handover (aiohttp_session, authData):

    headers = {
        "Accept":   "*/*",
        "Origin": "https://eid-connect.funktionstjanster.se",        
        "Referer":  f"{authData['bankid_app_url']}?lang=sv&aid={authData["bankid_aid"]}",
    }
    # https://eid-connect.funktionstjanster.se/id/finish?aid=b2iqqd59y
    # POST https://authpub.goteborg.se/sp/sps/eidpub/saml20/login
    # 302 -> GET https://authpub.goteborg.se/sp/sps/wssoi
    # 302 -> https://authpub.goteborg.se/idp/sps/auth?FedId=uuidc69b10fc-018d-1e46-bd45-84b46fd723a9

    # get samlRelayState and SAMLResponse from bankid app
    async with aiohttp_session.get(
        "https://eid-connect.funktionstjanster.se/id/finish",
        headers = headers,
        params={"aid": authData["bankid_aid"]},
        allow_redirects=False
    ) as response:
      responseData = await handleResponse(response, expectedRetCode=200)

    html = responseData["content"]
    soup = BeautifulSoup(html, "html.parser")

    form_action = None
    relay_state = None
    saml_response = None

    form = soup.find("form")
    if form:
        # --- form action (decode HTML entities like &#x3a;)
        raw_action = form.get("action")
        form_action = unescape(raw_action) if raw_action else None
        relay_state_input = form.find("input", {"name": "RelayState"})
        saml_response_input = form.find("input", {"name": "SAMLResponse"})
        relay_state = relay_state_input.get("value") if relay_state_input else None
        saml_response = saml_response_input.get("value") if saml_response_input else None

    if not form_action or not relay_state or not saml_response:
        err = "Could not parse BankID auth finish page"
        log.error (f"{err} - returned content:\n{html}")
        raise ValueError(err)

    # handover auth result to authpub.goteborg.se
    # redirects shoul land us on https://authpub.goteborg.se/idp/sps/auth?FedId=... 

    headers["Referer"] = "https://eid-connect.funktionstjanster.se"
    headers["Content-Type"] = "application/x-www-form-urlencoded"

    async with aiohttp_session.post(
        form_action,
        headers = headers,
        data={"RelayState": relay_state, "SAMLResponse": saml_response},
        allow_redirects=True
    ) as response:
      responseData = await handleResponse(response, expectedRetCode=200, expectedLocation="authpub.goteborg.se/idp/sps/auth")

    # idp/sps/auth contains html form that just reposts the SAMLResponse
    # to https://auth.vklass.se/saml/assertion

    # get the new saml responce anyway... should be the same...

    html = responseData["content"]
    soup = BeautifulSoup(html, "html.parser")

    saml_response = None
    form = soup.find("form")
    if form:
        # --- form action (decode HTML entities like &#x3a;)
        saml_response_input = form.find("input", {"name": "SAMLResponse"})
        saml_response = saml_response_input.get("value") if saml_response_input else None

    if not saml_response:
        err = "Could not parse SAMLResponse from html form"
        log.error (f"{err} - returned content:\n{html}")
        raise ValueError(err)

    # https://auth.vklass.se/saml/assertion redirects further, but
    # the se.vklass.authentication is set here so we are done
    headers["Origin"] = "https://authpub.goteborg.se"
    headers["Referer"] = "https://authpub.goteborg.se/"
    async with aiohttp_session.post(
        "https://auth.vklass.se/saml/assertion",
        headers = headers,
        data={"RelayState": "", "SAMLResponse": saml_response},
        allow_redirects=False
    ) as response:
      await handleResponse(response, expectedRetCode=302)

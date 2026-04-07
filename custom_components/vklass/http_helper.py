# just a helper for debugging aiohttp responses

import json
from typing import Any, Dict, Optional
from urllib.parse import urlparse, parse_qs, unquote
from logging import getLogger
import re

log = getLogger(__name__)


_DEBUG = False  # toggle globally if you want

def setDebug(dbgOn:bool=True):
    global _DEBUG
    _DEBUG = dbgOn


def make_headers(initial: dict | None = None, **kwargs) -> dict:
    headers = {} if initial is None else dict(initial)
    headers.update(kwargs)
    return {name: value for name, value in headers.items() if value is not None}

async def handleResponse(response, expectedRetCode: int, expectedLocation: Optional[str] = None,) -> Dict[str, Any]:

    # ------------------------------------------------------------
    # BASIC STRUCTURE
    # ------------------------------------------------------------
    result: Dict[str, Any] = {
        "request_url": str(response.request_info.url),
        "request_method": response.request_info.method,
        "content_type": None,
        "content": None,
        "redirect_url": None,
        "response_code": response.status,
        "url": str(response.url)
    }

    # ------------------------------------------------------------
    # REDIRECT (only relevant if allow_redirects=False)
    # ------------------------------------------------------------
    if "Location" in response.headers:
        result["redirect_url"] = response.headers.get("Location")

    # ------------------------------------------------------------
    # CONTENT PARSING (only when meaningful)
    # ------------------------------------------------------------
    content_type_raw = response.headers.get("Content-Type", "").lower()

    should_read_body = response.status in (200, 201, 202)

    if should_read_body:
        if "application/json" in content_type_raw:
            result["content_type"] = "json"
            try:
                result["content"] = await response.json()
            except Exception:
                result["content"] = await response.text()

        elif "text/html" in content_type_raw:
            result["content_type"] = "html"
            result["content"] = await response.text()

        elif "text/" in content_type_raw:
            result["content_type"] = "text"
            result["content"] = await response.text()

    # ------------------------------------------------------------
    # VALIDATION
    # ------------------------------------------------------------
    status_ok = response.status == expectedRetCode

    # determine "landing url"
    final_url = str(response.url)

    location_ok = True
    if expectedLocation:
        location_ok = expectedLocation in final_url

    if not status_ok or not location_ok or _DEBUG:
        await response_debug(response, result)

    if not status_ok:
        raise Exception(f"Unexpected status {response.status}, expected {expectedRetCode}")

    if not location_ok:
        raise Exception(f"Unexpected landing URL: {final_url} (expected to contain '{expectedLocation}')")

    return result



async def response_debug(response, data: Dict[str, Any]) -> None:

    # Redirect hops (keep raw objects)
    hops = list(response.history)
    final_url = str(response.url)

    # Determine ORIGINAL request (same logic as before)
    if response.history:
        original = response.history[0]
        original_url = str(original.request_info.url)
        original_method = original.request_info.method
        original_status = original.status
        original_req_headers = dict(original.request_info.headers)
    else:
        original_url = data["request_url"]
        original_method = data["request_method"]
        original_status = data["response_code"]
        original_req_headers = dict(response.request_info.headers)

    # Response headers (final response)
    resp_headers = dict(response.headers)

    # Cookies (important!)
    try:
        set_cookies = response.headers.getall("Set-Cookie", [])
    except Exception:
        set_cookies = []

    # Content preview
    content_preview = data.get("content")

    if isinstance(content_preview, (dict, list)):
        content_preview = prettyObject(content_preview)
    elif isinstance(content_preview, str):
        if len(content_preview) > 6000:
            content_preview = content_preview[:6000] + "\n... [truncated]"

    # ------------------------------------------------------------
    # BUILD OUTPUT (single log)
    # ------------------------------------------------------------
    lines = []
    lines.append("\n")
    lines.append("\n### AIOHTTP REQUEST DEBUG ##########################################")
    lines.append("#")

    lines.append(prettyPrintURL(original_url))
    lines.append(f"# {original_method}")
    lines.append(f"# {original_status}")
    lines.append("#")

    # Original request headers (FIXED)
    lines.append("\n-- Original Request Headers --------------------------------------------------------------------------------")
    lines.append(prettyObject(original_req_headers))

    # Redirect chain
    lines.append("\n-- Redirect Hops --------------------------------------------------------------------------------------------\n")
    if hops:
        for i, r in enumerate(hops, 1):
            hop_url = str(r.url)
            hop_method = r.request_info.method
            hop_status = r.status

            lines.append(
                f"--> hop {i} [{hop_method} -> {hop_status}] ---------------------\n"
                f"{prettyPrintURL(hop_url, prependNewLines='')}"
            )
    else:
        lines.append("  (no redirects)")

    lines.append("\n  => final:")
    lines.append(prettyPrintURL(final_url))

    # Response headers
    lines.append(f"\n-- Response Headers -- {data["request_method"]} -> {data["response_code"]} ------------------------------------------------------------------")
    lines.append("Location:")
    lines.append(prettyPrintURL(resp_headers.get("Location", final_url)))
    lines.append(prettyObject(resp_headers))

    # Cookies
    if set_cookies:
        lines.append("\n-- Set-Cookie Headers --------------------------------------------------------------------------------")
        for c in set_cookies:
            lines.append(f"  {c}")

    # Content
    lines.append("\n-- Content --------------------------------------------------------------------------------------------")
    lines.append("Location:")
    lines.append(prettyPrintURL(final_url))
    lines.append(f"Content Type: {data.get('content_type')}")
    lines.append(f"Content:\n{content_preview}")

    lines.append("\n##################################################################\n")

    log.info("\n".join(lines))

# ------------------------------------------------------------
# URL HELPERS
# ------------------------------------------------------------
def decodeURL(url: str) -> Dict[str, Any]:
    parsed = urlparse(url)

    base_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

    raw_params = parse_qs(parsed.query)

    # flatten + decode
    params = {}
    for k, v in raw_params.items():
        # parse_qs gives list → take first (typical case)
        val = v[0] if v else None
        if val is not None:
            val = unquote(val)
        params[k] = val

    return {
        "url": base_url,
        "params": params
    }


def prettyPrintURL(url: str, prependNewLines: str = "") -> str:
    decoded = decodeURL(url)

    lines = []

    if prependNewLines:
        lines.append(prependNewLines)

    lines.append(decoded["url"])

    if decoded["params"]:
        lines.append("  Query Parameters:")
        for k, v in decoded["params"].items():
            lines.append(f"    {k}: {v}")

    return "\n".join(lines)



def prettyObject(obj):
    try:
        return json.dumps(obj, indent=2, ensure_ascii=False)
    except Exception:
        return str(obj)
    

def snippet(value, limit: int = 240) -> str:
    text = str(value).replace("\n", "\\n").replace("\r", "\\r")
    if len(text) <= limit:
        return text
    return f"{text[:limit]}..."
from html import unescape
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup
import re
from logging import getLogger
import importlib
import pkgutil

from .const import (
    
    CALENDAR_EVENTTYPES,
    CALENDAR_EVENT_PUBLIC_HOLIDAY,

    CAL_ATTR_UID,
    CAL_ATTR_START,
    CAL_ATTR_END,
    CAL_ATTR_SUMMARY,
    CAL_ATTR_DESCR,
    CAL_ATTR_LOCATION,
    CAL_ATTR_CANCELLED,
    CAL_ATTR_DETAILURL,
    
    CAL_ATTR_NAME,
    CAL_ATTR_CONTEXT,
    CAL_ATTR_EVENTTYPE,
    CAL_ATTR_EVENTS,

    AUTH_ADAPTER_ATTR_NAME,
    AUTH_ADAPTER_ATTR_TITLE,
    AUTH_ADAPTER_ATTR_METHOD,
    AUTH_ADAPTER_ATTR_AUTH_FUNCTION,
)

log = getLogger(__name__)
_SWEDEN_TZ = ZoneInfo("Europe/Stockholm")
_CALENDAR_BUCKET_PUBLIC_HOLIDAYS_ID = "public_holidays"



###############################################################################
## Auth adapter helpers


def _auth_adapters_load() -> dict | None:

    _ADAPTER_ATTR_ADAPTERS = "AUTH_ADAPTERS"
    adapters = {}
    package_name = f"{__package__}.auth_adapters"
    package = importlib.import_module(package_name)

    for _, module_name, _ in pkgutil.iter_modules(package.__path__):
        module = importlib.import_module(f"{package_name}.{module_name}")

        mAdapters = getattr(module, _ADAPTER_ATTR_ADAPTERS, None)
        if not mAdapters or not isinstance(mAdapters, dict):
            log.error(f"Auth adapter {module_name}, does not define the {_ADAPTER_ATTR_ADAPTERS} dict")
            continue

        for adapterName, adapter in mAdapters.items():
            name = f"{module_name}.{adapterName}"

            if not (strFunction := adapter.get(AUTH_ADAPTER_ATTR_AUTH_FUNCTION, None)) or not isinstance(strFunction, str):
                log.error(f"Auth adapter {name}, must define AUTH_ADAPTER_TITLE as str")
                continue
            if AUTH_ADAPTER_ATTR_TITLE not in adapter:
                log.error(f"Auth adapter {name}, must define AUTH_ADAPTER_ATTR_TITLE")
                continue
            if AUTH_ADAPTER_ATTR_METHOD not in adapter:
                log.error(f"Auth adapter {name}, must define AUTH_ADAPTER_ATTR_METHOD")
                continue
            if not (authFn := getattr(module, strFunction, None)):
                log.error(f"Auth adapter {name}, could not find {strFunction} function ")
                continue

            adapter[AUTH_ADAPTER_ATTR_AUTH_FUNCTION] = authFn
            adapter[AUTH_ADAPTER_ATTR_NAME] = name

            adapters[f"{module_name}.{adapterName}"] = adapter

    return adapters


_AUTH_ADAPTERS = _auth_adapters_load()
MANUAL_COOKIE_ADAPTER = "manual_cookie.manual_cookie"

def auth_adapters_get_all() -> dict | None:
    return _AUTH_ADAPTERS


def auth_adapter_get(key: str):

    if not (adapter := _AUTH_ADAPTERS.get(key, None)):
        raise RuntimeError(f"Auth adapter {key} is not loaded")

    return adapter



###############################################################################
## Calendar helpers



def vklass_date_to_timestring(value: date | str) -> str:

    if isinstance(value, str):
        value = date.fromisoformat(value)
    elif not isinstance(value, date):
        return None

    return datetime(value.year, value.month, value.day, tzinfo=_SWEDEN_TZ).isoformat(timespec="seconds")


def _calendar_parse_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    parsed = datetime.strptime(value.strip(), "%Y-%m-%d %H:%M")
    return parsed.replace(tzinfo=_SWEDEN_TZ)


def _calendar_normalize_description(value: str | None) -> str | None:
    if value is None:
        return None

    text = str(value).replace("\r\n", "\n").replace("\r", "\n")
    text = unescape(text)

    if "<" in text and ">" in text:
        soup = BeautifulSoup(text, "html.parser")
        for tag in soup.find_all(["br", "p", "div", "li"]):
            tag.append("\n")
        text = soup.get_text()

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    text = text.strip()
    return text or None


def _calendar_normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None

def _calendar_bucket_id(context: str | None, event_type: int) -> str:
    if context is None:
        return _CALENDAR_BUCKET_PUBLIC_HOLIDAYS_ID
    normalized_context = re.sub(r"[^a-z0-9]+", "_", context.casefold()).strip("_")
    return f"{normalized_context or 'unknown'}.{event_type}"

def _calendar_bucket_name(context: str | None, event_type: int) -> str:
    if context is None:
        return CALENDAR_EVENT_PUBLIC_HOLIDAY
    return f"{context} - {CALENDAR_EVENTTYPES.get(event_type, str(event_type))}"


def _calendar_normalize_event(event: dict) -> tuple[str, dict, dict] | None:

    if not (detail_url := _calendar_normalize_text(event.get("detailUrl"))):
        log.warning("Calendar event skipped, detailUrl missing in event data")
        return None

    if not (summary := _calendar_normalize_text(event.get("title"))):
        log.warning(f"Calendar event skipped, title missing for {detail_url}")
        return None

    context = _calendar_normalize_text(event.get("context"))
    raw_event_type = event.get("eventType")
    if not isinstance(raw_event_type, int):
        log.warning(f"Calendar event skipped, unknown or missing eventType '{raw_event_type}' for {detail_url}")
        return None

    bucket_id = _calendar_bucket_id(context, raw_event_type)
    bucket = {
        CAL_ATTR_CONTEXT:   context,
        CAL_ATTR_EVENTTYPE: raw_event_type,
        CAL_ATTR_NAME:      _calendar_bucket_name(context, raw_event_type),
        CAL_ATTR_EVENTS:    [],
    }

    location = _calendar_normalize_text(event.get("location"))
    description = _calendar_normalize_description(event.get("text"))
    cancelled = bool(event.get("cancelled"))
    
    if not (start_at := _calendar_parse_datetime(event.get("start"))):
        log.warning(f"Calendar event skipped, start date missing or invalid for {detail_url}")
        return None

    if event.get("allDay"):
        start_value = start_at.date().isoformat()
        if not (end_at := _calendar_parse_datetime(event.get("end"))):
            end_value = (start_at.date() + timedelta(days=1)).isoformat()
        else:
            end_value = (end_at.date() + timedelta(days=1)).isoformat()
    else:
        if not (end_at := _calendar_parse_datetime(event.get("end"))):
            log.warning(f"Calendar event skipped, end date missing or invalid for timed event {detail_url}")
            return None

        start_value = start_at.isoformat(timespec="seconds")
        end_value = end_at.isoformat(timespec="seconds")

    normalized_event = {
        CAL_ATTR_UID:       f"vklass:{detail_url}",
        CAL_ATTR_DETAILURL: detail_url,
        CAL_ATTR_START:     start_value,
        CAL_ATTR_END:       end_value,
        CAL_ATTR_SUMMARY:   summary,
        CAL_ATTR_DESCR:     description,
        CAL_ATTR_LOCATION:  location,
        CAL_ATTR_CANCELLED: cancelled,
    }

    return bucket_id, bucket, normalized_event


def calendar_parse_events(raw_events: list[dict]) -> list[dict]:
    
    buckets = {}
    for raw_event in raw_events:
        if not isinstance(raw_event, dict):
            log.warning(f"Unexpected calendar event payload type: {type(raw_event)}, skipping")
            continue

        if (result := _calendar_normalize_event(raw_event)) is None:
            continue

        bucket_id, bucket, normalized_event = result

        if bucket_id not in buckets:
            buckets[bucket_id] = bucket
        
        buckets[bucket_id][CAL_ATTR_EVENTS].append(normalized_event)


    buckets = list(buckets.values())
    return buckets

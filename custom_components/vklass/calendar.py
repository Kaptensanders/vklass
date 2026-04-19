"""Calendar platform for Vklass."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
import logging
from typing import Any

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers import entity_registry as er
from homeassistant.util import slugify
from homeassistant.util import dt as dt_util
from homeassistant.helpers.event import async_track_point_in_time, async_track_time_interval

from . import can_entry_fetch
from .auth_state import get_callbacks
from .const import (
    CALENDAR_CANCELLED_DESCRIPTION_PREFIX,
    CALENDAR_CANCELLED_SUMMARY_PREFIX,
    CAL_ATTR_CANCELLED,
    CAL_ATTR_DESCR,
    CAL_ATTR_END,
    CAL_ATTR_EVENTS,
    CAL_ATTR_LOCATION,
    CAL_ATTR_NAME,
    CAL_ATTR_START,
    CAL_ATTR_SUMMARY,
    DATA_GATEWAY,
    DOMAIN,
)
from .vklassgateway import VklassGateway

_LOGGER = logging.getLogger(__name__)
_LONG_RANGE_MONTHS = 12
_HOURLY_NEAR_TERM_MONTHS = 2
_DAILY_REFRESH_HOUR = 3
_HOURLY_REFRESH_INTERVAL = timedelta(hours=1)


def _month_key(year: int, month: int) -> tuple[int, int]:
    return (int(year), int(month))


def _iter_months(start_year: int, start_month: int, count: int) -> list[tuple[int, int]]:
    months: list[tuple[int, int]] = []
    year = start_year
    month = start_month
    for _ in range(count):
        months.append((year, month))
        month += 1
        if month > 12:
            month = 1
            year += 1
    return months


def _parse_event_value(value: str) -> date | datetime:
    if "T" in value:
        return datetime.fromisoformat(value)
    return date.fromisoformat(value)


def _event_in_range(
    event: CalendarEvent, start_date: datetime, end_date: datetime
) -> bool:
    return event.start_datetime_local < end_date and event.end_datetime_local > start_date


def _cancelled_summary(summary: str, cancelled: bool) -> str:
    if not cancelled:
        return summary
    if summary.startswith(CALENDAR_CANCELLED_SUMMARY_PREFIX):
        return summary
    return f"{CALENDAR_CANCELLED_SUMMARY_PREFIX}{summary}"


def _cancelled_description(description: str | None, cancelled: bool) -> str | None:
    if not cancelled:
        return description
    if not description:
        return CALENDAR_CANCELLED_DESCRIPTION_PREFIX
    if description.startswith(CALENDAR_CANCELLED_DESCRIPTION_PREFIX):
        return description
    return f"{CALENDAR_CANCELLED_DESCRIPTION_PREFIX}\n{description}"


def _build_calendar_event(event_data: dict[str, Any]) -> CalendarEvent:
    cancelled = bool(event_data.get(CAL_ATTR_CANCELLED))
    summary = _cancelled_summary(str(event_data[CAL_ATTR_SUMMARY]), cancelled)
    description = _cancelled_description(event_data.get(CAL_ATTR_DESCR), cancelled)
    return CalendarEvent(
        uid=str(event_data["uid"]),
        start=_parse_event_value(str(event_data[CAL_ATTR_START])),
        end=_parse_event_value(str(event_data[CAL_ATTR_END])),
        summary=summary,
        description=description,
        location=event_data.get(CAL_ATTR_LOCATION),
    )


@dataclass
class BucketState:
    """Merged bucket state."""

    name: str
    events: list[dict[str, Any]]


class VklassCalendarRuntime:
    """Shared calendar runtime state for one config entry."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        gateway: VklassGateway,
        async_add_entities: AddConfigEntryEntitiesCallback,
    ) -> None:
        self.hass = hass
        self.entry = entry
        self.gateway = gateway
        self._async_add_entities = async_add_entities
        self._month_snapshots: dict[tuple[int, int], list[dict[str, Any]]] = {}
        self._buckets: dict[str, BucketState] = {}
        self._entities: dict[str, VklassCalendarEntity] = {}
        self._refresh_lock = False
        self._last_fetch_allowed: bool | None = None
        self._scheduled_unsubs: list[CALLBACK_TYPE] = []
        self._daily_refresh_unsub: CALLBACK_TYPE | None = None
        self._remove_runtime_callback: Callable[[], None] | None = None

    async def async_setup(self) -> None:
        runtime_data = self.hass.data[DOMAIN][self.entry.entry_id]
        callbacks = get_callbacks(runtime_data)
        callbacks.append(self._async_on_runtime_changed)
        self._remove_runtime_callback = lambda: callbacks.remove(self._async_on_runtime_changed)
        self._last_fetch_allowed = can_entry_fetch(self.hass, self.entry.entry_id)

        self._schedule_daily_refresh()
        self._scheduled_unsubs.append(
            async_track_time_interval(
                self.hass,
                self._async_hourly_refresh,
                _HOURLY_REFRESH_INTERVAL,
            )
        )

        await self.async_refresh(long_range=True, force_discovery=True)

    async def async_unload(self) -> None:
        for unsub in self._scheduled_unsubs:
            unsub()
        self._scheduled_unsubs.clear()
        if self._daily_refresh_unsub is not None:
            self._daily_refresh_unsub()
            self._daily_refresh_unsub = None
        if self._remove_runtime_callback is not None:
            self._remove_runtime_callback()
            self._remove_runtime_callback = None

    @callback
    def _schedule_daily_refresh(self) -> None:
        if self._daily_refresh_unsub is not None:
            self._daily_refresh_unsub()
            self._daily_refresh_unsub = None

        now = dt_util.now()
        next_run = dt_util.as_local(
            datetime.combine(now.date(), time(_DAILY_REFRESH_HOUR, 0), tzinfo=now.tzinfo)
        )
        if next_run <= now:
            next_run = next_run + timedelta(days=1)

        def _daily_callback(_: datetime) -> None:
            self.hass.async_create_task(self.async_refresh(long_range=True))
            self._schedule_daily_refresh()

        self._daily_refresh_unsub = async_track_point_in_time(
            self.hass, _daily_callback, next_run
        )

    async def _async_hourly_refresh(self, _: datetime) -> None:
        await self.async_refresh()

    async def _async_on_runtime_changed(self) -> None:
        can_fetch = can_entry_fetch(self.hass, self.entry.entry_id)
        previous = self._last_fetch_allowed
        self._last_fetch_allowed = can_fetch

        if not can_fetch or previous is True:
            return

        await self.async_refresh(long_range=True, force_discovery=True)

    async def async_refresh(
        self, *, long_range: bool = False, force_discovery: bool = False
    ) -> None:
        if self._refresh_lock:
            return
        can_fetch = can_entry_fetch(self.hass, self.entry.entry_id)
        self._last_fetch_allowed = can_fetch
        if not can_fetch:
            return

        self._refresh_lock = True
        try:
            now = dt_util.now()
            months = _iter_months(
                now.year,
                now.month,
                _LONG_RANGE_MONTHS if long_range else _HOURLY_NEAR_TERM_MONTHS,
            )
            fetched_snapshots: dict[tuple[int, int], list[dict[str, Any]]] = {}
            for year, month in months:
                _LOGGER.info(
                    "%s requesting calendar data for %04d-%02d",
                    self.entry.title,
                    year,
                    month,
                )
                buckets = await self.gateway.getCalendar(year=year, month=month)
                fetched_snapshots[_month_key(year, month)] = buckets

            if long_range:
                self._month_snapshots = fetched_snapshots
            else:
                self._month_snapshots.update(fetched_snapshots)

            self._rebuild_buckets()
            await self._async_add_new_entities()
            for entity in self._entities.values():
                entity.async_write_ha_state()
        except Exception as err:
            _LOGGER.warning(
                "Failed to refresh Vklass calendar for device %s (%s): %s",
                self.entry.title,
                self._calendar_log_targets(),
                err,
            )
        finally:
            self._refresh_lock = False

    def _calendar_log_targets(self) -> str:
        entity_ids = self._registered_calendar_entity_ids()
        if entity_ids:
            return f"calendar entities: {', '.join(entity_ids)}"

        if self._entities:
            bucket_names = ", ".join(sorted(self._entities))
            return f"calendar buckets: {bucket_names}"

        return "no calendar entities discovered yet"

    def _registered_calendar_entity_ids(self) -> list[str]:
        try:
            entity_registry = er.async_get(self.hass)
        except Exception:
            return []

        return sorted(
            entity_entry.entity_id
            for entity_entry in er.async_entries_for_config_entry(
                entity_registry, self.entry.entry_id
            )
            if entity_entry.entity_id.startswith("calendar.")
        )

    def _rebuild_buckets(self) -> None:
        merged: dict[str, dict[str, dict[str, Any]]] = {}

        for month_buckets in self._month_snapshots.values():
            for bucket in month_buckets:
                bucket_name = str(bucket[CAL_ATTR_NAME])
                bucket_events = merged.setdefault(bucket_name, {})
                for event in bucket.get(CAL_ATTR_EVENTS, []):
                    bucket_events[str(event["uid"])] = event

        self._buckets = {
            bucket_name: BucketState(
                name=bucket_name,
                events=sorted(
                    events.values(),
                    key=lambda item: (str(item[CAL_ATTR_START]), str(item["uid"])),
                ),
            )
            for bucket_name, events in merged.items()
        }

    async def _async_add_new_entities(self) -> None:
        new_entities: list[VklassCalendarEntity] = []
        for bucket_name in sorted(self._buckets):
            if bucket_name in self._entities:
                continue
            entity = VklassCalendarEntity(self, bucket_name)
            self._entities[bucket_name] = entity
            new_entities.append(entity)

        if new_entities:
            self._async_add_entities(new_entities, True)

    def get_bucket_events(self, bucket_name: str) -> list[CalendarEvent]:
        bucket = self._buckets.get(bucket_name)
        if bucket is None:
            return []
        return [_build_calendar_event(event) for event in bucket.events]

    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self.entry.entry_id)},
            name=self.entry.title,
            manufacturer="Vklass",
            model="Vklass",
        )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    runtime_data = hass.data[DOMAIN][entry.entry_id]
    gateway: VklassGateway = runtime_data[DATA_GATEWAY]
    runtime = VklassCalendarRuntime(hass, entry, gateway, async_add_entities)
    runtime_data["calendar_runtime"] = runtime
    await runtime.async_setup()


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    runtime_data = hass.data.setdefault(DOMAIN, {}).get(entry.entry_id, {})
    runtime: VklassCalendarRuntime | None = runtime_data.pop("calendar_runtime", None)
    if runtime is not None:
        await runtime.async_unload()


class VklassCalendarEntity(CalendarEntity):
    """Representation of a Vklass calendar bucket."""

    _attr_icon = "mdi:calendar"

    def __init__(self, runtime: VklassCalendarRuntime, bucket_name: str) -> None:
        self._runtime = runtime
        self._bucket_name = bucket_name
        self._attr_name = bucket_name
        self._attr_unique_id = f"{runtime.entry.entry_id}_{slugify(bucket_name)}"
        self._event: CalendarEvent | None = None

    @property
    def event(self) -> CalendarEvent | None:
        return self._event

    @property
    def device_info(self) -> DeviceInfo:
        return self._runtime.device_info()

    async def async_update(self) -> None:
        events = self._runtime.get_bucket_events(self._bucket_name)
        now = dt_util.now()

        future_events = [event for event in events if event.end_datetime_local > now]
        future_events.sort(key=lambda event: event.start_datetime_local)
        self._event = future_events[0] if future_events else None

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        events = self._runtime.get_bucket_events(self._bucket_name)
        return [event for event in events if _event_in_range(event, start_date, end_date)]

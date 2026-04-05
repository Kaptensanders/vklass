"""Calendar platform for Skolmat."""

from __future__ import annotations

from datetime import datetime, timedelta, date
import logging
from typing import Any

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util
from homeassistant.util import slugify

from .const import (
)
from .vklassgateway import VklassGateway

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    gateway:Gateway = data["gateway"]

    add_entities(
        [
            VklassCalendarEntity(
                hass=hass,
                entry=entry,
                gateway=gateway
            )
        ],
        update_before_add=True,
    )

class VklassCalendarEntity(CalendarEntity):

    _attr_icon = "mdi:calendar"

    def __init__(self, hass, entry, gateway:gateway):

    @staticmethod
    def _parse_time(v):
        if not v:
            return None
        return datetime.strptime(v, "%H:%M").time()

    @property
    def name(self):
        return self._name

    @property
    def device_info(self):
        model = "Vklass"
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=self._name,
            manufacturer="Vklass",
            model=model,
        )


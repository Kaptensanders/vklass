import asyncio
import logging
from types import SimpleNamespace

import pytest

from test.tests.helpers import bootstrap  # noqa: F401

pytest.importorskip("aiohttp")
pytest.importorskip("homeassistant")
pytest.importorskip("voluptuous")

from custom_components.vklass import calendar as calendar_module


def test_calendar_refresh_warning_includes_device_and_bucket_names(caplog, monkeypatch):
    async def run() -> None:
        runtime = calendar_module.VklassCalendarRuntime(
            hass=SimpleNamespace(),
            entry=SimpleNamespace(entry_id="entry-123", title="My Student"),
            gateway=SimpleNamespace(),
            async_add_entities=lambda entities, update_before_add: None,
        )
        runtime._entities["Lessons"] = calendar_module.VklassCalendarEntity(
            runtime, "Lessons"
        )
        runtime._entities["Assignments"] = calendar_module.VklassCalendarEntity(
            runtime, "Assignments"
        )

        monkeypatch.setattr(calendar_module, "can_entry_fetch", lambda hass, entry_id: True)

        async def raise_context_error(*, year: int, month: int):
            raise RuntimeError("Vklass context not loaded, login first")

        runtime.gateway.getCalendar = raise_context_error

        with caplog.at_level(logging.WARNING):
            await runtime.async_refresh()

        assert (
            'Failed to refresh Vklass calendar for device My Student '
            "(calendar buckets: Assignments, Lessons): "
            "Vklass context not loaded, login first"
        ) in caplog.text

    asyncio.run(run())


def test_calendar_runtime_change_refreshes_only_on_fetch_edge(monkeypatch):
    async def run() -> None:
        runtime = calendar_module.VklassCalendarRuntime(
            hass=SimpleNamespace(data={calendar_module.DOMAIN: {"entry-123": {}}}),
            entry=SimpleNamespace(entry_id="entry-123", title="My Student"),
            gateway=SimpleNamespace(),
            async_add_entities=lambda entities, update_before_add: None,
        )
        calls = 0
        fetch_allowed = True

        monkeypatch.setattr(
            calendar_module,
            "can_entry_fetch",
            lambda hass, entry_id: fetch_allowed,
        )

        async def fake_refresh(*, long_range: bool = False, force_discovery: bool = False) -> None:
            nonlocal calls
            calls += 1

        runtime._last_fetch_allowed = False
        runtime.async_refresh = fake_refresh

        await runtime._async_on_runtime_changed()
        await runtime._async_on_runtime_changed()

        assert calls == 1

        fetch_allowed = False
        await runtime._async_on_runtime_changed()
        assert calls == 1

        fetch_allowed = True
        await runtime._async_on_runtime_changed()
        assert calls == 2

    asyncio.run(run())

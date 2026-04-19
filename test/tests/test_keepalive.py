import asyncio
from contextlib import suppress

import pytest

from test.tests.helpers import bootstrap  # noqa: F401

pytest.importorskip("aiohttp")
pytest.importorskip("bs4")
pytest.importorskip("homeassistant")
pytest.importorskip("voluptuous")
pytest.importorskip("yarl")

from custom_components.vklass.const import VKLASS_CONFKEY_AUTHADAPTER, VKLASS_CONFKEY_KEEPALIVE_MIN
from custom_components.vklass.gateway_helpers import MANUAL_COOKIE_ADAPTER
from custom_components.vklass.vklassgateway import VklassSession


def _config(keepalive_minutes: int = 1) -> dict:
    return {
        VKLASS_CONFKEY_AUTHADAPTER: MANUAL_COOKIE_ADAPTER,
        VKLASS_CONFKEY_KEEPALIVE_MIN: keepalive_minutes,
    }


def test_keepalive_start_is_idempotent_and_stoppable(monkeypatch):
    async def run():
        session = VklassSession(_config(keepalive_minutes=7))
        started = asyncio.Event()
        keepalive_args: list[int] = []

        async def fake_keepalive(loop_len: int) -> None:
            keepalive_args.append(loop_len)
            started.set()
            await asyncio.Event().wait()

        monkeypatch.setattr(session, "_keepAliveLoop", fake_keepalive)

        try:
            session._startKeepAlive()
            first_task = session._keepAliveTask
            session._startKeepAlive()

            assert session._keepAliveTask is first_task
            await asyncio.wait_for(started.wait(), timeout=1)
            assert keepalive_args == [7]

            await session._stopKeepAlive()
            assert session._keepAliveTask is None
        finally:
            await session.shutdown()

    asyncio.run(run())


def test_keepalive_loop_recovers_after_error(monkeypatch):
    async def run():
        session = VklassSession(_config(keepalive_minutes=0))
        calls = 0
        completed_recovery = asyncio.Event()

        async def fake_fetch(ep_key: str, data=None, forceAuthenticate: bool = False):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise ConnectionError("transient")

            completed_recovery.set()
            await asyncio.Event().wait()

        monkeypatch.setattr(session, "_fetch", fake_fetch)

        task = asyncio.create_task(session._keepAliveLoop(0))
        try:
            await asyncio.wait_for(completed_recovery.wait(), timeout=1)
            assert calls >= 2
        finally:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
            await session.shutdown()

    asyncio.run(run())


def test_keepalive_uses_custodian_endpoint(monkeypatch):
    async def run():
        session = VklassSession(_config(keepalive_minutes=0))
        captured: dict[str, object] = {}
        got_call = asyncio.Event()

        async def fake_fetch(ep_key: str, data=None, forceAuthenticate: bool = False):
            captured["ep_key"] = ep_key
            captured["data"] = data
            captured["force_authenticate"] = forceAuthenticate
            got_call.set()
            await asyncio.Event().wait()

        monkeypatch.setattr(session, "_fetch", fake_fetch)

        task = asyncio.create_task(session._keepAliveLoop(0))
        try:
            await asyncio.wait_for(got_call.wait(), timeout=1)
            assert captured["ep_key"] == "custodian"
            assert captured["data"] is None
            assert captured["force_authenticate"] is False
        finally:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
            await session.shutdown()

    asyncio.run(run())

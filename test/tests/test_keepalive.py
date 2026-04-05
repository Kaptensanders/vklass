import asyncio

from tests.helpers import bootstrap  # noqa: F401
from vklassgateway import (
    VklassSession,
    VKLASS_CONFKEY_ASYNC_COOKIE_CB,
    VKLASS_CONFKEY_COOKIEFILE,
    VKLASS_CONFKEY_COOKIEFILE_TYPE,
    VKLASS_CONFKEY_COOKIE_RETRIVAL_METHOD,
    VKLASS_CONFKEY_KEEPALIVE_MIN,
    VKLASS_CONFKEY_PASSWORD,
    VKLASS_CONFKEY_USERNAME,
    VKLASS_COOKIE_RETRIVAL_METHOD_MANUAL,
)


def _config(keepalive_minutes: int = 1) -> dict:
    return {
        VKLASS_CONFKEY_COOKIE_RETRIVAL_METHOD: VKLASS_COOKIE_RETRIVAL_METHOD_MANUAL,
        VKLASS_CONFKEY_ASYNC_COOKIE_CB: None,
        VKLASS_CONFKEY_USERNAME: None,
        VKLASS_CONFKEY_PASSWORD: None,
        VKLASS_CONFKEY_COOKIEFILE: None,
        VKLASS_CONFKEY_COOKIEFILE_TYPE: None,
        VKLASS_CONFKEY_KEEPALIVE_MIN: keepalive_minutes,
    }


def test_keepalive_start_is_idempotent_and_stoppable(monkeypatch):
    async def run():
        session = VklassSession(asyncio.to_thread, object(), _config(keepalive_minutes=0))
        calls = 0
        got_two_calls = asyncio.Event()

        async def fake_keepalive():
            nonlocal calls
            calls += 1
            if calls >= 2:
                got_two_calls.set()

        monkeypatch.setattr(session, "_keepAlive", fake_keepalive)

        session.startKeepAlive()
        first_task = session._keepAliveTask
        session.startKeepAlive()

        assert session._keepAliveTask is first_task

        await asyncio.wait_for(got_two_calls.wait(), timeout=1)
        await session.stopKeepAlive()

        assert session._keepAliveTask is None
        assert calls >= 2

    asyncio.run(run())


def test_keepalive_loop_recovers_after_error(monkeypatch):
    async def run():
        session = VklassSession(asyncio.to_thread, object(), _config(keepalive_minutes=0))
        calls = 0
        completed_recovery = asyncio.Event()

        async def fake_keepalive():
            nonlocal calls
            calls += 1
            if calls == 1:
                raise ConnectionError("transient")
            completed_recovery.set()

        monkeypatch.setattr(session, "_keepAlive", fake_keepalive)

        session.startKeepAlive()
        await asyncio.wait_for(completed_recovery.wait(), timeout=1)
        await session.stopKeepAlive()

        assert calls >= 2

    asyncio.run(run())


def test_keepalive_uses_home_with_redirects_disabled(monkeypatch):
    async def run():
        session = VklassSession(asyncio.to_thread, object(), _config())
        captured = {}

        async def fake_fetch_text(uri, data, debugName=None, expected_result_code=200, allow_redirects=True):
            captured["uri"] = uri
            captured["data"] = data
            captured["allow_redirects"] = allow_redirects
            return "<html></html>"

        monkeypatch.setattr(session, "fetch_text", fake_fetch_text)

        await session._keepAlive()

        assert captured["uri"] == "https://custodian.vklass.se/Home/Welcome"
        assert captured["data"] is None
        assert captured["allow_redirects"] is False

    asyncio.run(run())

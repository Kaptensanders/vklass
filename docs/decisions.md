# Decisions

- 2026-03-26: `gateway.py` keeps unsupported auth modes (`login` and `file`) as explicit `NotImplementedError` stubs for now. This preserves fail-fast behavior while the standalone gateway work focuses on the cookie-callback path used by the sandbox test.
- 2026-03-26: `VklassSession` now keeps cookies as an in-memory dict for requests and merges cookies returned by successful Vklass responses into that dict. External cookie sources may still provide plaintext cookies, which are normalized on input.
- 2026-03-27: `VklassSession` keepalive now runs as a single background task started/stopped via `startKeepAlive()`/`stopKeepAlive()`. The keepalive ping uses authenticated fetch of `/Home/Welcome` with redirects disabled, reusing existing auth renewal/cookie update flow. Keepalive errors are logged and retried on next interval; task cancellation exits immediately.

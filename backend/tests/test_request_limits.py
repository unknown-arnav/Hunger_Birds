"""The body-size cap and the response security headers.

These drive the ASGI middlewares directly rather than through a live server,
because the thing being tested is how they behave on a request shape a test
client will not easily produce: a chunked body, which carries no Content-Length
at all. That was the hole - the cap was read off a header the attacker simply
omits - so the test has to be able to send one.
"""

import json

import pytest

from app.core.http import (
    HSTS_HEADER,
    SECURITY_HEADERS,
    MaxBodySizeMiddleware,
    SecurityHeadersMiddleware,
)

MAX = 1024


async def echo_length_app(scope, receive, send):
    """Reads the whole body, then reports how much of it arrived.

    Reporting the length is what makes a bypass visible: if the middleware let
    the body through, this says so with a 200 and the byte count.
    """
    total = 0
    more = True
    while more:
        message = await receive()
        if message["type"] == "http.disconnect":
            return
        total += len(message.get("body", b""))
        more = message.get("more_body", False)
    body = json.dumps({"received": total}).encode()
    await send(
        {
            "type": "http.response.start",
            "status": 200,
            "headers": [(b"content-type", b"application/json")],
        }
    )
    await send({"type": "http.response.body", "body": body})


def _scope(headers, *, method="PATCH", path="/api/auth/me"):
    return {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "root_path": "",
        "scheme": "https",
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers],
        "client": ("10.0.0.1", 51000),
        "server": ("testserver", 443),
    }


async def _drive(app, scope, chunks):
    """Run one request through `app`, feeding `chunks` as the body."""
    queue = list(chunks)
    sent = []

    async def receive():
        if queue:
            chunk = queue.pop(0)
            return {"type": "http.request", "body": chunk, "more_body": bool(queue)}
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        sent.append(message)

    await app(scope, receive, send)

    status = next(m["status"] for m in sent if m["type"] == "http.response.start")
    body = b"".join(m.get("body", b"") for m in sent if m["type"] == "http.response.body")
    headers = {
        k.decode(): v.decode()
        for m in sent
        if m["type"] == "http.response.start"
        for k, v in m["headers"]
    }
    return status, (json.loads(body) if body else None), headers


@pytest.fixture
def capped():
    return MaxBodySizeMiddleware(echo_length_app, max_bytes=MAX)


# --- The declared-length path, which already worked --------------------------


async def test_a_body_within_the_cap_is_served(capped):
    payload = b"x" * (MAX // 2)
    status, body, _ = await _drive(
        capped,
        _scope([("content-type", "application/json"), ("content-length", str(len(payload)))]),
        [payload],
    )
    assert status == 200
    assert body == {"received": len(payload)}


async def test_an_oversized_declared_length_is_refused_before_reading(capped):
    status, body, _ = await _drive(
        capped,
        _scope([("content-length", str(MAX * 10))]),
        [b"x" * (MAX * 10)],
    )
    assert status == 413
    assert body == {"detail": "Request body too large"}


async def test_a_nonsense_content_length_is_a_400(capped):
    status, body, _ = await _drive(capped, _scope([("content-length", "banana")]), [b"x"])
    assert status == 400
    assert body == {"detail": "Invalid Content-Length"}


# --- The chunked path, which is the bug this class exists for ----------------


async def test_a_chunked_body_over_the_cap_is_refused(capped):
    """The regression. A chunked request carries no Content-Length, so the
    declared-size check had nothing to look at and waved it through; the body was
    then buffered and parsed in full. Verified against the running app at 40MB on
    an endpoint whose largest legitimate payload is a few hundred bytes."""
    status, body, _ = await _drive(
        capped,
        _scope([("content-type", "application/json"), ("transfer-encoding", "chunked")]),
        [b"x" * 256] * 64,  # 16KB in 256-byte chunks, no Content-Length anywhere
    )
    assert status == 413
    assert body == {"detail": "Request body too large"}


async def test_a_chunked_body_within_the_cap_still_works(capped):
    chunks = [b"y" * 100] * 5
    status, body, _ = await _drive(
        capped,
        _scope([("transfer-encoding", "chunked")]),
        chunks,
    )
    assert status == 200
    assert body == {"received": 500}


async def test_reading_stops_at_the_cap_rather_than_draining_the_sender():
    """Cost has to stay bounded by the cap, not by what the caller chose to send.

    Counting the chunks the inner app never sees is the check: if the middleware
    drained everything before answering, an attacker sets the memory bill.
    """
    consumed = 0

    async def counting_receive_app(scope, receive, send):  # pragma: no cover
        raise AssertionError("an oversized body must never reach the app")

    app = MaxBodySizeMiddleware(counting_receive_app, max_bytes=MAX)
    queue = [b"z" * 512 for _ in range(100)]  # 50KB against a 1KB cap
    sent = []

    async def receive():
        nonlocal consumed
        consumed += 1
        chunk = queue.pop(0) if queue else b""
        return {"type": "http.request", "body": chunk, "more_body": bool(queue)}

    async def send(message):
        sent.append(message)

    await app(_scope([("transfer-encoding", "chunked")]), receive, send)

    assert next(m["status"] for m in sent if m["type"] == "http.response.start") == 413
    # 1KB cap over 512-byte chunks: it takes three reads to know, not a hundred.
    assert consumed <= 4, f"drained {consumed} chunks before refusing"


async def test_a_bodyless_request_is_passed_through_untouched(capped):
    """A GET must not be made to wait on a body that is never coming."""
    status, body, _ = await _drive(
        capped, _scope([], method="GET", path="/api/vendors"), []
    )
    assert status == 200
    assert body == {"received": 0}


async def test_exempt_paths_skip_the_middleware_entirely():
    app = MaxBodySizeMiddleware(
        echo_length_app, max_bytes=MAX, exempt_prefixes=("/assets/",)
    )
    payload = b"x" * (MAX * 4)
    status, body, _ = await _drive(
        app,
        _scope([("content-length", str(len(payload)))], method="GET", path="/assets/app.js"),
        [payload],
    )
    assert status == 200


# --- Security headers -------------------------------------------------------


async def test_every_security_header_is_set():
    app = SecurityHeadersMiddleware(echo_length_app, include_hsts=True)
    _, _, headers = await _drive(app, _scope([]), [])
    for name, value in SECURITY_HEADERS.items():
        assert headers.get(name) == value, f"{name} missing or wrong"
    assert headers.get(HSTS_HEADER[0]) == HSTS_HEADER[1]


async def test_hsts_is_withheld_in_development():
    """So a local run cannot pin localhost to https for a year."""
    app = SecurityHeadersMiddleware(echo_length_app, include_hsts=False)
    _, _, headers = await _drive(app, _scope([]), [])
    assert HSTS_HEADER[0] not in headers
    # The rest still apply - only HSTS is environment-dependent.
    assert "content-security-policy" in headers


async def test_the_policy_blocks_the_things_it_is_there_to_block():
    policy = SECURITY_HEADERS["content-security-policy"]
    # No inline script: the built index.html has none, so nothing needs it, and
    # tokens live in localStorage where an injected script would reach them.
    assert "script-src 'self'" in policy
    assert "'unsafe-eval'" not in policy
    assert "script-src 'self' 'unsafe-inline'" not in policy
    assert "object-src 'none'" in policy
    assert "frame-ancestors 'none'" in policy


async def test_a_route_setting_its_own_header_is_not_overridden():
    async def opinionated(scope, receive, send):
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"x-frame-options", b"SAMEORIGIN")],
            }
        )
        await send({"type": "http.response.body", "body": b""})

    app = SecurityHeadersMiddleware(opinionated, include_hsts=True)
    _, _, headers = await _drive(app, _scope([]), [])
    assert headers["x-frame-options"] == "SAMEORIGIN"

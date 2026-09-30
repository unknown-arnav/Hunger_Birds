"""Transport-level guards that belong to every response, not to one route.

Both middlewares here are plain ASGI rather than Starlette's BaseHTTPMiddleware.
That matters for the body cap: BaseHTTPMiddleware only sees a request once the
server has already assembled it, which is exactly the work being budgeted.
"""

import json

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

# Set on responses this app generates. Deliberately conservative: the SPA is
# served from this same origin, loads its own hashed bundle, and talks to no
# third party except Google Fonts.
#
# - script-src 'self': the built index.html carries no inline script, only a
#   module tag pointing at /assets, so no nonce machinery is needed.
# - style-src 'unsafe-inline': React writes the handful of `style={{...}}` props
#   in the charts and tracking page out as style attributes, which CSP counts as
#   inline. Inline *style* is a far smaller concession than inline script.
# - img-src https:: a stall's image_url is vendor-supplied and may point at any
#   https host, so this cannot be narrowed without also narrowing that field.
# - connect-src 'self': covers the same-origin API and the wss:// socket.
CONTENT_SECURITY_POLICY = "; ".join(
    (
        "default-src 'self'",
        "base-uri 'self'",
        "object-src 'none'",
        "frame-ancestors 'none'",
        "form-action 'self'",
        "script-src 'self'",
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
        "font-src 'self' https://fonts.gstatic.com",
        "img-src 'self' data: https:",
        "connect-src 'self'",
    )
)

SECURITY_HEADERS: dict[str, str] = {
    "content-security-policy": CONTENT_SECURITY_POLICY,
    # Stops a browser second-guessing a declared type - the route that turns an
    # uploaded or user-named file into executable script.
    "x-content-type-options": "nosniff",
    # frame-ancestors above is the modern control; this covers older browsers.
    "x-frame-options": "DENY",
    # Order ids live in the tracking URL, so keep them off outbound requests to
    # the font CDN and any vendor-supplied image host.
    "referrer-policy": "strict-origin-when-cross-origin",
    "cross-origin-opener-policy": "same-origin",
    "permissions-policy": "camera=(), microphone=(), geolocation=(), payment=()",
}

# Only meaningful over TLS, and browsers ignore it on a plain-HTTP response, but
# it is withheld in development anyway so a local run cannot pin localhost to
# https for a year.
HSTS_HEADER = ("strict-transport-security", "max-age=31536000; includeSubDomains")


class SecurityHeadersMiddleware:
    """Attach the headers above to every response, static assets included."""

    def __init__(self, app: ASGIApp, *, include_hsts: bool) -> None:
        self.app = app
        self.include_hsts = include_hsts

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                for name, value in SECURITY_HEADERS.items():
                    # setdefault: a route that deliberately sets its own policy
                    # keeps it.
                    if name not in headers:
                        headers[name] = value
                if self.include_hsts and HSTS_HEADER[0] not in headers:
                    headers[HSTS_HEADER[0]] = HSTS_HEADER[1]
            await send(message)

        await self.app(scope, receive, send_with_headers)


def _json_response(status_code: int, detail: str) -> tuple[Message, Message]:
    body = json.dumps({"detail": detail}).encode()
    return (
        {
            "type": "http.response.start",
            "status": status_code,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode()),
            ],
        },
        {"type": "http.response.body", "body": body},
    )


class MaxBodySizeMiddleware:
    """Refuse a request body larger than `max_bytes`, counting what arrives.

    Checking `Content-Length` is not enough on its own, and checking only that
    was the bug this replaces. A request sent with `Transfer-Encoding: chunked`
    carries no `Content-Length` at all, so the declared-size check had nothing
    to look at, waved the request through, and the body was then buffered and
    parsed in full - tens of megabytes on an endpoint whose largest legitimate
    payload is a few hundred bytes, and reachable without authenticating.

    So the bytes are counted as they are read. The declared length is still
    consulted first, because rejecting an oversized request before reading it is
    cheaper than discovering the same thing halfway through.

    Bodies are buffered here rather than streamed through. Every route in this
    app takes a small JSON document - image bytes go straight to Cloudinary and
    never pass through the API - so there is no upload to keep streaming, and
    buffering is what lets the limit be enforced before a route sees anything.
    The buffer is bounded by `max_bytes`, which is the point.
    """

    def __init__(
        self,
        app: ASGIApp,
        *,
        max_bytes: int,
        exempt_paths: tuple[str, ...] = (),
        exempt_prefixes: tuple[str, ...] = (),
    ) -> None:
        self.app = app
        self.max_bytes = max_bytes
        self.exempt_paths = exempt_paths
        self.exempt_prefixes = exempt_prefixes

    def _exempt(self, path: str) -> bool:
        return path in self.exempt_paths or path.startswith(self.exempt_prefixes)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or self._exempt(scope.get("path", "")):
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        declared = headers.get("content-length")
        transfer_encoding = headers.get("transfer-encoding", "").lower()

        if declared is not None:
            try:
                declared_length = int(declared)
            except ValueError:
                await self._respond(send, 400, "Invalid Content-Length")
                return
            if declared_length > self.max_bytes:
                await self._respond(send, 413, "Request body too large")
                return

        # Nothing to police, and nothing to buffer: leave the request untouched
        # so an ordinary GET is not made to wait on a receive() that will only
        # ever hand back an empty body.
        if declared in (None, "0") and "chunked" not in transfer_encoding:
            await self.app(scope, receive, send)
            return

        chunks: list[bytes] = []
        received = 0
        more_body = True
        while more_body:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            chunk = message.get("body", b"")
            received += len(chunk)
            if received > self.max_bytes:
                # Stop reading. The remainder of an oversized body is never
                # pulled off the socket, so the cost of this request stays
                # bounded by max_bytes however much the caller meant to send.
                await self._respond(send, 413, "Request body too large")
                return
            chunks.append(chunk)
            more_body = message.get("more_body", False)

        body = b"".join(chunks)
        replayed = False

        async def replay() -> Message:
            nonlocal replayed
            if not replayed:
                replayed = True
                return {"type": "http.request", "body": body, "more_body": False}
            # Past the body, defer to the real transport so the route still
            # learns about a disconnect.
            return await receive()

        await self.app(scope, replay, send)

    async def _respond(self, send: Send, status_code: int, detail: str) -> None:
        start, body = _json_response(status_code, detail)
        await send(start)
        await send(body)


__all__ = [
    "CONTENT_SECURITY_POLICY",
    "HSTS_HEADER",
    "SECURITY_HEADERS",
    "MaxBodySizeMiddleware",
    "SecurityHeadersMiddleware",
]

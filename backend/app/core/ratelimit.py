"""Redis-backed request rate limiting.

Every limit applied in this project exists because something concrete goes
wrong without it - an attacker grinds a login code, burns the month's email
quota, mints unlimited Cloudinary upload permits, or floods a stall's order
queue until it can't serve real customers. Authorization stops people doing
things they shouldn't; rate limiting stops them doing permitted things so
often that the result is abuse.

Two identities are used. Anything reachable without a token is limited per
client address, because that is all we know about the caller. Anything behind
a token is limited per user id, which is stronger: switching IP doesn't reset
it, and a shared campus NAT doesn't punish everyone for one person.
"""

import logging
import time
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request, WebSocket, status
from redis.asyncio import Redis

from app.core.config import Settings, get_settings
from app.core.deps import get_current_user
from app.core.redis import get_redis
from app.db.models.user import User

logger = logging.getLogger("app.ratelimit")


@dataclass(frozen=True)
class Limit:
    """At most `requests` in any `seconds`-long window."""

    requests: int
    seconds: int

    def __post_init__(self) -> None:
        if self.requests < 1 or self.seconds < 1:
            raise ValueError("a limit needs a positive budget and window")


# Windows are fixed rather than sliding: the key carries the window number, so
# each window starts at zero and expires itself. The known cost is that a
# caller can spend one budget just before a boundary and another just after,
# briefly doubling the nominal rate. That is acceptable here - the limits below
# are set by what causes harm, not by what is exactly fair - and it buys one
# Redis round trip per check instead of maintaining a log of timestamps.
_CONSUME = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then
  redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return {count, redis.call('TTL', KEYS[1])}
"""


def client_ip(request: Request | WebSocket, settings: Settings) -> str:
    """The caller's address, as far as it can be trusted.

    Railway terminates the connection itself, so `request.client.host` is the
    proxy and every visitor would share a single bucket. The real address is in
    X-Forwarded-For - but that header is caller-controlled, and trusting its
    leftmost entry would let anyone send `X-Forwarded-For: <random>` to get a
    fresh bucket per request, silently disabling every limit in this module.

    So hops are counted from the right. Each proxy appends the address it
    received the connection from, so with one trusted proxy in front, the
    rightmost entry is the one Railway itself observed - the only one a caller
    cannot forge. Entries to the left of it may be invented and are ignored.

    This only holds if nothing else has already rewritten the request. Uvicorn
    does exactly that by default: --proxy-headers replaces request.client with
    the *leftmost* X-Forwarded-For entry, which is the forgeable one, and a
    forged header then wins whenever TRUSTED_PROXY_COUNT is 0. Every start
    command in this repo therefore passes --no-proxy-headers, so the header is
    interpreted here and only here. Testing this is what caught it: with
    uvicorn's default, eight requests carrying eight invented addresses each got
    their own budget.
    """
    peer = request.client.host if request.client else None

    hops = settings.trusted_proxy_count
    # A header only means something if whoever sent it is entitled to speak for
    # someone else. With TRUSTED_PROXY_COUNT=1 the rightmost entry is the proxy's
    # own observation *if the request came through the proxy* - and reading the
    # header cannot establish that, because one forged entry looks exactly like
    # one appended entry. TRUSTED_PROXY_HOSTS is how a deployment that is
    # reachable by more than its proxy says so; left empty, any peer is believed,
    # which is right on a platform whose edge is the only way in.
    if hops > 0 and settings.peer_may_set_forwarded_for(peer):
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            parts = [p.strip() for p in forwarded.split(",") if p.strip()]
            # Only trust the header when it carries at least as many hops as we
            # were told to expect. A shorter one means the request did not come
            # through those proxies, so nothing in it was written by anything we
            # trust and every entry is caller-supplied.
            #
            # This used to clamp to the leftmost entry instead, which failed in
            # the wrong direction: a caller reaching the app without the
            # expected hop - over private networking, or with the proxy count
            # misconfigured - could send `X-Forwarded-For: <anything>` and get a
            # fresh bucket on every request, which silently disables every
            # per-IP limit in this module. Falling back to the peer address
            # costs a shared bucket in that case and cannot be forged.
            if len(parts) >= hops:
                return parts[len(parts) - hops]
    return peer or "unknown"


async def consume(
    redis: Redis,
    name: str,
    identity: str,
    limits: tuple[Limit, ...],
    *,
    fail_open: bool = True,
) -> None:
    """Count one request against every limit, or raise 429.

    `fail_open` decides what an unreachable Redis means. For most endpoints the
    limiter going down should not take the whole app down with it, so the
    request is allowed and the failure logged loudly. For the login endpoints
    it is the other way round: a limiter that silently stops working there is
    exactly the hole this module exists to close, and those routes need Redis
    anyway (the codes live in it), so they refuse instead.
    """
    for limit in limits:
        window = int(time.time()) // limit.seconds
        key = f"rl:{name}:{identity}:{limit.seconds}:{window}"
        try:
            count, ttl = await redis.eval(_CONSUME, 1, key, limit.seconds)
        except Exception as exc:
            logger.error("rate limiter unavailable (%s): %s", name, exc)
            if fail_open:
                return
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                "Service temporarily unavailable, please try again shortly.",
            )

        if count > limit.requests:
            retry_after = ttl if ttl and ttl > 0 else limit.seconds
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                "Too many requests. Please slow down and try again shortly.",
                headers={"Retry-After": str(retry_after)},
            )


def limit_by_ip(name: str, *limits: Limit, fail_open: bool = True):
    """Limit an endpoint per client address. For anything reachable without a token."""

    async def dependency(
        request: Request,
        redis: Redis = Depends(get_redis),
        settings: Settings = Depends(get_settings),
    ) -> None:
        await consume(
            redis, name, f"ip:{client_ip(request, settings)}", limits, fail_open=fail_open
        )

    return dependency


def limit_by_user(name: str, *limits: Limit, fail_open: bool = True):
    """Limit an endpoint per account. For anything behind a token."""

    async def dependency(
        user: User = Depends(get_current_user),
        redis: Redis = Depends(get_redis),
    ) -> None:
        await consume(redis, name, f"user:{user.id}", limits, fail_open=fail_open)

    return dependency

"""Tests for the rate limiter, and especially for who it thinks you are.

A limiter that can be handed a fresh identity per request is not a limiter, so
client_ip gets the most attention here: it is four lines of index arithmetic
standing between the whole module and irrelevance.
"""

import uuid

import pytest
from fastapi import HTTPException

from app.core.config import Settings
from app.core.limits import MINUTE
from app.core.ratelimit import Limit, client_ip, consume


def settings(**overrides) -> Settings:
    return Settings(
        database_url="postgresql+asyncpg://u:p@localhost/db",
        redis_url="redis://localhost:6379/0",
        jwt_secret="test-secret",
        **overrides,
    )


class FakeRequest:
    """Stands in for a Request/WebSocket as far as client_ip cares."""

    def __init__(self, headers=None, peer="10.0.0.1"):
        self.headers = headers or {}

        class _Client:
            host = peer

        self.client = _Client() if peer else None


# --- Identity ---------------------------------------------------------------


def test_uses_peer_address_when_no_proxy_is_trusted():
    request = FakeRequest({"x-forwarded-for": "1.2.3.4"}, peer="10.0.0.1")
    # Nothing in front, so the header is noise and must be ignored entirely.
    assert client_ip(request, settings(trusted_proxy_count=0)) == "10.0.0.1"


def test_reads_the_real_client_through_one_trusted_proxy():
    # What Railway sends when the caller set no header of their own.
    request = FakeRequest({"x-forwarded-for": "203.0.113.9"}, peer="10.0.0.1")
    assert client_ip(request, settings(trusted_proxy_count=1)) == "203.0.113.9"


def test_a_forged_forwarded_for_cannot_change_the_bucket():
    """The attack this function exists to stop.

    A caller who prepends their own X-Forwarded-For gets it *appended to*, not
    replaced - the proxy adds the address it actually saw. Reading from the
    right means we get the proxy's observation and the forged entry is ignored,
    so the attacker keeps hitting the same bucket no matter what they send.
    """
    real = "203.0.113.9"
    for forged in ("1.2.3.4", "9.9.9.9, 8.8.8.8", "not-an-ip"):
        request = FakeRequest({"x-forwarded-for": f"{forged}, {real}"}, peer="10.0.0.1")
        assert client_ip(request, settings(trusted_proxy_count=1)) == real


def test_two_trusted_proxies_look_one_hop_further_left():
    request = FakeRequest(
        {"x-forwarded-for": "1.2.3.4, 203.0.113.9, 10.1.0.7"}, peer="10.0.0.1"
    )
    assert client_ip(request, settings(trusted_proxy_count=2)) == "203.0.113.9"


def test_a_header_shorter_than_the_trusted_hop_count_is_ignored():
    """Fewer hops present than configured, so the header is not to be believed.

    This used to clamp to the leftmost entry and return it, which was a bypass
    rather than a graceful degradation: a caller reaching the app without the
    expected proxy hop - over Railway's private networking, or with
    TRUSTED_PROXY_COUNT set higher than the real number of hops - could put any
    value in the header and be counted as a different client on every request,
    which silently switches off every per-IP limit in the module.

    Falling back to the peer address is the safe direction. The cost is that
    callers genuinely sharing that address share a bucket; the alternative cost
    was having no limits at all.
    """
    request = FakeRequest({"x-forwarded-for": "203.0.113.9"}, peer="10.0.0.1")
    assert client_ip(request, settings(trusted_proxy_count=3)) == "10.0.0.1"


def test_a_forged_header_cannot_buy_a_fresh_bucket_without_the_proxy():
    """The bypass the fallback above closes, stated as the attack.

    Every one of these reaches the app without the hop TRUSTED_PROXY_COUNT
    promises, so none of them may be allowed to change the identity.
    """
    for forged in ("1.2.3.4", "9.9.9.9", "not-an-ip", "  ,  "):
        request = FakeRequest({"x-forwarded-for": forged}, peer="10.0.0.1")
        assert client_ip(request, settings(trusted_proxy_count=2)) == "10.0.0.1"


def test_missing_header_and_missing_peer_still_yields_an_identity():
    assert client_ip(FakeRequest({}, peer=None), settings()) == "unknown"


# --- Counting ---------------------------------------------------------------
#
# These run against a real Redis so the Lua in ratelimit.py is actually
# executed rather than re-implemented in a stub that could agree with a bug.

redis_asyncio = pytest.importorskip("redis.asyncio")


@pytest.fixture
async def redis():
    client = redis_asyncio.Redis.from_url("redis://localhost:6379/0", decode_responses=True)
    try:
        await client.ping()
    except Exception:
        pytest.skip("needs a local Redis on 6379")
    yield client
    await client.aclose()


async def test_allows_the_budget_then_refuses(redis):
    identity = f"test:{uuid.uuid4()}"
    budget = Limit(3, MINUTE)

    for _ in range(3):
        await consume(redis, "unit", identity, (budget,))

    with pytest.raises(HTTPException) as exc:
        await consume(redis, "unit", identity, (budget,))
    assert exc.value.status_code == 429
    # Clients need to be told when to come back, not just that they failed.
    assert int(exc.value.headers["Retry-After"]) > 0


async def test_identities_do_not_share_a_bucket(redis):
    budget = Limit(1, MINUTE)
    await consume(redis, "unit", f"a:{uuid.uuid4()}", (budget,))
    # One caller spending their budget must not affect anyone else.
    await consume(redis, "unit", f"b:{uuid.uuid4()}", (budget,))


async def test_names_do_not_share_a_bucket(redis):
    identity = f"test:{uuid.uuid4()}"
    budget = Limit(1, MINUTE)
    await consume(redis, "endpoint-one", identity, (budget,))
    await consume(redis, "endpoint-two", identity, (budget,))


async def test_the_tightest_of_several_windows_wins(redis):
    identity = f"test:{uuid.uuid4()}"
    # Generous per minute, strict per hour: the hour must still bite.
    both = (Limit(100, MINUTE), Limit(2, 3600))
    await consume(redis, "unit", identity, both)
    await consume(redis, "unit", identity, both)
    with pytest.raises(HTTPException) as exc:
        await consume(redis, "unit", identity, both)
    assert exc.value.status_code == 429


# --- Behaviour when Redis is gone -------------------------------------------


class BrokenRedis:
    async def eval(self, *args, **kwargs):
        raise ConnectionError("redis is down")


async def test_fails_open_by_default_so_an_outage_is_not_an_outage():
    # Most endpoints would rather serve traffic unlimited than not at all.
    await consume(BrokenRedis(), "unit", "someone", (Limit(1, MINUTE),))


async def test_fails_closed_where_the_limit_is_the_security_control():
    # The login endpoints pass fail_open=False: silently losing the limiter
    # there is the hole, and they cannot work without Redis anyway.
    with pytest.raises(HTTPException) as exc:
        await consume(
            BrokenRedis(), "unit", "someone", (Limit(1, MINUTE),), fail_open=False
        )
    assert exc.value.status_code == 503


# --- Who is allowed to speak for someone else -------------------------------
#
# Counting hops from the right defeats a *prepended* forgery, because a real
# proxy appends its own observation after it. What it cannot defeat on its own is
# a request that never passed through that proxy: with one trusted hop, a single
# forged entry and a single appended entry are the same header. Only the identity
# of the peer distinguishes them, which is what TRUSTED_PROXY_HOSTS supplies.


def test_any_peer_is_believed_when_no_allow_list_is_configured():
    """The default, and what a platform deployment relies on.

    Railway's edge is the only route into the container, so the entry it appends
    is trustworthy without having to name the proxy's address.
    """
    request = FakeRequest({"x-forwarded-for": "203.0.113.9"}, peer="10.0.0.1")
    assert client_ip(request, settings(trusted_proxy_count=1)) == "203.0.113.9"


def test_a_configured_proxy_is_still_believed():
    request = FakeRequest({"x-forwarded-for": "203.0.113.9"}, peer="10.0.0.7")
    config = settings(trusted_proxy_count=1, trusted_proxy_hosts="10.0.0.0/8")
    assert client_ip(request, config) == "203.0.113.9"


def test_an_unlisted_peer_cannot_forge_an_identity():
    """The case reading-from-the-right cannot catch by itself.

    One trusted hop, one header entry, and nothing in front of the app: the entry
    is the caller's invention. Every forgery below must collapse to the address
    the connection actually came from, or the caller gets a fresh rate-limit
    budget per request and every per-IP limit is off.
    """
    config = settings(trusted_proxy_count=1, trusted_proxy_hosts="10.0.0.0/8")
    for forged in ("1.2.3.4", "9.9.9.9", "203.0.113.9, 198.51.100.1", "not-an-ip"):
        request = FakeRequest({"x-forwarded-for": forged}, peer="198.51.100.77")
        assert client_ip(request, config) == "198.51.100.77", forged


def test_a_single_host_may_be_listed_without_a_mask():
    config = settings(trusted_proxy_count=1, trusted_proxy_hosts="10.0.0.7")
    trusted = FakeRequest({"x-forwarded-for": "203.0.113.9"}, peer="10.0.0.7")
    other = FakeRequest({"x-forwarded-for": "203.0.113.9"}, peer="10.0.0.8")
    assert client_ip(trusted, config) == "203.0.113.9"
    assert client_ip(other, config) == "10.0.0.8"


def test_a_garbled_allow_list_entry_does_not_open_the_gate():
    """A typo must not silently mean "trust everyone" - it means trust the rest
    of the list, and this peer is not on it."""
    config = settings(trusted_proxy_count=1, trusted_proxy_hosts="not-a-network, 10.0.0.0/8")
    assert config.trusted_proxy_networks and len(config.trusted_proxy_networks) == 1
    request = FakeRequest({"x-forwarded-for": "1.2.3.4"}, peer="198.51.100.77")
    assert client_ip(request, config) == "198.51.100.77"


def test_an_unknown_peer_with_an_allow_list_is_not_trusted():
    config = settings(trusted_proxy_count=1, trusted_proxy_hosts="10.0.0.0/8")
    assert client_ip(FakeRequest({"x-forwarded-for": "1.2.3.4"}, peer=None), config) == "unknown"

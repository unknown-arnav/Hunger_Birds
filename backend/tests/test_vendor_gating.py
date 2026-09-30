"""Approval gates what a stall can do, not just what students can see.

Approval used to be checked in two places: the public stall list and the
order-placement path. That made it a filter on visibility rather than a limit on
capability, so suspending a stall left it holding every other route - its order
list (with each customer's name and phone number on it), the status machine for
those orders, its menu, and the is_open switch it could flip straight back on.

get_own_active_vendor is the single gate that fixes it. These tests pin the
dependency itself and, separately, assert that every stall-acting route is wired
to it - because the failure mode here is a route added later that quietly takes
the ungated dependency instead.
"""

import uuid

import pytest
from fastapi import HTTPException

from app.modules.vendors.deps import get_own_active_vendor


class FakeVendor:
    def __init__(self, *, is_approved: bool):
        self.id = uuid.uuid4()
        self.user_id = uuid.uuid4()
        self.stall_name = "Test Stall"
        self.is_approved = is_approved
        self.is_open = True


# --- The gate itself --------------------------------------------------------


async def test_an_approved_stall_passes_through():
    vendor = FakeVendor(is_approved=True)
    assert await get_own_active_vendor(vendor) is vendor


@pytest.mark.parametrize(
    "reason",
    [
        "never reviewed by an admin yet",
        "approved once and then suspended",
    ],
)
async def test_an_unapproved_stall_is_refused(reason):
    """Both states look the same to this gate, and should.

    A stall pending first review and a stall an admin has just shut down are
    equally not cleared to trade; the reason they are unapproved does not change
    what they may do.
    """
    with pytest.raises(HTTPException) as exc:
        await get_own_active_vendor(FakeVendor(is_approved=False))
    assert exc.value.status_code == 403


# --- Every stall-acting route is behind it ----------------------------------


def _api_routes() -> list[tuple[str, object]]:
    """Every (full_path, APIRoute) pair in the app, included routers included.

    FastAPI 0.141 stopped flattening include_router() into app.routes. Each call
    now leaves an _IncludedRouter wrapper whose own routes keep their *unprefixed*
    paths, with the prefix held separately in include_context - so a flat scan of
    app.routes finds four routes and none of the API, and reassembling the prefix
    is what makes the paths below match.
    """
    from fastapi.routing import APIRoute

    from app.main import app

    found: list[tuple[str, object]] = []

    def walk(routes, prefix: str) -> None:
        for route in routes:
            if isinstance(route, APIRoute):
                found.append((prefix + route.path, route))
                continue
            context = getattr(route, "include_context", None)
            nested = getattr(route, "original_router", None)
            if nested is not None:
                walk(nested.routes, prefix + getattr(context, "prefix", ""))

    walk(app.routes, "")
    return found


def test_the_route_scan_actually_finds_the_api():
    """Guards the guard.

    Every assertion below has the form "this route must have that dependency",
    which passes trivially if the scan returns nothing - exactly what happened
    when FastAPI changed how included routers are stored. So assert the scan
    still sees a whole API before trusting anything it reports.
    """
    paths = {path for path, _ in _api_routes()}
    assert len(paths) > 25, f"route scan found only {len(paths)} paths: {sorted(paths)}"
    assert "/api/media/signature" in paths
    assert "/api/vendors/me/orders" in paths


def _route_dependency_names(route) -> set[str]:
    names: set[str] = set()

    def walk(dependant):
        for sub in dependant.dependencies:
            names.add(getattr(sub.call, "__name__", ""))
            walk(sub)

    names.add(getattr(route.dependant.call, "__name__", ""))
    walk(route.dependant)
    return names


# Routes that act on a stall: they edit it, edit its menu, or touch its orders.
# Every one of these must sit behind the approval gate.
GATED_PATHS = {
    ("PATCH", "/api/vendors/me"),
    ("POST", "/api/vendors/me/categories"),
    ("GET", "/api/vendors/me/categories"),
    ("PATCH", "/api/vendors/me/categories/{category_id}"),
    ("DELETE", "/api/vendors/me/categories/{category_id}"),
    ("POST", "/api/vendors/me/items"),
    ("GET", "/api/vendors/me/items"),
    ("PATCH", "/api/vendors/me/items/{item_id}"),
    ("DELETE", "/api/vendors/me/items/{item_id}"),
    ("GET", "/api/vendors/me/orders"),
    ("PATCH", "/api/vendors/me/orders/{order_id}/status"),
}


def test_every_stall_acting_route_requires_approval():
    seen = set()
    for path, route in _api_routes():
        for method in route.methods:
            key = (method, path)
            if key not in GATED_PATHS:
                continue
            seen.add(key)
            assert "get_own_active_vendor" in _route_dependency_names(route), (
                f"{method} {path} acts on a stall but does not require approval"
            )

    missing = GATED_PATHS - seen
    assert not missing, f"routes renamed or removed; update this list: {missing}"


def test_reading_your_own_stall_stays_open_to_a_pending_one():
    """The one deliberate exception.

    The merchant app's "under review" screen polls GET /vendors/me to find out
    whether it has been approved yet. Gating that would leave a pending vendor
    unable to learn they are pending.
    """
    for path, route in _api_routes():
        if path == "/api/vendors/me" and "GET" in route.methods:
            names = _route_dependency_names(route)
            assert "get_own_vendor" in names
            assert "get_own_active_vendor" not in names
            return
    raise AssertionError("GET /api/vendors/me not found")


def test_minting_an_upload_permit_requires_approval_too():
    """Each signature is a write permit for our Cloudinary account, so it is
    limited to the people who put photos on a menu rather than to anyone with a
    campus login."""
    for path, route in _api_routes():
        if path == "/api/media/signature":
            assert "require_upload_rights" in _route_dependency_names(route)
            return
    raise AssertionError("GET /api/media/signature not found")

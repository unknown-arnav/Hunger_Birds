import pytest

from app.db.models.order import OrderStatus
from app.modules.orders.service import can_transition, order_channel, vendor_channel


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (OrderStatus.PLACED, OrderStatus.ACCEPTED),
        (OrderStatus.PLACED, OrderStatus.REJECTED),
        (OrderStatus.PLACED, OrderStatus.CANCELLED),
        (OrderStatus.ACCEPTED, OrderStatus.PREPARING),
        (OrderStatus.ACCEPTED, OrderStatus.CANCELLED),
        (OrderStatus.PREPARING, OrderStatus.READY),
        (OrderStatus.READY, OrderStatus.COMPLETED),
    ],
)
def test_allowed_transitions(current, target):
    assert can_transition(current, target)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        # can't skip ahead
        (OrderStatus.PLACED, OrderStatus.READY),
        (OrderStatus.PLACED, OrderStatus.COMPLETED),
        (OrderStatus.ACCEPTED, OrderStatus.COMPLETED),
        # can't go backwards
        (OrderStatus.PREPARING, OrderStatus.ACCEPTED),
        (OrderStatus.READY, OrderStatus.PREPARING),
        # a vendor can't reject after accepting
        (OrderStatus.ACCEPTED, OrderStatus.REJECTED),
        # terminal states are final
        (OrderStatus.COMPLETED, OrderStatus.READY),
        (OrderStatus.REJECTED, OrderStatus.ACCEPTED),
        (OrderStatus.CANCELLED, OrderStatus.ACCEPTED),
    ],
)
def test_rejected_transitions(current, target):
    assert not can_transition(current, target)


def test_terminal_states_have_no_way_out():
    for status in (OrderStatus.COMPLETED, OrderStatus.REJECTED, OrderStatus.CANCELLED):
        assert all(not can_transition(status, target) for target in OrderStatus)


def test_channels_are_scoped_per_order_and_vendor():
    assert order_channel("abc") == "order:abc"
    assert vendor_channel("xyz") == "vendor:xyz"
    assert order_channel("abc") != vendor_channel("abc")

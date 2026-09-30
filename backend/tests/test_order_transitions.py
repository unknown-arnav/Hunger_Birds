import pytest

from app.db.models.order import OrderStatus
from app.modules.orders.service import (
    can_customer_cancel,
    can_transition,
    order_channel,
    vendor_channel,
)


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
        # A stall must be able to release an order it cannot fill, from any
        # non-terminal state. Without these two an order that reached preparing
        # had no exit but the stall advancing it, so a stall that went quiet left
        # the customer stuck with an order nobody could close.
        (OrderStatus.PREPARING, OrderStatus.CANCELLED),
        (OrderStatus.READY, OrderStatus.CANCELLED),
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


# --- Who may cancel, as opposed to what the state machine permits ------------


@pytest.mark.parametrize("status", [OrderStatus.PLACED, OrderStatus.ACCEPTED])
def test_a_customer_may_cancel_before_cooking_starts(status):
    assert can_customer_cancel(status)


@pytest.mark.parametrize(
    "status",
    [
        # The food is being made or is waiting on the counter. The stall can
        # still cancel from here, and an admin can; the customer cannot.
        OrderStatus.PREPARING,
        OrderStatus.READY,
        OrderStatus.COMPLETED,
        OrderStatus.REJECTED,
        OrderStatus.CANCELLED,
    ],
)
def test_a_customer_may_not_cancel_once_it_is_being_made(status):
    assert not can_customer_cancel(status)


def test_the_customer_rule_is_stricter_than_the_state_machine():
    """The reason cancel_order asks can_customer_cancel and not can_transition.

    Opening preparing and ready to cancellation gave the stall a release valve.
    Reading that new permission off the state machine alone would have handed
    the same exit to the customer, which is not the intent - so the two must
    genuinely disagree here.
    """
    assert can_transition(OrderStatus.PREPARING, OrderStatus.CANCELLED)
    assert not can_customer_cancel(OrderStatus.PREPARING)

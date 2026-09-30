from redis.asyncio import Redis

from app.db.models.order import Order, OrderStatus
from app.modules.orders.schemas import OrderOut

# Which statuses an order may move to from its current status. Anything not
# listed as a key (COMPLETED, REJECTED, CANCELLED) is terminal.
#
# preparing and ready can now be cancelled. Before, they could not: preparing
# led only to ready and ready only to completed, both vendor-driven, so an order
# that reached preparing had no exit that anyone but the stall could take. A
# stall that stopped tapping - closed for the day, or suspended mid-service -
# left the customer with an order stuck open forever, unable to cancel and with
# nobody able to close it for them. Letting a cancellation out of those states
# gives the stall a way to release an order it cannot fill, and gives an admin a
# way to clean one up. It is not an exit for the customer: cancel_order applies
# can_customer_cancel below on top of this.
ALLOWED_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.PLACED: {OrderStatus.ACCEPTED, OrderStatus.REJECTED, OrderStatus.CANCELLED},
    OrderStatus.ACCEPTED: {OrderStatus.PREPARING, OrderStatus.CANCELLED},
    OrderStatus.PREPARING: {OrderStatus.READY, OrderStatus.CANCELLED},
    OrderStatus.READY: {OrderStatus.COMPLETED, OrderStatus.CANCELLED},
}

# How far a customer may back out on their own. Deliberately narrower than the
# table above: cancelling is free before the stall starts cooking and costly
# afterwards, so the food being made is where the customer's own cancel stops.
CUSTOMER_CANCELLABLE: frozenset[OrderStatus] = frozenset(
    {OrderStatus.PLACED, OrderStatus.ACCEPTED}
)


def can_transition(current: OrderStatus, target: OrderStatus) -> bool:
    return target in ALLOWED_TRANSITIONS.get(current, set())


def can_customer_cancel(current: OrderStatus) -> bool:
    """Whether the customer may cancel their own order from this status."""
    return current in CUSTOMER_CANCELLABLE


def order_channel(order_id) -> str:
    return f"order:{order_id}"


def vendor_channel(vendor_id) -> str:
    return f"vendor:{vendor_id}"


async def publish_order_event(redis: Redis, order: Order) -> None:
    payload = OrderOut.model_validate(order).model_dump_json()
    await redis.publish(order_channel(order.id), payload)
    await redis.publish(vendor_channel(order.vendor_id), payload)

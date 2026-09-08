from redis.asyncio import Redis

from app.db.models.order import Order, OrderStatus
from app.modules.orders.schemas import OrderOut

# Which statuses an order may move to from its current status. Anything not
# listed as a key (COMPLETED, REJECTED, CANCELLED) is terminal.
ALLOWED_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.PLACED: {OrderStatus.ACCEPTED, OrderStatus.REJECTED, OrderStatus.CANCELLED},
    OrderStatus.ACCEPTED: {OrderStatus.PREPARING, OrderStatus.CANCELLED},
    OrderStatus.PREPARING: {OrderStatus.READY},
    OrderStatus.READY: {OrderStatus.COMPLETED},
}


def can_transition(current: OrderStatus, target: OrderStatus) -> bool:
    return target in ALLOWED_TRANSITIONS.get(current, set())


def order_channel(order_id) -> str:
    return f"order:{order_id}"


def vendor_channel(vendor_id) -> str:
    return f"vendor:{vendor_id}"


async def publish_order_event(redis: Redis, order: Order) -> None:
    payload = OrderOut.model_validate(order).model_dump_json()
    await redis.publish(order_channel(order.id), payload)
    await redis.publish(vendor_channel(order.vendor_id), payload)

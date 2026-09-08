import asyncio
import contextlib
import uuid

import jwt
from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect, status
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis
from app.core.security import TokenType, decode_token
from app.db.models.order import Order
from app.db.models.user import User, UserRole
from app.db.models.vendor import Vendor
from app.db.session import get_db
from app.modules.orders.service import order_channel, vendor_channel

router = APIRouter(tags=["realtime"])

CLOSE_UNAUTHORIZED = 4401


async def _authenticate_ws(token: str, db: AsyncSession) -> User | None:
    try:
        payload = decode_token(token)
    except jwt.PyJWTError:
        return None
    if payload.get("type") != TokenType.ACCESS.value:
        return None
    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError):
        return None
    return await db.get(User, user_id)


async def _pump_channel_to_socket(websocket: WebSocket, redis: Redis, channel: str) -> None:
    pubsub = redis.pubsub()
    await pubsub.subscribe(channel)
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                await websocket.send_text(message["data"])
    finally:
        with contextlib.suppress(Exception):
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()


async def _watch_for_disconnect(websocket: WebSocket) -> None:
    # Clients don't need to send anything over this socket; this loop's only
    # job is to notice (via WebSocketDisconnect) when they go away.
    while True:
        await websocket.receive_text()


@router.websocket("/ws/orders/{order_id}")
async def ws_order_tracking(
    websocket: WebSocket,
    order_id: uuid.UUID,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> None:
    await websocket.accept()

    user = await _authenticate_ws(token, db)
    order = await db.get(Order, order_id) if user is not None else None

    authorized = False
    if user is not None and order is not None:
        is_owner_customer = order.customer_id == user.id
        is_owner_vendor = False
        if user.role == UserRole.VENDOR:
            result = await db.execute(select(Vendor).where(Vendor.user_id == user.id))
            vendor = result.scalar_one_or_none()
            is_owner_vendor = vendor is not None and vendor.id == order.vendor_id
        authorized = is_owner_customer or is_owner_vendor or user.role == UserRole.ADMIN

    if not authorized:
        await websocket.close(code=CLOSE_UNAUTHORIZED)
        return

    await _run_socket_after_accept(websocket, redis, order_channel(order_id))


@router.websocket("/ws/vendor/{vendor_id}")
async def ws_vendor_queue(
    websocket: WebSocket,
    vendor_id: uuid.UUID,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> None:
    await websocket.accept()

    user = await _authenticate_ws(token, db)
    vendor = await db.get(Vendor, vendor_id) if user is not None else None

    authorized = (
        vendor is not None
        and user is not None
        and ((user.role == UserRole.VENDOR and vendor.user_id == user.id) or user.role == UserRole.ADMIN)
    )

    if not authorized:
        await websocket.close(code=CLOSE_UNAUTHORIZED)
        return

    await _run_socket_after_accept(websocket, redis, vendor_channel(vendor_id))


async def _run_socket_after_accept(websocket: WebSocket, redis: Redis, channel: str) -> None:
    pump_task = asyncio.create_task(_pump_channel_to_socket(websocket, redis, channel))
    watch_task = asyncio.create_task(_watch_for_disconnect(websocket))
    try:
        await asyncio.wait([pump_task, watch_task], return_when=asyncio.FIRST_COMPLETED)
    finally:
        pump_task.cancel()
        watch_task.cancel()
        for task in (pump_task, watch_task):
            with contextlib.suppress(asyncio.CancelledError, WebSocketDisconnect, Exception):
                await task

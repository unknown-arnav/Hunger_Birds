from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, require_role
from app.db.models.user import User, UserRole
from app.db.models.vendor import Vendor
from app.db.session import get_db


async def get_own_vendor(
    user: User = Depends(require_role(UserRole.VENDOR)),
    db: AsyncSession = Depends(get_db),
) -> Vendor:
    """The caller's stall, whatever state it is in.

    Use this only where a stall that is pending review or suspended still has
    business reading its own record - which is the "under review" screen in the
    merchant app, and nothing else. Everything that acts on the stall should
    take get_own_active_vendor instead.
    """
    result = await db.execute(select(Vendor).where(Vendor.user_id == user.id))
    vendor = result.scalar_one_or_none()
    if vendor is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Vendor profile not found")
    return vendor


async def get_own_active_vendor(vendor: Vendor = Depends(get_own_vendor)) -> Vendor:
    """The caller's stall, but only while an admin says it may trade.

    Approval used to be checked in exactly two places - the public stall list and
    the order-placement path - which made it a filter on what students could see
    rather than a limit on what a stall could do. A suspended vendor kept every
    other route: it could still read its existing orders, and with them each
    customer's name and phone number; still drive those orders through the status
    machine; still edit its menu; and still set is_open back to true. In other
    words, suspending a stall for misbehaving left it holding the data and the
    controls, which is the opposite of what the button appears to do.

    Checking it here instead means one dependency governs every stall action, so
    a route added later inherits the rule rather than having to remember it.
    """
    if not vendor.is_approved:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "This stall is not currently approved to trade. "
            "Contact an admin if you think that is a mistake.",
        )
    return vendor


async def require_upload_rights(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Who may mint a Cloudinary upload signature.

    Each signature is a permit to write into our Cloudinary account, so it was
    worth narrowing from "anyone with a login" - every student on campus, none of
    whom has anything to upload - to the people who actually put photos on a
    menu. A suspended stall is excluded for the same reason it loses the rest of
    its routes: it should not still be spending our quota.
    """
    if user.role == UserRole.ADMIN:
        return user
    if user.role == UserRole.VENDOR:
        result = await db.execute(select(Vendor).where(Vendor.user_id == user.id))
        vendor = result.scalar_one_or_none()
        if vendor is not None and vendor.is_approved:
            return user
    raise HTTPException(
        status.HTTP_403_FORBIDDEN, "Only an approved stall can upload images"
    )

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_role
from app.db.models.user import User, UserRole
from app.db.models.vendor import Vendor
from app.db.session import get_db


async def get_own_vendor(
    user: User = Depends(require_role(UserRole.VENDOR)),
    db: AsyncSession = Depends(get_db),
) -> Vendor:
    result = await db.execute(select(Vendor).where(Vendor.user_id == user.id))
    vendor = result.scalar_one_or_none()
    if vendor is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Vendor profile not found")
    return vendor

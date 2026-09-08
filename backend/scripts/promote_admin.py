"""One-off script to promote an existing user to the admin role.

Usage (from backend/, with the venv activated and .env pointing at the
target database):

    PYTHONPATH=. python scripts/promote_admin.py someone@bitmesra.ac.in

The user must already exist (i.e. have logged in via OTP at least once).
"""

import asyncio
import sys

from sqlalchemy import select

from app.db.models.user import User, UserRole
from app.db.session import async_session_factory
from app.modules.auth.service import normalize_email


async def promote(email: str) -> None:
    normalized = normalize_email(email)
    async with async_session_factory() as db:
        result = await db.execute(select(User).where(User.email == normalized))
        user = result.scalar_one_or_none()
        if user is None:
            print(f"No user found with email {normalized}. Have them log in once first.")
            sys.exit(1)

        user.role = UserRole.ADMIN
        await db.commit()
        print(f"Promoted {normalized} to admin.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/promote_admin.py <email>")
        sys.exit(1)
    asyncio.run(promote(sys.argv[1]))

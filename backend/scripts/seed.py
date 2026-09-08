"""Seeds a few demo stalls, menus and an admin user so the apps have
something to show before real vendors onboard.

Usage (from backend/, venv active, .env pointing at the target database):

    PYTHONPATH=. python scripts/seed.py

Safe to re-run: stalls are matched by name and skipped if they already exist.
"""

import asyncio
import sys

from sqlalchemy import select

from app.db.models.menu import MenuCategory, MenuItem
from app.db.models.user import User, UserRole
from app.db.models.vendor import Vendor
from app.db.session import async_session_factory
from app.modules.auth.service import normalize_email

ADMIN_EMAIL = "admin@bitmesra.ac.in"

DEMO_STALLS = [
    {
        "email": "momopoint@bitmesra.ac.in",
        "stall_name": "Momo Point",
        "description": "Steamed and fried momos, right by the hostel gate",
        "sections": {
            "Momos": [
                ("Steamed Veg Momo", "8 pcs with spicy chutney", 60),
                ("Fried Veg Momo", "8 pcs, crispy", 80),
                ("Paneer Momo", "8 pcs, tandoori style", 100),
            ],
            "Beverages": [
                ("Masala Chai", None, 15),
                ("Cold Coffee", None, 50),
            ],
        },
    },
    {
        "email": "chaitapri@bitmesra.ac.in",
        "stall_name": "Chai Tapri",
        "description": "Chai, maggi and sandwiches near the main gate",
        "sections": {
            "Maggi": [
                ("Plain Maggi", None, 40),
                ("Cheese Maggi", "Loaded with cheese", 70),
                ("Egg Maggi", None, 60),
            ],
            "Snacks": [
                ("Veg Sandwich", "Grilled", 50),
                ("Samosa", "2 pcs", 20),
            ],
        },
    },
    {
        "email": "southexpress@bitmesra.ac.in",
        "stall_name": "South Express",
        "description": "Dosa, idli and filter coffee all day",
        "sections": {
            "Dosa": [
                ("Plain Dosa", None, 60),
                ("Masala Dosa", "With potato filling", 80),
                ("Cheese Dosa", None, 100),
            ],
            "Idli & More": [
                ("Idli Sambar", "3 pcs", 50),
                ("Filter Coffee", None, 25),
            ],
        },
    },
]


async def get_or_create_user(db, email: str, role: UserRole) -> User:
    normalized = normalize_email(email)
    result = await db.execute(select(User).where(User.email == normalized))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(email=normalized, role=role)
        db.add(user)
        await db.flush()
    elif user.role != role:
        user.role = role
    return user


async def seed() -> None:
    async with async_session_factory() as db:
        await get_or_create_user(db, ADMIN_EMAIL, UserRole.ADMIN)

        for stall in DEMO_STALLS:
            existing = await db.execute(
                select(Vendor).where(Vendor.stall_name == stall["stall_name"])
            )
            if existing.scalar_one_or_none() is not None:
                print(f"skipping {stall['stall_name']} (already seeded)")
                continue

            owner = await get_or_create_user(db, stall["email"], UserRole.VENDOR)
            vendor = Vendor(
                user_id=owner.id,
                stall_name=stall["stall_name"],
                description=stall["description"],
                is_approved=True,
                is_open=True,
            )
            db.add(vendor)
            await db.flush()

            for order, (section, items) in enumerate(stall["sections"].items()):
                category = MenuCategory(vendor_id=vendor.id, name=section, sort_order=order)
                db.add(category)
                await db.flush()
                for name, description, price in items:
                    db.add(
                        MenuItem(
                            vendor_id=vendor.id,
                            category_id=category.id,
                            name=name,
                            description=description,
                            price=price,
                        )
                    )
            print(f"seeded {stall['stall_name']}")

        await db.commit()

    print(f"\nDone. Admin account: {ADMIN_EMAIL}")
    print("Log in with that email in either app to get admin access.")


if __name__ == "__main__":
    try:
        asyncio.run(seed())
    except Exception as exc:  # surface a readable message instead of a traceback wall
        print(f"Seeding failed: {exc}")
        sys.exit(1)

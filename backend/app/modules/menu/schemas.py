import uuid
from decimal import Decimal

from pydantic import BaseModel


class CategoryCreate(BaseModel):
    name: str
    sort_order: int = 0


class CategoryUpdate(BaseModel):
    name: str | None = None
    sort_order: int | None = None


class CategoryOut(BaseModel):
    id: uuid.UUID
    name: str
    sort_order: int

    model_config = {"from_attributes": True}


class ItemCreate(BaseModel):
    name: str
    description: str | None = None
    price: Decimal
    category_id: uuid.UUID | None = None
    image_url: str | None = None


class ItemUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    price: Decimal | None = None
    category_id: uuid.UUID | None = None
    image_url: str | None = None
    is_available: bool | None = None


class ItemOut(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    price: Decimal
    category_id: uuid.UUID | None
    image_url: str | None
    is_available: bool

    model_config = {"from_attributes": True}


class CategoryWithItems(CategoryOut):
    items: list[ItemOut]

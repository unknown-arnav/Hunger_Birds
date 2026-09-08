import uuid

from pydantic import BaseModel

from app.modules.menu.schemas import CategoryWithItems, ItemOut


class VendorApply(BaseModel):
    stall_name: str
    description: str | None = None


class VendorUpdate(BaseModel):
    stall_name: str | None = None
    description: str | None = None
    cover_image_url: str | None = None
    is_open: bool | None = None


class VendorOut(BaseModel):
    id: uuid.UUID
    stall_name: str
    description: str | None
    cover_image_url: str | None
    is_approved: bool
    is_open: bool

    model_config = {"from_attributes": True}


class VendorDetailOut(VendorOut):
    categories: list[CategoryWithItems]
    uncategorized_items: list[ItemOut]

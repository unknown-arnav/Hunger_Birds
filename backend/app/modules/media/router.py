import time

import cloudinary.utils
from fastapi import APIRouter, Depends, HTTPException, status

from app.core import limits
from app.core.config import Settings, get_settings
from app.core.ratelimit import limit_by_user
from app.modules.media.schemas import UploadSignature
from app.modules.vendors.deps import require_upload_rights

# Signed alongside the timestamp and folder, so Cloudinary rejects an upload
# whose format is not one of these. Without a format in the signature the permit
# covered anything the client cared to send.
#
# This narrows the permit rather than sealing it: Cloudinary excludes
# resource_type from the signed parameter set, so the same signature can still
# be aimed at the raw or video endpoints. Closing that off for good needs a
# signed upload preset configured in the Cloudinary dashboard, pinning
# resource_type and a maximum file size; this is the part enforceable from here.
ALLOWED_UPLOAD_FORMATS = "jpg,jpeg,png,webp"

router = APIRouter(prefix="/media", tags=["media"])


@router.get(
    "/signature",
    response_model=UploadSignature,
    dependencies=[Depends(limit_by_user("media_signature", *limits.MEDIA_SIGNATURE))],
)
async def get_upload_signature(
    _=Depends(require_upload_rights),
    settings: Settings = Depends(get_settings),
) -> UploadSignature:
    if not settings.cloudinary_api_secret:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Image uploads are not configured yet"
        )

    timestamp = int(time.time())
    params_to_sign = {
        "timestamp": timestamp,
        "folder": settings.cloudinary_upload_folder,
        "allowed_formats": ALLOWED_UPLOAD_FORMATS,
    }
    signature = cloudinary.utils.api_sign_request(params_to_sign, settings.cloudinary_api_secret)

    # Every signed parameter has to be echoed by the client, or Cloudinary
    # recomputes a different signature and refuses the upload - so
    # allowed_formats is returned rather than left for the client to guess.
    return UploadSignature(
        cloud_name=settings.cloudinary_cloud_name,
        api_key=settings.cloudinary_api_key,
        timestamp=timestamp,
        signature=signature,
        folder=settings.cloudinary_upload_folder,
        allowed_formats=ALLOWED_UPLOAD_FORMATS,
    )

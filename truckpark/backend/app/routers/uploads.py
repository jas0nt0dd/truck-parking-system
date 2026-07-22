"""
Simple local-disk photo upload endpoint for entry/exit photos.

In production this would typically point at S3/Cloud Storage instead;
the interface (returns a `url` string) is kept storage-agnostic so the
backend can swap implementations without touching routers/schemas.
"""
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status

from app.core.config import settings
from app.core.dependencies import require_gatekeeper_or_admin
from app.models.user import User

router = APIRouter(prefix="/uploads", tags=["uploads"])

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}


@router.post("/photo")
async def upload_photo(
    file: UploadFile,
    current_user: User = Depends(require_gatekeeper_or_admin),
):
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only JPEG, PNG, or WEBP images are allowed",
        )

    contents = await file.read()
    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    if len(contents) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large (max {settings.MAX_UPLOAD_MB}MB)",
        )

    tenant_folder = str(current_user.tenant_id) if current_user.tenant_id else "platform"
    upload_dir = Path(settings.UPLOAD_DIR) / tenant_folder
    upload_dir.mkdir(parents=True, exist_ok=True)

    ext = Path(file.filename or "photo.jpg").suffix or ".jpg"
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = upload_dir / filename
    filepath.write_bytes(contents)

    return {"url": f"/{settings.UPLOAD_DIR}/{tenant_folder}/{filename}"}

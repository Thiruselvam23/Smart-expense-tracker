import os
import uuid
from fastapi import UploadFile, HTTPException
from app.config import settings

ALLOWED_MIME_TYPES = {
    'image/jpeg', 'image/png', 'image/webp',
    'image/bmp', 'image/gif', 'image/heic', 'image/heif',
}
ALLOWED_EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif', '.heic', '.heif',
}


def validate_image_file(file: UploadFile) -> None:
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: JPG, PNG, WebP, BMP, GIF, HEIC",
        )
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Please upload an image.",
        )


async def save_upload_file(file: UploadFile) -> str:
    """Save file locally for OCR processing. Returns local filepath."""
    contents = await file.read()
    size_mb  = len(contents) / (1024 * 1024)

    if size_mb > settings.MAX_FILE_SIZE_MB:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum {settings.MAX_FILE_SIZE_MB}MB allowed.",
        )

    ext      = os.path.splitext(file.filename)[1].lower() or '.jpg'
    filename = f"{uuid.uuid4().hex}{ext}"
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    filepath = os.path.join(settings.UPLOAD_DIR, filename)

    with open(filepath, 'wb') as f:
        f.write(contents)

    return filepath


def delete_file(filepath: str) -> None:
    try:
        if filepath and os.path.exists(filepath):
            os.remove(filepath)
    except Exception:
        pass
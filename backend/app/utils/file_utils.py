import os
import uuid
import cloudinary
import cloudinary.uploader
from fastapi import UploadFile, HTTPException
from app.config import settings

ALLOWED_MIME_TYPES = {
    'image/jpeg', 'image/png', 'image/webp',
    'image/bmp', 'image/gif', 'image/heic', 'image/heif',
}
ALLOWED_EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif', '.heic', '.heif',
}

# Configure Cloudinary
def configure_cloudinary():
    if settings.CLOUDINARY_CLOUD_NAME:
        cloudinary.config(
            cloud_name=settings.CLOUDINARY_CLOUD_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET,
            secure=True,
        )
        return True
    return False

USE_CLOUDINARY = configure_cloudinary()


def validate_image_file(file: UploadFile) -> None:
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: JPG, PNG, WebP, BMP, GIF, HEIC",
        )
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Invalid MIME type. Please upload an image file.",
        )


async def save_upload_file(file: UploadFile, folder: str = "receipts") -> str:
    """
    Upload file to Cloudinary if configured, else save locally.
    Returns the accessible URL/path.
    """
    contents = await file.read()
    size_mb = len(contents) / (1024 * 1024)
    if size_mb > settings.MAX_FILE_SIZE_MB:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {settings.MAX_FILE_SIZE_MB}MB.",
        )

    if USE_CLOUDINARY:
        # Upload to Cloudinary
        result = cloudinary.uploader.upload(
            contents,
            folder=f"expense_tracker/{folder}",
            public_id=uuid.uuid4().hex,
            resource_type="image",
        )
        return result["secure_url"]   # https://res.cloudinary.com/...
    else:
        # Fallback: save locally
        ext = os.path.splitext(file.filename)[1].lower() or '.jpg'
        filename = f"{uuid.uuid4().hex}{ext}"
        filepath = os.path.join(settings.UPLOAD_DIR, filename)
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        with open(filepath, 'wb') as f:
            f.write(contents)
        return filepath


async def save_profile_image(contents: bytes, user_id: str, ext: str) -> str:
    """Upload profile image — overwrites previous one for same user."""
    if USE_CLOUDINARY:
        result = cloudinary.uploader.upload(
            contents,
            folder="expense_tracker/profiles",
            public_id=f"profile_{user_id}",   # same ID = overwrites old photo
            overwrite=True,
            resource_type="image",
            transformation=[
                {"width": 300, "height": 300, "crop": "fill", "gravity": "face"}
            ],
        )
        return result["secure_url"]
    else:
        filename = f"profile_{user_id}{ext}"
        filepath = os.path.join(settings.UPLOAD_DIR, filename)
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        with open(filepath, 'wb') as f:
            f.write(contents)
        return f"/uploads/{filename}"


def delete_file(filepath: str) -> None:
    try:
        if filepath and os.path.exists(filepath):
            os.remove(filepath)
    except Exception:
        pass
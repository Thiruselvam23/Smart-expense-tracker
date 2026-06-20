import os
import uuid
import requests
from datetime import datetime, timedelta
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query
from fastapi.responses import RedirectResponse
from bson import ObjectId

from app.models.user import UserRegister, UserLogin, TokenResponse, RefreshRequest, AccessTokenResponse
from app.services.auth_service import AuthService
from app.dependencies import get_current_user
from app.database import get_db
from app.config import settings
from app.utils.security import create_access_token, create_refresh_token, hash_password
from app.repositories.user_repo import UserRepository

router = APIRouter()

ALLOWED_IMAGE_TYPES = {'image/jpeg', 'image/png', 'image/webp', 'image/gif', 'image/bmp'}

GOOGLE_AUTH_URL  = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USER_URL  = "https://www.googleapis.com/oauth2/v2/userinfo"


def format_user(user: dict, user_id: str = None) -> dict:
    uid = user_id or user.get("id") or str(user.get("_id", ""))
    return {
        "id":            uid,
        "email":         user.get("email"),
        "full_name":     user.get("full_name"),
        "created_at":    user.get("created_at"),
        "preferences":   user.get("preferences", {}),
        "profile_image": user.get("profile_image"),
    }


# ── Standard Auth ─────────────────────────────────────────────────────────────

@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(data: UserRegister, db=Depends(get_db)):
    return await AuthService(db).register(data.full_name, data.email, data.password)


@router.post("/login", response_model=TokenResponse)
async def login(data: UserLogin, db=Depends(get_db)):
    return await AuthService(db).login(data.email, data.password)


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh(data: RefreshRequest, db=Depends(get_db)):
    return await AuthService(db).refresh_token(data.refresh_token)


@router.post("/logout")
async def logout(current_user=Depends(get_current_user), db=Depends(get_db)):
    await AuthService(db).logout(current_user["id"])
    return {"message": "Logged out successfully"}


@router.get("/me")
async def me(current_user=Depends(get_current_user)):
    return format_user(current_user)


# ── Profile Image Upload ──────────────────────────────────────────────────────

@router.post("/profile-image")
async def upload_profile_image(
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
    db=Depends(get_db),
):
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Only image files are allowed")

    contents = await file.read()
    if len(contents) > 2 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Image must be under 2MB")

    ext = os.path.splitext(file.filename)[1].lower() or '.jpg'

    # Use Cloudinary or local storage
    from app.utils.file_utils import save_profile_image
    image_url = await save_profile_image(contents, current_user['id'], ext)

    await db.users.update_one(
        {"_id": ObjectId(current_user["id"])},
        {"$set": {"profile_image": image_url, "updated_at": datetime.utcnow()}},
    )
    return {"profile_image_url": image_url}


# ── Google OAuth ──────────────────────────────────────────────────────────────

@router.get("/google")
async def google_login():
    """Step 1 — Redirect user to Google consent screen."""
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=503, detail="Google OAuth not configured")

    params = {
        "client_id":     settings.GOOGLE_CLIENT_ID,
        "redirect_uri":  settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope":         "openid email profile",
        "access_type":   "offline",
        "prompt":        "select_account",   # always show account chooser
    }
    url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
    return RedirectResponse(url)


@router.get("/google/callback")
async def google_callback(
    code:  str = Query(...),
    db=Depends(get_db),
):
    """Step 2 — Google redirects back here with ?code=..."""
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=503, detail="Google OAuth not configured")

    # Exchange code for tokens
    token_resp = requests.post(GOOGLE_TOKEN_URL, data={
        "code":          code,
        "client_id":     settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "redirect_uri":  settings.GOOGLE_REDIRECT_URI,
        "grant_type":    "authorization_code",
    })
    if not token_resp.ok:
        raise HTTPException(status_code=400, detail="Failed to exchange Google code")

    google_access_token = token_resp.json().get("access_token")

    # Fetch user info from Google
    user_resp = requests.get(
        GOOGLE_USER_URL,
        headers={"Authorization": f"Bearer {google_access_token}"},
    )
    if not user_resp.ok:
        raise HTTPException(status_code=400, detail="Failed to fetch Google user info")

    guser = user_resp.json()
    email      = guser.get("email")
    full_name  = guser.get("name", email.split("@")[0])
    google_pic = guser.get("picture")  # Google profile picture URL
    google_id  = guser.get("id")

    if not email:
        raise HTTPException(status_code=400, detail="Could not get email from Google")

    repo = UserRepository(db)

    # Check if user already exists
    existing = await repo.find_by_email(email)

    if existing:
        # Update Google info if missing
        update = {"updated_at": datetime.utcnow()}
        if not existing.get("google_id"):
            update["google_id"] = google_id
        if not existing.get("profile_image") and google_pic:
            update["profile_image"] = google_pic
        await db.users.update_one({"_id": existing["_id"]}, {"$set": update})
        # Re-fetch updated user
        existing = await repo.find_by_email(email)
        user_id  = str(existing["_id"])
        user_doc = existing
    else:
        # Create new user (no password — Google-only account)
        now = datetime.utcnow()
        new_user = {
            "email":           email,
            "full_name":       full_name,
            "hashed_password": hash_password(uuid.uuid4().hex),  # random unusable password
            "google_id":       google_id,
            "profile_image":   google_pic,
            "is_active":       True,
            "auth_provider":   "google",
            "preferences":     {"currency": "INR", "default_view": "monthly"},
            "created_at":      now,
            "updated_at":      now,
        }
        result  = await db.users.insert_one(new_user)
        user_id = str(result.inserted_id)
        user_doc = new_user
        user_doc["_id"] = result.inserted_id

    # Issue JWT tokens
    access_token  = create_access_token(user_id)
    refresh_token = create_refresh_token(user_id)

    expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    await repo.save_refresh_token(user_id, refresh_token, expires_at)

    # Redirect to frontend with tokens in URL fragment
    # Frontend reads these from the URL and stores them
    frontend_url = settings.FRONTEND_URL
    redirect_url = (
        f"{frontend_url}/auth/google/success"
        f"?access_token={access_token}"
        f"&refresh_token={refresh_token}"
    )
    return RedirectResponse(redirect_url)
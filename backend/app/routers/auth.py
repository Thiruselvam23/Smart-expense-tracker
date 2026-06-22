import os
import uuid
import logging
import requests
from datetime import datetime, timedelta
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query
from fastapi.responses import RedirectResponse, HTMLResponse
from bson import ObjectId

from app.models.user import UserRegister, UserLogin, TokenResponse, RefreshRequest, AccessTokenResponse
from app.services.auth_service import AuthService
from app.dependencies import get_current_user
from app.database import get_db
from app.config import settings
from app.utils.security import create_access_token, create_refresh_token, hash_password
from app.repositories.user_repo import UserRepository

router = APIRouter()
logger = logging.getLogger(__name__)

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

    ext      = os.path.splitext(file.filename)[1].lower() or '.jpg'
    filename = f"profile_{current_user['id']}{ext}"
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    filepath = os.path.join(settings.UPLOAD_DIR, filename)

    with open(filepath, 'wb') as f:
        f.write(contents)

    image_url = f"/uploads/{filename}"
    await db.users.update_one(
        {"_id": ObjectId(current_user["id"])},
        {"$set": {"profile_image": image_url, "updated_at": datetime.utcnow()}},
    )
    return {"profile_image_url": image_url}


# ── Google OAuth ──────────────────────────────────────────────────────────────

@router.get("/google")
async def google_login():
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=503, detail="Google OAuth not configured")

    params = {
        "client_id":     settings.GOOGLE_CLIENT_ID,
        "redirect_uri":  settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope":         "openid email profile",
        "access_type":   "offline",
        "prompt":        "select_account",
    }
    url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
    return RedirectResponse(url)


@router.get("/google/callback")
async def google_callback(
    code: str = Query(...),
    db=Depends(get_db),
):
    frontend_url = settings.FRONTEND_URL

    try:
        logger.info(f"Google callback — using redirect_uri: {settings.GOOGLE_REDIRECT_URI}")

        # ── Step 1: Exchange code for token ──────────────────────────────
        token_resp = requests.post(GOOGLE_TOKEN_URL, data={
            "code":          code,
            "client_id":     settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri":  settings.GOOGLE_REDIRECT_URI,
            "grant_type":    "authorization_code",
        }, timeout=10)

        if not token_resp.ok:
            err = token_resp.json()
            logger.error(f"Token exchange failed: {err}")
            error_msg = err.get('error_description', err.get('error', 'Token exchange failed'))
            return RedirectResponse(f"{frontend_url}/login?error={error_msg}")

        google_access_token = token_resp.json().get("access_token")
        logger.info("Token exchange successful")

        # ── Step 2: Get user info from Google ────────────────────────────
        user_resp = requests.get(
            GOOGLE_USER_URL,
            headers={"Authorization": f"Bearer {google_access_token}"},
            timeout=10,
        )

        if not user_resp.ok:
            logger.error(f"User info fetch failed: {user_resp.text}")
            return RedirectResponse(f"{frontend_url}/login?error=Failed to get user info from Google")

        guser      = user_resp.json()
        email      = guser.get("email", "").strip().lower()
        full_name  = guser.get("name") or email.split("@")[0]
        google_pic = guser.get("picture")
        google_id  = str(guser.get("id", ""))

        logger.info(f"Google user: {email}")

        if not email:
            return RedirectResponse(f"{frontend_url}/login?error=No email from Google")

        # ── Step 3: Find or create user ──────────────────────────────────
        existing = await db.users.find_one({"email": email})

        if existing:
            user_id = str(existing["_id"])
            update  = {"updated_at": datetime.utcnow()}
            if not existing.get("google_id"):
                update["google_id"] = google_id
            if not existing.get("profile_image") and google_pic:
                update["profile_image"] = google_pic
            await db.users.update_one({"_id": existing["_id"]}, {"$set": update})
            logger.info(f"Existing user logged in: {user_id}")
        else:
            now = datetime.utcnow()
            result = await db.users.insert_one({
                "email":           email,
                "full_name":       full_name,
                "hashed_password": hash_password(uuid.uuid4().hex[:32]),
                "google_id":       google_id,
                "profile_image":   google_pic,
                "is_active":       True,
                "auth_provider":   "google",
                "preferences":     {"currency": "INR", "default_view": "monthly"},
                "created_at":      now,
                "updated_at":      now,
            })
            user_id = str(result.inserted_id)
            logger.info(f"New user created: {user_id}")

        # ── Step 4: Issue JWT tokens ──────────────────────────────────────
        access_token  = create_access_token(user_id)
        refresh_token = create_refresh_token(user_id)

        expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        # Save refresh token directly (avoid repo issues)
        await db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {
                "refresh_token":         refresh_token,
                "refresh_token_expires": expires_at,
            }}
        )

        logger.info(f"Tokens issued for user: {user_id}")

        # ── Step 5: Redirect to frontend ─────────────────────────────────
        redirect_url = (
            f"{frontend_url}/auth/google/success"
            f"?access_token={access_token}"
            f"&refresh_token={refresh_token}"
        )
        return RedirectResponse(redirect_url)

    except Exception as e:
        logger.error(f"Google callback unexpected error: {str(e)}", exc_info=True)
        return RedirectResponse(f"{frontend_url}/login?error=Login failed. Please try again.")
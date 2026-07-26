import os
import uuid
import logging
import secrets
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
from app.utils.security import (
    create_access_token, create_refresh_token,
    hash_password, verify_refresh_token,
)
from app.utils.email_utils import send_verification_email

router = APIRouter()
logger = logging.getLogger(__name__)

ALLOWED_IMAGE_TYPES = {'image/jpeg', 'image/png', 'image/webp', 'image/gif', 'image/bmp'}
GOOGLE_AUTH_URL  = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USER_URL  = "https://www.googleapis.com/oauth2/v2/userinfo"


def format_user(user: dict, user_id: str = None) -> dict:
    uid = user_id or user.get("id") or str(user.get("_id", ""))
    return {
        "id":              uid,
        "email":           user.get("email"),
        "full_name":       user.get("full_name"),
        "created_at":      user.get("created_at"),
        "preferences":     user.get("preferences", {}),
        "profile_image":   user.get("profile_image"),
        "is_verified":     user.get("is_verified", False),
    }


# ── Register ──────────────────────────────────────────────────────────────────

@router.post("/register", status_code=201)
async def register(data: UserRegister, db=Depends(get_db)):
    # Check if email already exists
    existing = await db.users.find_one({"email": data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    from app.utils.security import hash_password
    now   = datetime.utcnow()
    token = secrets.token_urlsafe(32)  # email verification token

    new_user = {
        "email":              data.email,
        "full_name":          data.full_name,
        "hashed_password":    hash_password(data.password),
        "is_active":          True,
        "is_verified":        False,           # not verified yet
        "verification_token": token,
        "verification_sent":  now,
        "auth_provider":      "email",
        "preferences":        {"currency": "INR", "default_view": "monthly"},
        "created_at":         now,
        "updated_at":         now,
    }

    result  = await db.users.insert_one(new_user)
    user_id = str(result.inserted_id)

    # Send verification email
    email_sent = send_verification_email(data.email, data.full_name, token)

    if email_sent:
        return {
            "message": "Registration successful! Please check your email to verify your account.",
            "email_sent": True,
            "email": data.email,
        }
    else:
        # If email fails (no RESEND key), auto-verify and return token
        # This allows local dev to work without email setup
        await db.users.update_one(
            {"_id": result.inserted_id},
            {"$set": {"is_verified": True}}
        )
        access_token  = create_access_token(user_id)
        refresh_token = create_refresh_token(user_id)
        expires_at    = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        await db.users.update_one(
            {"_id": result.inserted_id},
            {"$set": {"refresh_token": refresh_token, "refresh_token_expires": expires_at}}
        )
        new_user["_id"] = result.inserted_id
        return {
            "access_token":  access_token,
            "refresh_token": refresh_token,
            "token_type":    "bearer",
            "expires_in":    settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user":          format_user(new_user, user_id),
            "email_sent":    False,
        }


# ── Verify Email ──────────────────────────────────────────────────────────────

@router.get("/verify-email")
async def verify_email(token: str = Query(...), db=Depends(get_db)):
    user = await db.users.find_one({"verification_token": token})
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired verification link")

    # Check token not older than 24 hours
    sent_at = user.get("verification_sent")
    if sent_at and (datetime.utcnow() - sent_at).total_seconds() > 86400:
        raise HTTPException(status_code=400, detail="Verification link expired. Please register again.")

    # Mark as verified
    await db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {"is_verified": True, "updated_at": datetime.utcnow()},
         "$unset": {"verification_token": "", "verification_sent": ""}}
    )

    # Issue tokens and redirect to frontend dashboard
    user_id       = str(user["_id"])
    access_token  = create_access_token(user_id)
    refresh_token = create_refresh_token(user_id)
    expires_at    = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    await db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {"refresh_token": refresh_token, "refresh_token_expires": expires_at}}
    )

    # Redirect to frontend with tokens (same as Google OAuth flow)
    redirect_url = (
        f"{settings.FRONTEND_URL}/auth/google/success"
        f"?access_token={access_token}"
        f"&refresh_token={refresh_token}"
    )
    return RedirectResponse(redirect_url)


# ── Resend Verification ───────────────────────────────────────────────────────

@router.post("/resend-verification")
async def resend_verification(email: str, db=Depends(get_db)):
    user = await db.users.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=404, detail="Email not found")
    if user.get("is_verified"):
        raise HTTPException(status_code=400, detail="Email already verified")

    token = secrets.token_urlsafe(32)
    await db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {"verification_token": token, "verification_sent": datetime.utcnow()}}
    )
    send_verification_email(email, user.get("full_name", ""), token)
    return {"message": "Verification email resent. Please check your inbox."}


# ── Login ─────────────────────────────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse)
async def login(data: UserLogin, db=Depends(get_db)):
    from app.utils.security import verify_password
    user = await db.users.find_one({"email": data.email})

    if not user or not verify_password(data.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.get("is_active", True):
        raise HTTPException(status_code=403, detail="Account is deactivated")

    # Block login if email not verified (only for email/password users)
    if user.get("auth_provider", "email") == "email" and not user.get("is_verified", False):
        raise HTTPException(
            status_code=403,
            detail="Please verify your email before logging in. Check your inbox for the verification link."
        )

    user_id       = str(user["_id"])
    access_token  = create_access_token(user_id)
    refresh_token = create_refresh_token(user_id)
    expires_at    = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    await db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {"refresh_token": refresh_token, "refresh_token_expires": expires_at}}
    )

    return {
        "access_token":  access_token,
        "refresh_token": refresh_token,
        "token_type":    "bearer",
        "expires_in":    settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user":          format_user(user, user_id),
    }


# ── Refresh ───────────────────────────────────────────────────────────────────

@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh(data: RefreshRequest, db=Depends(get_db)):
    token   = data.refresh_token
    payload = verify_refresh_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user_id = payload["sub"]
    user    = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    if user.get("refresh_token") != token:
        raise HTTPException(status_code=401, detail="Refresh token revoked")

    return {
        "access_token": create_access_token(user_id),
        "token_type":   "bearer",
        "expires_in":   settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


# ── Logout ────────────────────────────────────────────────────────────────────

@router.post("/logout")
async def logout(current_user=Depends(get_current_user), db=Depends(get_db)):
    await db.users.update_one(
        {"_id": ObjectId(current_user["id"])},
        {"$unset": {"refresh_token": "", "refresh_token_expires": ""}},
    )
    return {"message": "Logged out successfully"}


# ── Me ────────────────────────────────────────────────────────────────────────

@router.get("/me")
async def me(current_user=Depends(get_current_user)):
    return format_user(current_user)


# ── Profile Image ─────────────────────────────────────────────────────────────

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
    return RedirectResponse(f"{GOOGLE_AUTH_URL}?{urlencode(params)}")


@router.get("/google/callback")
async def google_callback(code: str = Query(...), db=Depends(get_db)):
    frontend_url = settings.FRONTEND_URL
    try:
        token_resp = requests.post(GOOGLE_TOKEN_URL, data={
            "code": code, "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",
        }, timeout=15)

        if not token_resp.ok:
            err = token_resp.json()
            return RedirectResponse(f"{frontend_url}/login?error={err.get('error_description','Auth failed')}")

        google_access_token = token_resp.json().get("access_token")
        user_resp = requests.get(GOOGLE_USER_URL,
            headers={"Authorization": f"Bearer {google_access_token}"}, timeout=15)

        if not user_resp.ok:
            return RedirectResponse(f"{frontend_url}/login?error=Could not get Google profile")

        guser      = user_resp.json()
        email      = guser.get("email", "").strip().lower()
        full_name  = guser.get("name") or email.split("@")[0]
        google_pic = guser.get("picture")
        google_id  = str(guser.get("id", ""))

        if not email:
            return RedirectResponse(f"{frontend_url}/login?error=No email from Google")

        existing = await db.users.find_one({"email": email})
        if existing:
            user_id = str(existing["_id"])
            update  = {"updated_at": datetime.utcnow()}
            if not existing.get("google_id"):     update["google_id"]     = google_id
            if not existing.get("profile_image"): update["profile_image"] = google_pic
            if not existing.get("is_verified"):   update["is_verified"]   = True
            await db.users.update_one({"_id": existing["_id"]}, {"$set": update})
        else:
            now    = datetime.utcnow()
            result = await db.users.insert_one({
                "email": email, "full_name": full_name,
                "hashed_password": hash_password(uuid.uuid4().hex[:32]),
                "google_id": google_id, "profile_image": google_pic,
                "is_active": True, "is_verified": True,
                "auth_provider": "google",
                "preferences": {"currency": "INR", "default_view": "monthly"},
                "created_at": now, "updated_at": now,
            })
            user_id = str(result.inserted_id)

        access_token  = create_access_token(user_id)
        refresh_token = create_refresh_token(user_id)
        expires_at    = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        await db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"refresh_token": refresh_token, "refresh_token_expires": expires_at}}
        )

        return RedirectResponse(
            f"{frontend_url}/auth/google/success"
            f"?access_token={access_token}&refresh_token={refresh_token}"
        )
    except Exception as e:
        logger.error(f"Google callback error: {e}", exc_info=True)
        return RedirectResponse(f"{frontend_url}/login?error=Login+failed.+Please+try+again.")
from datetime import datetime, timedelta
from fastapi import HTTPException, status
from app.repositories.user_repo import UserRepository
from app.utils.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, verify_refresh_token,
)
from app.config import settings


class AuthService:
    def __init__(self, db):
        self.repo = UserRepository(db)

    async def register(self, full_name: str, email: str, password: str) -> dict:
        existing = await self.repo.find_by_email(email)
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")

        hashed = hash_password(password)
        user   = await self.repo.create(email, hashed, full_name)
        access  = create_access_token(user["id"])
        refresh = create_refresh_token(user["id"])

        expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        await self.repo.save_refresh_token(user["id"], refresh, expires_at)

        return {
            "access_token":  access,
            "refresh_token": refresh,
            "token_type":    "bearer",
            "expires_in":    settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user":          self._format_user(user),
        }

    async def login(self, email: str, password: str) -> dict:
        user = await self.repo.find_by_email(email)
        if not user or not verify_password(password, user["hashed_password"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )
        if not user.get("is_active", True):
            raise HTTPException(status_code=403, detail="Account is deactivated")

        user_id = str(user["_id"])
        access  = create_access_token(user_id)
        refresh = create_refresh_token(user_id)

        expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        await self.repo.save_refresh_token(user_id, refresh, expires_at)

        return {
            "access_token":  access,
            "refresh_token": refresh,
            "token_type":    "bearer",
            "expires_in":    settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user":          self._format_user(user, user_id),
        }

    async def refresh_token(self, token: str) -> dict:
        payload = verify_refresh_token(token)
        if not payload:
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        user_id = payload["sub"]
        stored  = await self.repo.get_refresh_token(user_id)
        if stored != token:
            raise HTTPException(status_code=401, detail="Refresh token has been revoked")

        new_access = create_access_token(user_id)
        return {
            "access_token": new_access,
            "token_type":   "bearer",
            "expires_in":   settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        }

    async def logout(self, user_id: str):
        await self.repo.invalidate_refresh_token(user_id)

    def _format_user(self, user: dict, user_id: str = None) -> dict:
        uid = user_id or user.get("id") or str(user.get("_id", ""))
        return {
            "id":            uid,
            "email":         user.get("email"),
            "full_name":     user.get("full_name"),
            "created_at":    user.get("created_at", datetime.utcnow()),
            "preferences":   user.get("preferences", {}),
            "profile_image": user.get("profile_image"),   # ← included in login response
        }
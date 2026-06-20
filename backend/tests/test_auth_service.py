import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime


# ─── Helpers ─────────────────────────────────────────────────────────────────

def make_db():
    """Return a mock db object."""
    return MagicMock()


def fake_user(user_id="64a1b2c3d4e5f6789abcdef0"):
    return {
        "_id": user_id,
        "id": user_id,
        "email": "test@example.com",
        "full_name": "Test User",
        "hashed_password": "$2b$12$KIXJkQz7O9YJ5GvK8q.3Ou3VhKpQ0A9YJ5KIXJkQz7O9YJ5Gv",
        "is_active": True,
        "preferences": {},
        "created_at": datetime.utcnow(),
    }


# ─── Registration Tests ───────────────────────────────────────────────────────

class TestRegister:

    @pytest.mark.asyncio
    async def test_register_success(self):
        from app.services.auth_service import AuthService

        db = make_db()
        service = AuthService(db)
        service.repo = AsyncMock()
        service.repo.find_by_email.return_value = None
        service.repo.create.return_value = fake_user()
        service.repo.save_refresh_token.return_value = None

        result = await service.register("Test User", "test@example.com", "Password123")

        assert "access_token" in result
        assert "refresh_token" in result
        assert result["user"]["email"] == "test@example.com"
        service.repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self):
        from app.services.auth_service import AuthService
        from fastapi import HTTPException

        db = make_db()
        service = AuthService(db)
        service.repo = AsyncMock()
        service.repo.find_by_email.return_value = fake_user()

        with pytest.raises(HTTPException) as exc:
            await service.register("Test User", "test@example.com", "Password123")

        assert exc.value.status_code == 400
        assert "already registered" in exc.value.detail.lower()

    @pytest.mark.asyncio
    async def test_register_creates_tokens(self):
        from app.services.auth_service import AuthService

        db = make_db()
        service = AuthService(db)
        service.repo = AsyncMock()
        service.repo.find_by_email.return_value = None
        service.repo.create.return_value = fake_user()
        service.repo.save_refresh_token.return_value = None

        result = await service.register("Test User", "new@example.com", "Password123")

        # Both tokens should be non-empty strings
        assert isinstance(result["access_token"], str)
        assert len(result["access_token"]) > 10
        assert isinstance(result["refresh_token"], str)
        assert len(result["refresh_token"]) > 10


# ─── Login Tests ──────────────────────────────────────────────────────────────

class TestLogin:

    @pytest.mark.asyncio
    async def test_login_success(self):
        from app.services.auth_service import AuthService
        from app.utils.security import hash_password

        db = make_db()
        service = AuthService(db)
        service.repo = AsyncMock()

        hashed = hash_password("Password123")
        user = fake_user()
        user["hashed_password"] = hashed
        user["_id"] = MagicMock()
        user["_id"].__str__ = lambda self: "64a1b2c3d4e5f6789abcdef0"

        service.repo.find_by_email.return_value = user
        service.repo.save_refresh_token.return_value = None

        result = await service.login("test@example.com", "Password123")

        assert "access_token" in result
        assert result["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_wrong_password(self):
        from app.services.auth_service import AuthService
        from app.utils.security import hash_password
        from fastapi import HTTPException

        db = make_db()
        service = AuthService(db)
        service.repo = AsyncMock()

        user = fake_user()
        user["hashed_password"] = hash_password("CorrectPassword123")
        user["_id"] = MagicMock()
        user["_id"].__str__ = lambda self: "64a1b2c3d4e5f6789abcdef0"
        service.repo.find_by_email.return_value = user

        with pytest.raises(HTTPException) as exc:
            await service.login("test@example.com", "WrongPassword")

        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_login_user_not_found(self):
        from app.services.auth_service import AuthService
        from fastapi import HTTPException

        db = make_db()
        service = AuthService(db)
        service.repo = AsyncMock()
        service.repo.find_by_email.return_value = None

        with pytest.raises(HTTPException) as exc:
            await service.login("nobody@example.com", "Password123")

        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_login_inactive_account(self):
        from app.services.auth_service import AuthService
        from app.utils.security import hash_password
        from fastapi import HTTPException

        db = make_db()
        service = AuthService(db)
        service.repo = AsyncMock()

        user = fake_user()
        user["is_active"] = False
        user["hashed_password"] = hash_password("Password123")
        user["_id"] = MagicMock()
        user["_id"].__str__ = lambda self: "64a1b2c3d4e5f6789abcdef0"
        service.repo.find_by_email.return_value = user

        with pytest.raises(HTTPException) as exc:
            await service.login("test@example.com", "Password123")

        assert exc.value.status_code == 403


# ─── JWT / Security Tests ─────────────────────────────────────────────────────

class TestSecurity:

    def test_hash_and_verify_password(self):
        from app.utils.security import hash_password, verify_password

        pwd = "MySecurePass123!"
        hashed = hash_password(pwd)

        assert hashed != pwd
        assert verify_password(pwd, hashed)
        assert not verify_password("WrongPassword", hashed)

    def test_access_token_valid(self):
        from app.utils.security import create_access_token, verify_access_token

        token = create_access_token("user123")
        payload = verify_access_token(token)

        assert payload is not None
        assert payload["sub"] == "user123"
        assert payload["type"] == "access"

    def test_refresh_token_valid(self):
        from app.utils.security import create_refresh_token, verify_refresh_token

        token = create_refresh_token("user123")
        payload = verify_refresh_token(token)

        assert payload is not None
        assert payload["sub"] == "user123"
        assert payload["type"] == "refresh"

    def test_access_token_wrong_type_rejected(self):
        from app.utils.security import create_refresh_token, verify_access_token

        # Refresh token should be rejected by access token verifier
        token = create_refresh_token("user123")
        payload = verify_access_token(token)

        assert payload is None

    def test_invalid_token_rejected(self):
        from app.utils.security import verify_access_token

        payload = verify_access_token("this.is.not.a.real.token")
        assert payload is None

    def test_tampered_token_rejected(self):
        from app.utils.security import create_access_token, verify_access_token

        token = create_access_token("user123")
        tampered = token[:-5] + "XXXXX"
        payload = verify_access_token(tampered)

        assert payload is None


# ─── Refresh Token Tests ──────────────────────────────────────────────────────

class TestRefreshToken:

    @pytest.mark.asyncio
    async def test_refresh_valid_token(self):
        from app.services.auth_service import AuthService
        from app.utils.security import create_refresh_token

        db = make_db()
        service = AuthService(db)
        service.repo = AsyncMock()

        token = create_refresh_token("user123")
        service.repo.get_refresh_token.return_value = token

        result = await service.refresh_token(token)

        assert "access_token" in result
        assert result["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_refresh_revoked_token(self):
        from app.services.auth_service import AuthService
        from app.utils.security import create_refresh_token
        from fastapi import HTTPException

        db = make_db()
        service = AuthService(db)
        service.repo = AsyncMock()

        token = create_refresh_token("user123")
        # Stored token is different (already rotated/revoked)
        service.repo.get_refresh_token.return_value = "different_token"

        with pytest.raises(HTTPException) as exc:
            await service.refresh_token(token)

        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_invalid_token(self):
        from app.services.auth_service import AuthService
        from fastapi import HTTPException

        db = make_db()
        service = AuthService(db)
        service.repo = AsyncMock()

        with pytest.raises(HTTPException) as exc:
            await service.refresh_token("invalid.token.here")

        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_logout_invalidates_token(self):
        from app.services.auth_service import AuthService

        db = make_db()
        service = AuthService(db)
        service.repo = AsyncMock()
        service.repo.invalidate_refresh_token.return_value = None

        await service.logout("user123")

        service.repo.invalidate_refresh_token.assert_called_once_with("user123")

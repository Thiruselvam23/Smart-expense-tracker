from datetime import datetime
from bson import ObjectId
from app.repositories.base import BaseRepository, serialize_doc


class UserRepository(BaseRepository):
    def __init__(self, db):
        super().__init__(db, "users")

    async def create(self, email: str, hashed_password: str, full_name: str) -> dict:
        doc = {
            "email": email,
            "hashed_password": hashed_password,
            "full_name": full_name,
            "is_active": True,
            "preferences": {"currency": "INR", "default_view": "monthly"},
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        result = await self.collection.insert_one(doc)
        doc["_id"] = result.inserted_id
        return serialize_doc(doc)

    async def find_by_email(self, email: str) -> dict:
        doc = await self.collection.find_one({"email": email})
        return doc  # Return raw (includes hashed_password for auth check)

    async def find_by_id_raw(self, user_id: str) -> dict:
        doc = await self.collection.find_one({"_id": ObjectId(user_id)})
        return doc

    async def save_refresh_token(self, user_id: str, token: str, expires_at: datetime):
        await self.collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"refresh_token": token, "refresh_token_expires": expires_at}},
        )

    async def invalidate_refresh_token(self, user_id: str):
        await self.collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$unset": {"refresh_token": "", "refresh_token_expires": ""}},
        )

    async def get_refresh_token(self, user_id: str) -> str:
        doc = await self.collection.find_one(
            {"_id": ObjectId(user_id)}, {"refresh_token": 1}
        )
        return doc.get("refresh_token") if doc else None

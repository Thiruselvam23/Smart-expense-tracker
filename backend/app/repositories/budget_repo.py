from datetime import datetime
from bson import ObjectId
from typing import Optional, List
from app.repositories.base import BaseRepository, serialize_doc


class BudgetRepository(BaseRepository):
    def __init__(self, db):
        super().__init__(db, "budgets")

    async def upsert(self, user_id: str, data: dict) -> dict:
        """Create or update budget for a given month/year."""
        now = datetime.utcnow()
        result = await self.collection.find_one_and_update(
            {
                "user_id": ObjectId(user_id),
                "year": data["year"],
                "month": data["month"],
            },
            {
                "$set": {
                    "total_budget": data["total_budget"],
                    "category_budgets": data["category_budgets"],
                    "updated_at": now,
                },
                "$setOnInsert": {
                    "user_id": ObjectId(user_id),
                    "created_at": now,
                },
            },
            upsert=True,
            return_document=True,
        )
        return serialize_doc(result)

    async def find_by_month(self, user_id: str, year: int, month: int) -> Optional[dict]:
        doc = await self.collection.find_one(
            {"user_id": ObjectId(user_id), "year": year, "month": month}
        )
        return serialize_doc(doc)

    async def find_all_for_user(self, user_id: str) -> List[dict]:
        cursor = self.collection.find({"user_id": ObjectId(user_id)}).sort(
            [("year", -1), ("month", -1)]
        )
        docs = await cursor.to_list(length=None)
        return [serialize_doc(d) for d in docs]

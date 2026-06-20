from datetime import datetime, date
from bson import ObjectId
from typing import Optional
from app.repositories.base import BaseRepository, serialize_doc


class ExpenseRepository(BaseRepository):
    def __init__(self, db):
        super().__init__(db, "expenses")

    async def create(self, user_id: str, data: dict) -> dict:
        data["user_id"] = ObjectId(user_id)
        data["created_at"] = datetime.utcnow()
        data["updated_at"] = datetime.utcnow()
        # Convert date to datetime for MongoDB storage
        if isinstance(data.get("date"), date):
            data["date"] = datetime.combine(data["date"], datetime.min.time())
        result = await self.collection.insert_one(data)
        return await self.find_by_id(str(result.inserted_id), user_id)

    async def update(self, expense_id: str, user_id: str, data: dict) -> Optional[dict]:
        data["updated_at"] = datetime.utcnow()
        if isinstance(data.get("date"), date):
            data["date"] = datetime.combine(data["date"], datetime.min.time())
        result = await self.collection.find_one_and_update(
            {"_id": ObjectId(expense_id), "user_id": ObjectId(user_id)},
            {"$set": data},
            return_document=True,
        )
        return serialize_doc(result)

    def _build_filter_query(self, user_id: str, filters: dict) -> dict:
        query = {"user_id": ObjectId(user_id)}

        if filters.get("category"):
            query["category"] = filters["category"]

        date_filter = {}
        if filters.get("start_date"):
            d = filters["start_date"]
            date_filter["$gte"] = datetime.combine(d, datetime.min.time())
        if filters.get("end_date"):
            d = filters["end_date"]
            date_filter["$lte"] = datetime.combine(d, datetime.max.time())
        if date_filter:
            query["date"] = date_filter

        amount_filter = {}
        if filters.get("min_amount") is not None:
            amount_filter["$gte"] = filters["min_amount"]
        if filters.get("max_amount") is not None:
            amount_filter["$lte"] = filters["max_amount"]
        if amount_filter:
            query["amount"] = amount_filter

        if filters.get("search"):
            query["$text"] = {"$search": filters["search"]}

        return query

    async def find_filtered(self, user_id: str, filters: dict) -> dict:
        query = self._build_filter_query(user_id, filters)
        sort_field = filters.get("sort_by", "date")
        sort_order = -1 if filters.get("order", "desc") == "desc" else 1
        page = filters.get("page", 1)
        limit = filters.get("limit", 20)
        return await self.find_paginated(query, page, limit, sort_field, sort_order)

    async def aggregate_by_category(self, user_id: str, start_date: datetime, end_date: datetime) -> list:
        pipeline = [
            {"$match": {"user_id": ObjectId(user_id), "date": {"$gte": start_date, "$lte": end_date}}},
            {"$group": {"_id": "$category", "total": {"$sum": "$amount"}, "count": {"$sum": 1}}},
            {"$sort": {"total": -1}},
            {"$project": {"category": "$_id", "total": 1, "count": 1, "_id": 0}},
        ]
        cursor = self.collection.aggregate(pipeline)
        return await cursor.to_list(length=None)

    async def aggregate_monthly_trend(self, user_id: str, months: int = 6) -> list:
        from dateutil.relativedelta import relativedelta
        start = datetime.utcnow() - relativedelta(months=months - 1)
        start = start.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        pipeline = [
            {"$match": {"user_id": ObjectId(user_id), "date": {"$gte": start}}},
            {"$group": {
                "_id": {"year": {"$year": "$date"}, "month": {"$month": "$date"}},
                "total": {"$sum": "$amount"},
                "count": {"$sum": 1},
            }},
            {"$sort": {"_id.year": 1, "_id.month": 1}},
            {"$project": {"year": "$_id.year", "month": "$_id.month", "total": 1, "count": 1, "_id": 0}},
        ]
        cursor = self.collection.aggregate(pipeline)
        return await cursor.to_list(length=None)

    async def get_total_for_period(self, user_id: str, start_date: datetime, end_date: datetime) -> float:
        pipeline = [
            {"$match": {"user_id": ObjectId(user_id), "date": {"$gte": start_date, "$lte": end_date}}},
            {"$group": {"_id": None, "total": {"$sum": "$amount"}}},
        ]
        cursor = self.collection.aggregate(pipeline)
        results = await cursor.to_list(length=1)
        return results[0]["total"] if results else 0.0

    async def count_for_period(self, user_id: str, start_date: datetime, end_date: datetime) -> int:
        return await self.collection.count_documents(
            {"user_id": ObjectId(user_id), "date": {"$gte": start_date, "$lte": end_date}}
        )

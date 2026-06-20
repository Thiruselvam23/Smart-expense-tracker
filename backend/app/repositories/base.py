from bson import ObjectId
from datetime import datetime
from typing import Optional
import math


def serialize_doc(doc: dict) -> dict:
    """Convert MongoDB document to JSON-serializable dict."""
    if doc is None:
        return None
    doc = dict(doc)
    if "_id" in doc:
        doc["id"] = str(doc.pop("_id"))
    if "user_id" in doc:
        doc["user_id"] = str(doc["user_id"])
    return doc


class BaseRepository:
    def __init__(self, db, collection_name: str):
        self.collection = db[collection_name]

    async def find_by_id(self, doc_id: str, user_id: str = None) -> Optional[dict]:
        query = {"_id": ObjectId(doc_id)}
        if user_id:
            query["user_id"] = ObjectId(user_id)
        doc = await self.collection.find_one(query)
        return serialize_doc(doc)

    async def delete_by_id(self, doc_id: str, user_id: str) -> bool:
        result = await self.collection.delete_one(
            {"_id": ObjectId(doc_id), "user_id": ObjectId(user_id)}
        )
        return result.deleted_count > 0

    async def find_paginated(self, query: dict, page: int, limit: int, sort_field: str = "date", sort_order: int = -1):
        skip = (page - 1) * limit
        cursor = self.collection.find(query).sort(sort_field, sort_order).skip(skip).limit(limit)
        items = await cursor.to_list(length=limit)
        total = await self.collection.count_documents(query)
        return {
            "items": [serialize_doc(doc) for doc in items],
            "total": total,
            "page": page,
            "limit": limit,
            "pages": math.ceil(total / limit) if total else 0,
        }

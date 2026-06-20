from fastapi import APIRouter, Depends, Query
from datetime import datetime
from bson import ObjectId
from app.services.insight_service import InsightService
from app.dependencies import get_current_user
from app.database import get_db

router = APIRouter()


@router.get("")
async def get_insights(
    month: int = Query(None, ge=1, le=12),
    year:  int = Query(None, ge=2000, le=2100),
    force: bool = Query(False),
    current_user=Depends(get_current_user),
    db=Depends(get_db),
):
    now   = datetime.utcnow()
    month = month or now.month
    year  = year  or now.year

    # force=True → delete stale MongoDB cache so Gemini is called fresh
    if force:
        await db.insights_cache.delete_one({
            "user_id": ObjectId(current_user["id"]),
            "month":   month,
            "year":    year,
        })

    service = InsightService(db)
    return await service.get_insights(current_user["id"], month, year)

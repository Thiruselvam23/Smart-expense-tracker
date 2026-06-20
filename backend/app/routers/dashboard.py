from fastapi import APIRouter, Depends, Query
from typing import Optional
from app.services.analytics_service import AnalyticsService
from app.dependencies import get_current_user
from app.database import get_db

router = APIRouter()


@router.get("/summary")
async def dashboard_summary(current_user=Depends(get_current_user), db=Depends(get_db)):
    service = AnalyticsService(db)
    return await service.get_dashboard_summary(current_user["id"])


@router.get("/by-category")
async def category_breakdown(
    year: Optional[int] = None,
    month: Optional[int] = None,
    current_user=Depends(get_current_user),
    db=Depends(get_db),
):
    service = AnalyticsService(db)
    return await service.get_category_breakdown(current_user["id"], year, month)


@router.get("/monthly-trend")
async def monthly_trend(
    months: int = Query(6, ge=1, le=12),
    current_user=Depends(get_current_user),
    db=Depends(get_db),
):
    service = AnalyticsService(db)
    return await service.get_monthly_trend(current_user["id"], months)

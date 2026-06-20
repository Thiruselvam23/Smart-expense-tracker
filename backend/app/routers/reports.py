from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from datetime import datetime
import calendar

from app.dependencies import get_current_user
from app.database import get_db
from app.repositories.expense_repo import ExpenseRepository
from app.services.analytics_service import AnalyticsService
from app.utils.pdf_generator import generate_monthly_pdf
from app.utils.excel_generator import generate_monthly_excel

router = APIRouter()


async def _get_report_data(user_id: str, month: int, year: int, db):
    """Shared helper: fetch expenses + summary for a given month."""
    expense_repo = ExpenseRepository(db)
    analytics = AnalyticsService(db)

    start = datetime(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    end = datetime(year, month, last_day, 23, 59, 59)

    # Fetch all expenses for the month (no pagination)
    result = await expense_repo.find_paginated(
        query={"user_id": __import__("bson").ObjectId(user_id), "date": {"$gte": start, "$lte": end}},
        page=1,
        limit=1000,
        sort_field="date",
        sort_order=1,
    )
    expenses = result["items"]

    summary = await analytics.get_dashboard_summary(user_id)
    return expenses, summary


@router.get("/pdf")
async def download_pdf(
    month: int = Query(None, ge=1, le=12),
    year: int = Query(None, ge=2000, le=2100),
    current_user=Depends(get_current_user),
    db=Depends(get_db),
):
    now = datetime.utcnow()
    month = month or now.month
    year = year or now.year

    expenses, summary = await _get_report_data(current_user["id"], month, year, db)

    pdf_bytes = generate_monthly_pdf(
        user=current_user,
        expenses=expenses,
        summary=summary,
        month=month,
        year=year,
    )

    filename = f"expense_report_{calendar.month_abbr[month]}_{year}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/excel")
async def download_excel(
    month: int = Query(None, ge=1, le=12),
    year: int = Query(None, ge=2000, le=2100),
    current_user=Depends(get_current_user),
    db=Depends(get_db),
):
    now = datetime.utcnow()
    month = month or now.month
    year = year or now.year

    expenses, summary = await _get_report_data(current_user["id"], month, year, db)

    excel_bytes = generate_monthly_excel(
        user=current_user,
        expenses=expenses,
        summary=summary,
        month=month,
        year=year,
    )

    filename = f"expense_report_{calendar.month_abbr[month]}_{year}.xlsx"
    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

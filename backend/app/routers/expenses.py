from fastapi import APIRouter, Depends, Query
from typing import Optional
from datetime import date
from app.models.expense import ExpenseCreate, ExpenseUpdate, ExpenseFilters, Category
from app.services.expense_service import ExpenseService
from app.dependencies import get_current_user
from app.database import get_db

router = APIRouter()


@router.get("")
async def list_expenses(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    category: Optional[Category] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None,
    search: Optional[str] = None,
    sort_by: Optional[str] = "date",
    order: Optional[str] = "desc",
    current_user=Depends(get_current_user),
    db=Depends(get_db),
):
    filters = ExpenseFilters(
        page=page, limit=limit, category=category,
        start_date=start_date, end_date=end_date,
        min_amount=min_amount, max_amount=max_amount,
        search=search, sort_by=sort_by, order=order,
    )
    service = ExpenseService(db)
    return await service.get_all(current_user["id"], filters)


@router.post("", status_code=201)
async def create_expense(
    data: ExpenseCreate,
    current_user=Depends(get_current_user),
    db=Depends(get_db),
):
    service = ExpenseService(db)
    return await service.create(current_user["id"], data)


@router.get("/{expense_id}")
async def get_expense(
    expense_id: str,
    current_user=Depends(get_current_user),
    db=Depends(get_db),
):
    service = ExpenseService(db)
    return await service.get_one(current_user["id"], expense_id)


@router.put("/{expense_id}")
async def update_expense(
    expense_id: str,
    data: ExpenseUpdate,
    current_user=Depends(get_current_user),
    db=Depends(get_db),
):
    service = ExpenseService(db)
    return await service.update(current_user["id"], expense_id, data)


@router.delete("/{expense_id}")
async def delete_expense(
    expense_id: str,
    current_user=Depends(get_current_user),
    db=Depends(get_db),
):
    service = ExpenseService(db)
    await service.delete(current_user["id"], expense_id)
    return {"message": "Expense deleted"}

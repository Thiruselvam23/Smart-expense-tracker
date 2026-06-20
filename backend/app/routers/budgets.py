from fastapi import APIRouter, Depends
from app.models.budget import BudgetCreate
from app.services.budget_service import BudgetService
from app.dependencies import get_current_user
from app.database import get_db

router = APIRouter()


@router.get("")
async def list_budgets(current_user=Depends(get_current_user), db=Depends(get_db)):
    service = BudgetService(db)
    return await service.get_all(current_user["id"])


@router.post("", status_code=201)
async def upsert_budget(data: BudgetCreate, current_user=Depends(get_current_user), db=Depends(get_db)):
    service = BudgetService(db)
    return await service.upsert(current_user["id"], data.model_dump())


@router.get("/current")
async def current_budget(current_user=Depends(get_current_user), db=Depends(get_db)):
    service = BudgetService(db)
    return await service.get_current_vs_actual(current_user["id"])


@router.get("/{year}/{month}")
async def budget_by_month(year: int, month: int, current_user=Depends(get_current_user), db=Depends(get_db)):
    service = BudgetService(db)
    return await service.get_vs_actual(current_user["id"], year, month)


@router.delete("/{budget_id}")
async def delete_budget(budget_id: str, current_user=Depends(get_current_user), db=Depends(get_db)):
    service = BudgetService(db)
    await service.delete(current_user["id"], budget_id)
    return {"message": "Budget deleted"}

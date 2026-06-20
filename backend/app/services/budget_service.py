from datetime import datetime
from fastapi import HTTPException
from app.repositories.budget_repo import BudgetRepository
from app.repositories.expense_repo import ExpenseRepository
from app.models.expense import Category

CATEGORIES = [c.value for c in Category]


class BudgetService:
    def __init__(self, db):
        self.budget_repo = BudgetRepository(db)
        self.expense_repo = ExpenseRepository(db)

    async def upsert(self, user_id: str, data: dict) -> dict:
        return await self.budget_repo.upsert(user_id, data)

    async def get_all(self, user_id: str) -> list:
        return await self.budget_repo.find_all_for_user(user_id)

    async def get_by_month(self, user_id: str, year: int, month: int) -> dict:
        budget = await self.budget_repo.find_by_month(user_id, year, month)
        if not budget:
            raise HTTPException(status_code=404, detail="Budget not found for this month")
        return budget

    async def get_current_vs_actual(self, user_id: str) -> dict:
        now = datetime.utcnow()
        return await self._compute_vs_actual(user_id, now.year, now.month)

    async def get_vs_actual(self, user_id: str, year: int, month: int) -> dict:
        return await self._compute_vs_actual(user_id, year, month)

    async def _compute_vs_actual(self, user_id: str, year: int, month: int) -> dict:
        budget = await self.budget_repo.find_by_month(user_id, year, month)

        start = datetime(year, month, 1)
        if month == 12:
            end = datetime(year + 1, 1, 1)
        else:
            end = datetime(year, month + 1, 1)

        category_data = await self.expense_repo.aggregate_by_category(user_id, start, end)
        actual_by_cat = {row["category"]: row["total"] for row in category_data}
        total_spent = sum(actual_by_cat.values())

        cat_budgets = {}
        if budget:
            cat_budgets = budget.get("category_budgets", {})

        variance = {}
        for cat in CATEGORIES:
            b = cat_budgets.get(cat, 0)
            a = actual_by_cat.get(cat, 0)
            variance[cat] = round(b - a, 2)

        total_budget = budget["total_budget"] if budget else 0
        pct = round((total_spent / total_budget * 100), 1) if total_budget > 0 else 0

        return {
            "budget": budget,
            "actual": actual_by_cat,
            "total_spent": round(total_spent, 2),
            "variance": variance,
            "total_variance": round(total_budget - total_spent, 2),
            "percentage_used": pct,
        }

    async def delete(self, user_id: str, budget_id: str) -> bool:
        deleted = await self.budget_repo.delete_by_id(budget_id, user_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Budget not found")
        return True

from fastapi import HTTPException
from app.repositories.expense_repo import ExpenseRepository
from app.models.expense import ExpenseCreate, ExpenseUpdate, ExpenseFilters


class ExpenseService:
    def __init__(self, db):
        self.repo = ExpenseRepository(db)

    async def create(self, user_id: str, data: ExpenseCreate) -> dict:
        payload = data.model_dump()
        return await self.repo.create(user_id, payload)

    async def get_all(self, user_id: str, filters: ExpenseFilters) -> dict:
        return await self.repo.find_filtered(user_id, filters.model_dump())

    async def get_one(self, user_id: str, expense_id: str) -> dict:
        expense = await self.repo.find_by_id(expense_id, user_id)
        if not expense:
            raise HTTPException(status_code=404, detail="Expense not found")
        return expense

    async def update(self, user_id: str, expense_id: str, data: ExpenseUpdate) -> dict:
        payload = {k: v for k, v in data.model_dump().items() if v is not None}
        updated = await self.repo.update(expense_id, user_id, payload)
        if not updated:
            raise HTTPException(status_code=404, detail="Expense not found")
        return updated

    async def delete(self, user_id: str, expense_id: str) -> bool:
        deleted = await self.repo.delete_by_id(expense_id, user_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Expense not found")
        return True

from pydantic import BaseModel, field_validator
from typing import Optional, Dict
from datetime import datetime


CATEGORIES = ["Food", "Travel", "Shopping", "Entertainment", "Healthcare", "Utilities", "Education", "Other"]


class CategoryBudgets(BaseModel):
    Food: float = 0
    Travel: float = 0
    Shopping: float = 0
    Entertainment: float = 0
    Healthcare: float = 0
    Utilities: float = 0
    Education: float = 0
    Other: float = 0


class BudgetCreate(BaseModel):
    month: int
    year: int
    total_budget: float
    category_budgets: CategoryBudgets

    @field_validator("month")
    @classmethod
    def valid_month(cls, v):
        if not 1 <= v <= 12:
            raise ValueError("Month must be between 1 and 12")
        return v

    @field_validator("year")
    @classmethod
    def valid_year(cls, v):
        if not 2000 <= v <= 2100:
            raise ValueError("Invalid year")
        return v

    @field_validator("total_budget")
    @classmethod
    def budget_positive(cls, v):
        if v <= 0:
            raise ValueError("Budget must be greater than 0")
        return round(v, 2)


class BudgetOut(BaseModel):
    id: str
    month: int
    year: int
    total_budget: float
    category_budgets: dict
    created_at: datetime
    updated_at: Optional[datetime] = None


class BudgetVsActual(BaseModel):
    budget: Optional[BudgetOut]
    actual: Dict[str, float]
    total_spent: float
    variance: Dict[str, float]
    total_variance: float
    percentage_used: float

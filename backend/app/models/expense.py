from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import date, datetime
from enum import Enum


class Category(str, Enum):
    FOOD = "Food"
    TRAVEL = "Travel"
    SHOPPING = "Shopping"
    ENTERTAINMENT = "Entertainment"
    HEALTHCARE = "Healthcare"
    UTILITIES = "Utilities"
    EDUCATION = "Education"
    OTHER = "Other"


class PaymentMethod(str, Enum):
    CASH = "Cash"
    UPI = "UPI"
    CARD = "Card"
    NET_BANKING = "NetBanking"
    OTHER = "Other"


class ExpenseSource(str, Enum):
    MANUAL = "manual"
    OCR = "ocr"


class ExpenseCreate(BaseModel):
    title: str
    amount: float
    category: Category
    date: date
    description: Optional[str] = None
    payment_method: Optional[PaymentMethod] = PaymentMethod.CASH
    tags: Optional[List[str]] = []
    source: Optional[ExpenseSource] = ExpenseSource.MANUAL
    receipt_image_url: Optional[str] = None

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v):
        if v <= 0:
            raise ValueError("Amount must be greater than 0")
        return round(v, 2)

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v):
        if not v.strip():
            raise ValueError("Title cannot be empty")
        return v.strip()


class ExpenseUpdate(BaseModel):
    title: Optional[str] = None
    amount: Optional[float] = None
    category: Optional[Category] = None
    date: Optional[date] = None
    description: Optional[str] = None
    payment_method: Optional[PaymentMethod] = None
    tags: Optional[List[str]] = None

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v):
        if v is not None and v <= 0:
            raise ValueError("Amount must be greater than 0")
        return round(v, 2) if v else v


class ExpenseOut(BaseModel):
    id: str
    title: str
    amount: float
    category: str
    date: date
    description: Optional[str] = None
    payment_method: Optional[str] = None
    tags: List[str] = []
    source: str
    receipt_image_url: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class ExpenseFilters(BaseModel):
    page: int = 1
    limit: int = 20
    category: Optional[Category] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    search: Optional[str] = None
    sort_by: Optional[str] = "date"
    order: Optional[str] = "desc"


class PaginatedExpenses(BaseModel):
    items: List[ExpenseOut]
    total: int
    page: int
    limit: int
    pages: int

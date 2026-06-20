import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import date, datetime


USER_ID = "64a1b2c3d4e5f6789abcdef0"


def fake_expense(expense_id="64b1c2d3e4f5a6789abcdef1"):
    return {
        "id": expense_id,
        "user_id": USER_ID,
        "title": "Swiggy Dinner",
        "amount": 320.50,
        "category": "Food",
        "date": datetime(2025, 6, 10),
        "description": "Biryani order",
        "payment_method": "UPI",
        "tags": ["delivery"],
        "source": "manual",
        "receipt_image_url": None,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }


def make_expense_create():
    from app.models.expense import ExpenseCreate, Category, PaymentMethod
    return ExpenseCreate(
        title="Swiggy Dinner",
        amount=320.50,
        category=Category.FOOD,
        date=date(2025, 6, 10),
        description="Biryani order",
        payment_method=PaymentMethod.UPI,
        tags=["delivery"],
    )


# ─── Create Tests ─────────────────────────────────────────────────────────────

class TestCreateExpense:

    @pytest.mark.asyncio
    async def test_create_expense_success(self):
        from app.services.expense_service import ExpenseService

        db = MagicMock()
        service = ExpenseService(db)
        service.repo = AsyncMock()
        service.repo.create.return_value = fake_expense()

        data = make_expense_create()
        result = await service.create(USER_ID, data)

        assert result["title"] == "Swiggy Dinner"
        assert result["amount"] == 320.50
        assert result["category"] == "Food"
        service.repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_passes_user_id(self):
        from app.services.expense_service import ExpenseService

        db = MagicMock()
        service = ExpenseService(db)
        service.repo = AsyncMock()
        service.repo.create.return_value = fake_expense()

        data = make_expense_create()
        await service.create(USER_ID, data)

        call_args = service.repo.create.call_args
        assert call_args[0][0] == USER_ID


# ─── Read Tests ───────────────────────────────────────────────────────────────

class TestGetExpense:

    @pytest.mark.asyncio
    async def test_get_one_found(self):
        from app.services.expense_service import ExpenseService

        db = MagicMock()
        service = ExpenseService(db)
        service.repo = AsyncMock()
        service.repo.find_by_id.return_value = fake_expense()

        result = await service.get_one(USER_ID, "64b1c2d3e4f5a6789abcdef1")

        assert result["id"] == "64b1c2d3e4f5a6789abcdef1"

    @pytest.mark.asyncio
    async def test_get_one_not_found(self):
        from app.services.expense_service import ExpenseService
        from fastapi import HTTPException

        db = MagicMock()
        service = ExpenseService(db)
        service.repo = AsyncMock()
        service.repo.find_by_id.return_value = None

        with pytest.raises(HTTPException) as exc:
            await service.get_one(USER_ID, "nonexistent_id")

        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_get_all_returns_paginated(self):
        from app.services.expense_service import ExpenseService
        from app.models.expense import ExpenseFilters

        db = MagicMock()
        service = ExpenseService(db)
        service.repo = AsyncMock()
        service.repo.find_filtered.return_value = {
            "items": [fake_expense()],
            "total": 1,
            "page": 1,
            "limit": 20,
            "pages": 1,
        }

        filters = ExpenseFilters()
        result = await service.get_all(USER_ID, filters)

        assert result["total"] == 1
        assert len(result["items"]) == 1


# ─── Update Tests ─────────────────────────────────────────────────────────────

class TestUpdateExpense:

    @pytest.mark.asyncio
    async def test_update_success(self):
        from app.services.expense_service import ExpenseService
        from app.models.expense import ExpenseUpdate

        db = MagicMock()
        service = ExpenseService(db)
        service.repo = AsyncMock()
        updated = fake_expense()
        updated["title"] = "Updated Title"
        service.repo.update.return_value = updated

        data = ExpenseUpdate(title="Updated Title")
        result = await service.update(USER_ID, "64b1c2d3e4f5a6789abcdef1", data)

        assert result["title"] == "Updated Title"

    @pytest.mark.asyncio
    async def test_update_not_found(self):
        from app.services.expense_service import ExpenseService
        from app.models.expense import ExpenseUpdate
        from fastapi import HTTPException

        db = MagicMock()
        service = ExpenseService(db)
        service.repo = AsyncMock()
        service.repo.update.return_value = None

        data = ExpenseUpdate(title="New Title")
        with pytest.raises(HTTPException) as exc:
            await service.update(USER_ID, "nonexistent", data)

        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_update_strips_none_fields(self):
        from app.services.expense_service import ExpenseService
        from app.models.expense import ExpenseUpdate

        db = MagicMock()
        service = ExpenseService(db)
        service.repo = AsyncMock()
        service.repo.update.return_value = fake_expense()

        # Only title is set, rest are None
        data = ExpenseUpdate(title="Only Title Updated")
        await service.update(USER_ID, "64b1c2d3e4f5a6789abcdef1", data)

        call_kwargs = service.repo.update.call_args[0][2]
        assert "title" in call_kwargs
        assert "amount" not in call_kwargs  # None fields stripped


# ─── Delete Tests ─────────────────────────────────────────────────────────────

class TestDeleteExpense:

    @pytest.mark.asyncio
    async def test_delete_success(self):
        from app.services.expense_service import ExpenseService

        db = MagicMock()
        service = ExpenseService(db)
        service.repo = AsyncMock()
        service.repo.delete_by_id.return_value = True

        result = await service.delete(USER_ID, "64b1c2d3e4f5a6789abcdef1")

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_not_found(self):
        from app.services.expense_service import ExpenseService
        from fastapi import HTTPException

        db = MagicMock()
        service = ExpenseService(db)
        service.repo = AsyncMock()
        service.repo.delete_by_id.return_value = False

        with pytest.raises(HTTPException) as exc:
            await service.delete(USER_ID, "nonexistent")

        assert exc.value.status_code == 404


# ─── Validation Tests (Pydantic model level) ──────────────────────────────────

class TestExpenseValidation:

    def test_negative_amount_rejected(self):
        from app.models.expense import ExpenseCreate, Category
        import pydantic

        with pytest.raises(pydantic.ValidationError):
            ExpenseCreate(
                title="Test",
                amount=-100,
                category=Category.FOOD,
                date=date.today(),
            )

    def test_zero_amount_rejected(self):
        from app.models.expense import ExpenseCreate, Category
        import pydantic

        with pytest.raises(pydantic.ValidationError):
            ExpenseCreate(
                title="Test",
                amount=0,
                category=Category.FOOD,
                date=date.today(),
            )

    def test_empty_title_rejected(self):
        from app.models.expense import ExpenseCreate, Category
        import pydantic

        with pytest.raises(pydantic.ValidationError):
            ExpenseCreate(
                title="   ",
                amount=100,
                category=Category.FOOD,
                date=date.today(),
            )

    def test_invalid_category_rejected(self):
        from app.models.expense import ExpenseCreate
        import pydantic

        with pytest.raises(pydantic.ValidationError):
            ExpenseCreate(
                title="Test",
                amount=100,
                category="InvalidCategory",
                date=date.today(),
            )

    def test_valid_expense_passes(self):
        from app.models.expense import ExpenseCreate, Category

        exp = ExpenseCreate(
            title="Coffee",
            amount=150.00,
            category=Category.FOOD,
            date=date.today(),
        )
        assert exp.amount == 150.00
        assert exp.title == "Coffee"

    def test_amount_rounded_to_2_decimals(self):
        from app.models.expense import ExpenseCreate, Category

        exp = ExpenseCreate(
            title="Test",
            amount=199.999,
            category=Category.FOOD,
            date=date.today(),
        )
        assert exp.amount == 200.00

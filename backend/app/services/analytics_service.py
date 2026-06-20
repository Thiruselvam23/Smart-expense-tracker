from datetime import datetime
import calendar
from app.repositories.expense_repo import ExpenseRepository
from app.repositories.budget_repo import BudgetRepository


class AnalyticsService:
    def __init__(self, db):
        self.expense_repo = ExpenseRepository(db)
        self.budget_repo = BudgetRepository(db)

    def _month_range(self, year: int, month: int):
        start = datetime(year, month, 1)
        last_day = calendar.monthrange(year, month)[1]
        end = datetime(year, month, last_day, 23, 59, 59)
        return start, end

    async def get_dashboard_summary(self, user_id: str) -> dict:
        now = datetime.utcnow()
        year, month = now.year, now.month
        start, end = self._month_range(year, month)

        # Previous month
        if month == 1:
            prev_year, prev_month = year - 1, 12
        else:
            prev_year, prev_month = year, month - 1
        prev_start, prev_end = self._month_range(prev_year, prev_month)

        total = await self.expense_repo.get_total_for_period(user_id, start, end)
        count = await self.expense_repo.count_for_period(user_id, start, end)
        prev_total = await self.expense_repo.get_total_for_period(user_id, prev_start, prev_end)
        budget = await self.budget_repo.find_by_month(user_id, year, month)

        days_elapsed = now.day
        avg_per_day = round(total / days_elapsed, 2) if days_elapsed > 0 else 0

        mom_change = 0
        if prev_total > 0:
            mom_change = round(((total - prev_total) / prev_total) * 100, 1)

        total_budget = budget["total_budget"] if budget else 0
        budget_pct = round((total / total_budget * 100), 1) if total_budget > 0 else 0

        return {
            "total_spent": round(total, 2),
            "transaction_count": count,
            "avg_per_day": avg_per_day,
            "mom_change_pct": mom_change,
            "total_budget": total_budget,
            "budget_remaining": round(total_budget - total, 2),
            "budget_used_pct": budget_pct,
            "month": month,
            "year": year,
        }

    async def get_category_breakdown(self, user_id: str, year: int = None, month: int = None) -> list:
        now = datetime.utcnow()
        year = year or now.year
        month = month or now.month
        start, end = self._month_range(year, month)
        return await self.expense_repo.aggregate_by_category(user_id, start, end)

    async def get_monthly_trend(self, user_id: str, months: int = 6) -> list:
        raw = await self.expense_repo.aggregate_monthly_trend(user_id, months)
        # Fill in missing months with 0
        now = datetime.utcnow()
        result = []
        for i in range(months - 1, -1, -1):
            if now.month - i <= 0:
                m = now.month - i + 12
                y = now.year - 1
            else:
                m = now.month - i
                y = now.year
            found = next((r for r in raw if r["year"] == y and r["month"] == m), None)
            result.append({
                "year": y,
                "month": m,
                "month_name": calendar.month_abbr[m],
                "total": found["total"] if found else 0,
                "count": found["count"] if found else 0,
            })
        return result

    async def compute_monthly_stats(self, user_id: str, month: int, year: int) -> dict:
        """Compute full stats for AI insight generation."""
        start, end = self._month_range(year, month)

        # Previous month
        pm = month - 1 if month > 1 else 12
        py = year if month > 1 else year - 1
        prev_start, prev_end = self._month_range(py, pm)

        total = await self.expense_repo.get_total_for_period(user_id, start, end)
        prev_total = await self.expense_repo.get_total_for_period(user_id, prev_start, prev_end)
        count = await self.expense_repo.count_for_period(user_id, start, end)
        category_data = await self.expense_repo.aggregate_by_category(user_id, start, end)
        budget = await self.budget_repo.find_by_month(user_id, year, month)
        trend = await self.get_monthly_trend(user_id, 3)

        mom_change = 0
        if prev_total > 0:
            mom_change = round(((total - prev_total) / prev_total) * 100, 1)

        days = calendar.monthrange(year, month)[1]
        avg_daily = round(total / days, 2)

        cat_budgets = budget.get("category_budgets", {}) if budget else {}
        over_budget = []
        for cat in category_data:
            b = cat_budgets.get(cat["category"], 0)
            if b > 0 and cat["total"] > b:
                over_budget.append({
                    "category": cat["category"],
                    "spent": cat["total"],
                    "budget": b,
                    "over_by": round(cat["total"] - b, 2),
                })

        return {
            "month": month,
            "year": year,
            "month_name": calendar.month_name[month],
            "total_spent": round(total, 2),
            "prev_total": round(prev_total, 2),
            "mom_change_pct": mom_change,
            "transaction_count": count,
            "avg_daily_spend": avg_daily,
            "total_budget": budget["total_budget"] if budget else 0,
            "category_breakdown": category_data[:5],
            "over_budget_categories": over_budget,
            "three_month_trend": trend,
        }

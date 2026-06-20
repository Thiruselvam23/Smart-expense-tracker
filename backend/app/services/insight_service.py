import re
import logging
from datetime import datetime, timedelta
from bson import ObjectId

from app.services.analytics_service import AnalyticsService
from app.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a helpful personal finance advisor.
Analyze the spending data and provide exactly 4-5 clear, actionable recommendations in plain language.
Be specific with numbers. Be encouraging but honest about overspending.
Format as a numbered list. Each recommendation must be 1-2 sentences maximum.
Do not add any intro or outro — just the numbered list."""


def build_prompt(stats: dict) -> str:
    cats = "\n".join(
        [f"  • {c['category']}: ₹{c['total']:,.0f}" for c in stats["category_breakdown"]]
    )
    over = ""
    if stats["over_budget_categories"]:
        over = "\nOver-budget categories:\n" + "\n".join(
            [f"  • {o['category']}: spent ₹{o['spent']:,.0f} vs budget ₹{o['budget']:,.0f} "
             f"(over by ₹{o['over_by']:,.0f})"
             for o in stats["over_budget_categories"]]
        )
    trend = " → ".join(
        [f"{t['month_name']} ₹{t['total']:,.0f}" for t in stats["three_month_trend"]]
    )
    direction = "up" if stats["mom_change_pct"] > 0 else "down"

    return f"""{SYSTEM_PROMPT}

Expense summary for {stats['month_name']} {stats['year']}:

- Total spending: ₹{stats['total_spent']:,.0f} ({direction} {abs(stats['mom_change_pct'])}% from last month's ₹{stats['prev_total']:,.0f})
- Daily average: ₹{stats['avg_daily_spend']:,.0f}
- Total transactions: {stats['transaction_count']}
- Monthly budget: ₹{stats['total_budget']:,.0f}

Category breakdown:
{cats}
{over}

3-month trend: {trend}

Please provide 4-5 actionable recommendations based on this data."""


def parse_recommendations(text: str) -> list:
    lines = text.strip().split("\n")
    recs = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Strip numbering like "1." or "1)" or "* "
        clean = re.sub(r"^(\d+[.)]\s*|\*\s*|-\s*)", "", line).strip()
        if len(clean) > 10:
            recs.append(clean)
    return recs[:5]


def fallback_recommendations(stats: dict) -> list:
    recs = []
    if stats["mom_change_pct"] > 15:
        recs.append(
            f"Your spending increased by {stats['mom_change_pct']}% this month. "
            f"Review your largest categories for potential cutbacks."
        )
    if stats["over_budget_categories"]:
        cat = stats["over_budget_categories"][0]
        recs.append(
            f"You exceeded your {cat['category']} budget by ₹{cat['over_by']:,.0f}. "
            f"Consider adjusting your budget or reducing spending in this area."
        )
    if stats["total_budget"] > 0 and stats["total_spent"] > stats["total_budget"] * 0.9:
        recs.append(
            "You are close to or over your monthly budget. "
            "Try to limit discretionary spending for the rest of the month."
        )
    if not recs:
        recs.append(
            "Keep tracking your expenses consistently to get better insights next month."
        )
    return recs


async def call_gemini(prompt: str) -> list:
    """Call Google Gemini API and return parsed recommendations."""
    try:
        import google.generativeai as genai

        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel(settings.LLM_MODEL)

        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=600,
                temperature=0.7,
            ),
        )
        text = response.text
        return parse_recommendations(text)

    except ImportError:
        logger.error("google-generativeai package not installed. Run: pip install google-generativeai")
        return None
    except Exception as e:
        logger.error(f"Gemini API call failed: {e}")
        return None


class InsightService:
    def __init__(self, db):
        self.db = db
        self.analytics = AnalyticsService(db)
        self.cache_col = db["insights_cache"]

    async def get_insights(self, user_id: str, month: int, year: int) -> dict:
        # 1. Check cache first
        cached = await self.cache_col.find_one(
            {"user_id": ObjectId(user_id), "month": month, "year": year}
        )
        if cached and cached.get("expires_at", datetime.min) > datetime.utcnow():
            logger.info(f"Returning cached insights for user {user_id} {month}/{year}")
            return {
                "recommendations": cached["recommendations"],
                "statistics": cached["statistics"],
                "cached": True,
                "generated_at": cached["generated_at"],
            }

        # 2. Compute analytics
        stats = await self.analytics.compute_monthly_stats(user_id, month, year)

        # 3. Call Gemini
        prompt = build_prompt(stats)
        recommendations = await call_gemini(prompt)

        # 4. Fallback if Gemini fails
        if not recommendations:
            logger.warning("Gemini failed — using fallback recommendations")
            recommendations = fallback_recommendations(stats)

        # 5. Save to cache (TTL via MongoDB TTL index)
        now = datetime.utcnow()
        expires = now + timedelta(hours=settings.INSIGHT_CACHE_HOURS)
        await self.cache_col.update_one(
            {"user_id": ObjectId(user_id), "month": month, "year": year},
            {
                "$set": {
                    "user_id": ObjectId(user_id),
                    "month": month,
                    "year": year,
                    "statistics": stats,
                    "recommendations": recommendations,
                    "generated_at": now,
                    "expires_at": expires,
                }
            },
            upsert=True,
        )

        return {
            "recommendations": recommendations,
            "statistics": stats,
            "cached": False,
            "generated_at": now,
        }

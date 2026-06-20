from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List
from app.dependencies import get_current_user
from app.config import settings
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

FINANCE_KEYWORDS = [
    'expense', 'budget', 'saving', 'spend', 'money', 'cost', 'finance', 'financial',
    'income', 'salary', 'invest', 'debt', 'loan', 'emi', 'tax', 'insurance',
    'category', 'track', 'monthly', 'bill', 'payment', 'price', 'afford', 'cut',
    'reduce', 'plan', 'goal', 'wealth', 'cash', 'fund', 'rupee', '₹', 'inr',
    'habit', 'tip', 'trick', 'strategy', 'manage', 'analysis', 'report', 'chart'
]

OFF_TOPIC_RESPONSE = (
    "I can't answer this question. I am only allowed to provide information "
    "related to expenses, budgeting, spending analysis, and financial planning."
)

SYSTEM_PROMPT = """You are an Expense Assistant — a focused financial advisor chatbot.
You ONLY answer questions about:
- Personal expense management and tracking
- Budget planning and creation
- Saving strategies and money-saving tips
- Spending analysis and patterns
- Financial habits improvement
- Expense categorization

For ANY question unrelated to these topics, respond EXACTLY:
"I can't answer this question. I am only allowed to provide information related to expenses, budgeting, spending analysis, and financial planning."

Be concise, practical, and helpful. Use ₹ for Indian currency examples."""


class ChatMessage(BaseModel):
    role: str   # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    system: str = SYSTEM_PROMPT


def is_finance_related(text: str) -> bool:
    """Quick keyword check before calling LLM."""
    text_lower = text.lower()
    return any(kw in text_lower for kw in FINANCE_KEYWORDS)


async def call_gemini_chat(messages: List[ChatMessage]) -> str:
    try:
        import google.generativeai as genai
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel(
            settings.LLM_MODEL,
            system_instruction=SYSTEM_PROMPT,
        )

        # Build Gemini-compatible history
        history = []
        for m in messages[:-1]:  # all except last
            history.append({
                'role': 'user' if m.role == 'user' else 'model',
                'parts': [m.content],
            })

        chat = model.start_chat(history=history)
        last_user_msg = messages[-1].content
        response = chat.send_message(
            last_user_msg,
            generation_config={"max_output_tokens": 500, "temperature": 0.7},
        )
        return response.text

    except ImportError:
        raise HTTPException(status_code=500, detail="google-generativeai not installed")
    except Exception as e:
        logger.error(f"Gemini chat error: {e}")
        raise HTTPException(status_code=500, detail="AI service error")


@router.post("")
async def chat(req: ChatRequest, current_user=Depends(get_current_user)):
    if not settings.GEMINI_API_KEY:
        raise HTTPException(status_code=503, detail="AI service not configured")

    # Get last user message for keyword check
    user_messages = [m for m in req.messages if m.role == 'user']
    if not user_messages:
        raise HTTPException(status_code=400, detail="No user message provided")

    last_msg = user_messages[-1].content.strip()

    # Backend guardrail — if clearly off-topic, skip LLM call entirely
    if not is_finance_related(last_msg) and len(last_msg.split()) > 3:
        return {"response": OFF_TOPIC_RESPONSE}

    # Call Gemini
    response = await call_gemini_chat(req.messages)
    return {"response": response}

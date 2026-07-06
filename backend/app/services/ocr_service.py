import re
import base64
import logging
from typing import Optional
from app.config import settings

logger = logging.getLogger(__name__)


# ── Category suggestion ────────────────────────────────────────────────────────

def suggest_category(text: str) -> str:
    text = text.lower()
    rules = {
        "Food":          ["swiggy","zomato","restaurant","cafe","food","pizza","burger","biryani","dhaba","hotel","bakery","kitchen","dining","eatery"],
        "Travel":        ["uber","ola","fuel","petrol","diesel","ticket","flight","railway","irctc","cab","bus","metro","rapido"],
        "Shopping":      ["amazon","flipkart","mall","store","mart","shop","myntra","ajio","retail","supermarket","bazaar","market"],
        "Entertainment": ["netflix","prime","spotify","movie","cinema","pvr","inox","game","theatre","bookmyshow"],
        "Healthcare":    ["pharmacy","medical","hospital","clinic","doctor","lab","apollo","medplus","health","chemist","diagnostic"],
        "Utilities":     ["electricity","water","gas","internet","broadband","jio","airtel","bsnl","bill","recharge","vi","vodafone"],
        "Education":     ["book","course","college","school","udemy","coursera","tuition","stationery","pen","notebook"],
    }
    for category, keywords in rules.items():
        if any(kw in text for kw in keywords):
            return category
    return "Other"


# ── Text parsing helpers ───────────────────────────────────────────────────────

def extract_amount(lines: list) -> Optional[float]:
    patterns = [
        r"(?:grand\s*total|total\s*amount|net\s*amount|amount\s*due|total)[:\s₹$rs\.]*\s*([\d,]+\.?\d*)",
        r"[₹$]\s*([\d,]+\.\d{2})\b",
        r"\b([\d]{1,6}[.,][\d]{2})\b",
        r"\btotal[:\s]*([\d,]+)\b",
    ]
    for line in reversed(lines):
        line_clean = line.strip().lower()
        for pat in patterns:
            m = re.search(pat, line_clean, re.IGNORECASE)
            if m:
                try:
                    return round(float(m.group(1).replace(",", "")), 2)
                except ValueError:
                    continue
    return None


def extract_date(text: str) -> Optional[str]:
    patterns = [
        r"\b(\d{2}[/\-]\d{2}[/\-]\d{4})\b",
        r"\b(\d{4}[/\-]\d{2}[/\-]\d{2})\b",
        r"\b(\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{4})\b",
        r"\b(\d{2}\.\d{2}\.\d{4})\b",
        r"\b(\d{2}[/\-]\d{2}[/\-]\d{2})\b",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group(1)
    return None


def extract_merchant(lines: list) -> Optional[str]:
    skip = {"receipt","invoice","bill","tax","gst","gstin","date","time","order","no","number","www","http"}
    for line in lines[:6]:
        clean = line.strip()
        if len(clean) < 3 or len(clean) > 60:
            continue
        if any(w in clean.lower() for w in skip):
            continue
        if re.search(r"[a-zA-Z]{3,}", clean):
            return clean.title()
    return None


def calculate_confidence(merchant, amount, date) -> float:
    score = 0.0
    if merchant: score += 0.35
    if amount:   score += 0.45
    if date:     score += 0.20
    return round(score, 2)


# ── Gemini Vision OCR ─────────────────────────────────────────────────────────

async def process_receipt(image_path: str) -> dict:
    """
    Use Google Gemini Vision to extract text from receipt image.
    Uses the same GEMINI_API_KEY already configured for AI insights.
    """
    import os

    try:
        if not settings.GEMINI_API_KEY:
            logger.error("GEMINI_API_KEY not set")
            return _error_result("AI service not configured")

        # Read and encode image
        with open(image_path, "rb") as f:
            image_bytes = f.read()

        image_b64   = base64.b64encode(image_bytes).decode("utf-8")
        ext         = os.path.splitext(image_path)[1].lower()
        mime_map    = {".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                       ".png": "image/png",  ".webp": "image/webp",
                       ".bmp": "image/bmp",  ".gif":  "image/gif"}
        mime_type   = mime_map.get(ext, "image/jpeg")

        import google.generativeai as genai
        genai.configure(api_key=settings.GEMINI_API_KEY)

        model = genai.GenerativeModel("gemini-1.5-flash")

        prompt = """You are a receipt OCR assistant. Extract the following from this receipt image:
1. Merchant/Store name (first line or top of receipt)
2. Total amount paid (grand total, final amount, net amount — the final number after taxes)
3. Date of purchase

Return ONLY this exact format, nothing else:
MERCHANT: <name>
AMOUNT: <number only, no currency symbols>
DATE: <date in DD/MM/YYYY or YYYY-MM-DD format>

If you cannot find a field, write UNKNOWN for that field."""

        response = model.generate_content([
            prompt,
            {"mime_type": mime_type, "data": image_b64}
        ])

        raw_text = response.text.strip()
        logger.info(f"Gemini OCR raw response: {raw_text}")

        # Parse Gemini structured response
        merchant = None
        amount   = None
        date_str = None

        for line in raw_text.split("\n"):
            line = line.strip()
            if line.startswith("MERCHANT:"):
                val = line.replace("MERCHANT:", "").strip()
                if val and val.upper() != "UNKNOWN":
                    merchant = val
            elif line.startswith("AMOUNT:"):
                val = line.replace("AMOUNT:", "").strip()
                if val and val.upper() != "UNKNOWN":
                    try:
                        amount = round(float(val.replace(",", "")), 2)
                    except ValueError:
                        pass
            elif line.startswith("DATE:"):
                val = line.replace("DATE:", "").strip()
                if val and val.upper() != "UNKNOWN":
                    date_str = val

        # Fallback: parse raw text if structured parsing failed
        if not merchant or not amount:
            lines = [l.strip() for l in raw_text.split("\n") if l.strip()]
            if not merchant:
                merchant = extract_merchant(lines)
            if not amount:
                amount = extract_amount(lines)
            if not date_str:
                date_str = extract_date(raw_text)

        confidence = calculate_confidence(merchant, amount, date_str)
        category   = suggest_category(f"{merchant or ''} {raw_text}")

        logger.info(f"OCR extracted — merchant:{merchant} amount:{amount} date:{date_str} confidence:{confidence}")

        return {
            "success":            True,
            "merchant":           merchant,
            "amount":             amount,
            "date":               date_str,
            "confidence":         confidence,
            "suggested_category": category,
            "raw_text":           raw_text[:2000],
        }

    except Exception as e:
        logger.error(f"Gemini OCR error: {str(e)}", exc_info=True)
        return _error_result(str(e))

    finally:
        # Delete temp file
        import os
        if image_path and os.path.exists(image_path):
            try:
                os.remove(image_path)
            except Exception:
                pass


def _error_result(error: str) -> dict:
    return {
        "success":            False,
        "error":              error,
        "merchant":           None,
        "amount":             None,
        "date":               None,
        "confidence":         0.0,
        "suggested_category": "Other",
        "raw_text":           "",
    }
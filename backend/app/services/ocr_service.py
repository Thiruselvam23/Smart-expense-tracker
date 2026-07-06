import re
import base64
import logging
import os
from typing import Optional
from app.config import settings

logger = logging.getLogger(__name__)


def suggest_category(text: str) -> str:
    text = text.lower()
    rules = {
        "Food":          ["restaurant","cafe","food","pizza","burger","biryani","hotel","bakery","dining","swiggy","zomato"],
        "Travel":        ["uber","ola","fuel","petrol","cab","bus","metro","flight","railway"],
        "Shopping":      ["amazon","flipkart","mall","store","mart","shop","supermarket"],
        "Entertainment": ["netflix","movie","cinema","pvr","inox","spotify"],
        "Healthcare":    ["pharmacy","medical","hospital","clinic","doctor","lab"],
        "Utilities":     ["electricity","water","gas","internet","jio","airtel","bill"],
        "Education":     ["book","course","college","school","tuition"],
    }
    for category, keywords in rules.items():
        if any(kw in text for kw in keywords):
            return category
    return "Other"


async def process_receipt(image_path: str) -> dict:
    try:
        if not settings.GEMINI_API_KEY:
            return {
                "success": False, "error": "GEMINI_API_KEY not configured",
                "merchant": None, "amount": None, "date": None,
                "confidence": 0.0, "suggested_category": "Other", "raw_text": "",
            }

        with open(image_path, "rb") as f:
            image_bytes = f.read()

        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        ext = os.path.splitext(image_path)[1].lower()
        mime_map = {
            ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
            ".png": "image/png",  ".webp": "image/webp",
            ".bmp": "image/bmp",  ".gif":  "image/gif",
        }
        mime_type = mime_map.get(ext, "image/jpeg")

        import google.generativeai as genai
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-1.5-flash")

        prompt = """Extract details from this receipt image.
Return ONLY these 3 lines, nothing else:
MERCHANT: <store or restaurant name>
AMOUNT: <final total amount as number only, no symbols>
DATE: <date in DD/MM/YYYY format>

If a field is not found, write UNKNOWN."""

        response = model.generate_content([
            prompt,
            {"mime_type": mime_type, "data": image_b64}
        ])

        raw_text = response.text.strip()
        logger.info(f"Gemini OCR response: {raw_text}")

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

        confidence = 0.0
        if merchant: confidence += 0.35
        if amount:   confidence += 0.45
        if date_str: confidence += 0.20
        confidence = round(confidence, 2)

        category = suggest_category(f"{merchant or ''} {raw_text}")

        logger.info(f"Parsed — merchant:{merchant} amount:{amount} date:{date_str} conf:{confidence}")

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
        logger.error(f"Gemini OCR crashed: {str(e)}", exc_info=True)
        return {
            "success": False, "error": str(e),
            "merchant": None, "amount": None, "date": None,
            "confidence": 0.0, "suggested_category": "Other", "raw_text": "",
        }
    finally:
        if image_path and os.path.exists(image_path):
            try:
                os.remove(image_path)
            except Exception:
                pass
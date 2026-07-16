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
        "Food":          ["restaurant","cafe","food","pizza","burger","biryani","hotel","bakery","dining","swiggy","zomato","chicken","prawn","veg","kitchen","eatery","mess","canteen"],
        "Travel":        ["uber","ola","fuel","petrol","cab","bus","metro","flight","railway","rapido","auto"],
        "Shopping":      ["amazon","flipkart","mall","store","mart","shop","supermarket","retail","bazaar"],
        "Entertainment": ["netflix","movie","cinema","pvr","inox","spotify","bookmyshow"],
        "Healthcare":    ["pharmacy","medical","hospital","clinic","doctor","lab","chemist","diagnostic"],
        "Utilities":     ["electricity","water","gas","internet","jio","airtel","bsnl","bill","recharge"],
        "Education":     ["book","course","college","school","tuition","stationery"],
    }
    for category, keywords in rules.items():
        if any(kw in text for kw in keywords):
            return category
    return "Other"


def parse_amount(text: str) -> Optional[float]:
    """Extract amount from any text format."""
    # Remove currency symbols
    text = text.replace("₹", "").replace("$", "").replace("Rs", "").replace("rs", "").strip()
    # Remove commas
    text = text.replace(",", "")
    # Try to extract number
    match = re.search(r'[\d]+\.?\d*', text)
    if match:
        try:
            return round(float(match.group()), 2)
        except ValueError:
            pass
    return None


def parse_date(text: str) -> Optional[str]:
    """Extract date from any text format."""
    patterns = [
        r'\b(\d{2}[/\-]\d{2}[/\-]\d{4})\b',
        r'\b(\d{4}[/\-]\d{2}[/\-]\d{2})\b',
        r'\b(\d{2}[/\-]\d{2}[/\-]\d{2})\b',
        r'\b(\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{2,4})\b',
        r'\b(\d{2}\.\d{2}\.\d{4})\b',
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group(1)
    return None


async def process_receipt(image_path: str) -> dict:
    try:
        if not settings.GEMINI_API_KEY:
            logger.error("GEMINI_API_KEY is not set")
            return _error("GEMINI_API_KEY not configured")

        logger.info(f"OCR start: {image_path}")

        with open(image_path, "rb") as f:
            image_bytes = f.read()

        logger.info(f"Image bytes: {len(image_bytes)}")

        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        ext = os.path.splitext(image_path)[1].lower()
        mime_map = {
            ".jpg":  "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png":  "image/png",
            ".webp": "image/webp",
            ".bmp":  "image/bmp",
            ".gif":  "image/gif",
        }
        mime_type = mime_map.get(ext, "image/jpeg")

        import google.generativeai as genai
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-1.5-flash")

        prompt = """This is a receipt image. Extract these 3 fields:
1. Store/Restaurant name (top of receipt)
2. Grand Total or Final Amount (bottom of receipt, the largest total)
3. Date of purchase

Respond in EXACTLY this format (3 lines only):
MERCHANT: <name>
AMOUNT: <number only, no symbols>
DATE: <date>

Write UNKNOWN if not found."""

        logger.info("Calling Gemini...")
        response = model.generate_content([
            prompt,
            {"mime_type": mime_type, "data": image_b64}
        ])

        raw_text = response.text.strip()
        logger.info(f"Gemini response: {repr(raw_text)}")

        # Parse response - handle any format Gemini returns
        merchant = None
        amount   = None
        date_str = None

        lines = raw_text.split("\n")
        for line in lines:
            line = line.strip()
            upper = line.upper()

            if "MERCHANT:" in upper:
                val = line.split(":", 1)[-1].strip()
                if val and "UNKNOWN" not in val.upper():
                    merchant = val

            elif "AMOUNT:" in upper:
                val = line.split(":", 1)[-1].strip()
                if val and "UNKNOWN" not in val.upper():
                    amount = parse_amount(val)
                    logger.info(f"Parsed amount: {amount} from '{val}'")

            elif "DATE:" in upper:
                val = line.split(":", 1)[-1].strip()
                if val and "UNKNOWN" not in val.upper():
                    date_str = val if val else None

        # If structured parsing failed, try regex on raw text
        if not amount:
            logger.warning("Structured amount parse failed, trying regex on raw text")
            # Look for grand total pattern in raw text
            patterns = [
                r"grand\s*total[:\s₹]*\s*([\d,]+\.?\d*)",
                r"total[:\s₹]*\s*([\d,]+\.?\d*)",
                r"₹\s*([\d,]+\.?\d*)",
                r"\b(\d{3,5}\.\d{2})\b",
            ]
            for pat in patterns:
                m = re.search(pat, raw_text, re.IGNORECASE)
                if m:
                    try:
                        amount = round(float(m.group(1).replace(",", "")), 2)
                        logger.info(f"Regex found amount: {amount}")
                        break
                    except ValueError:
                        pass

        if not date_str:
            date_str = parse_date(raw_text)

        if not merchant:
            # Try first non-empty line of raw text
            for line in lines:
                line = line.strip()
                if len(line) > 3 and re.search(r'[a-zA-Z]{3,}', line):
                    if "MERCHANT" not in line.upper() and "AMOUNT" not in line.upper():
                        merchant = line
                        break

        confidence = 0.0
        if merchant: confidence += 0.35
        if amount:   confidence += 0.45
        if date_str: confidence += 0.20
        confidence = round(confidence, 2)

        category = suggest_category(f"{merchant or ''} {raw_text}")

        logger.info(f"FINAL: merchant={merchant} amount={amount} date={date_str} confidence={confidence} category={category}")

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
        logger.error(f"OCR crashed: {str(e)}", exc_info=True)
        return _error(str(e))

    finally:
        if image_path and os.path.exists(image_path):
            try:
                os.remove(image_path)
            except Exception:
                pass


def _error(msg: str) -> dict:
    return {
        "success":            False,
        "error":              msg,
        "merchant":           None,
        "amount":             None,
        "date":               None,
        "confidence":         0.0,
        "suggested_category": "Other",
        "raw_text":           "",
    }
    
    
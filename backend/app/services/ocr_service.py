import re
import logging
import os
import requests
from typing import Optional
from app.config import settings

logger = logging.getLogger(__name__)


def suggest_category(text: str) -> str:
    text = text.lower()
    rules = {
        "Food":          ["restaurant","cafe","food","pizza","burger","biryani","hotel","bakery","dining","swiggy","zomato","chicken","prawn","veg","kitchen","eatery"],
        "Travel":        ["uber","ola","fuel","petrol","cab","bus","metro","flight","railway","rapido"],
        "Shopping":      ["amazon","flipkart","mall","store","mart","shop","supermarket","retail"],
        "Entertainment": ["netflix","movie","cinema","pvr","inox","spotify"],
        "Healthcare":    ["pharmacy","medical","hospital","clinic","doctor","lab","chemist"],
        "Utilities":     ["electricity","water","gas","internet","jio","airtel","bill"],
        "Education":     ["book","course","college","school","tuition","stationery"],
    }
    for category, keywords in rules.items():
        if any(kw in text for kw in keywords):
            return category
    return "Other"


def parse_amount(val: str) -> Optional[float]:
    val = re.sub(r'[^\d.]', '', str(val).replace(",", ""))
    try:
        return round(float(val), 2) if val else None
    except ValueError:
        return None


def extract_with_regex(text: str):
    """Regex-based extraction for raw OCR text."""
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    # Merchant — first meaningful line
    merchant = None
    skip = {"receipt","invoice","bill","tax","gst","gstin","date","time","www","http","tel","ph","mobile","m:","cashier","dine"}
    for line in lines[:8]:
        if len(line) < 3 or len(line) > 60:
            continue
        if any(w in line.lower() for w in skip):
            continue
        if re.search(r'[a-zA-Z]{3,}', line):
            merchant = line.title()
            break

    # Amount — from bottom up
    amount = None
    for pat in [
        r"grand\s*total[:\s₹]*\s*([\d,]+\.?\d*)",
        r"net\s*amount[:\s₹]*\s*([\d,]+\.?\d*)",
        r"total\s*amount[:\s₹]*\s*([\d,]+\.?\d*)",
        r"total[:\s₹]+\s*([\d,]+\.?\d*)",
        r"₹\s*([\d,]+\.\d{2})\b",
        r"\b(\d{3,6}\.\d{2})\b",
    ]:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            amount = parse_amount(m.group(1))
            if amount and amount > 0:
                break

    # Date
    date_str = None
    for pat in [
        r"\b(\d{2}[/\-]\d{2}[/\-]\d{4})\b",
        r"\b(\d{4}[/\-]\d{2}[/\-]\d{2})\b",
        r"\b(\d{2}[/\-]\d{2}[/\-]\d{2})\b",
        r"\b(\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{2,4})\b",
    ]:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            date_str = m.group(1)
            break

    return merchant, amount, date_str


async def call_api4ai(image_path: str) -> Optional[dict]:
    """
    Call API4AI Receipt OCR API.
    Returns parsed receipt data directly.
    Docs: https://api4.ai/docs/receipt-ocr
    """
    if not settings.API4AI_KEY:
        logger.warning("API4AI_KEY not set")
        return None

    try:
        url = "https://ocr44.p.rapidapi.com/v1/results"

        with open(image_path, "rb") as f:
            files = {"image": f}
            headers = {
                "X-RapidAPI-Key":  settings.API4AI_KEY,
                "X-RapidAPI-Host": "ocr44.p.rapidapi.com",
            }
            resp = requests.post(url, files=files, headers=headers, timeout=30)

        logger.info(f"API4AI status: {resp.status_code}")
        logger.info(f"API4AI response: {resp.text[:500]}")

        if not resp.ok:
            logger.error(f"API4AI error: {resp.text}")
            return None

        data = resp.json()

        # Extract from API4AI response structure
        merchant = None
        amount   = None
        date_str = None

        # API4AI returns structured fields
        results = data.get("results", [{}])
        if results:
            entities = results[0].get("entities", [])
            for entity in entities:
                name  = entity.get("name", "").lower()
                value = entity.get("value", "")

                if "merchant" in name or "store" in name or "company" in name:
                    merchant = str(value).strip()

                elif "total" in name and "sub" not in name:
                    amount = parse_amount(str(value))

                elif "date" in name:
                    date_str = str(value).strip()

            # Also try raw text if structured parsing missed fields
            raw_text = results[0].get("text", "")
            if raw_text:
                m2, a2, d2 = extract_with_regex(raw_text)
                if not merchant: merchant = m2
                if not amount:   amount   = a2
                if not date_str: date_str = d2

            return {
                "merchant": merchant,
                "amount":   amount,
                "date":     date_str,
                "raw_text": raw_text[:2000],
            }

    except Exception as e:
        logger.error(f"API4AI exception: {e}")
        return None


async def call_gemini_vision(image_path: str) -> Optional[dict]:
    """Try Gemini with multiple methods."""
    if not settings.GEMINI_API_KEY:
        return None

    try:
        import base64
        with open(image_path, "rb") as f:
            image_bytes = f.read()

        ext = os.path.splitext(image_path)[1].lower().lstrip(".")
        mime_map = {"jpg":"image/jpeg","jpeg":"image/jpeg","png":"image/png","webp":"image/webp","bmp":"image/bmp"}
        mime_type = mime_map.get(ext, "image/jpeg")
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        prompt = """Read this receipt image. Reply ONLY in this exact format (3 lines, nothing else):
MERCHANT: <store name>
AMOUNT: <grand total number only, e.g. 2683.00>
DATE: <DD/MM/YYYY>
Write UNKNOWN if not found."""

        payload = {
            "contents": [{"parts": [
                {"text": prompt},
                {"inline_data": {"mime_type": mime_type, "data": image_b64}}
            ]}],
            "generationConfig": {"temperature": 0.1, "maxOutputTokens": 100}
        }

        # Try URL key method
        resp = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={settings.GEMINI_API_KEY}",
            json=payload, timeout=25
        )
        logger.info(f"Gemini status: {resp.status_code}")

        if resp.ok:
            raw = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            logger.info(f"Gemini response: {repr(raw)}")

            merchant, amount, date_str = None, None, None
            for line in raw.split("\n"):
                line = line.strip()
                upper = line.upper()
                if "MERCHANT:" in upper:
                    val = line.split(":",1)[-1].strip()
                    if val and "UNKNOWN" not in val.upper(): merchant = val
                elif "AMOUNT:" in upper:
                    val = line.split(":",1)[-1].strip()
                    if val and "UNKNOWN" not in val.upper(): amount = parse_amount(val)
                elif "DATE:" in upper:
                    val = line.split(":",1)[-1].strip()
                    if val and "UNKNOWN" not in val.upper(): date_str = val

            # Regex fallback
            m2, a2, d2 = extract_with_regex(raw)
            if not merchant: merchant = m2
            if not amount:   amount   = a2
            if not date_str: date_str = d2

            return {"merchant": merchant, "amount": amount, "date": date_str, "raw_text": raw}

        logger.warning(f"Gemini failed: {resp.text[:200]}")
        return None

    except Exception as e:
        logger.warning(f"Gemini exception: {e}")
        return None


async def process_receipt(image_path: str) -> dict:
    try:
        logger.info(f"=== OCR START: {image_path} ===")

        result = None
        source = "none"

        # Method 1: API4AI (best for receipts, dedicated OCR API)
        if settings.API4AI_KEY:
            logger.info("Trying API4AI...")
            result = await call_api4ai(image_path)
            if result:
                source = "api4ai"
                logger.info(f"API4AI success: {result}")

        # Method 2: Gemini Vision
        if not result and settings.GEMINI_API_KEY:
            logger.info("Trying Gemini Vision...")
            result = await call_gemini_vision(image_path)
            if result:
                source = "gemini"
                logger.info(f"Gemini success: {result}")

        # Method 3: Tesseract (local fallback, no API needed)
        if not result:
            logger.info("Trying Tesseract fallback...")
            try:
                import pytesseract
                from PIL import Image
                import io
                with open(image_path, "rb") as f:
                    img_bytes = f.read()
                img = Image.open(io.BytesIO(img_bytes))
                raw_text = pytesseract.image_to_string(img, lang='eng')
                if raw_text.strip():
                    merchant, amount, date_str = extract_with_regex(raw_text)
                    result = {"merchant": merchant, "amount": amount, "date": date_str, "raw_text": raw_text}
                    source = "tesseract"
                    logger.info(f"Tesseract success: merchant={merchant} amount={amount}")
            except Exception as e:
                logger.warning(f"Tesseract failed: {e}")

        if not result:
            return _error("All OCR methods failed. Please enter receipt details manually.")

        merchant  = result.get("merchant")
        amount    = result.get("amount")
        date_str  = result.get("date")
        raw_text  = result.get("raw_text", "")

        confidence = round(
            (0.35 if merchant else 0.0) +
            (0.45 if amount   else 0.0) +
            (0.20 if date_str else 0.0), 2
        )
        category = suggest_category(f"{merchant or ''} {raw_text}")

        logger.info(f"=== OCR DONE (via {source}): merchant={merchant} amount={amount} date={date_str} conf={confidence} ===")

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
        logger.error(f"OCR crashed: {e}", exc_info=True)
        return _error(str(e))
    finally:
        if image_path and os.path.exists(image_path):
            try: os.remove(image_path)
            except: pass


def _error(msg: str) -> dict:
    return {
        "success": False, "error": msg,
        "merchant": None, "amount": None, "date": None,
        "confidence": 0.0, "suggested_category": "Other", "raw_text": "",
    }
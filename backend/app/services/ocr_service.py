import re
import base64
import logging
import os
import requests
from typing import Optional
from app.config import settings

logger = logging.getLogger(__name__)


def suggest_category(text: str) -> str:
    text = text.lower()
    rules = {
        "Food":          ["restaurant","cafe","food","pizza","burger","biryani","hotel","bakery","dining","swiggy","zomato","chicken","prawn","veg","kitchen","eatery","mess"],
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


def parse_amount(val: str) -> Optional[float]:
    val = re.sub(r'[^\d.]', '', str(val).replace(",", ""))
    try:
        return round(float(val), 2) if val else None
    except ValueError:
        return None


def extract_fields(text: str):
    """Extract merchant, amount, date from raw OCR text using regex."""
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    # Merchant — first meaningful line at top
    merchant = None
    skip = {"receipt","invoice","bill","tax","gst","gstin","date","time","www","http",
            "tel","ph","mobile","m:","cashier","dine","order","no","number","hsn"}
    for line in lines[:8]:
        if len(line) < 3 or len(line) > 60:
            continue
        if any(w in line.lower() for w in skip):
            continue
        if re.search(r'[a-zA-Z]{3,}', line):
            merchant = line.title()
            break

    # Amount — search for grand total from bottom
    amount = None
    for pat in [
        r"grand\s*total[:\s₹]*\s*([\d,]+\.?\d*)",
        r"net\s*amount[:\s₹]*\s*([\d,]+\.?\d*)",
        r"total\s*amount[:\s₹]*\s*([\d,]+\.?\d*)",
        r"amount\s*due[:\s₹]*\s*([\d,]+\.?\d*)",
        r"total[:\s₹]+\s*([\d,]+\.?\d*)",
        r"₹\s*([\d,]+\.\d{2})\b",
        r"\b(\d{3,6}\.\d{2})\b",
    ]:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            amount = parse_amount(m.group(1))
            if amount and amount > 0:
                logger.info(f"Amount found with pattern '{pat}': {amount}")
                break

    # Date
    date_str = None
    for pat in [
        r"\b(\d{2}[/\-]\d{2}[/\-]\d{4})\b",
        r"\b(\d{4}[/\-]\d{2}[/\-]\d{2})\b",
        r"\b(\d{2}[/\-]\d{2}[/\-]\d{2})\b",
        r"\b(\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{2,4})\b",
        r"\b(\d{2}\.\d{2}\.\d{4})\b",
    ]:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            date_str = m.group(1)
            break

    return merchant, amount, date_str


async def call_google_vision(image_path: str) -> Optional[str]:
    """Call Google Cloud Vision API for text detection."""
    if not settings.GOOGLE_VISION_API_KEY:
        logger.warning("GOOGLE_VISION_API_KEY not set")
        return None

    try:
        with open(image_path, "rb") as f:
            image_bytes = f.read()

        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        payload = {
            "requests": [{
                "image": {"content": image_b64},
                "features": [{"type": "TEXT_DETECTION", "maxResults": 1}],
                "imageContext": {"languageHints": ["en"]}
            }]
        }

        url = f"https://vision.googleapis.com/v1/images:annotate?key={settings.GOOGLE_VISION_API_KEY}"
        resp = requests.post(url, json=payload, timeout=20)

        logger.info(f"Vision API status: {resp.status_code}")

        if not resp.ok:
            logger.error(f"Vision API error: {resp.text[:300]}")
            return None

        data = resp.json()
        annotations = data.get("responses", [{}])[0].get("textAnnotations", [])

        if not annotations:
            logger.warning("Vision API returned no text annotations")
            return None

        full_text = annotations[0].get("description", "")
        logger.info(f"Vision API extracted text:\n{full_text[:500]}")
        return full_text

    except Exception as e:
        logger.error(f"Vision API exception: {e}")
        return None


async def call_gemini_vision(image_path: str) -> Optional[str]:
    """Call Gemini Vision as fallback."""
    if not settings.GEMINI_API_KEY:
        return None

    try:
        with open(image_path, "rb") as f:
            image_bytes = f.read()

        ext = os.path.splitext(image_path)[1].lower().lstrip(".")
        mime_map = {"jpg":"image/jpeg","jpeg":"image/jpeg","png":"image/png","webp":"image/webp"}
        mime_type = mime_map.get(ext, "image/jpeg")
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        payload = {
            "contents": [{"parts": [
                {"text": "Extract ALL text from this receipt image exactly as it appears. Return only the raw text, nothing else."},
                {"inline_data": {"mime_type": mime_type, "data": image_b64}}
            ]}],
            "generationConfig": {"temperature": 0, "maxOutputTokens": 500}
        }

        resp = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={settings.GEMINI_API_KEY}",
            json=payload, timeout=25
        )
        logger.info(f"Gemini status: {resp.status_code}")

        if resp.ok:
            text = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            logger.info(f"Gemini text: {text[:300]}")
            return text

        logger.warning(f"Gemini failed: {resp.text[:200]}")
        return None

    except Exception as e:
        logger.warning(f"Gemini exception: {e}")
        return None


async def process_receipt(image_path: str) -> dict:
    try:
        logger.info(f"=== OCR START: {image_path} ===")

        raw_text = None
        source   = "none"

        # Method 1: Google Cloud Vision (best accuracy)
        raw_text = await call_google_vision(image_path)
        if raw_text:
            source = "google_vision"

        # Method 2: Gemini Vision fallback
        if not raw_text:
            raw_text = await call_gemini_vision(image_path)
            if raw_text:
                source = "gemini"

        # Method 3: Tesseract local fallback
        if not raw_text:
            try:
                import pytesseract
                from PIL import Image
                import io
                with open(image_path, "rb") as f:
                    img_bytes = f.read()
                img = Image.open(io.BytesIO(img_bytes))
                raw_text = pytesseract.image_to_string(img, lang='eng')
                if raw_text.strip():
                    source = "tesseract"
                    logger.info(f"Tesseract text: {raw_text[:200]}")
            except Exception as e:
                logger.warning(f"Tesseract failed: {e}")

        if not raw_text or not raw_text.strip():
            return _error("Could not extract text from image. Please enter details manually.")

        logger.info(f"OCR source: {source}")
        logger.info(f"Full text:\n{raw_text[:800]}")

        # Extract fields using regex
        merchant, amount, date_str = extract_fields(raw_text)

        confidence = round(
            (0.35 if merchant else 0.0) +
            (0.45 if amount   else 0.0) +
            (0.20 if date_str else 0.0), 2
        )
        category = suggest_category(f"{merchant or ''} {raw_text}")

        logger.info(f"=== OCR RESULT ({source}): merchant={merchant} amount={amount} date={date_str} conf={confidence} ===")

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
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
        "Healthcare":    ["pharmacy","medical","hospital","clinic","doctor","lab","chemist"],
        "Utilities":     ["electricity","water","gas","internet","jio","airtel","bill","recharge"],
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
    """Extract merchant, amount, date from raw OCR text."""
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    # Merchant — first meaningful line
    merchant = None
    skip = {"receipt","invoice","bill","tax","gst","gstin","date","time","www","http",
            "tel","ph","mobile","m:","cashier","dine","order","no","number","hsn","qty","price"}
    for line in lines[:8]:
        if len(line) < 3 or len(line) > 60:
            continue
        if any(w in line.lower() for w in skip):
            continue
        if re.search(r'[a-zA-Z]{3,}', line):
            merchant = line.title()
            break

    # Amount — grand total from bottom
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
                logger.info(f"Amount: {amount} via pattern '{pat}'")
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


async def call_ocr_space(image_path: str) -> Optional[str]:
    """
    OCR.space free API — 25,000 requests/month, no credit card needed.
    Get free key at: https://ocr.space/ocrapi/freekey
    """
    api_key = getattr(settings, 'OCR_SPACE_KEY', '') or 'helloworld'
    # 'helloworld' is OCR.space's public demo key (limited but works for testing)

    try:
        with open(image_path, "rb") as f:
            image_bytes = f.read()

        # Convert to base64
        ext = os.path.splitext(image_path)[1].lower().lstrip(".")
        mime_map = {"jpg":"image/jpeg","jpeg":"image/jpeg","png":"image/png","webp":"image/webp","bmp":"image/bmp"}
        mime_type = mime_map.get(ext, "image/jpeg")
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        base64_image = f"data:{mime_type};base64,{image_b64}"

        payload = {
            "apikey":           api_key,
            "base64Image":      base64_image,
            "language":         "eng",
            "isOverlayRequired": False,
            "detectOrientation": True,
            "scale":            True,
            "OCREngine":        2,  # Engine 2 is better for receipts
        }

        resp = requests.post(
            "https://api.ocr.space/parse/image",
            data=payload,
            timeout=30
        )

        logger.info(f"OCR.space status: {resp.status_code}")

        if not resp.ok:
            logger.error(f"OCR.space error: {resp.text[:200]}")
            return None

        data = resp.json()
        logger.info(f"OCR.space response: {str(data)[:300]}")

        if data.get("IsErroredOnProcessing"):
            logger.error(f"OCR.space processing error: {data.get('ErrorMessage')}")
            return None

        results = data.get("ParsedResults", [])
        if not results:
            logger.warning("OCR.space returned no results")
            return None

        text = results[0].get("ParsedText", "")
        logger.info(f"OCR.space extracted:\n{text[:500]}")
        return text if text.strip() else None

    except Exception as e:
        logger.error(f"OCR.space exception: {e}")
        return None


async def call_gemini_vision(image_path: str) -> Optional[str]:
    """Gemini Vision fallback."""
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
                {"text": "Extract ALL text from this receipt image exactly as it appears. Return only the raw text."},
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

        logger.warning(f"Gemini failed: {resp.status_code} {resp.text[:100]}")
        return None
    except Exception as e:
        logger.warning(f"Gemini exception: {e}")
        return None


async def process_receipt(image_path: str) -> dict:
    try:
        logger.info(f"=== OCR START: {image_path} ===")

        raw_text = None
        source   = "none"

        # Method 1: OCR.space (free, no billing needed)
        logger.info("Trying OCR.space...")
        raw_text = await call_ocr_space(image_path)
        if raw_text:
            source = "ocr_space"
            logger.info("OCR.space succeeded")

        # Method 2: Gemini Vision fallback
        if not raw_text:
            logger.info("Trying Gemini Vision...")
            raw_text = await call_gemini_vision(image_path)
            if raw_text:
                source = "gemini"
                logger.info("Gemini succeeded")

        # Method 3: Tesseract local fallback
        if not raw_text:
            logger.info("Trying Tesseract...")
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
                    logger.info(f"Tesseract succeeded: {raw_text[:100]}")
            except Exception as e:
                logger.warning(f"Tesseract failed: {e}")

        if not raw_text or not raw_text.strip():
            logger.error("All OCR methods failed")
            return _error("Could not read receipt. Please enter details manually.")

        logger.info(f"OCR source: {source}")
        logger.info(f"Full extracted text:\n{raw_text[:1000]}")

        merchant, amount, date_str = extract_fields(raw_text)
        confidence = round(
            (0.35 if merchant else 0.0) +
            (0.45 if amount   else 0.0) +
            (0.20 if date_str else 0.0), 2
        )
        category = suggest_category(f"{merchant or ''} {raw_text}")

        logger.info(f"=== RESULT ({source}): merchant={merchant} amount={amount} date={date_str} conf={confidence} ===")

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
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
        "Food":          ["restaurant","cafe","food","pizza","burger","biryani","hotel","bakery","dining","swiggy","zomato","chicken","prawn","veg","kitchen"],
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


def parse_amount(val: str) -> Optional[float]:
    val = re.sub(r'[^\d.]', '', val.replace(",", ""))
    try:
        return round(float(val), 2) if val else None
    except ValueError:
        return None


def extract_with_regex(text: str):
    """Extract merchant, amount, date using regex from raw OCR text."""
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    # Merchant — first meaningful line
    merchant = None
    skip = {"receipt","invoice","bill","tax","gst","gstin","date","time","order","www","http","tel","ph","mobile","m:"}
    for line in lines[:8]:
        if len(line) < 3 or len(line) > 60:
            continue
        if any(w in line.lower() for w in skip):
            continue
        if re.search(r'[a-zA-Z]{3,}', line):
            merchant = line.title()
            break

    # Amount — search from bottom for grand total
    amount = None
    amount_patterns = [
        r"grand\s*total[:\s₹]*\s*([\d,]+\.?\d*)",
        r"net\s*amount[:\s₹]*\s*([\d,]+\.?\d*)",
        r"total\s*amount[:\s₹]*\s*([\d,]+\.?\d*)",
        r"amount\s*due[:\s₹]*\s*([\d,]+\.?\d*)",
        r"total[:\s₹]+\s*([\d,]+\.?\d*)",
        r"₹\s*([\d,]+\.\d{2})\b",
        r"\b(\d{3,6}\.\d{2})\b",
    ]
    for pat in amount_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            amount = parse_amount(m.group(1))
            if amount and amount > 0:
                break

    # Date
    date_str = None
    date_patterns = [
        r"\b(\d{2}[/\-]\d{2}[/\-]\d{4})\b",
        r"\b(\d{4}[/\-]\d{2}[/\-]\d{2})\b",
        r"\b(\d{2}[/\-]\d{2}[/\-]\d{2})\b",
        r"\b(\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{2,4})\b",
    ]
    for pat in date_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            date_str = m.group(1)
            break

    return merchant, amount, date_str


async def call_gemini_vision(image_bytes: bytes, mime_type: str) -> Optional[str]:
    """Try Gemini Vision with multiple auth methods for AQ. keys."""
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")

    prompt = """Read this receipt image. Reply ONLY in this exact format:
MERCHANT: <name>
AMOUNT: <number only>
DATE: <DD/MM/YYYY>
Write UNKNOWN if not found."""

    payload = {
        "contents": [{
            "parts": [
                {"text": prompt},
                {"inline_data": {"mime_type": mime_type, "data": image_b64}}
            ]
        }],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 100}
    }

    # Try 1: API key in URL (works for AIza keys)
    try:
        resp = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={settings.GEMINI_API_KEY}",
            json=payload, timeout=25
        )
        logger.info(f"Gemini URL-key status: {resp.status_code}")
        if resp.ok:
            return resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        logger.warning(f"URL-key failed: {resp.text[:150]}")
    except Exception as e:
        logger.warning(f"URL-key exception: {e}")

    # Try 2: Bearer token in header (works for AQ. keys)
    try:
        resp = requests.post(
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent",
            json=payload,
            headers={
                "Authorization": f"Bearer {settings.GEMINI_API_KEY}",
                "x-goog-api-key": settings.GEMINI_API_KEY,
                "Content-Type": "application/json",
            },
            timeout=25
        )
        logger.info(f"Gemini bearer status: {resp.status_code}")
        if resp.ok:
            return resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        logger.warning(f"Bearer failed: {resp.text[:150]}")
    except Exception as e:
        logger.warning(f"Bearer exception: {e}")

    # Try 3: google-genai new SDK (best for AQ. keys)
    try:
        from google import genai as newgenai
        from google.genai import types as gtypes
        client = newgenai.Client(api_key=settings.GEMINI_API_KEY)
        img_part = gtypes.Part.from_bytes(data=image_bytes, mime_type=mime_type)
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=[prompt, img_part],
        )
        logger.info("google-genai new SDK success")
        return response.text.strip()
    except Exception as e:
        logger.warning(f"google-genai new SDK: {e}")

    # Try 4: old google-generativeai SDK
    try:
        import google.generativeai as oldgenai
        oldgenai.configure(api_key=settings.GEMINI_API_KEY)
        model = oldgenai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content([
            prompt,
            {"mime_type": mime_type, "data": image_b64}
        ])
        logger.info("old google-generativeai SDK success")
        return response.text.strip()
    except Exception as e:
        logger.warning(f"old SDK: {e}")

    return None


async def process_receipt(image_path: str) -> dict:
    try:
        logger.info(f"=== OCR START: {image_path} ===")

        with open(image_path, "rb") as f:
            image_bytes = f.read()

        logger.info(f"Image size: {len(image_bytes)} bytes")

        ext = os.path.splitext(image_path)[1].lower().lstrip(".")
        mime_map = {
            "jpg": "image/jpeg", "jpeg": "image/jpeg",
            "png": "image/png",  "webp": "image/webp",
            "bmp": "image/bmp",  "gif":  "image/gif",
        }
        mime_type = mime_map.get(ext, "image/jpeg")

        raw_text = None
        source   = "none"

        # Try Gemini first (best accuracy)
        if settings.GEMINI_API_KEY:
            raw_text = await call_gemini_vision(image_bytes, mime_type)
            if raw_text:
                source = "gemini"
                logger.info(f"Gemini response: {repr(raw_text)}")

        # Fallback: Tesseract OCR (works without any API key)
        if not raw_text:
            logger.info("Trying Tesseract fallback...")
            try:
                import pytesseract
                from PIL import Image
                import io
                img = Image.open(io.BytesIO(image_bytes))
                raw_text = pytesseract.image_to_string(img, lang='eng')
                source = "tesseract"
                logger.info(f"Tesseract extracted: {repr(raw_text[:200])}")
            except Exception as e:
                logger.warning(f"Tesseract failed: {e}")

        if not raw_text or not raw_text.strip():
            logger.error("All OCR methods failed — no text extracted")
            return _error("Could not extract text from image. Please enter details manually.")

        # Parse extracted text
        if source == "gemini":
            # Parse structured Gemini response
            merchant, amount, date_str = None, None, None
            for line in raw_text.split("\n"):
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
                        logger.info(f"Amount parsed: {amount}")
                elif "DATE:" in upper:
                    val = line.split(":", 1)[-1].strip()
                    if val and "UNKNOWN" not in val.upper() and len(val) > 3:
                        date_str = val
            # Fallback regex if structured parse missed something
            if not amount or not merchant:
                m2, a2, d2 = extract_with_regex(raw_text)
                if not merchant: merchant = m2
                if not amount:   amount   = a2
                if not date_str: date_str = d2
        else:
            # Regex parse for Tesseract output
            merchant, amount, date_str = extract_with_regex(raw_text)

        confidence = round(
            (0.35 if merchant else 0.0) +
            (0.45 if amount   else 0.0) +
            (0.20 if date_str else 0.0), 2
        )
        category = suggest_category(f"{merchant or ''} {raw_text}")

        logger.info(f"=== OCR RESULT (via {source}): merchant={merchant} amount={amount} date={date_str} conf={confidence} ===")

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
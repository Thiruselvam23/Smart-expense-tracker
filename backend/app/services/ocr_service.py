import re
import base64
import logging
import requests
from typing import Optional
from app.config import settings

logger = logging.getLogger(__name__)


# ── Category suggestion ────────────────────────────────────────────────────────

def suggest_category(merchant: str, lines: list) -> str:
    text = " ".join([merchant or ""] + lines).lower()
    rules = {
        "Food":          ["swiggy","zomato","restaurant","cafe","food","pizza","burger","biryani","dhaba","hotel","bakery","kitchen"],
        "Travel":        ["uber","ola","fuel","petrol","diesel","ticket","flight","railway","irctc","cab","bus","metro"],
        "Shopping":      ["amazon","flipkart","mall","store","mart","shop","myntra","ajio","retail","supermarket","bazaar"],
        "Entertainment": ["netflix","prime","spotify","movie","cinema","pvr","inox","game","theatre"],
        "Healthcare":    ["pharmacy","medical","hospital","clinic","doctor","lab","apollo","medplus","health"],
        "Utilities":     ["electricity","water","gas","internet","broadband","jio","airtel","bill","recharge"],
        "Education":     ["book","course","college","school","udemy","coursera","tuition","stationery"],
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
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group(1)
    return None


def extract_merchant(lines: list) -> Optional[str]:
    skip = {"receipt","invoice","bill","tax","gst","gstin","date","time","order","no","number"}
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


# ── Google Vision OCR ─────────────────────────────────────────────────────────

async def process_receipt(image_path: str) -> dict:
    """
    Use Google Cloud Vision API for OCR.
    Falls back to basic error if API key not configured.
    """
    try:
        # Read image and encode to base64
        with open(image_path, "rb") as f:
            image_bytes = f.read()

        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        if not settings.GOOGLE_VISION_API_KEY:
            logger.warning("GOOGLE_VISION_API_KEY not set — OCR unavailable")
            return {
                "success": False,
                "error": "OCR service not configured",
                "merchant": None, "amount": None, "date": None,
                "confidence": 0.0, "suggested_category": "Other", "raw_text": "",
            }

        # Call Google Vision API
        url = f"https://vision.googleapis.com/v1/images:annotate?key={settings.GOOGLE_VISION_API_KEY}"
        payload = {
            "requests": [{
                "image": {"content": image_b64},
                "features": [{"type": "TEXT_DETECTION", "maxResults": 1}],
            }]
        }

        resp = requests.post(url, json=payload, timeout=15)

        if not resp.ok:
            logger.error(f"Vision API error: {resp.text}")
            return {
                "success": False,
                "error": f"Vision API error: {resp.status_code}",
                "merchant": None, "amount": None, "date": None,
                "confidence": 0.0, "suggested_category": "Other", "raw_text": "",
            }

        result = resp.json()
        annotations = result.get("responses", [{}])[0].get("textAnnotations", [])

        if not annotations:
            return {
                "success": False,
                "error": "No text found in image",
                "merchant": None, "amount": None, "date": None,
                "confidence": 0.0, "suggested_category": "Other", "raw_text": "",
            }

        # First annotation is the full text
        full_text = annotations[0].get("description", "")
        lines = [l.strip() for l in full_text.split("\n") if l.strip()]

        # Parse fields
        merchant   = extract_merchant(lines)
        amount     = extract_amount(lines)
        date_str   = extract_date(full_text)
        confidence = calculate_confidence(merchant, amount, date_str)
        category   = suggest_category(merchant or "", lines)

        logger.info(f"OCR success — merchant:{merchant} amount:{amount} date:{date_str} confidence:{confidence}")

        return {
            "success":            True,
            "merchant":           merchant,
            "amount":             amount,
            "date":               date_str,
            "confidence":         confidence,
            "suggested_category": category,
            "raw_text":           full_text[:2000],
        }

    except Exception as e:
        logger.error(f"OCR error: {e}")
        return {
            "success": False,
            "error":   str(e),
            "merchant": None, "amount": None, "date": None,
            "confidence": 0.0, "suggested_category": "Other", "raw_text": "",
        }
    finally:
        # Clean up temp file
        import os
        if image_path and os.path.exists(image_path):
            try:
                os.remove(image_path)
            except Exception:
                pass
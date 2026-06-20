import re
import os
import cv2
import numpy as np
from datetime import datetime
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Load EasyOCR reader once at startup (heavy model)
_reader = None


def get_reader():
    global _reader
    if _reader is None:
        try:
            import easyocr
            _reader = easyocr.Reader(["en"], gpu=False)
            logger.info("EasyOCR reader loaded")
        except Exception as e:
            logger.error(f"EasyOCR load failed: {e}")
    return _reader


def preprocess_image(image_path: str) -> np.ndarray:
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError("Cannot read image file")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Upscale if small
    h, w = gray.shape
    if w < 800:
        scale = 800 / w
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

    # Adaptive threshold for uneven lighting
    thresh = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 10
    )

    # Denoise
    denoised = cv2.fastNlMeansDenoising(thresh, h=10)
    return denoised


def extract_amount(lines: list[str]) -> Optional[float]:
    patterns = [
        r"(?:grand\s*total|total\s*amount|net\s*amount|total)[:\s]+[₹$rs\.]*\s*([\d,]+\.?\d*)",
        r"[₹$]\s*([\d,]+\.\d{2})\b",
        r"\b([\d]{1,5}[,.][\d]{2})\b",
        r"\btotal[:\s]*([\d,]+)\b",
    ]
    # Search from bottom (totals appear last on receipts)
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


def extract_merchant(lines: list[str]) -> Optional[str]:
    # Merchant name is usually in the first 3 lines, all-caps or title-cased
    skip_words = {"receipt", "invoice", "bill", "tax", "gst", "gstin", "date", "time", "order"}
    for line in lines[:5]:
        clean = line.strip()
        if len(clean) < 3 or len(clean) > 60:
            continue
        if any(w in clean.lower() for w in skip_words):
            continue
        if re.search(r"[a-zA-Z]{3,}", clean):
            return clean.title()
    return None


def suggest_category(merchant: str, lines: list[str]) -> str:
    text = " ".join([merchant or ""] + lines).lower()
    rules = {
        "Food": ["swiggy", "zomato", "restaurant", "cafe", "food", "pizza", "burger", "hotel", "biryani", "dhaba"],
        "Travel": ["uber", "ola", "fuel", "petrol", "diesel", "ticket", "flight", "railway", "irctc", "cab"],
        "Shopping": ["amazon", "flipkart", "mall", "store", "mart", "shop", "myntra", "ajio"],
        "Entertainment": ["netflix", "prime", "spotify", "movie", "cinema", "pvr", "inox", "game"],
        "Healthcare": ["pharmacy", "medical", "hospital", "clinic", "doctor", "lab", "apollo", "medplus"],
        "Utilities": ["electricity", "water", "gas", "internet", "broadband", "jio", "airtel", "bill"],
        "Education": ["book", "course", "college", "school", "udemy", "coursera", "tuition"],
    }
    for category, keywords in rules.items():
        if any(kw in text for kw in keywords):
            return category
    return "Other"


def calculate_confidence(merchant, amount, date) -> float:
    score = 0.0
    if merchant:
        score += 0.35
    if amount:
        score += 0.45
    if date:
        score += 0.20
    return round(score, 2)


async def process_receipt(image_path: str) -> dict:
    try:
        processed = preprocess_image(image_path)

        reader = get_reader()
        if reader is None:
            raise RuntimeError("OCR engine not available")

        results = reader.readtext(processed, detail=0, paragraph=False)
        lines = [r.strip() for r in results if r.strip()]
        full_text = " ".join(lines)

        merchant = extract_merchant(lines)
        amount = extract_amount(lines)
        date_str = extract_date(full_text)
        confidence = calculate_confidence(merchant, amount, date_str)
        category = suggest_category(merchant or "", lines)

        return {
            "success": True,
            "merchant": merchant,
            "amount": amount,
            "date": date_str,
            "confidence": confidence,
            "suggested_category": category,
            "raw_text": full_text[:2000],
        }
    except Exception as e:
        logger.error(f"OCR processing error: {e}")
        return {
            "success": False,
            "error": str(e),
            "merchant": None,
            "amount": None,
            "date": None,
            "confidence": 0.0,
            "suggested_category": "Other",
            "raw_text": "",
        }
    finally:
        if os.path.exists(image_path):
            os.remove(image_path)

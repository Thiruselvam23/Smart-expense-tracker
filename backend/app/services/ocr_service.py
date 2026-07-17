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
        "Food":          ["restaurant","cafe","food","pizza","burger","biryani","hotel","bakery","dining","swiggy","zomato","chicken","prawn","veg","kitchen","eatery"],
        "Travel":        ["uber","ola","fuel","petrol","cab","bus","metro","flight","railway","rapido"],
        "Shopping":      ["amazon","flipkart","mall","store","mart","shop","supermarket","retail"],
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


async def process_receipt(image_path: str) -> dict:
    try:
        if not settings.GEMINI_API_KEY:
            logger.error("GEMINI_API_KEY not set")
            return _error("GEMINI_API_KEY not configured")

        logger.info(f"OCR starting: {image_path}")

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

        prompt = """You are a receipt reader. Look at this receipt image carefully.
Extract the following and reply in EXACTLY this format with nothing else:
MERCHANT: <store or restaurant name from top of receipt>
AMOUNT: <the final grand total as a plain number like 2683.00>
DATE: <date in DD/MM/YYYY format>

If you cannot find a field write UNKNOWN.
Do not add any explanation, just the 3 lines."""

        raw_text = None

        # Method 1: Try google-genai (new SDK for AQ. keys)
        try:
            from google import genai
            from google.genai import types
            client = genai.Client(api_key=settings.GEMINI_API_KEY)
            image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[prompt, image_part],
            )
            raw_text = response.text.strip()
            logger.info(f"google-genai SDK success: {repr(raw_text)}")
        except Exception as e1:
            logger.warning(f"google-genai SDK failed: {e1}")

            # Method 2: Try google-generativeai (old SDK)
            try:
                import google.generativeai as genai2
                genai2.configure(api_key=settings.GEMINI_API_KEY)
                model = genai2.GenerativeModel("gemini-1.5-flash")
                image_b64 = base64.b64encode(image_bytes).decode("utf-8")
                response = model.generate_content([
                    prompt,
                    {"mime_type": mime_type, "data": image_b64}
                ])
                raw_text = response.text.strip()
                logger.info(f"google-generativeai SDK success: {repr(raw_text)}")
            except Exception as e2:
                logger.warning(f"google-generativeai SDK failed: {e2}")

                # Method 3: REST API with Authorization header (for AQ. keys)
                try:
                    import requests
                    image_b64 = base64.b64encode(image_bytes).decode("utf-8")
                    payload = {
                        "contents": [{
                            "parts": [
                                {"text": prompt},
                                {"inline_data": {"mime_type": mime_type, "data": image_b64}}
                            ]
                        }],
                        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 150}
                    }
                    # AQ. keys use Authorization Bearer header
                    headers = {
                        "Authorization": f"Bearer {settings.GEMINI_API_KEY}",
                        "Content-Type": "application/json",
                        "x-goog-api-key": settings.GEMINI_API_KEY,
                    }
                    resp = requests.post(
                        "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent",
                        json=payload, headers=headers, timeout=30
                    )
                    logger.info(f"REST API status: {resp.status_code} body: {resp.text[:300]}")
                    if resp.ok:
                        data = resp.json()
                        raw_text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                        logger.info(f"REST API success: {repr(raw_text)}")
                    else:
                        logger.error(f"REST API failed: {resp.text}")
                        return _error(f"All Gemini methods failed. Last error: {resp.text[:200]}")
                except Exception as e3:
                    logger.error(f"REST API also failed: {e3}")
                    return _error(f"All Gemini methods failed: {str(e3)}")

        if not raw_text:
            return _error("Gemini returned empty response")

        logger.info(f"Gemini response: {repr(raw_text)}")

        # Parse structured response
        merchant = None
        amount   = None
        date_str = None

        for line in raw_text.split("\n"):
            line = line.strip()
            if not line:
                continue
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
                if val and "UNKNOWN" not in val.upper() and len(val) > 3:
                    date_str = val

        # Fallback regex on raw text
        if not amount:
            for pat in [
                r"grand\s*total[:\s₹]*\s*([\d,]+\.?\d*)",
                r"total[:\s₹]*\s*([\d,]+\.?\d*)",
                r"₹\s*([\d,]+\.?\d*)",
                r"\b(\d{3,6}\.\d{2})\b",
            ]:
                m = re.search(pat, raw_text, re.IGNORECASE)
                if m:
                    amount = parse_amount(m.group(1))
                    if amount:
                        logger.info(f"Fallback amount: {amount}")
                        break

        if not date_str:
            for pat in [r"\b(\d{2}[/\-]\d{2}[/\-]\d{4})\b", r"\b(\d{4}[/\-]\d{2}[/\-]\d{2})\b"]:
                m = re.search(pat, raw_text)
                if m:
                    date_str = m.group(1)
                    break

        confidence = round(
            (0.35 if merchant else 0.0) +
            (0.45 if amount   else 0.0) +
            (0.20 if date_str else 0.0), 2
        )
        category = suggest_category(f"{merchant or ''} {raw_text}")

        logger.info(f"FINAL: merchant={merchant} amount={amount} date={date_str} conf={confidence} cat={category}")

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
        "success": False, "error": msg,
        "merchant": None, "amount": None, "date": None,
        "confidence": 0.0, "suggested_category": "Other", "raw_text": "",
    }
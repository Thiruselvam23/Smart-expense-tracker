import pytest


# ─── Amount Extraction Tests ──────────────────────────────────────────────────

class TestExtractAmount:

    def test_total_with_colon(self):
        from app.services.ocr_service import extract_amount
        lines = ["Item 1: 200", "Item 2: 300", "Total: 500.00"]
        assert extract_amount(lines) == 500.00

    def test_grand_total_pattern(self):
        from app.services.ocr_service import extract_amount
        lines = ["Sub Total: 800", "GST 18%: 144", "Grand Total: 944.00"]
        assert extract_amount(lines) == 944.00

    def test_rupee_symbol_pattern(self):
        from app.services.ocr_service import extract_amount
        lines = ["Swiggy Order", "₹ 320.50", "Thank you!"]
        assert extract_amount(lines) == 320.50

    def test_amount_with_commas(self):
        from app.services.ocr_service import extract_amount
        lines = ["Total Amount: 1,249.00"]
        assert extract_amount(lines) == 1249.00

    def test_no_amount_returns_none(self):
        from app.services.ocr_service import extract_amount
        lines = ["Big Bazaar", "Receipt No: 12345", "Thank you for shopping!"]
        result = extract_amount(lines)
        assert result is None

    def test_total_prioritized_over_sub_items(self):
        from app.services.ocr_service import extract_amount
        # Last "total" line should win
        lines = ["Item A: 100.00", "Item B: 200.00", "Net Amount: 300.00"]
        result = extract_amount(lines)
        assert result == 300.00


# ─── Date Extraction Tests ────────────────────────────────────────────────────

class TestExtractDate:

    def test_dd_mm_yyyy_slash(self):
        from app.services.ocr_service import extract_date
        assert extract_date("Date: 10/06/2025") == "10/06/2025"

    def test_dd_mm_yyyy_dash(self):
        from app.services.ocr_service import extract_date
        assert extract_date("Invoice date: 10-06-2025") == "10-06-2025"

    def test_yyyy_mm_dd(self):
        from app.services.ocr_service import extract_date
        assert extract_date("2025-06-10 14:30") == "2025-06-10"

    def test_dd_mmm_yyyy(self):
        from app.services.ocr_service import extract_date
        result = extract_date("Date: 10 Jun 2025")
        assert result == "10 Jun 2025"

    def test_no_date_returns_none(self):
        from app.services.ocr_service import extract_date
        assert extract_date("No date in this text at all") is None

    def test_date_embedded_in_text(self):
        from app.services.ocr_service import extract_date
        text = "Order #12345 placed on 05/12/2025 at your store"
        result = extract_date(text)
        assert result == "05/12/2025"


# ─── Merchant Extraction Tests ────────────────────────────────────────────────

class TestExtractMerchant:

    def test_first_line_is_merchant(self):
        from app.services.ocr_service import extract_merchant
        lines = ["Big Bazaar", "Store #42", "Date: 10/06/2025", "Total: 1249.00"]
        result = extract_merchant(lines)
        assert result is not None
        assert "Big" in result

    def test_skips_generic_words(self):
        from app.services.ocr_service import extract_merchant
        lines = ["Receipt", "Tax Invoice", "Apollo Pharmacy", "Date: 10/06/2025"]
        result = extract_merchant(lines)
        # Should skip "Receipt" and "Tax Invoice", return "Apollo Pharmacy"
        assert result is not None
        assert "Apollo" in result

    def test_too_short_line_skipped(self):
        from app.services.ocr_service import extract_merchant
        lines = ["AB", "Dominos Pizza", "Order #123"]
        result = extract_merchant(lines)
        assert "Dominos" in result

    def test_no_valid_merchant_returns_none(self):
        from app.services.ocr_service import extract_merchant
        lines = ["12345", "###", "----"]
        # All lines have no letters so should return None
        result = extract_merchant(lines)
        assert result is None


# ─── Category Suggestion Tests ────────────────────────────────────────────────

class TestSuggestCategory:

    def test_swiggy_is_food(self):
        from app.services.ocr_service import suggest_category
        assert suggest_category("Swiggy", ["Food delivery"]) == "Food"

    def test_uber_is_travel(self):
        from app.services.ocr_service import suggest_category
        assert suggest_category("Uber", ["Cab ride"]) == "Travel"

    def test_amazon_is_shopping(self):
        from app.services.ocr_service import suggest_category
        assert suggest_category("Amazon", ["Order delivered"]) == "Shopping"

    def test_netflix_is_entertainment(self):
        from app.services.ocr_service import suggest_category
        assert suggest_category("Netflix", ["Monthly subscription"]) == "Entertainment"

    def test_pharmacy_is_healthcare(self):
        from app.services.ocr_service import suggest_category
        assert suggest_category("Apollo Pharmacy", ["Medicine"]) == "Healthcare"

    def test_electricity_is_utilities(self):
        from app.services.ocr_service import suggest_category
        assert suggest_category("BESCOM", ["Electricity bill payment"]) == "Utilities"

    def test_unknown_is_other(self):
        from app.services.ocr_service import suggest_category
        assert suggest_category("XYZ Store", ["random items"]) == "Other"


# ─── Confidence Score Tests ───────────────────────────────────────────────────

class TestCalculateConfidence:

    def test_all_fields_high_confidence(self):
        from app.services.ocr_service import calculate_confidence
        score = calculate_confidence("Merchant", 500.0, "10/06/2025")
        assert score == 1.0

    def test_missing_merchant_lower_confidence(self):
        from app.services.ocr_service import calculate_confidence
        score = calculate_confidence(None, 500.0, "10/06/2025")
        assert score == 0.65

    def test_missing_amount_lower_confidence(self):
        from app.services.ocr_service import calculate_confidence
        score = calculate_confidence("Merchant", None, "10/06/2025")
        assert score == 0.55

    def test_no_fields_zero_confidence(self):
        from app.services.ocr_service import calculate_confidence
        score = calculate_confidence(None, None, None)
        assert score == 0.0

    def test_only_amount_medium_confidence(self):
        from app.services.ocr_service import calculate_confidence
        score = calculate_confidence(None, 320.0, None)
        assert score == 0.45


# ─── Image Validation Tests ───────────────────────────────────────────────────

class TestFileValidation:

    def test_png_allowed(self):
        from app.utils.file_utils import validate_image_file
        from unittest.mock import MagicMock

        file = MagicMock()
        file.filename = "receipt.png"
        file.content_type = "image/png"

        # Should not raise
        validate_image_file(file)

    def test_jpg_allowed(self):
        from app.utils.file_utils import validate_image_file
        from unittest.mock import MagicMock

        file = MagicMock()
        file.filename = "receipt.jpg"
        file.content_type = "image/jpeg"

        validate_image_file(file)

    def test_pdf_rejected(self):
        from app.utils.file_utils import validate_image_file
        from unittest.mock import MagicMock
        from fastapi import HTTPException

        file = MagicMock()
        file.filename = "receipt.pdf"
        file.content_type = "application/pdf"

        with pytest.raises(HTTPException) as exc:
            validate_image_file(file)
        assert exc.value.status_code == 400

    def test_svg_rejected(self):
        from app.utils.file_utils import validate_image_file
        from unittest.mock import MagicMock
        from fastapi import HTTPException

        file = MagicMock()
        file.filename = "malicious.svg"
        file.content_type = "image/svg+xml"

        with pytest.raises(HTTPException) as exc:
            validate_image_file(file)
        assert exc.value.status_code == 400

    def test_wrong_extension_rejected(self):
        from app.utils.file_utils import validate_image_file
        from unittest.mock import MagicMock
        from fastapi import HTTPException

        file = MagicMock()
        file.filename = "script.exe"
        file.content_type = "image/jpeg"  # lying about type

        with pytest.raises(HTTPException) as exc:
            validate_image_file(file)
        assert exc.value.status_code == 400

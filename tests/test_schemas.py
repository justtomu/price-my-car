"""
Tests for Pydantic schemas.
"""

import pytest
from pydantic import ValidationError

from app.schemas.llm import CachedResult, CarExtraction
from app.schemas.request import PriceCarRequest
from app.schemas.response import ErrorResponse, PriceCarResponse


class TestPriceCarRequest:
    """Tests for PriceCarRequest schema."""

    def test_valid_request(self) -> None:
        """Test valid request creation."""
        request = PriceCarRequest(
            title="2007 Honda Accord",
            description="Clean title, runs great",
        )
        assert request.title == "2007 Honda Accord"
        assert request.description == "Clean title, runs great"

    def test_title_too_short(self) -> None:
        """Test title minimum length validation."""
        with pytest.raises(ValidationError) as exc_info:
            PriceCarRequest(title="ab", description="Valid description here")
        assert "title" in str(exc_info.value)

    def test_description_too_short(self) -> None:
        """Test description minimum length validation."""
        with pytest.raises(ValidationError) as exc_info:
            PriceCarRequest(title="Valid title", description="short")
        assert "description" in str(exc_info.value)

    def test_missing_title(self) -> None:
        """Test missing title validation."""
        with pytest.raises(ValidationError):
            PriceCarRequest(description="Valid description here")

    def test_missing_description(self) -> None:
        """Test missing description validation."""
        with pytest.raises(ValidationError):
            PriceCarRequest(title="Valid title")


class TestPriceCarResponse:
    """Tests for PriceCarResponse schema."""

    def test_valid_response(self) -> None:
        """Test valid response creation."""
        response = PriceCarResponse(
            make="Honda",
            model="Accord",
            price=12500,
            request_id="test-123",
        )
        assert response.make == "Honda"
        assert response.model == "Accord"
        assert response.price == 12500
        assert response.request_id == "test-123"

    def test_negative_price(self) -> None:
        """Test negative price validation."""
        with pytest.raises(ValidationError) as exc_info:
            PriceCarResponse(
                make="Honda",
                model="Accord",
                price=-100,
                request_id="test-123",
            )
        assert "price" in str(exc_info.value)


class TestErrorResponse:
    """Tests for ErrorResponse schema."""

    def test_valid_error(self) -> None:
        """Test valid error response creation."""
        error = ErrorResponse(error="Something went wrong", request_id="test-123")
        assert error.error == "Something went wrong"
        assert error.request_id == "test-123"


class TestCarExtraction:
    """Tests for CarExtraction schema."""

    def test_valid_extraction(self) -> None:
        """Test valid extraction creation."""
        extraction = CarExtraction(make="Honda", model="Accord")
        assert extraction.make == "Honda"
        assert extraction.model == "Accord"

    def test_empty_make(self) -> None:
        """Test empty make validation."""
        with pytest.raises(ValidationError):
            CarExtraction(make="", model="Accord")

    def test_empty_model(self) -> None:
        """Test empty model validation."""
        with pytest.raises(ValidationError):
            CarExtraction(make="Honda", model="")


class TestCachedResult:
    """Tests for CachedResult schema."""

    def test_valid_cached_result(self) -> None:
        """Test valid cached result creation."""
        result = CachedResult(make="Honda", model="Accord", price=12500)
        assert result.make == "Honda"
        assert result.model == "Accord"
        assert result.price == 12500

    def test_json_serialization(self) -> None:
        """Test JSON serialization/deserialization."""
        result = CachedResult(make="Honda", model="Accord", price=12500)
        json_str = result.model_dump_json()
        restored = CachedResult.model_validate_json(json_str)
        assert restored == result

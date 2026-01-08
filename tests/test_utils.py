"""
Tests for utility functions.
"""

import pytest

from app.utils.helpers import generate_cache_key, generate_request_id
from app.utils.validators import normalize_car_info, validate_car_make, validate_car_model


class TestGenerateRequestId:
    """Tests for generate_request_id function."""

    def test_generates_uuid_format(self) -> None:
        """Test that generated ID is in UUID format."""
        request_id = generate_request_id()
        # UUID format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
        parts = request_id.split("-")
        assert len(parts) == 5
        assert len(parts[0]) == 8
        assert len(parts[1]) == 4
        assert len(parts[2]) == 4
        assert len(parts[3]) == 4
        assert len(parts[4]) == 12

    def test_generates_unique_ids(self) -> None:
        """Test that generated IDs are unique."""
        ids = [generate_request_id() for _ in range(100)]
        assert len(set(ids)) == 100


class TestGenerateCacheKey:
    """Tests for generate_cache_key function."""

    def test_generates_consistent_key(self) -> None:
        """Test that same inputs produce same key."""
        key1 = generate_cache_key("title", "description")
        key2 = generate_cache_key("title", "description")
        assert key1 == key2

    def test_different_inputs_different_keys(self) -> None:
        """Test that different inputs produce different keys."""
        key1 = generate_cache_key("title1", "description")
        key2 = generate_cache_key("title2", "description")
        assert key1 != key2

    def test_key_format(self) -> None:
        """Test that key has correct format."""
        key = generate_cache_key("title", "description")
        assert key.startswith("cache:")
        # SHA256 hash is 64 characters
        assert len(key) == 6 + 64  # "cache:" + sha256 hash

    def test_case_insensitive(self) -> None:
        """Test that key generation is case insensitive."""
        key1 = generate_cache_key("TITLE", "DESCRIPTION")
        key2 = generate_cache_key("title", "description")
        assert key1 == key2

    def test_whitespace_normalized(self) -> None:
        """Test that whitespace is normalized."""
        key1 = generate_cache_key("  title  ", "  description  ")
        key2 = generate_cache_key("title", "description")
        assert key1 == key2


class TestValidateCarMake:
    """Tests for validate_car_make function."""

    def test_valid_make(self) -> None:
        """Test valid car makes."""
        assert validate_car_make("Honda") is True
        assert validate_car_make("Mercedes-Benz") is True
        assert validate_car_make("Rolls Royce") is True

    def test_invalid_make_empty(self) -> None:
        """Test empty string is invalid."""
        assert validate_car_make("") is False
        assert validate_car_make("   ") is False

    def test_invalid_make_numbers(self) -> None:
        """Test make starting with number is invalid."""
        assert validate_car_make("123Honda") is False


class TestValidateCarModel:
    """Tests for validate_car_model function."""

    def test_valid_model(self) -> None:
        """Test valid car models."""
        assert validate_car_model("Accord") is True
        assert validate_car_model("3 Series") is True
        assert validate_car_model("CR-V") is True

    def test_invalid_model_empty(self) -> None:
        """Test empty string is invalid."""
        assert validate_car_model("") is False
        assert validate_car_model("   ") is False


class TestNormalizeCarInfo:
    """Tests for normalize_car_info function."""

    def test_normalizes_to_title_case(self) -> None:
        """Test normalization to title case."""
        make, model = normalize_car_info("HONDA", "ACCORD")
        assert make == "Honda"
        assert model == "Accord"

    def test_strips_whitespace(self) -> None:
        """Test whitespace stripping."""
        make, model = normalize_car_info("  honda  ", "  accord  ")
        assert make == "Honda"
        assert model == "Accord"

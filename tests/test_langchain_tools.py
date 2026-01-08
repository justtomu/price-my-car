"""
Tests for LangChain tools.
"""

import pytest

from app.services.langchain_tools import CAR_PRICES, get_car_price, lookup_car_price
from app.utils.exceptions import CarNotFoundError


class TestLookupCarPrice:
    """Tests for lookup_car_price function."""

    def test_lookup_known_car(self) -> None:
        """Test lookup for a known car."""
        price = lookup_car_price("Honda", "Accord")
        assert price == 12500

    def test_lookup_case_insensitive_make(self) -> None:
        """Test case-insensitive make lookup."""
        price = lookup_car_price("HONDA", "Accord")
        assert price == 12500

    def test_lookup_case_insensitive_model(self) -> None:
        """Test case-insensitive model lookup."""
        price = lookup_car_price("Honda", "ACCORD")
        assert price == 12500

    def test_lookup_with_whitespace(self) -> None:
        """Test lookup with extra whitespace."""
        price = lookup_car_price("  Honda  ", "  Accord  ")
        assert price == 12500

    def test_lookup_unknown_make(self) -> None:
        """Test lookup for unknown make."""
        with pytest.raises(CarNotFoundError) as exc_info:
            lookup_car_price("UnknownMake", "Model")
        assert "Car not found" in str(exc_info.value)

    def test_lookup_unknown_model(self) -> None:
        """Test lookup for unknown model."""
        with pytest.raises(CarNotFoundError) as exc_info:
            lookup_car_price("Honda", "UnknownModel")
        assert "Car not found" in str(exc_info.value)

    def test_lookup_various_makes(self) -> None:
        """Test lookup for various car makes."""
        test_cases = [
            ("Toyota", "Camry", 14000),
            ("BMW", "3 Series", 28000),
            ("Tesla", "Model 3", 35000),
            ("Ford", "F-150", 28000),
        ]
        for make, model, expected_price in test_cases:
            price = lookup_car_price(make, model)
            assert price == expected_price, f"Failed for {make} {model}"


class TestGetCarPriceTool:
    """Tests for get_car_price LangChain tool."""

    def test_tool_name(self) -> None:
        """Test tool has correct name."""
        assert get_car_price.name == "get_car_price"

    def test_tool_description(self) -> None:
        """Test tool has description."""
        assert get_car_price.description is not None
        assert "price" in get_car_price.description.lower()

    def test_tool_invocation(self) -> None:
        """Test tool can be invoked."""
        result = get_car_price.invoke({"make": "Honda", "model": "Accord"})
        assert result == 12500

    def test_tool_unknown_car(self) -> None:
        """Test tool raises error for unknown car."""
        with pytest.raises(CarNotFoundError):
            get_car_price.invoke({"make": "Unknown", "model": "Car"})


class TestCarPricesDatabase:
    """Tests for CAR_PRICES database."""

    def test_database_not_empty(self) -> None:
        """Test database is not empty."""
        assert len(CAR_PRICES) > 0

    def test_database_has_major_brands(self) -> None:
        """Test database has major car brands."""
        major_brands = ["Honda", "Toyota", "Ford", "BMW", "Tesla"]
        for brand in major_brands:
            assert brand in CAR_PRICES, f"Missing brand: {brand}"

    def test_all_prices_positive(self) -> None:
        """Test all prices are positive."""
        for make, models in CAR_PRICES.items():
            for model, price in models.items():
                assert price > 0, f"Invalid price for {make} {model}"

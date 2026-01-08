"""
Tests for PricingService.
"""

import pytest

from app.services.pricing_service import PricingService
from app.utils.exceptions import CarNotFoundError


class TestPricingService:
    """Tests for PricingService."""

    @pytest.fixture
    def service(self) -> PricingService:
        """Create pricing service instance."""
        return PricingService()

    @pytest.mark.asyncio
    async def test_get_price_known_car(self, service: PricingService) -> None:
        """Test getting price for known car."""
        price = await service.get_price("Honda", "Accord")
        assert price == 12500

    @pytest.mark.asyncio
    async def test_get_price_unknown_car(self, service: PricingService) -> None:
        """Test getting price for unknown car raises error."""
        with pytest.raises(CarNotFoundError):
            await service.get_price("Unknown", "Car")

    @pytest.mark.asyncio
    async def test_get_price_case_insensitive(self, service: PricingService) -> None:
        """Test price lookup is case insensitive."""
        price1 = await service.get_price("honda", "accord")
        price2 = await service.get_price("HONDA", "ACCORD")
        assert price1 == price2 == 12500

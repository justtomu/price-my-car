"""
Pricing service for orchestrating car price lookups.

Delegates to the LangChain get_car_price tool and handles
error mapping for appropriate API responses.
"""

from app.logger import get_logger
from app.services.langchain_tools import lookup_car_price
from app.utils.exceptions import CarNotFoundError

logger = get_logger("pricing_service")


class PricingService:
    """
    Service for looking up car prices.

    Orchestrates pricing lookups by delegating to the
    underlying pricing function. Handles error mapping
    for appropriate API responses.
    """

    async def get_price(self, make: str, model: str) -> int:
        """
        Get price for a car make and model.

        Args:
            make: Car manufacturer
            model: Car model

        Returns:
            int: Estimated price in dollars

        Raises:
            CarNotFoundError: If car is not found in pricing database
        """
        logger.debug(
            "price_lookup_started",
            extra={"make": make, "model": model},
        )

        try:
            # Delegate to the pricing lookup function
            price = lookup_car_price(make, model)

            logger.debug(
                "price_lookup_completed",
                extra={"make": make, "model": model, "price": price},
            )

            return price

        except CarNotFoundError:
            logger.warning(
                "price_lookup_not_found",
                extra={"make": make, "model": model},
            )
            raise

"""
LangChain tools for car pricing operations.

Defines tools using @tool decorator for auto-schema generation
and agent compatibility.
"""

from langchain_core.tools import tool

from app.logger import get_logger
from app.utils.exceptions import CarNotFoundError

logger = get_logger("langchain_tools")

# Sample pricing database (in production, this would be a real database)
# Prices are estimated average market values in USD
CAR_PRICES: dict[str, dict[str, int]] = {
    "Honda": {
        "Accord": 12500,
        "Civic": 10000,
        "CR-V": 15000,
        "Pilot": 18000,
        "Odyssey": 14000,
        "HR-V": 12000,
        "Fit": 8000,
    },
    "Toyota": {
        "Camry": 14000,
        "Corolla": 11000,
        "RAV4": 16000,
        "Highlander": 20000,
        "Tacoma": 22000,
        "Prius": 13000,
        "4Runner": 25000,
    },
    "Ford": {
        "F-150": 28000,
        "Mustang": 25000,
        "Explorer": 22000,
        "Escape": 15000,
        "Bronco": 35000,
        "Ranger": 24000,
        "Edge": 18000,
    },
    "Chevrolet": {
        "Silverado": 30000,
        "Camaro": 26000,
        "Equinox": 16000,
        "Tahoe": 35000,
        "Malibu": 12000,
        "Colorado": 22000,
        "Traverse": 20000,
    },
    "BMW": {
        "3 Series": 28000,
        "5 Series": 35000,
        "X3": 32000,
        "X5": 40000,
        "M3": 55000,
        "X1": 25000,
        "7 Series": 50000,
    },
    "Mercedes-Benz": {
        "C-Class": 30000,
        "E-Class": 38000,
        "S-Class": 55000,
        "GLC": 35000,
        "GLE": 42000,
        "A-Class": 25000,
        "CLA": 28000,
    },
    "Audi": {
        "A4": 28000,
        "A6": 35000,
        "Q5": 32000,
        "Q7": 40000,
        "A3": 24000,
        "Q3": 28000,
        "A8": 50000,
    },
    "Nissan": {
        "Altima": 13000,
        "Rogue": 15000,
        "Sentra": 10000,
        "Pathfinder": 22000,
        "Maxima": 18000,
        "Frontier": 20000,
        "Murano": 18000,
    },
    "Hyundai": {
        "Elantra": 11000,
        "Sonata": 14000,
        "Tucson": 16000,
        "Santa Fe": 20000,
        "Kona": 14000,
        "Palisade": 28000,
        "Accent": 9000,
    },
    "Kia": {
        "Optima": 13000,
        "Sorento": 18000,
        "Sportage": 16000,
        "Forte": 11000,
        "Telluride": 30000,
        "Soul": 12000,
        "K5": 15000,
    },
    "Subaru": {
        "Outback": 18000,
        "Forester": 17000,
        "Crosstrek": 16000,
        "Impreza": 12000,
        "WRX": 22000,
        "Legacy": 15000,
        "Ascent": 22000,
    },
    "Mazda": {
        "Mazda3": 14000,
        "Mazda6": 16000,
        "CX-5": 18000,
        "CX-9": 22000,
        "MX-5 Miata": 20000,
        "CX-30": 16000,
        "CX-50": 22000,
    },
    "Volkswagen": {
        "Jetta": 12000,
        "Passat": 15000,
        "Tiguan": 18000,
        "Atlas": 24000,
        "Golf": 14000,
        "ID.4": 28000,
        "Arteon": 22000,
    },
    "Tesla": {
        "Model 3": 35000,
        "Model Y": 42000,
        "Model S": 60000,
        "Model X": 65000,
        "Cybertruck": 70000,
    },
    "Lexus": {
        "ES": 32000,
        "RX": 38000,
        "NX": 30000,
        "IS": 28000,
        "GX": 42000,
        "LS": 55000,
        "UX": 26000,
    },
    "Jeep": {
        "Wrangler": 30000,
        "Grand Cherokee": 28000,
        "Cherokee": 20000,
        "Compass": 16000,
        "Gladiator": 32000,
        "Renegade": 14000,
    },
    "Ram": {
        "1500": 32000,
        "2500": 40000,
        "3500": 45000,
        "ProMaster": 28000,
    },
    "GMC": {
        "Sierra": 35000,
        "Yukon": 42000,
        "Acadia": 24000,
        "Terrain": 18000,
        "Canyon": 26000,
    },
    "Dodge": {
        "Charger": 25000,
        "Challenger": 28000,
        "Durango": 28000,
        "Hornet": 22000,
    },
    "Porsche": {
        "911": 85000,
        "Cayenne": 60000,
        "Macan": 45000,
        "Panamera": 70000,
        "Taycan": 75000,
        "718 Boxster": 50000,
    },
}


def _normalize_string(s: str) -> str:
    """Normalize string for case-insensitive matching."""
    return s.strip().title()


def lookup_car_price(make: str, model: str) -> int:
    """
    Look up car price from the pricing database.

    This is the core pricing logic, separate from the LangChain tool
    for easier testing and reuse.

    Args:
        make: Car manufacturer name
        model: Car model name

    Returns:
        int: Estimated price in dollars

    Raises:
        CarNotFoundError: If make/model combination is not found
    """
    normalized_make = _normalize_string(make)
    normalized_model = _normalize_string(model)

    # Try exact match first
    if normalized_make in CAR_PRICES:
        models = CAR_PRICES[normalized_make]
        if normalized_model in models:
            return models[normalized_model]

        # Try case-insensitive model search
        for db_model, price in models.items():
            if db_model.lower() == normalized_model.lower():
                return price

    # Try case-insensitive make search
    for db_make, models in CAR_PRICES.items():
        if db_make.lower() == normalized_make.lower():
            for db_model, price in models.items():
                if db_model.lower() == normalized_model.lower():
                    return price

    raise CarNotFoundError(
        f"Car not found: {make} {model}",
        details={"make": make, "model": model},
    )


@tool
def get_car_price(make: str, model: str) -> int:
    """
    Get estimated market price for a car make and model.

    Use this tool to look up the current market price for a specific
    car make and model combination.

    Args:
        make: Car manufacturer (e.g., Honda, Toyota, BMW)
        model: Car model (e.g., Accord, Camry, 3 Series)

    Returns:
        Estimated price in dollars as an integer
    """
    logger.debug(
        "tool_invoked",
        extra={"tool": "get_car_price", "make": make, "model": model},
    )

    price = lookup_car_price(make, model)

    logger.debug(
        "tool_result",
        extra={"tool": "get_car_price", "make": make, "model": model, "price": price},
    )

    return price

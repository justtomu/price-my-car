"""
Custom validators for data validation.

Provides reusable validation functions for common scenarios
beyond what Pydantic handles automatically.
"""

import re


def validate_car_make(make: str) -> bool:
    """
    Validate that car make is a reasonable string.

    Args:
        make: Car manufacturer name

    Returns:
        bool: True if valid, False otherwise
    """
    if not make or not make.strip():
        return False

    # Allow letters, spaces, hyphens (e.g., "Mercedes-Benz", "Rolls Royce")
    pattern = r"^[a-zA-Z][a-zA-Z\s\-]{0,49}$"
    return bool(re.match(pattern, make.strip()))


def validate_car_model(model: str) -> bool:
    """
    Validate that car model is a reasonable string.

    Args:
        model: Car model name

    Returns:
        bool: True if valid, False otherwise
    """
    if not model or not model.strip():
        return False

    # Allow letters, numbers, spaces, hyphens (e.g., "Accord", "3 Series", "A4")
    pattern = r"^[a-zA-Z0-9][a-zA-Z0-9\s\-]{0,49}$"
    return bool(re.match(pattern, model.strip()))


def normalize_car_info(make: str, model: str) -> tuple[str, str]:
    """
    Normalize car make and model for consistent storage and lookup.

    Args:
        make: Car manufacturer name
        model: Car model name

    Returns:
        tuple[str, str]: Normalized (make, model) as title case
    """
    return make.strip().title(), model.strip().title()

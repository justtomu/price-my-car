"""
Utility helper functions.

Provides common utilities used across the application
for request tracking, cache key generation, JSON extraction, etc.
"""

import hashlib
import json
import re
import uuid


def generate_request_id() -> str:
    """
    Generate a unique request ID for tracking.

    Uses UUID4 for guaranteed uniqueness across distributed systems.

    Returns:
        str: Unique request identifier (UUID format)
    """
    return str(uuid.uuid4())


def generate_cache_key(title: str, description: str) -> str:
    """
    Generate a deterministic cache key from title and description.

    Uses SHA256 hash of concatenated inputs for consistent key generation.
    The same inputs will always produce the same cache key.

    Args:
        title: Car listing title
        description: Car listing description

    Returns:
        str: Cache key in format 'cache:{sha256_hash}'
    """
    # Normalize inputs (lowercase, strip whitespace)
    normalized = f"{title.lower().strip()}:{description.lower().strip()}"

    # Generate SHA256 hash (more secure than MD5)
    hash_value = hashlib.sha256(normalized.encode()).hexdigest()

    return f"cache:{hash_value}"


def extract_json_from_text(text: str) -> dict[str, str] | None:
    """
    Extract JSON object from text that may contain additional content.

    Handles cases where LLM returns JSON wrapped in markdown or
    with additional explanatory text.

    Args:
        text: Text that may contain JSON with make/model fields

    Returns:
        Extracted dict with 'make' and 'model' keys, or None if not found
    """
    # Try to find JSON with make/model
    json_pattern = r'\{[^{}]*"make"[^{}]*"model"[^{}]*\}'
    matches = re.findall(json_pattern, text, re.IGNORECASE | re.DOTALL)

    for match in matches:
        try:
            data: dict[str, str] = json.loads(match)
            if "make" in data and "model" in data:
                return data
        except json.JSONDecodeError:
            continue

    # Try simpler pattern for fragmented responses
    make_pattern = r'"make"\s*:\s*"([^"]+)"'
    model_pattern = r'"model"\s*:\s*"([^"]+)"'

    make_match = re.search(make_pattern, text)
    model_match = re.search(model_pattern, text)

    if make_match and model_match:
        return {"make": make_match.group(1), "model": model_match.group(1)}

    return None

"""
LLM-related schemas for extraction output.

Defines Pydantic models used with LangChain OutputParser
for structured LLM response parsing.
"""

from pydantic import BaseModel, Field


class CarExtraction(BaseModel):
    """
    Structured output from LLM car information extraction.

    This model is used with LangChain's PydanticOutputParser
    to ensure LLM responses conform to expected structure.

    Attributes:
        make: Car manufacturer (e.g., Honda, Toyota, BMW)
        model: Car model (e.g., Accord, Camry, 3 Series)

    Example:
        {
            "make": "Honda",
            "model": "Accord"
        }
    """

    make: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Car manufacturer name (e.g., Honda, Toyota, BMW)",
    )
    model: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Car model name (e.g., Accord, Camry, 3 Series)",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"make": "Honda", "model": "Accord"},
                {"make": "Toyota", "model": "Camry"},
                {"make": "BMW", "model": "3 Series"},
            ]
        }
    }


class CachedResult(BaseModel):
    """
    Cached result structure for Redis storage.

    Stores successfully extracted and priced car information
    for cache retrieval without re-querying LLM.

    Attributes:
        make: Car manufacturer
        model: Car model
        price: Estimated market price in dollars
    """

    make: str = Field(..., description="Car manufacturer")
    model: str = Field(..., description="Car model")
    price: int = Field(..., ge=0, description="Estimated price in dollars")

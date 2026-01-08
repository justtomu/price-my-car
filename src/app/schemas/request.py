"""
Request schemas for API endpoints.

Defines Pydantic models for validating incoming request data.
"""

from pydantic import BaseModel, Field


class PriceCarRequest(BaseModel):
    """
    Request model for /price-car endpoint.

    Attributes:
        title: Car listing title (e.g., "2007 Honda Accord for sale")
        description: Car listing description with details

    Example:
        {
            "title": "2007 Honda Accord EX-L V6",
            "description": "Clean title, one owner, 150k miles, leather seats..."
        }
    """

    title: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description="Car listing title",
        examples=["2007 Honda Accord EX-L V6"],
    )
    description: str = Field(
        ...,
        min_length=10,
        max_length=5000,
        description="Car listing description",
        examples=["Clean title, one owner, 150k miles, leather seats, runs great"],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "title": "2007 Honda Accord EX-L V6",
                    "description": "Clean title, one owner from California. "
                    "150,000 miles, leather seats, sunroof, "
                    "V6 engine runs great. Recently serviced.",
                }
            ]
        }
    }

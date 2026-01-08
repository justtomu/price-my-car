#!/usr/bin/env python3
"""
Seed script for populating test data.

This script can be used to pre-populate the cache with sample data
for testing and demonstration purposes.
"""

import asyncio

from app.schemas.llm import CachedResult
from app.services.cache_service import CacheService
from app.settings import get_settings


async def seed_cache() -> None:
    """Seed the cache with sample car data."""
    settings = get_settings()
    cache = CacheService(settings)

    await cache.connect()

    # Sample car listings to seed
    sample_data = [
        {
            "title": "2007 Honda Accord EX-L V6",
            "description": "Clean title, one owner, 150k miles",
            "make": "Honda",
            "model": "Accord",
            "price": 12500,
        },
        {
            "title": "2020 Toyota Camry SE",
            "description": "Low mileage, excellent condition",
            "make": "Toyota",
            "model": "Camry",
            "price": 14000,
        },
        {
            "title": "2019 BMW 3 Series 330i",
            "description": "Sport package, navigation, leather",
            "make": "BMW",
            "model": "3 Series",
            "price": 28000,
        },
        {
            "title": "2021 Tesla Model 3 Long Range",
            "description": "Autopilot, white interior, low miles",
            "make": "Tesla",
            "model": "Model 3",
            "price": 35000,
        },
    ]

    print("Seeding cache with sample data...")

    for item in sample_data:
        result = CachedResult(
            make=item["make"],
            model=item["model"],
            price=item["price"],
        )
        await cache.set(item["title"], item["description"], result)
        print(f"  ✓ Cached: {item['make']} {item['model']}")

    await cache.disconnect()
    print("\nSeeding complete!")


if __name__ == "__main__":
    asyncio.run(seed_cache())

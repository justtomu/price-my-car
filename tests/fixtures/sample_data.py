"""
Sample data for testing.
"""

# Sample car listings for testing
SAMPLE_LISTINGS = [
    {
        "title": "2007 Honda Accord EX-L V6",
        "description": "Clean title, one owner from California. 150,000 miles, "
        "leather seats, sunroof, V6 engine runs great.",
        "expected_make": "Honda",
        "expected_model": "Accord",
        "expected_price": 12500,
    },
    {
        "title": "2020 Toyota Camry SE",
        "description": "Low mileage, excellent condition, all maintenance records available.",
        "expected_make": "Toyota",
        "expected_model": "Camry",
        "expected_price": 14000,
    },
    {
        "title": "2019 BMW 3 Series 330i",
        "description": "Sport package, navigation, leather interior, premium sound.",
        "expected_make": "BMW",
        "expected_model": "3 Series",
        "expected_price": 28000,
    },
]

# Invalid requests for testing error handling
INVALID_REQUESTS = [
    {
        "description": "Missing title",
        "data": {"description": "Some description here"},
        "expected_status": 422,
    },
    {
        "description": "Missing description",
        "data": {"title": "Some title here"},
        "expected_status": 422,
    },
    {
        "description": "Title too short",
        "data": {"title": "ab", "description": "Valid description here"},
        "expected_status": 422,
    },
    {
        "description": "Description too short",
        "data": {"title": "Valid title here", "description": "short"},
        "expected_status": 422,
    },
]

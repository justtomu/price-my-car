"""
Mock LLM responses for testing.
"""

# Successful extraction response (JSON format)
VALID_EXTRACTION_RESPONSE = '{"make": "Honda", "model": "Accord"}'

# Various valid extraction responses
EXTRACTION_RESPONSES = {
    "honda_accord": '{"make": "Honda", "model": "Accord"}',
    "toyota_camry": '{"make": "Toyota", "model": "Camry"}',
    "bmw_3series": '{"make": "BMW", "model": "3 Series"}',
    "tesla_model3": '{"make": "Tesla", "model": "Model 3"}',
}

# Invalid extraction responses
INVALID_EXTRACTION_RESPONSES = [
    "",  # Empty response
    "not json",  # Plain text
    '{"make": "Honda"}',  # Missing model
    '{"model": "Accord"}',  # Missing make
    '{"make": "", "model": "Accord"}',  # Empty make
    '{"make": "Honda", "model": ""}',  # Empty model
]

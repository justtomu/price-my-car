"""
Integration tests for API endpoints.

Tests cover request validation, response models, and endpoint behavior
with mocked services.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.schemas.llm import CachedResult
from app.schemas.request import PriceCarRequest
from app.schemas.response import ErrorResponse, PriceCarResponse
from app.services.agent_service import AgentResult
from app.utils.exceptions import CarNotFoundError, LLMExtractionError, LLMTimeoutError


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    def test_health_check_returns_ok(self) -> None:
        """Test basic health check endpoint returns status ok."""
        with TestClient(app, raise_server_exceptions=False) as client:
            # Health endpoint is simple and doesn't require mocking
            response = client.get("/health")
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}


class TestRootEndpoint:
    """Tests for root endpoint."""

    def test_root_returns_api_info(self) -> None:
        """Test root endpoint returns API info."""
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/")
            assert response.status_code == 200
            data = response.json()
            assert "message" in data
            assert "version" in data
            assert "docs" in data
            assert data["docs"] == "/docs"


class TestPriceCarRequestValidation:
    """Tests for /price-car request validation without running the server."""

    def test_valid_request(self) -> None:
        """Test valid request passes validation."""
        request = PriceCarRequest(
            title="2007 Honda Accord EX-L V6",
            description="Clean title, one owner, 150k miles, runs great",
        )
        assert request.title == "2007 Honda Accord EX-L V6"

    def test_missing_title_raises_error(self) -> None:
        """Test missing title raises validation error."""
        with pytest.raises(ValidationError):
            PriceCarRequest(description="Some description here")  # type: ignore

    def test_missing_description_raises_error(self) -> None:
        """Test missing description raises validation error."""
        with pytest.raises(ValidationError):
            PriceCarRequest(title="Some title")  # type: ignore

    def test_short_title_raises_error(self) -> None:
        """Test short title raises validation error."""
        with pytest.raises(ValidationError):
            PriceCarRequest(title="ab", description="Valid description here")

    def test_short_description_raises_error(self) -> None:
        """Test short description raises validation error."""
        with pytest.raises(ValidationError):
            PriceCarRequest(title="Valid title here", description="short")

    def test_title_max_length(self) -> None:
        """Test title max length validation."""
        with pytest.raises(ValidationError):
            PriceCarRequest(
                title="x" * 501,
                description="Valid description here",
            )

    def test_description_max_length(self) -> None:
        """Test description max length validation."""
        with pytest.raises(ValidationError):
            PriceCarRequest(
                title="Valid title here",
                description="x" * 5001,
            )


class TestResponseModels:
    """Tests for response model validation."""

    def test_price_car_response(self) -> None:
        """Test PriceCarResponse creation."""
        response = PriceCarResponse(
            make="Honda",
            model="Accord",
            price=12500,
            request_id="test-123",
        )
        assert response.make == "Honda"
        assert response.price == 12500

    def test_error_response(self) -> None:
        """Test ErrorResponse creation."""
        response = ErrorResponse(
            error="Something went wrong",
            request_id="test-123",
        )
        assert response.error == "Something went wrong"

    def test_price_car_response_negative_price_fails(self) -> None:
        """Test that negative price fails validation."""
        with pytest.raises(ValidationError):
            PriceCarResponse(
                make="Honda",
                model="Accord",
                price=-100,
                request_id="test-123",
            )


class TestPriceCarEndpoint:
    """Tests for /price-car endpoint with mocked services."""

    def _create_mock_services(self):
        """Create mocked services for testing."""

        mock_agent = MagicMock()
        mock_agent.get_car_price = AsyncMock(
            return_value=AgentResult(make="Honda", model="Accord", price=12500)
        )

        mock_cache = MagicMock()
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock(return_value=True)

        mock_metrics = MagicMock()
        mock_metrics.record_request = AsyncMock()
        mock_metrics.record_success = AsyncMock()
        mock_metrics.record_cache_hit = AsyncMock()
        mock_metrics.record_cache_miss = AsyncMock()
        mock_metrics.record_response_time = AsyncMock()
        mock_metrics.record_llm_latency = AsyncMock()
        mock_metrics.record_llm_success = AsyncMock()
        mock_metrics.record_car_found = AsyncMock()
        mock_metrics.record_error = AsyncMock()
        mock_metrics.record_llm_failure = AsyncMock()
        mock_metrics.record_car_not_found = AsyncMock()

        return mock_agent, mock_cache, mock_metrics

    def test_price_car_success(self) -> None:
        """Test successful price car request."""
        mock_agent, mock_cache, mock_metrics = self._create_mock_services()

        from app.api.dependencies import (
            get_agent_service,
            get_cache_service,
            get_metrics_service,
        )

        # Override dependencies
        app.dependency_overrides[get_agent_service] = lambda: mock_agent
        app.dependency_overrides[get_cache_service] = lambda: mock_cache
        app.dependency_overrides[get_metrics_service] = lambda: mock_metrics

        try:
            with TestClient(app, raise_server_exceptions=False) as client:
                response = client.post(
                    "/price-car",
                    json={
                        "title": "2007 Honda Accord EX-L V6",
                        "description": "Clean title, one owner, 150k miles",
                    },
                )

                assert response.status_code == 200
                data = response.json()
                assert data["make"] == "Honda"
                assert data["model"] == "Accord"
                assert data["price"] == 12500
                assert "request_id" in data
        finally:
            app.dependency_overrides.clear()

    def test_price_car_from_cache(self) -> None:
        """Test price car request served from cache."""
        mock_agent, mock_cache, mock_metrics = self._create_mock_services()

        # Return cached result
        mock_cache.get = AsyncMock(
            return_value=CachedResult(make="Toyota", model="Camry", price=14000)
        )

        from app.api.dependencies import (
            get_agent_service,
            get_cache_service,
            get_metrics_service,
        )

        app.dependency_overrides[get_agent_service] = lambda: mock_agent
        app.dependency_overrides[get_cache_service] = lambda: mock_cache
        app.dependency_overrides[get_metrics_service] = lambda: mock_metrics

        try:
            with TestClient(app, raise_server_exceptions=False) as client:
                response = client.post(
                    "/price-car",
                    json={
                        "title": "Toyota Camry for sale",
                        "description": "Great condition, low miles",
                    },
                )

                assert response.status_code == 200
                data = response.json()
                assert data["make"] == "Toyota"
                assert data["model"] == "Camry"
                assert data["price"] == 14000

                # Agent should not be called when cache hit
                mock_agent.get_car_price.assert_not_called()
        finally:
            app.dependency_overrides.clear()

    def test_price_car_invalid_request(self) -> None:
        """Test invalid request returns 422."""
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(
                "/price-car",
                json={
                    "title": "ab",  # Too short
                    "description": "Valid description here",
                },
            )
            assert response.status_code == 422

    def test_price_car_car_not_found(self) -> None:
        """Test car not found returns 404."""
        mock_agent, mock_cache, mock_metrics = self._create_mock_services()
        mock_agent.get_car_price = AsyncMock(
            side_effect=CarNotFoundError("Car not found")
        )

        from app.api.dependencies import (
            get_agent_service,
            get_cache_service,
            get_metrics_service,
        )

        app.dependency_overrides[get_agent_service] = lambda: mock_agent
        app.dependency_overrides[get_cache_service] = lambda: mock_cache
        app.dependency_overrides[get_metrics_service] = lambda: mock_metrics

        try:
            with TestClient(app, raise_server_exceptions=False) as client:
                response = client.post(
                    "/price-car",
                    json={
                        "title": "Unknown Brand Car",
                        "description": "Some unknown car description",
                    },
                )

                assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()

    def test_price_car_llm_extraction_error(self) -> None:
        """Test LLM extraction error returns 400."""
        mock_agent, mock_cache, mock_metrics = self._create_mock_services()
        mock_agent.get_car_price = AsyncMock(
            side_effect=LLMExtractionError("Failed to extract")
        )

        from app.api.dependencies import (
            get_agent_service,
            get_cache_service,
            get_metrics_service,
        )

        app.dependency_overrides[get_agent_service] = lambda: mock_agent
        app.dependency_overrides[get_cache_service] = lambda: mock_cache
        app.dependency_overrides[get_metrics_service] = lambda: mock_metrics

        try:
            with TestClient(app, raise_server_exceptions=False) as client:
                response = client.post(
                    "/price-car",
                    json={
                        "title": "Some car listing",
                        "description": "Description that can't be parsed",
                    },
                )

                assert response.status_code == 400
        finally:
            app.dependency_overrides.clear()

    def test_price_car_llm_timeout(self) -> None:
        """Test LLM timeout returns 504."""
        mock_agent, mock_cache, mock_metrics = self._create_mock_services()
        mock_agent.get_car_price = AsyncMock(side_effect=LLMTimeoutError("Timeout"))

        from app.api.dependencies import (
            get_agent_service,
            get_cache_service,
            get_metrics_service,
        )

        app.dependency_overrides[get_agent_service] = lambda: mock_agent
        app.dependency_overrides[get_cache_service] = lambda: mock_cache
        app.dependency_overrides[get_metrics_service] = lambda: mock_metrics

        try:
            with TestClient(app, raise_server_exceptions=False) as client:
                response = client.post(
                    "/price-car",
                    json={
                        "title": "Some car listing",
                        "description": "Description causing timeout",
                    },
                )

                assert response.status_code == 504
        finally:
            app.dependency_overrides.clear()

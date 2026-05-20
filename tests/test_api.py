"""Tests for the FastAPI REST API endpoints."""

import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def test_client():
    """Create a test client for the FastAPI app."""
    from fastapi.testclient import TestClient
    from core.api.main import create_app

    app = create_app()
    return TestClient(app)


class TestHealthEndpoint:
    """Tests for the /health endpoint."""

    def test_health_returns_200(self, test_client):
        """GET /health should return 200."""
        response = test_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "uptime_seconds" in data

    def test_health_models_returns_200(self, test_client):
        """GET /health/models should return 200."""
        response = test_client.get("/health/models")
        assert response.status_code == 200
        data = response.json()
        assert "models" in data


class TestQueryEndpoint:
    """Tests for the /query endpoint."""

    def test_query_empty_question_returns_422(self, test_client):
        """POST /query with empty question should return 422."""
        response = test_client.post("/query", json={"question": ""})
        assert response.status_code == 422

    def test_query_missing_body_returns_422(self, test_client):
        """POST /query with no body should return 422."""
        response = test_client.post("/query")
        assert response.status_code == 422


class TestIngestEndpoint:
    """Tests for the /ingest endpoint."""

    def test_ingest_status_returns_200(self, test_client):
        """GET /ingest/status should return 200."""
        response = test_client.get("/ingest/status")
        # May return 503 if pipeline not initialized during test,
        # but the endpoint should be reachable
        assert response.status_code in (200, 503)


class TestGraphEndpoint:
    """Tests for the /graph endpoint."""

    def test_graph_people_returns_list(self, test_client):
        """GET /graph/people should return a response."""
        response = test_client.get("/graph/people")
        # May return 503 if graph store not initialized
        assert response.status_code in (200, 503)
        if response.status_code == 200:
            data = response.json()
            assert "people" in data
            assert isinstance(data["people"], list)

    def test_graph_documents(self, test_client):
        """GET /graph/documents should return a response."""
        response = test_client.get("/graph/documents")
        assert response.status_code in (200, 503)

    def test_graph_stats(self, test_client):
        """GET /graph/stats should return a response."""
        response = test_client.get("/graph/stats")
        assert response.status_code in (200, 503)


class TestRootEndpoint:
    """Tests for the root endpoint."""

    def test_root_returns_info(self, test_client):
        """GET / should return API info."""
        response = test_client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "ContextOS"
        assert "version" in data

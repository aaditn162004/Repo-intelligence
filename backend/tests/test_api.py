"""Integration tests for the FastAPI endpoints."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_services():
    """Mock out external services (Qdrant, Redis, Ollama)."""
    vector_store = MagicMock()
    vector_store.initialize = AsyncMock()
    vector_store.delete_collection = AsyncMock()

    cache = MagicMock()
    cache.initialize = AsyncMock()
    cache.close = AsyncMock()
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock(return_value=True)
    cache.delete = AsyncMock()

    return vector_store, cache


@pytest.fixture
def client(mock_services):
    from app.main import app

    vector_store, cache = mock_services
    app.state.vector_store = vector_store
    app.state.cache = cache

    with TestClient(app) as c:
        yield c


def test_health_endpoint(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_list_repositories_empty(client):
    response = client.get("/api/v1/repositories")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_nonexistent_repository(client):
    response = client.get("/api/v1/repositories/nonexistent-id")
    assert response.status_code == 404

"""
PortfolioAI - Phase 1 Setup & Route Tests
Verifies application factory, configuration, error handling, and landing page rendering.
"""

import pytest
from app import create_app


@pytest.fixture
def app():
    """Create application configured for testing."""
    test_app = create_app("testing")
    return test_app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


def test_landing_page(client):
    """Test that landing page renders with HTTP 200 and expected branding."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"PortfolioAI" in response.data
    assert b"Generative AI" in response.data
    assert b"Modern Tech" in response.data


def test_health_check(client):
    """Test health endpoint returns healthy status code 200 and json."""
    response = client.get("/health")
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data["status"] == "healthy"
    assert "PortfolioAI" in json_data["service"]


def test_404_error_page(client):
    """Test custom 404 handler renders properly on non-existent route."""
    response = client.get("/non-existent-endpoint-xyz")
    assert response.status_code == 404
    assert b"Resource Not Found" in response.data


def test_auth_routes_accessible(client):
    """Test that auth routes (/login, /register) are reachable and render correctly."""
    login_res = client.get("/login")
    assert login_res.status_code == 200
    assert b"Welcome Back" in login_res.data

    reg_res = client.get("/register")
    assert reg_res.status_code == 200
    assert b"Create Your Account" in reg_res.data

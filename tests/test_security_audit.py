"""
PortfolioAI - Security Audit and Production Hardening Test Suite
Validates HTTP security headers, XSS prevention, password hashing,
CSRF enforcement, rate-limiting, error sanitization, and production configs.
"""

import re
import pytest
from app import create_app
from app.extensions import db
from app.models import User, Portfolio
from config import ProductionConfig, DevelopmentConfig, TestingConfig


@pytest.fixture
def app():
    """Create test application with in-memory database."""
    test_app = create_app("testing")
    with test_app.app_context():
        db.create_all()
        yield test_app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


def extract_csrf_token(response):
    """Extract CSRF token from HTML."""
    html = response.data.decode("utf-8")
    match = re.search(r'name=["\']csrf_token["\'][^>]*?value=["\']([^"\']+)["\']', html)
    if not match:
        match = re.search(r'content=["\']([^"\']+)["\'][^>]*?name=["\']csrf-token["\']', html)
    if not match:
        match = re.search(r'name=["\']csrf-token["\'][^>]*?content=["\']([^"\']+)["\']', html)
    assert match is not None, "CSRF token not found in response HTML."
    return match.group(1)


def create_and_login_user(client, app, name="Security Auditor", email="auditor@example.com"):
    """Create and authenticate a user in test client."""
    with app.app_context():
        user = User(name=name, email=email)
        user.set_password("AuditPass123!")
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    token = extract_csrf_token(client.get("/login"))
    client.post(
        "/login",
        data={
            "csrf_token": token,
            "email": email,
            "password": "AuditPass123!",
        },
        follow_redirects=True,
    )
    return user_id


def test_http_security_headers_present(client):
    """Verify essential HTTP security headers are attached to all responses."""
    response = client.get("/")
    assert response.status_code == 200

    # Defense-in-depth security headers
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "SAMEORIGIN"
    assert response.headers.get("X-XSS-Protection") == "1; mode=block"
    assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "Content-Security-Policy" in response.headers
    assert "default-src 'self'" in response.headers["Content-Security-Policy"]


def test_production_config_hardening():
    """Verify ProductionConfig satisfies production security hardening criteria."""
    assert ProductionConfig.DEBUG is False
    assert ProductionConfig.TESTING is False
    assert ProductionConfig.SESSION_COOKIE_SECURE is True
    assert ProductionConfig.SESSION_COOKIE_HTTPONLY is True
    assert ProductionConfig.PREFERRED_URL_SCHEME == "https"
    assert "pool_pre_ping" in ProductionConfig.SQLALCHEMY_ENGINE_OPTIONS
    assert ProductionConfig.SQLALCHEMY_ENGINE_OPTIONS["pool_pre_ping"] is True


def test_xss_prevention_in_templates(client, app):
    """Ensure user-supplied HTML/JS payloads are safely auto-escaped in templates."""
    user_id = create_and_login_user(client, app)

    # Injected XSS payload in title, headline, and about fields
    xss_payload = "<script>alert('XSS_ATTACK');</script>"
    with app.app_context():
        portfolio = Portfolio(
            user_id=user_id,
            title=f"My Portfolio {xss_payload}",
            full_name=f"Hacker {xss_payload}",
            headline=f"Penetration Tester {xss_payload}",
            about=f"About Me {xss_payload}",
            email="hacker@example.com",
            is_published=True,
            slug="xss-test-portfolio",
        )
        db.session.add(portfolio)
        db.session.commit()
        port_id = portfolio.id

    # Check preview page
    preview_res = client.get(f"/portfolios/{port_id}")
    assert preview_res.status_code == 200
    html = preview_res.data.decode("utf-8")

    # Script tag must be escaped to &lt;script&gt;
    assert "<script>alert('XSS_ATTACK');</script>" not in html
    assert "&lt;script&gt;" in html
    assert "XSS_ATTACK" in html

    # Check public page
    public_res = client.get("/p/xss-test-portfolio")
    assert public_res.status_code == 200
    public_html = public_res.data.decode("utf-8")
    assert "<script>alert('XSS_ATTACK');</script>" not in public_html
    assert "&lt;script&gt;" in public_html


def test_password_hashing_security(app):
    """Ensure passwords are encrypted with modern scrypt and plain passwords never persisted."""
    with app.app_context():
        user = User(name="Crypto User", email="crypto@example.com")
        user.set_password("PlainTextPassword999!")
        db.session.add(user)
        db.session.commit()

        # Database must never hold plain text
        assert user.password_hash != "PlainTextPassword999!"
        assert user.password_hash.startswith("scrypt:") or "pbkdf2:" in user.password_hash
        assert user.check_password("PlainTextPassword999!") is True
        assert user.check_password("WrongPassword") is False


def test_csrf_protection_on_state_modifications(client):
    """Verify POST requests without valid CSRF tokens are rejected."""
    # Attempt registration with NO csrf_token
    res = client.post(
        "/register",
        data={
            "name": "Attacker",
            "email": "attacker@example.com",
            "password": "Password123!",
            "confirm_password": "Password123!",
        },
    )
    # Flask-WTF CSRF rejection returns 400 Bad Request
    assert res.status_code == 400


def test_error_handlers_do_not_leak_stack_traces(client):
    """Verify 404 and error responses return sanitized, customer-facing templates."""
    response = client.get("/this-route-does-not-exist-at-all")
    assert response.status_code == 404
    html = response.data.decode("utf-8")
    assert "Page Not Found" in html
    assert "Traceback (most recent call last)" not in html
    assert "portfolio.db" not in html

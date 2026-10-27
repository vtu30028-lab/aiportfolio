"""
PortfolioAI - Authentication & Security Test Suite
Validates registration, password hashing, session management, route protection,
and CSRF enforcement.
"""

import re
import pytest
from werkzeug.security import check_password_hash
from app import create_app
from app.extensions import db
from app.models import User


@pytest.fixture
def app():
    """Create test application with in-memory database and fresh schema."""
    test_app = create_app("testing")
    with test_app.app_context():
        db.create_all()
        yield test_app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client with cookie jar."""
    return app.test_client()


def extract_csrf_token(response):
    """Helper to extract CSRF token from rendered HTML forms."""
    html = response.data.decode("utf-8")
    match = re.search(r'name=["\']csrf_token["\'][^>]*?value=["\']([^"\']+)["\']', html)
    if not match:
        match = re.search(r'value=["\']([^"\']+)["\'][^>]*?name=["\']csrf_token["\']', html)
    assert match is not None, "CSRF token not found in response HTML."
    return match.group(1)


# 1. Registration page loads successfully
def test_registration_page_loads(client):
    """Test that the registration page is reachable and renders form fields."""
    response = client.get("/register")
    assert response.status_code == 200
    assert b"Create Your Account" in response.data
    assert b"Full Name" in response.data
    assert b"Email Address" in response.data
    assert b"csrf_token" in response.data


# 2. Valid registration creates a database user
def test_valid_registration_creates_user(client, app):
    """Test valid registration persists user and redirects to dashboard."""
    token = extract_csrf_token(client.get("/register"))
    response = client.post(
        "/register",
        data={
            "csrf_token": token,
            "name": "Alex Rivera",
            "email": "alex.rivera@example.com",
            "password": "SecurePassword123!",
            "confirm_password": "SecurePassword123!",
            "terms": "y",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Welcome to PortfolioAI, Alex Rivera!" in response.data

    with app.app_context():
        user = User.query.filter_by(email="alex.rivera@example.com").first()
        assert user is not None
        assert user.name == "Alex Rivera"


# 3. Password is stored as a hash
def test_password_stored_as_hash(client, app):
    """Verify that plain text passwords are never stored in the database."""
    raw_password = "SuperSecretPassword2026!"
    token = extract_csrf_token(client.get("/register"))
    client.post(
        "/register",
        data={
            "csrf_token": token,
            "name": "Hashed User",
            "email": "hash.test@example.com",
            "password": raw_password,
            "confirm_password": raw_password,
            "terms": "y",
        },
    )

    with app.app_context():
        user = User.query.filter_by(email="hash.test@example.com").first()
        assert user is not None
        assert user.password_hash != raw_password
        assert check_password_hash(user.password_hash, raw_password) is True
        assert user.check_password(raw_password) is True
        assert user.check_password("WrongPassword") is False


# 4. Duplicate email registration is rejected
def test_duplicate_email_rejected(client, app):
    """Verify that registering with an existing email address fails gracefully."""
    with app.app_context():
        u = User(name="Original User", email="duplicate@example.com")
        u.set_password("Password123!")
        db.session.add(u)
        db.session.commit()

    token = extract_csrf_token(client.get("/register"))
    response = client.post(
        "/register",
        data={
            "csrf_token": token,
            "name": "Duplicate User",
            "email": "duplicate@example.com",
            "password": "Password123!",
            "confirm_password": "Password123!",
            "terms": "y",
        },
    )
    assert response.status_code == 200
    assert b"already exists" in response.data

    with app.app_context():
        count = User.query.filter_by(email="duplicate@example.com").count()
        assert count == 1


# 5. Invalid email is rejected
def test_invalid_email_rejected(client, app):
    """Test that malformed email strings are rejected by WTForms validator."""
    token = extract_csrf_token(client.get("/register"))
    response = client.post(
        "/register",
        data={
            "csrf_token": token,
            "name": "Invalid Email User",
            "email": "not-an-email-at-all",
            "password": "Password123!",
            "confirm_password": "Password123!",
            "terms": "y",
        },
    )
    assert response.status_code == 200
    assert b"valid email address" in response.data

    with app.app_context():
        user = User.query.filter_by(name="Invalid Email User").first()
        assert user is None


# 6. Password mismatch is rejected
def test_password_mismatch_rejected(client, app):
    """Verify that registration requires matching password and confirm_password."""
    token = extract_csrf_token(client.get("/register"))
    response = client.post(
        "/register",
        data={
            "csrf_token": token,
            "name": "Mismatch User",
            "email": "mismatch@example.com",
            "password": "Password123!",
            "confirm_password": "CompletelyDifferentPassword456!",
            "terms": "y",
        },
    )
    assert response.status_code == 200
    assert b"Passwords do not match" in response.data

    with app.app_context():
        user = User.query.filter_by(email="mismatch@example.com").first()
        assert user is None


# 7. Valid login succeeds
def test_valid_login_succeeds(client, app):
    """Test that correct credentials authenticate user and allow dashboard access."""
    with app.app_context():
        u = User(name="Login Tester", email="login.tester@example.com")
        u.set_password("CorrectPassword123!")
        db.session.add(u)
        db.session.commit()

    token = extract_csrf_token(client.get("/login"))
    response = client.post(
        "/login",
        data={
            "csrf_token": token,
            "email": "login.tester@example.com",
            "password": "CorrectPassword123!",
            "remember_me": "y",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Welcome back, Login Tester!" in response.data
    assert b"Login Tester" in response.data


# 8. Invalid login fails safely
def test_invalid_login_fails_safely(client, app):
    """Test that incorrect credentials return a generic error message without enumerating users."""
    with app.app_context():
        u = User(name="Existing User", email="existing@example.com")
        u.set_password("RightPassword123!")
        db.session.add(u)
        db.session.commit()

    # Wrong password on existing user
    token1 = extract_csrf_token(client.get("/login"))
    res1 = client.post(
        "/login",
        data={
            "csrf_token": token1,
            "email": "existing@example.com",
            "password": "WrongPassword!",
        },
    )
    assert res1.status_code == 401
    assert b"Invalid email address or password" in res1.data

    # Non-existent user
    token2 = extract_csrf_token(client.get("/login"))
    res2 = client.post(
        "/login",
        data={
            "csrf_token": token2,
            "email": "nonexistent@example.com",
            "password": "SomePassword123!",
        },
    )
    assert res2.status_code == 401
    assert b"Invalid email address or password" in res2.data


# 9. Authenticated users can access the dashboard
def test_authenticated_dashboard_access(client, app):
    """Test that logged-in users can load their personal dashboard."""
    with app.app_context():
        u = User(name="Dashboard User", email="dash@example.com")
        u.set_password("Pass123456!")
        db.session.add(u)
        db.session.commit()

    # Log in
    token = extract_csrf_token(client.get("/login"))
    client.post(
        "/login",
        data={
            "csrf_token": token,
            "email": "dash@example.com",
            "password": "Pass123456!",
        },
        follow_redirects=True,
    )

    response = client.get("/dashboard/")
    assert response.status_code == 200
    assert b"Dashboard User" in response.data
    assert b"dash@example.com" in response.data
    assert b"Create My Portfolio" in response.data


# 10. Unauthenticated users cannot access the dashboard
def test_unauthenticated_dashboard_redirects(client):
    """Test that unauthenticated access to /dashboard redirects to /login with next param."""
    response = client.get("/dashboard/", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]
    assert "next=" in response.headers["Location"]


# 11. Logout clears the authenticated session
def test_logout_clears_session(client, app):
    """Test that POST /logout terminates the session and prevents dashboard access."""
    with app.app_context():
        u = User(name="Logout User", email="logout@example.com")
        u.set_password("LogoutPass123!")
        db.session.add(u)
        db.session.commit()

    # Log in
    login_token = extract_csrf_token(client.get("/login"))
    client.post(
        "/login",
        data={
            "csrf_token": login_token,
            "email": "logout@example.com",
            "password": "LogoutPass123!",
        },
        follow_redirects=True,
    )

    # Verify authenticated
    dash_res = client.get("/dashboard/")
    assert dash_res.status_code == 200

    # Obtain CSRF token and post to /logout
    logout_token = extract_csrf_token(dash_res)
    logout_res = client.post(
        "/logout",
        data={"csrf_token": logout_token},
        follow_redirects=True,
    )
    assert logout_res.status_code == 200
    assert b"You have been signed out successfully" in logout_res.data

    # Verify protected access is now revoked
    revoked_res = client.get("/dashboard/", follow_redirects=False)
    assert revoked_res.status_code == 302
    assert "/login" in revoked_res.headers["Location"]


# 12. CSRF protection is enabled for state-changing form submissions
def test_csrf_protection_enforced(client, app):
    """Verify that POST requests lacking a valid CSRF token are rejected with HTTP 400."""
    # Attempt registration without csrf_token
    res_no_token = client.post(
        "/register",
        data={
            "name": "Attacker",
            "email": "attacker@example.com",
            "password": "MaliciousPassword123!",
            "confirm_password": "MaliciousPassword123!",
            "terms": "y",
        },
    )
    assert res_no_token.status_code == 400

    # Attempt logout without csrf_token
    res_logout_no_token = client.post("/logout")
    assert res_logout_no_token.status_code == 400

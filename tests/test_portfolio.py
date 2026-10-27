"""
PortfolioAI - Portfolio CRUD & Ownership Test Suite
Validates creation, editing, deletion, previewing, ownership isolation,
validation constraints, and CSRF protection.
"""

import re
import pytest
from app import create_app
from app.extensions import db
from app.models import User, Portfolio


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


def create_and_login_user(client, app, name="Test User", email="user@example.com"):
    """Helper to create and authenticate a user in the test client."""
    with app.app_context():
        user = User(name=name, email=email)
        user.set_password("Password123!")
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    token = extract_csrf_token(client.get("/login"))
    client.post(
        "/login",
        data={
            "csrf_token": token,
            "email": email,
            "password": "Password123!",
        },
        follow_redirects=True,
    )
    return user_id


# 1. A logged-in user can create a portfolio
def test_create_portfolio(client, app):
    """Test that an authenticated user can submit the creation form to add a portfolio."""
    user_id = create_and_login_user(client, app, name="Dev User", email="dev@test.com")

    token = extract_csrf_token(client.get("/portfolios/create"))
    response = client.post(
        "/portfolios/create",
        data={
            "csrf_token": token,
            "title": "Full-Stack AI Portfolio",
            "full_name": "Dev User",
            "headline": "Lead Systems Architect & AI Specialist",
            "about": "Building high-throughput generative microservices and modern web apps.",
            "email": "dev@test.com",
            "phone": "+1-555-0199",
            "location": "Seattle, WA",
            "github_url": "https://github.com/devuser",
            "linkedin_url": "https://linkedin.com/in/devuser",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"created successfully" in response.data
    assert b"Full-Stack AI Portfolio" in response.data


# 2. Portfolio data persists after restarting the application
def test_portfolio_persistence(client, app):
    """Verify that portfolio records correctly persist in the database."""
    user_id = create_and_login_user(client, app, name="Persist User", email="persist@test.com")

    token = extract_csrf_token(client.get("/portfolios/create"))
    client.post(
        "/portfolios/create",
        data={
            "csrf_token": token,
            "title": "Cloud Architect Portfolio",
            "full_name": "Persist User",
            "headline": "AWS & Kubernetes Engineer",
            "about": "Automating cloud infrastructure at scale with Terraform and Python.",
            "email": "persist@test.com",
            "location": "Austin, TX",
            "github_url": "https://github.com/persist",
        },
        follow_redirects=True,
    )

    with app.app_context():
        portfolio = Portfolio.query.filter_by(title="Cloud Architect Portfolio").first()
        assert portfolio is not None
        assert portfolio.user_id == user_id
        assert portfolio.headline == "AWS & Kubernetes Engineer"
        assert portfolio.location == "Austin, TX"
        assert portfolio.github_url == "https://github.com/persist"
        assert portfolio.created_at is not None
        assert portfolio.updated_at is not None


# 3. A user can view their own portfolios
def test_view_own_portfolios(client, app):
    """Test that GET /portfolios lists all portfolios belonging to the authenticated user."""
    user_id = create_and_login_user(client, app, name="Viewer", email="viewer@test.com")

    with app.app_context():
        p1 = Portfolio(
            user_id=user_id,
            title="Frontend Specialist",
            full_name="Viewer",
            headline="React and TypeScript Developer",
            about="Focused on accessible interactive web interfaces.",
            email="viewer@test.com",
        )
        p2 = Portfolio(
            user_id=user_id,
            title="Backend Specialist",
            full_name="Viewer",
            headline="Python and Flask API Architect",
            about="Designing resilient REST APIs and SQL schemas.",
            email="viewer@test.com",
        )
        db.session.add_all([p1, p2])
        db.session.commit()

    response = client.get("/portfolios/")
    assert response.status_code == 200
    assert b"Frontend Specialist" in response.data
    assert b"Backend Specialist" in response.data


# 4. A user can edit their own portfolio
def test_edit_own_portfolio(client, app):
    """Verify that a user can update their portfolio via GET and POST /portfolios/<id>/edit."""
    user_id = create_and_login_user(client, app, name="Editor", email="editor@test.com")

    with app.app_context():
        p = Portfolio(
            user_id=user_id,
            title="Original Title",
            full_name="Editor",
            headline="Original Headline",
            about="Original about text with sufficient length.",
            email="editor@test.com",
        )
        db.session.add(p)
        db.session.commit()
        portfolio_id = p.id

    # Load edit page
    edit_get = client.get(f"/portfolios/{portfolio_id}/edit")
    assert edit_get.status_code == 200
    assert b"Original Title" in edit_get.data

    # Submit updated details
    token = extract_csrf_token(edit_get)
    edit_post = client.post(
        f"/portfolios/{portfolio_id}/edit",
        data={
            "csrf_token": token,
            "title": "Updated Modern Title",
            "full_name": "Editor",
            "headline": "Updated Headline with More Skills",
            "about": "Updated about text with extensive descriptions.",
            "email": "editor@test.com",
            "location": "Boston, MA",
        },
        follow_redirects=True,
    )
    assert edit_post.status_code == 200
    assert b"updated successfully" in edit_post.data

    with app.app_context():
        updated = db.session.get(Portfolio, portfolio_id)
        assert updated.title == "Updated Modern Title"
        assert updated.headline == "Updated Headline with More Skills"
        assert updated.location == "Boston, MA"


# 5. A user can delete their own portfolio
def test_delete_own_portfolio(client, app):
    """Verify that a user can delete their portfolio via POST /portfolios/<id>/delete."""
    user_id = create_and_login_user(client, app, name="Deleter", email="deleter@test.com")

    with app.app_context():
        p = Portfolio(
            user_id=user_id,
            title="To Be Deleted",
            full_name="Deleter",
            headline="Temporary Headline",
            about="Temporary bio text before removal.",
            email="deleter@test.com",
        )
        db.session.add(p)
        db.session.commit()
        portfolio_id = p.id

    list_res = client.get("/portfolios/")
    token = extract_csrf_token(list_res)

    del_res = client.post(
        f"/portfolios/{portfolio_id}/delete",
        data={"csrf_token": token},
        follow_redirects=True,
    )
    assert del_res.status_code == 200
    assert b"deleted successfully" in del_res.data

    with app.app_context():
        assert db.session.get(Portfolio, portfolio_id) is None


# 6. Unauthenticated users are redirected to login
def test_unauthenticated_portfolio_routes_redirect(client):
    """Verify that all portfolio routes redirect unauthenticated visitors to login."""
    routes = [
        "/portfolios/",
        "/portfolios/create",
        "/portfolios/1",
        "/portfolios/1/edit",
    ]
    for r in routes:
        res = client.get(r, follow_redirects=False)
        assert res.status_code == 302
        assert "/login" in res.headers["Location"]

    # Test POST delete route as well with a valid CSRF token from an unauthenticated session
    token = extract_csrf_token(client.get("/login"))
    post_res = client.post(
        "/portfolios/1/delete",
        data={"csrf_token": token},
        follow_redirects=False,
    )
    assert post_res.status_code == 302
    assert "/login" in post_res.headers["Location"]


# 7. User A cannot view, edit, or delete User B's portfolio
def test_ownership_isolation_returns_404(client, app):
    """Ensure strict ownership: attempting to view, edit, or delete another user's portfolio returns 404."""
    # Create User A and their portfolio
    with app.app_context():
        user_a = User(name="User A", email="usera@test.com")
        user_a.set_password("Pass123!")
        db.session.add(user_a)
        db.session.commit()

        p_a = Portfolio(
            user_id=user_a.id,
            title="User A Secret Portfolio",
            full_name="User A",
            headline="User A Headline",
            about="User A about me details.",
            email="usera@test.com",
        )
        db.session.add(p_a)
        db.session.commit()
        portfolio_a_id = p_a.id

    # Now create and log in as User B
    create_and_login_user(client, app, name="User B", email="userb@test.com")

    # User B tries to view User A's portfolio preview
    view_res = client.get(f"/portfolios/{portfolio_a_id}")
    assert view_res.status_code == 404

    # User B tries to edit User A's portfolio
    edit_get = client.get(f"/portfolios/{portfolio_a_id}/edit")
    assert edit_get.status_code == 404

    token = extract_csrf_token(client.get("/portfolios/"))
    edit_post = client.post(
        f"/portfolios/{portfolio_a_id}/edit",
        data={
            "csrf_token": token,
            "title": "Hacked Title",
            "full_name": "Hacker",
            "headline": "Hacked Headline",
            "about": "Hacked about description.",
            "email": "hacker@test.com",
        },
    )
    assert edit_post.status_code == 404

    # User B tries to delete User A's portfolio
    del_post = client.post(
        f"/portfolios/{portfolio_a_id}/delete",
        data={"csrf_token": token},
    )
    assert del_post.status_code == 404

    # Verify User A's portfolio is unmodified in database
    with app.app_context():
        unmodified = db.session.get(Portfolio, portfolio_a_id)
        assert unmodified is not None
        assert unmodified.title == "User A Secret Portfolio"


# 8. Invalid form data is rejected
def test_invalid_portfolio_form_rejected(client, app):
    """Test that submitting missing required fields or invalid URLs produces validation errors."""
    create_and_login_user(client, app, name="Tester", email="test@test.com")

    token = extract_csrf_token(client.get("/portfolios/create"))
    response = client.post(
        "/portfolios/create",
        data={
            "csrf_token": token,
            "title": "A",  # Too short (min 2)
            "full_name": "",  # Missing
            "headline": "Hi",  # Too short (min 5)
            "about": "Short",  # Too short (min 10)
            "email": "invalid-email-string",
            "github_url": "invalid-url",
        },
    )
    assert response.status_code == 200
    assert b"Please enter your full professional name" in response.data or b"Please provide a valid email" in response.data

    with app.app_context():
        assert Portfolio.query.count() == 0


# 9. CSRF protection works correctly
def test_portfolio_csrf_protection(client, app):
    """Verify that portfolio POST requests without a CSRF token return HTTP 400."""
    create_and_login_user(client, app, name="CSRF Test", email="csrf@test.com")

    # POST create without token
    res_create = client.post(
        "/portfolios/create",
        data={
            "title": "No Token Portfolio",
            "full_name": "No Token",
            "headline": "Headline without token",
            "about": "About me without token.",
            "email": "csrf@test.com",
        },
    )
    assert res_create.status_code == 400

    # POST delete without token
    res_del = client.post("/portfolios/1/delete")
    assert res_del.status_code == 400


# 10. Existing registration and login features still work
def test_existing_auth_remains_functional(client, app):
    """Ensure Phase 1 & 2 auth functionality remains intact alongside Phase 3."""
    reg_token = extract_csrf_token(client.get("/register"))
    reg_res = client.post(
        "/register",
        data={
            "csrf_token": reg_token,
            "name": "Intact User",
            "email": "intact@example.com",
            "password": "Password123!",
            "confirm_password": "Password123!",
            "terms": "y",
        },
        follow_redirects=True,
    )
    assert reg_res.status_code == 200
    assert b"Welcome to PortfolioAI, Intact User!" in reg_res.data

    # Check dashboard loads with portfolio count = 0
    dash_res = client.get("/dashboard/")
    assert dash_res.status_code == 200
    assert b"Total Portfolios" in dash_res.data
    assert b"0 portfolio" in dash_res.data

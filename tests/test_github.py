"""
PortfolioAI - GitHub Integration Test Suite
Tests GitHub REST API repository fetching, username validation, rate-limiting,
network timeouts, AI description generation, portfolio ownership isolation,
duplicate import prevention, and transactional project persistence.
"""

import re
import pytest
from unittest.mock import patch, MagicMock
import requests
from app import create_app
from app.extensions import db
from app.models import User, Portfolio, Project
from app.ai.service import AIServiceError


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
    """Create test client with session cookies."""
    return app.test_client()


def extract_csrf_token(response):
    """Extract CSRF token from rendered HTML."""
    html = response.data.decode("utf-8")
    match = re.search(r'name=["\']csrf_token["\'][^>]*?value=["\']([^"\']+)["\']', html)
    if not match:
        match = re.search(r'content=["\']([^"\']+)["\'][^>]*?name=["\']csrf-token["\']', html)
    if not match:
        match = re.search(r'name=["\']csrf-token["\'][^>]*?content=["\']([^"\']+)["\']', html)
    assert match is not None, "CSRF token not found in response HTML."
    return match.group(1)


def create_and_login_user(client, app, name="GitHub Developer", email="dev@example.com"):
    """Create and authenticate a user in the test client."""
    with app.app_context():
        user = User(name=name, email=email)
        user.set_password("SecurePass123!")
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    token = extract_csrf_token(client.get("/login"))
    client.post(
        "/login",
        data={
            "csrf_token": token,
            "email": email,
            "password": "SecurePass123!",
        },
        follow_redirects=True,
    )
    return user_id


def create_test_portfolio(app, user_id, title="Main Portfolio"):
    """Create a portfolio for tests."""
    with app.app_context():
        portfolio = Portfolio(
            user_id=user_id,
            title=title,
            full_name="GitHub Developer",
            headline="Full Stack Engineer",
            about="Experienced software engineer specializing in Python and cloud systems.",
            email="dev@example.com",
            github_url="https://github.com/octocat",
        )
        db.session.add(portfolio)
        db.session.commit()
        return portfolio.id


MOCK_GITHUB_REPOS = [
    {
        "name": "ai-portfolio-generator",
        "full_name": "octocat/ai-portfolio-generator",
        "description": "An AI-powered portfolio generator built with Flask and Gemini.",
        "html_url": "https://github.com/octocat/ai-portfolio-generator",
        "language": "Python",
        "stargazers_count": 42,
        "forks_count": 8,
        "topics": ["flask", "gemini-ai", "portfolio"],
        "updated_at": "2026-03-15T10:00:00Z",
        "homepage": "https://portfolio-ai.demo",
        "fork": False,
        "default_branch": "main",
    },
    {
        "name": "data-pipeline-tools",
        "full_name": "octocat/data-pipeline-tools",
        "description": "High performance ETL processing pipeline utilities.",
        "html_url": "https://github.com/octocat/data-pipeline-tools",
        "language": "Go",
        "stargazers_count": 15,
        "forks_count": 3,
        "topics": ["etl", "golang", "pipeline"],
        "updated_at": "2026-02-20T14:30:00Z",
        "homepage": None,
        "fork": False,
        "default_branch": "master",
    },
]


def test_github_import_page_loads_authenticated(client, app):
    """Verify /github/import page loads properly for logged-in user with their portfolios."""
    user_id = create_and_login_user(client, app)
    port_id = create_test_portfolio(app, user_id, "Primary Portfolio")

    response = client.get(f"/github/import?portfolio_id={port_id}")
    assert response.status_code == 200
    html = response.data.decode("utf-8")
    assert "Import Public Repositories" in html
    assert "Primary Portfolio" in html
    assert "octocat" in html  # Default username extracted from portfolio.github_url


def test_unauthenticated_github_routes_redirect(client):
    """Ensure unauthenticated access to GitHub endpoints is strictly prevented."""
    login_page = client.get("/login")
    csrf_token = extract_csrf_token(login_page)

    # GET import page
    get_res = client.get("/github/import")
    assert get_res.status_code == 302
    assert "/login" in get_res.headers["Location"]

    # POST fetch
    fetch_res = client.post(
        "/github/fetch",
        json={"username": "octocat", "portfolio_id": 1},
        headers={"X-CSRFToken": csrf_token},
    )
    assert fetch_res.status_code == 302
    assert "/login" in fetch_res.headers["Location"]

    # POST import
    import_res = client.post(
        "/github/import",
        json={"portfolio_id": 1, "projects": []},
        headers={"X-CSRFToken": csrf_token},
    )
    assert import_res.status_code == 302
    assert "/login" in import_res.headers["Location"]


@patch("requests.get")
def test_valid_github_username_fetch(mock_get, client, app):
    """Test fetching public repositories for a valid GitHub username."""
    user_id = create_and_login_user(client, app)
    port_id = create_test_portfolio(app, user_id)

    # Mock GitHub API HTTP 200
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = MOCK_GITHUB_REPOS
    mock_get.return_value = mock_resp

    page = client.get("/github/import")
    csrf_token = extract_csrf_token(page)

    response = client.post(
        "/github/fetch",
        json={"username": "octocat", "portfolio_id": port_id},
        headers={"X-CSRFToken": csrf_token},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["username"] == "octocat"
    assert data["total_count"] == 2
    assert len(data["repositories"]) == 2

    first_repo = data["repositories"][0]
    assert first_repo["name"] == "ai-portfolio-generator"
    assert first_repo["language"] == "Python"
    assert first_repo["stars"] == 42
    assert "gemini-ai" in first_repo["topics"]
    assert first_repo["already_imported"] is False


def test_invalid_github_username_rejected(client, app):
    """Test username format validation rejects malformed usernames."""
    user_id = create_and_login_user(client, app)
    port_id = create_test_portfolio(app, user_id)

    page = client.get("/github/import")
    csrf_token = extract_csrf_token(page)

    invalid_names = [
        "-leading-hyphen",
        "trailing-hyphen-",
        "double--hyphen",
        "user with space",
        "user@special!",
        "a" * 40,  # exceeds 39 chars
    ]

    for bad_name in invalid_names:
        response = client.post(
            "/github/fetch",
            json={"username": bad_name, "portfolio_id": port_id},
            headers={"X-CSRFToken": csrf_token},
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "Invalid GitHub username" in data["error"] or "cannot" in data["error"]


@patch("requests.get")
def test_nonexistent_github_user_returns_404(mock_get, client, app):
    """Test handling of 404 from GitHub for non-existent usernames."""
    user_id = create_and_login_user(client, app)
    port_id = create_test_portfolio(app, user_id)

    mock_resp = MagicMock()
    mock_resp.status_code = 404
    mock_get.return_value = mock_resp

    page = client.get("/github/import")
    csrf_token = extract_csrf_token(page)

    response = client.post(
        "/github/fetch",
        json={"username": "thisuserdefinitelydoesnotexist999", "portfolio_id": port_id},
        headers={"X-CSRFToken": csrf_token},
    )

    assert response.status_code == 404
    data = response.get_json()
    assert data["success"] is False
    assert "was not found on GitHub" in data["error"]


@patch("requests.get")
def test_github_rate_limit_handled_gracefully(mock_get, client, app):
    """Test handling of GitHub API rate limit (HTTP 403 with X-RateLimit-Remaining: 0)."""
    user_id = create_and_login_user(client, app)
    port_id = create_test_portfolio(app, user_id)

    mock_resp = MagicMock()
    mock_resp.status_code = 403
    mock_resp.headers = {"X-RateLimit-Remaining": "0"}
    mock_resp.text = '{"message": "API rate limit exceeded for user"}'
    mock_get.return_value = mock_resp

    page = client.get("/github/import")
    csrf_token = extract_csrf_token(page)

    response = client.post(
        "/github/fetch",
        json={"username": "octocat", "portfolio_id": port_id},
        headers={"X-CSRFToken": csrf_token},
    )

    assert response.status_code == 429
    data = response.get_json()
    assert data["success"] is False
    assert "rate limit reached" in data["error"].lower()


@patch("requests.get")
def test_github_network_timeout_handled(mock_get, client, app):
    """Test safe handling when GitHub API connection times out."""
    user_id = create_and_login_user(client, app)
    port_id = create_test_portfolio(app, user_id)

    mock_get.side_effect = requests.exceptions.Timeout("Connection timed out")

    page = client.get("/github/import")
    csrf_token = extract_csrf_token(page)

    response = client.post(
        "/github/fetch",
        json={"username": "octocat", "portfolio_id": port_id},
        headers={"X-CSRFToken": csrf_token},
    )

    assert response.status_code == 504
    data = response.get_json()
    assert data["success"] is False
    assert "timed out" in data["error"].lower()


@patch("requests.get")
def test_empty_repository_list(mock_get, client, app):
    """Test user with 0 public repositories returns clean empty list."""
    user_id = create_and_login_user(client, app)
    port_id = create_test_portfolio(app, user_id)

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = []
    mock_get.return_value = mock_resp

    page = client.get("/github/import")
    csrf_token = extract_csrf_token(page)

    response = client.post(
        "/github/fetch",
        json={"username": "emptyuser", "portfolio_id": port_id},
        headers={"X-CSRFToken": csrf_token},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["total_count"] == 0
    assert data["repositories"] == []


@patch("app.ai.service.AIService.generate_github_repo_description")
def test_ai_description_generation_from_repo_metadata(mock_ai_gen, client, app):
    """Test AI project description generation endpoint for GitHub repository."""
    create_and_login_user(client, app)

    mock_ai_gen.return_value = (
        "AI Portfolio Generator is a full-stack Flask application that automates professional "
        "portfolio creation using generative AI.\n\n"
        "• Features end-to-end resume extraction, Gemini prompt structuring, and real-time showcase previews.\n"
        "• Verified Technologies: Python, Flask, Gemini AI."
    )

    page = client.get("/github/import")
    csrf_token = extract_csrf_token(page)

    response = client.post(
        "/github/generate-description",
        json={
            "name": "ai-portfolio-generator",
            "description": "Portfolio builder with Flask",
            "language": "Python",
            "topics": ["flask", "gemini-ai"],
        },
        headers={"X-CSRFToken": csrf_token},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert "AI Portfolio Generator is a full-stack" in data["generated_description"]
    assert "Verified Technologies: Python" in data["generated_description"]


@patch("app.ai.service.AIService.generate_github_repo_description")
def test_ai_generation_failure_handled(mock_ai_gen, client, app):
    """Test safe handling when Gemini AI service raises an AIServiceError."""
    create_and_login_user(client, app)

    mock_ai_gen.side_effect = AIServiceError("Gemini API key is not configured.")

    page = client.get("/github/import")
    csrf_token = extract_csrf_token(page)

    response = client.post(
        "/github/generate-description",
        json={
            "name": "ai-portfolio-generator",
            "description": "Portfolio builder",
            "language": "Python",
            "topics": [],
        },
        headers={"X-CSRFToken": csrf_token},
    )

    assert response.status_code == 500
    data = response.get_json()
    assert data["success"] is False
    assert "Gemini API key is not configured" in data["error"]


def test_cross_user_portfolio_isolation(client, app):
    """Ensure a user cannot fetch or import repositories into another user's portfolio."""
    # User A creates a portfolio
    with app.app_context():
        user_a = User(name="User A", email="a@example.com")
        user_a.set_password("Password123!")
        db.session.add(user_a)
        db.session.commit()

        port_a = Portfolio(
            user_id=user_a.id,
            title="User A's Portfolio",
            full_name="User A",
            headline="Engineer",
            about="About User A",
            email="a@example.com",
        )
        db.session.add(port_a)
        db.session.commit()
        port_a_id = port_a.id

    # User B logs in
    create_and_login_user(client, app, name="User B", email="b@example.com")

    page = client.get("/github/import")
    csrf_token = extract_csrf_token(page)

    # User B tries to fetch into User A's portfolio
    fetch_res = client.post(
        "/github/fetch",
        json={"username": "octocat", "portfolio_id": port_a_id},
        headers={"X-CSRFToken": csrf_token},
    )
    assert fetch_res.status_code == 404

    # User B tries to import into User A's portfolio
    import_res = client.post(
        "/github/import",
        json={
            "portfolio_id": port_a_id,
            "projects": [
                {
                    "title": "Tamper Project",
                    "github_url": "https://github.com/octocat/tamper",
                }
            ],
        },
        headers={"X-CSRFToken": csrf_token},
    )
    assert import_res.status_code == 404


def test_successful_project_import_and_persistence(client, app):
    """Test importing selected repositories persists them into the database."""
    user_id = create_and_login_user(client, app)
    port_id = create_test_portfolio(app, user_id, "Engineering Showcase")

    page = client.get("/github/import")
    csrf_token = extract_csrf_token(page)

    projects_payload = [
        {
            "title": "AI Portfolio Generator",
            "description": "Production-grade portfolio builder with Gemini 2.5",
            "technologies": "Python, Flask, Docker",
            "github_url": "https://github.com/octocat/ai-portfolio-generator",
            "live_url": "https://portfolio-ai.demo",
            "stars_count": 42,
            "forks_count": 8,
        },
        {
            "title": "Data Pipeline Tools",
            "description": "High performance ETL processing utilities",
            "technologies": "Go, Docker",
            "github_url": "https://github.com/octocat/data-pipeline-tools",
            "live_url": None,
            "stars_count": 15,
            "forks_count": 3,
        },
    ]

    response = client.post(
        "/github/import",
        json={"portfolio_id": port_id, "projects": projects_payload},
        headers={"X-CSRFToken": csrf_token},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["imported_count"] == 2

    # Verify in DB
    with app.app_context():
        portfolio = db.session.get(Portfolio, port_id)
        assert len(portfolio.projects) == 2
        p1 = portfolio.projects[1]  # Ordered by created_at desc
        assert p1.github_url == "https://github.com/octocat/ai-portfolio-generator"
        assert p1.stars_count == 42
        assert p1.import_source == "github"
        assert p1.live_url == "https://portfolio-ai.demo"

    # Verify rendering on preview page
    preview_res = client.get(f"/portfolios/{port_id}")
    assert preview_res.status_code == 200
    preview_html = preview_res.data.decode("utf-8")
    assert "AI Portfolio Generator" in preview_html
    assert "Data Pipeline Tools" in preview_html
    assert "42" in preview_html  # Stars


def test_duplicate_import_prevention_and_overwrite(client, app):
    """Test duplicate repository detection returns 409 conflict, and confirm_overwrite updates record."""
    user_id = create_and_login_user(client, app)
    port_id = create_test_portfolio(app, user_id)

    page = client.get("/github/import")
    csrf_token = extract_csrf_token(page)

    initial_project = [
        {
            "title": "AI Portfolio Generator",
            "description": "Initial description",
            "technologies": "Python",
            "github_url": "https://github.com/octocat/ai-portfolio-generator",
            "stars_count": 10,
        }
    ]

    # First import: should succeed
    res1 = client.post(
        "/github/import",
        json={"portfolio_id": port_id, "projects": initial_project, "confirm_overwrite": False},
        headers={"X-CSRFToken": csrf_token},
    )
    assert res1.status_code == 200

    # Second import without confirm_overwrite: should return 409 Conflict
    updated_project = [
        {
            "title": "AI Portfolio Generator",
            "description": "Updated new description with Gemini AI",
            "technologies": "Python, Flask, Google Gemini",
            "github_url": "https://github.com/octocat/ai-portfolio-generator",
            "stars_count": 99,
        }
    ]

    res2 = client.post(
        "/github/import",
        json={"portfolio_id": port_id, "projects": updated_project, "confirm_overwrite": False},
        headers={"X-CSRFToken": csrf_token},
    )
    assert res2.status_code == 409
    data2 = res2.get_json()
    assert data2["success"] is False
    assert data2["error"] == "conflict"
    assert "already exists in this portfolio" in data2["message"]

    # Third import with confirm_overwrite = True: should succeed and update
    res3 = client.post(
        "/github/import",
        json={"portfolio_id": port_id, "projects": updated_project, "confirm_overwrite": True},
        headers={"X-CSRFToken": csrf_token},
    )
    assert res3.status_code == 200
    data3 = res3.get_json()
    assert data3["success"] is True
    assert data3["updated_count"] == 1

    # Verify updated in database
    with app.app_context():
        portfolio = db.session.get(Portfolio, port_id)
        assert len(portfolio.projects) == 1
        assert portfolio.projects[0].description == "Updated new description with Gemini AI"
        assert portfolio.projects[0].stars_count == 99


def test_project_deletion_from_portfolio(client, app):
    """Test deleting an imported project from a portfolio."""
    user_id = create_and_login_user(client, app)
    port_id = create_test_portfolio(app, user_id)

    with app.app_context():
        project = Project(
            portfolio_id=port_id,
            title="Temp Project",
            description="Testing deletion",
            github_url="https://github.com/octocat/temp",
        )
        db.session.add(project)
        db.session.commit()
        project_id = project.id

    page = client.get(f"/portfolios/{port_id}")
    csrf_token = extract_csrf_token(page)

    # Delete project
    del_res = client.post(
        f"/portfolios/{port_id}/projects/{project_id}/delete",
        data={"csrf_token": csrf_token},
        follow_redirects=True,
    )
    assert del_res.status_code == 200
    assert "was removed from portfolio" in del_res.data.decode("utf-8")

    with app.app_context():
        assert db.session.get(Project, project_id) is None

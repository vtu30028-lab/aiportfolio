"""
PortfolioAI - Theme Builder & Live Customizer Test Suite
Tests theme rendering across all 4 themes, font families, layout variations,
section visibility controls, invalid preference rejection, and ownership isolation.
"""

import re
import json
import pytest
from app import create_app
from app.extensions import db
from app.models import User, Portfolio, Project


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
    """Extract CSRF token from HTML."""
    html = response.data.decode("utf-8")
    match = re.search(r'name=["\']csrf_token["\'][^>]*?value=["\']([^"\']+)["\']', html)
    if not match:
        match = re.search(r'content=["\']([^"\']+)["\'][^>]*?name=["\']csrf-token["\']', html)
    if not match:
        match = re.search(r'name=["\']csrf-token["\'][^>]*?content=["\']([^"\']+)["\']', html)
    assert match is not None, "CSRF token not found in response HTML."
    return match.group(1)


def create_and_login_user(client, app, name="Theme Designer", email="designer@example.com"):
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


def create_populated_portfolio(app, user_id):
    """Create a fully populated portfolio with all sections."""
    with app.app_context():
        portfolio = Portfolio(
            user_id=user_id,
            title="Senior Engineer Showcase",
            full_name="Alex Mercer",
            headline="Principal Distributed Systems Architect",
            about="Building resilient cloud architectures with 8+ years of production experience.",
            email="alex.mercer@example.com",
            phone="+1-555-0199",
            location="Seattle, WA",
            github_url="https://github.com/alexmercer",
            linkedin_url="https://linkedin.com/in/alexmercer",
            skills="Python, Go, Kubernetes, Terraform, PostgreSQL, Distributed Systems",
            experience=json.dumps([
                {
                    "role": "Staff Cloud Architect",
                    "company": "Enterprise Cloud Corp",
                    "duration": "2022 - Present",
                    "description": "Architected low-latency microservices handling 50k QPS.",
                }
            ]),
            education=json.dumps([
                {
                    "degree": "B.S. in Computer Science",
                    "institution": "University of Washington",
                    "year": "2018",
                    "details": "Summa Cum Laude, Honors in Systems Architecture.",
                }
            ]),
            certifications=json.dumps([
                {
                    "name": "AWS Certified Solutions Architect - Professional",
                    "issuer": "Amazon Web Services",
                    "year": "2024",
                }
            ]),
            theme="modern-dark",
            accent_color="#6366f1",
            font_family="plus-jakarta-sans",
            layout_style="standard",
        )
        db.session.add(portfolio)
        db.session.commit()

        # Add a sample project
        proj = Project(
            portfolio_id=portfolio.id,
            title="Raft Consensus Engine",
            description="High throughput distributed consensus implementation in Go.",
            technologies="Go, gRPC, Docker",
            github_url="https://github.com/alexmercer/raft-engine",
            stars_count=84,
            forks_count=12,
        )
        db.session.add(proj)
        db.session.commit()

        return portfolio.id


def test_theme_editor_page_loads_authenticated(client, app):
    """Verify Theme Studio loads with all presets, controls, and active portfolio data."""
    user_id = create_and_login_user(client, app)
    port_id = create_populated_portfolio(app, user_id)

    response = client.get(f"/portfolios/{port_id}/theme")
    assert response.status_code == 200
    html = response.data.decode("utf-8")
    assert "Theme Builder" in html
    assert "Dark Developer" in html
    assert "Minimal Pro" in html
    assert "Glassmorphism" in html
    assert "AI Futuristic" in html
    assert "Creative Colorful" in html
    assert "Premium Elegant" in html
    assert "Terminal Hacker" in html
    assert "Student Starter" in html
    assert "Senior Engineer Showcase" in html


def test_unauthenticated_theme_routes_redirect(client):
    """Verify unauthenticated requests to theme studio, live preview, and save are blocked."""
    login_page = client.get("/login")
    csrf_token = extract_csrf_token(login_page)

    # GET theme editor
    res1 = client.get("/portfolios/1/theme")
    assert res1.status_code == 302
    assert "/login" in res1.headers["Location"]

    # GET live portfolio
    res2 = client.get("/portfolios/1/live")
    assert res2.status_code == 302
    assert "/login" in res2.headers["Location"]

    # POST save theme
    res3 = client.post(
        "/portfolios/1/theme",
        json={"theme": "modern-dark"},
        headers={"X-CSRFToken": csrf_token},
    )
    assert res3.status_code == 302
    assert "/login" in res3.headers["Location"]


def test_cross_user_theme_isolation(client, app):
    """Ensure User B cannot view or modify User A's theme configurations."""
    # User A creates a portfolio
    with app.app_context():
        user_a = User(name="User A", email="a@example.com")
        user_a.set_password("Password123!")
        db.session.add(user_a)
        db.session.commit()
        port_a_id = create_populated_portfolio(app, user_a.id)

    # User B logs in
    create_and_login_user(client, app, name="User B", email="b@example.com")

    token = extract_csrf_token(client.get("/portfolios"))

    # User B attempts to access User A's theme editor -> 404
    get_res = client.get(f"/portfolios/{port_a_id}/theme")
    assert get_res.status_code == 404

    # User B attempts to access User A's live themed preview -> 404
    live_res = client.get(f"/portfolios/{port_a_id}/live")
    assert live_res.status_code == 404

    # User B attempts to save theme to User A's portfolio -> 404
    post_res = client.post(
        f"/portfolios/{port_a_id}/theme",
        json={"theme": "minimal-light"},
        headers={"X-CSRFToken": token},
    )
    assert post_res.status_code == 404


def test_all_eight_themes_render_successfully(client, app):
    """Test all 8 themes render valid HTML with the user's authentic portfolio data."""
    user_id = create_and_login_user(client, app)
    port_id = create_populated_portfolio(app, user_id)

    themes = [
        "modern-dark",
        "minimal-light",
        "creative-gradient",
        "professional-blue",
        "creative-colorful",
        "premium-elegant",
        "terminal-hacker",
        "student-starter",
    ]

    for theme_name in themes:
        res = client.get(f"/portfolios/{port_id}/live?theme={theme_name}")
        assert res.status_code == 200, f"Theme '{theme_name}' returned {res.status_code}"
        html = res.data.decode("utf-8")

        # Must include theme CSS class
        assert f"theme-{theme_name}" in html, f"CSS class 'theme-{theme_name}' not found"

        # Must render real user content
        assert "Alex Mercer" in html
        assert "Principal Distributed Systems Architect" in html
        assert "Raft Consensus Engine" in html
        assert "alex.mercer@example.com" in html


def test_hide_optional_sections_when_no_data(client, app):
    """Test optional sections are completely hidden when no data exists (zero dummy data)."""
    user_id = create_and_login_user(client, app)

    # Minimal portfolio with only essential info, NO skills, NO projects, NO experience, NO education
    with app.app_context():
        portfolio = Portfolio(
            user_id=user_id,
            title="Minimalist Dev",
            full_name="Taylor Swift",
            headline="Junior Developer",
            about="Passionate newcomer to full stack development.",
            email="taylor@example.com",
            # skills, experience, education, certifications left None
        )
        db.session.add(portfolio)
        db.session.commit()
        min_port_id = portfolio.id

    res = client.get(f"/portfolios/{min_port_id}/live")
    assert res.status_code == 200
    html = res.data.decode("utf-8")

    # Essential sections rendered
    assert "Taylor Swift" in html
    assert "Passionate newcomer to full stack development." in html

    # Empty sections MUST NOT be rendered
    assert 'id="section-skills"' not in html
    assert 'id="section-projects"' not in html
    assert 'id="section-experience"' not in html
    assert 'id="section-education"' not in html
    assert 'id="section-certifications"' not in html


def test_save_valid_theme_preferences(client, app):
    """Test saving valid theme, accent color, font family, and layout variations."""
    user_id = create_and_login_user(client, app)
    port_id = create_populated_portfolio(app, user_id)

    page = client.get(f"/portfolios/{port_id}/theme")
    csrf_token = extract_csrf_token(page)

    payload = {
        "theme": "creative-gradient",
        "accent_color": "#f43f5e",
        "font_family": "outfit",
        "layout_style": "compact",
        "visible_sections": {
            "about": True,
            "skills": False,  # Toggled off
            "projects": True,
            "experience": True,
            "education": True,
            "certifications": False,
            "contact": True,
        },
    }

    response = client.post(
        f"/portfolios/{port_id}/theme",
        json=payload,
        headers={"X-CSRFToken": csrf_token},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert "saved successfully" in data["message"].lower()

    # Verify updated in database
    with app.app_context():
        port = db.session.get(Portfolio, port_id)
        assert port.theme == "creative-gradient"
        assert port.accent_color == "#f43f5e"
        assert port.font_family == "outfit"
        assert port.layout_style == "compact"
        visibility = port.get_section_visibility()
        assert visibility["skills"] is False
        assert visibility["certifications"] is False
        assert visibility["about"] is True


def test_invalid_theme_preferences_rejected(client, app):
    """Test validation rejects invalid themes, colors, fonts, and layouts with HTTP 400."""
    user_id = create_and_login_user(client, app)
    port_id = create_populated_portfolio(app, user_id)

    page = client.get(f"/portfolios/{port_id}/theme")
    csrf_token = extract_csrf_token(page)

    # 1. Invalid theme name
    res1 = client.post(
        f"/portfolios/{port_id}/theme",
        json={"theme": "hacker-matrix-green"},
        headers={"X-CSRFToken": csrf_token},
    )
    assert res1.status_code == 400
    assert "Invalid theme" in res1.get_json()["error"]

    # 2. Invalid accent color
    res2 = client.post(
        f"/portfolios/{port_id}/theme",
        json={"accent_color": "not-a-valid-hex"},
        headers={"X-CSRFToken": csrf_token},
    )
    assert res2.status_code == 400
    assert "Invalid accent color" in res2.get_json()["error"]

    # 3. Invalid font family
    res3 = client.post(
        f"/portfolios/{port_id}/theme",
        json={"font_family": "comic-sans-ms"},
        headers={"X-CSRFToken": csrf_token},
    )
    assert res3.status_code == 400
    assert "Invalid font family" in res3.get_json()["error"]

    # 4. Invalid layout style
    res4 = client.post(
        f"/portfolios/{port_id}/theme",
        json={"layout_style": "circular-wheel"},
        headers={"X-CSRFToken": csrf_token},
    )
    assert res4.status_code == 400
    assert "Invalid layout style" in res4.get_json()["error"]


def test_reset_theme_preferences(client, app):
    """Test resetting theme preferences back to default values."""
    user_id = create_and_login_user(client, app)
    port_id = create_populated_portfolio(app, user_id)

    page = client.get(f"/portfolios/{port_id}/theme")
    csrf_token = extract_csrf_token(page)

    # Change settings first
    client.post(
        f"/portfolios/{port_id}/theme",
        json={"theme": "minimal-light", "accent_color": "#10b981"},
        headers={"X-CSRFToken": csrf_token},
    )

    # Trigger reset
    res = client.post(
        f"/portfolios/{port_id}/theme/reset",
        headers={"X-CSRFToken": csrf_token},
    )
    assert res.status_code == 200

    # Verify back to default in database
    with app.app_context():
        port = db.session.get(Portfolio, port_id)
        assert port.theme == "modern-dark"
        assert port.accent_color == "#6366f1"
        assert port.font_family == "plus-jakarta-sans"
        assert port.layout_style == "standard"


def test_live_preview_query_overrides(client, app):
    """Test query parameter overrides allow instant previewing without persisting changes."""
    user_id = create_and_login_user(client, app)
    port_id = create_populated_portfolio(app, user_id)

    response = client.get(f"/portfolios/{port_id}/live?theme=professional-blue&accent=%2310b981&font=mono&layout=sidebar")
    assert response.status_code == 200
    html = response.data.decode("utf-8")

    assert "theme-professional-blue" in html
    assert "--theme-accent: #10b981" in html
    assert "font-mono" in html
    assert "layout-sidebar" in html

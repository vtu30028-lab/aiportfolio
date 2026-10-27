"""
PortfolioAI - PDF Export & QR Code Generator Test Suite
Tests publication-quality PDF generation, ReportLab flowable compilation,
PNG QR code generation for published portfolios, privacy guardrails,
public URL routing, and cross-user ownership isolation.
"""

import io
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


def create_and_login_user(client, app, name="Export Specialist", email="export@example.com"):
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


def create_full_portfolio(app, user_id, title="Senior Architect Portfolio"):
    """Create a populated portfolio with projects, experience, and education."""
    with app.app_context():
        portfolio = Portfolio(
            user_id=user_id,
            title=title,
            full_name="Elena Rostova",
            headline="Lead Cloud & AI Solutions Architect",
            about="Passionate software architect with a decade of distributed systems engineering.",
            email="elena.rostova@example.com",
            phone="+1-555-8822",
            location="San Francisco, CA",
            github_url="https://github.com/elena-rostova",
            linkedin_url="https://linkedin.com/in/elena-rostova",
            skills="Python, Go, Kubernetes, Kafka, PyTorch, PostgreSQL, AWS",
            experience=json.dumps([
                {
                    "role": "Principal Systems Architect",
                    "company": "NextGen AI Corp",
                    "duration": "2021 - Present",
                    "description": "Led architecture for large-scale GPU inference cluster serving millions of users.",
                }
            ]),
            education=json.dumps([
                {
                    "degree": "M.S. in Computer Science",
                    "institution": "Stanford University",
                    "year": "2019",
                    "details": "Specialization in Artificial Intelligence and Distributed Networks.",
                }
            ]),
            certifications=json.dumps([
                {
                    "name": "AWS Certified DevOps Engineer - Professional",
                    "issuer": "Amazon Web Services",
                    "year": "2023",
                }
            ]),
            accent_color="#0ea5e9",
        )
        db.session.add(portfolio)
        db.session.commit()

        # Add project
        proj = Project(
            portfolio_id=portfolio.id,
            title="Real-Time Streaming Engine",
            description="Event-driven stream processing pipeline processing 100k events/sec.",
            technologies="Python, Kafka, Redis",
            github_url="https://github.com/elena-rostova/streaming-engine",
            live_url="https://stream.elena-demo.com",
            stars_count=120,
            forks_count=25,
        )
        db.session.add(proj)
        db.session.commit()

        return portfolio.id


def test_valid_pdf_export_headers_and_bytes(client, app):
    """Test generating a downloadable PDF returns HTTP 200, PDF headers, and %PDF- bytes."""
    user_id = create_and_login_user(client, app)
    port_id = create_full_portfolio(app, user_id)

    response = client.get(f"/portfolios/{port_id}/export/pdf")
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/pdf"
    assert "attachment" in response.headers["Content-Disposition"]
    assert "Elena_Rostova_portfolio.pdf" in response.headers["Content-Disposition"]

    # PDF binary signature check (%PDF-)
    data = response.data
    assert data.startswith(b"%PDF-")
    assert len(data) > 1000  # Non-trivial document size


def test_pdf_export_minimal_portfolio_omits_empty_sections(client, app):
    """Test PDF generation for a minimal portfolio gracefully omits non-existent sections."""
    user_id = create_and_login_user(client, app)

    with app.app_context():
        min_portfolio = Portfolio(
            user_id=user_id,
            title="Bare Minimum Dev",
            full_name="Sam Fisher",
            headline="Junior Web Developer",
            about="Starting my software journey.",
            email="sam@example.com",
            # skills, projects, experience, education, certifications are all None
        )
        db.session.add(min_portfolio)
        db.session.commit()
        min_id = min_portfolio.id

    response = client.get(f"/portfolios/{min_id}/export/pdf")
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/pdf"
    assert response.data.startswith(b"%PDF-")


def test_unauthenticated_export_and_qr_redirects(client):
    """Ensure unauthenticated requests to export, qr, and publish routes redirect to login."""
    login_page = client.get("/login")
    csrf_token = extract_csrf_token(login_page)

    # PDF export
    res1 = client.get("/portfolios/1/export/pdf")
    assert res1.status_code == 302
    assert "/login" in res1.headers["Location"]

    # QR code
    res2 = client.get("/portfolios/1/qr")
    assert res2.status_code == 302
    assert "/login" in res2.headers["Location"]

    # Publish toggle
    res3 = client.post(
        "/portfolios/1/publish",
        data={"csrf_token": csrf_token},
    )
    assert res3.status_code == 302
    assert "/login" in res3.headers["Location"]


def test_cross_user_export_and_qr_isolation(client, app):
    """Ensure a user cannot export or generate QR codes for another user's portfolio."""
    # User A creates a portfolio
    with app.app_context():
        user_a = User(name="User A", email="a@example.com")
        user_a.set_password("Password123!")
        db.session.add(user_a)
        db.session.commit()
        port_a_id = create_full_portfolio(app, user_a.id)

    # User B logs in
    create_and_login_user(client, app, name="User B", email="b@example.com")
    csrf_token = extract_csrf_token(client.get("/portfolios"))

    # User B tries to export User A's PDF -> 404
    pdf_res = client.get(f"/portfolios/{port_a_id}/export/pdf")
    assert pdf_res.status_code == 404

    # User B tries to access User A's QR code -> 404
    qr_res = client.get(f"/portfolios/{port_a_id}/qr")
    assert qr_res.status_code == 404

    # User B tries to publish User A's portfolio -> 404
    pub_res = client.post(
        f"/portfolios/{port_a_id}/publish",
        headers={"X-CSRFToken": csrf_token},
    )
    assert pub_res.status_code == 404


def test_qr_code_blocked_for_unpublished_draft(client, app):
    """Test QR code route returns HTTP 400 when portfolio is in private draft state."""
    user_id = create_and_login_user(client, app)
    port_id = create_full_portfolio(app, user_id)

    # Ensure unpublished
    with app.app_context():
        port = db.session.get(Portfolio, port_id)
        port.is_published = False
        db.session.commit()

    # Request with JSON accept header
    response = client.get(
        f"/portfolios/{port_id}/qr",
        headers={"Accept": "application/json"},
    )
    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False
    assert "must be published before generating a public QR code" in data["error"]


def test_qr_code_generation_for_published_portfolio(client, app):
    """Test QR code generation for a published portfolio returns valid PNG image."""
    user_id = create_and_login_user(client, app)
    port_id = create_full_portfolio(app, user_id)

    # Publish portfolio
    with app.app_context():
        port = db.session.get(Portfolio, port_id)
        port.is_published = True
        port.ensure_slug()
        db.session.commit()
        slug = port.slug

    # Inline QR view
    response = client.get(f"/portfolios/{port_id}/qr")
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "image/png"
    assert response.data.startswith(b"\x89PNG\r\n\x1a\n")

    # Download QR view (?download=1)
    dl_response = client.get(f"/portfolios/{port_id}/qr?download=1")
    assert dl_response.status_code == 200
    assert dl_response.headers["Content-Type"] == "image/png"
    assert "attachment" in dl_response.headers["Content-Disposition"]
    assert f"{slug}_qr.png" in dl_response.headers["Content-Disposition"]


def test_portfolio_publish_toggle_and_slug_generation(client, app):
    """Test publishing portfolio generates a unique slug and toggles state."""
    user_id = create_and_login_user(client, app)
    port_id = create_full_portfolio(app, user_id)

    token = extract_csrf_token(client.get("/portfolios"))

    # Publish
    res = client.post(
        f"/portfolios/{port_id}/publish",
        json={"publish": True},
        headers={"X-CSRFToken": token},
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["is_published"] is True
    assert "elena-rostova-" in data["slug"]
    assert f"/p/{data['slug']}" in data["public_url"]

    # Verify in DB
    with app.app_context():
        port = db.session.get(Portfolio, port_id)
        assert port.is_published is True
        assert port.slug == data["slug"]

    # Unpublish
    res2 = client.post(
        f"/portfolios/{port_id}/publish",
        json={"publish": False},
        headers={"X-CSRFToken": token},
    )
    assert res2.status_code == 200
    data2 = res2.get_json()
    assert data2["is_published"] is False

    with app.app_context():
        port = db.session.get(Portfolio, port_id)
        assert port.is_published is False


def test_public_portfolio_route_access(client, app):
    """Test public portfolio URL /p/<slug> is accessible without authentication when published."""
    # Create published portfolio
    with app.app_context():
        user = User(name="Public Author", email="author@example.com")
        user.set_password("Password123!")
        db.session.add(user)
        db.session.commit()

        port = Portfolio(
            user_id=user.id,
            title="Public Engineering Portfolio",
            full_name="Marcus Vance",
            headline="Cloud Platform Engineer",
            about="Designing automated CI/CD and platform tools.",
            email="marcus@example.com",
            is_published=True,
            slug="marcus-vance-cloud",
        )
        db.session.add(port)
        db.session.commit()

    # Unauthenticated visitor accesses public portfolio
    public_res = client.get("/p/marcus-vance-cloud")
    assert public_res.status_code == 200
    html = public_res.data.decode("utf-8")
    assert "Marcus Vance" in html
    assert "Cloud Platform Engineer" in html

    # Non-existent slug returns 404
    assert client.get("/p/non-existent-slug-xyz").status_code == 404

    # Unpublished portfolio slug returns 404
    with app.app_context():
        p = Portfolio.query.filter_by(slug="marcus-vance-cloud").first()
        p.is_published = False
        db.session.commit()

    assert client.get("/p/marcus-vance-cloud").status_code == 404


def test_custom_production_base_url_configuration(app):
    """Test PUBLIC_BASE_URL configuration is respected in get_public_url."""
    app.config["PUBLIC_BASE_URL"] = "https://portfolio-ai.onrender.com"

    with app.app_context():
        port = Portfolio(
            user_id=1,
            title="Render App",
            full_name="Render User",
            headline="Cloud Dev",
            about="About me",
            email="user@example.com",
            is_published=True,
            slug="render-user-abc123",
        )
        pub_url = port.get_public_url()
        assert pub_url == "https://portfolio-ai.onrender.com/p/render-user-abc123"

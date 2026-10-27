"""
PortfolioAI - Resume Parsing Test Suite
Validates PDF upload filtering, pypdf text layer extraction, Gemini structured parsing,
scanned/encrypted/oversized PDF rejection, human-in-the-loop import, and portfolio ownership.
"""

import io
import re
from unittest.mock import patch
import pytest
from reportlab.pdfgen import canvas
from app import create_app
from app.extensions import db
from app.models import User, Portfolio
from app.resume.parser import ResumeParser, InvalidPDFError, EmptyPDFError
from app.ai.service import AIService, AIServiceError


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
    """Helper to extract CSRF token from rendered HTML forms or meta tags."""
    html = response.data.decode("utf-8")
    match = re.search(r'<meta name="csrf-token" content="([^"]+)"', html)
    if not match:
        match = re.search(r'name=["\']csrf_token["\'][^>]*?value=["\']([^"\']+)["\']', html)
    if not match:
        match = re.search(r'value=["\']([^"\']+)["\'][^>]*?name=["\']csrf_token["\']', html)
    assert match is not None, "CSRF token not found in response HTML."
    return match.group(1)


def create_and_login_user(client, app, name="Resume Tester", email="resume.test@test.com"):
    """Helper to create and authenticate a user in the test client."""
    with app.app_context():
        user = User(name=name, email=email)
        user.set_password("SecurePassword123!")
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    token = extract_csrf_token(client.get("/login"))
    client.post(
        "/login",
        data={
            "csrf_token": token,
            "email": email,
            "password": "SecurePassword123!",
        },
        follow_redirects=True,
    )
    return user_id


def generate_valid_pdf_bytes(name="Alex Rivera", headline="Senior Python Developer"):
    """Generate a real valid PDF in memory using ReportLab."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(100, 750, f"Full Name: {name}")
    c.drawString(100, 730, f"Headline: {headline}")
    c.drawString(100, 710, "Email: alex.rivera@example.com")
    c.drawString(100, 690, "Phone: +1-555-0199 | Location: San Francisco, CA")
    c.drawString(100, 670, "Skills: Python, Flask, Docker, PostgreSQL, React, AWS")
    c.drawString(100, 650, "Education: B.S. in Computer Science, University of California, 2024")
    c.drawString(100, 630, "Project: Cloud-Native Portfolio Engine using Gemini API")
    c.save()
    buf.seek(0)
    return buf


def generate_empty_pdf_bytes():
    """Generate an empty PDF page with no text (simulates scanned photo/blank)."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.showPage()
    c.save()
    buf.seek(0)
    return buf


# 1. Valid PDF file parsing
@patch.object(AIService, "_execute_prompt")
def test_valid_pdf_resume_parsing(mock_execute, client, app):
    """Test uploading and parsing a valid PDF with mocked Gemini AI structuring."""
    mock_execute.return_value = """
    {
      "full_name": "Alex Rivera",
      "email": "alex.rivera@example.com",
      "phone": "+1-555-0199",
      "location": "San Francisco, CA",
      "headline": "Senior Full-Stack & AI Systems Engineer",
      "summary": "Experienced engineer specializing in cloud-native microservices.",
      "technical_skills": ["Python", "Flask", "Docker", "PostgreSQL"],
      "soft_skills": ["System Design", "Agile"],
      "education": [{"institution": "UC Berkeley", "degree": "B.S. Computer Science", "year": "2024"}],
      "projects": [{"title": "PortfolioAI", "technologies": "Python, Flask"}],
      "experience": [{"company": "Tech Corp", "role": "Software Engineer"}],
      "certifications": [],
      "github_url": "https://github.com/alexrivera",
      "linkedin_url": "https://linkedin.com/in/alexrivera"
    }
    """
    create_and_login_user(client, app)
    csrf_token = extract_csrf_token(client.get("/resume/upload"))

    pdf_stream = generate_valid_pdf_bytes()
    data = {
        "resume": (pdf_stream, "resume.pdf", "application/pdf"),
    }

    response = client.post(
        "/resume/parse",
        headers={"X-CSRFToken": csrf_token},
        data=data,
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    res_json = response.get_json()
    assert res_json["success"] is True
    assert res_json["data"]["full_name"] == "Alex Rivera"
    assert res_json["data"]["email"] == "alex.rivera@example.com"
    assert "Python" in res_json["data"]["technical_skills"]


# 2. Invalid file type rejection
def test_invalid_file_extension_rejected(client, app):
    """Verify that uploading non-PDF files (.txt, .png) is rejected with 400 Bad Request."""
    create_and_login_user(client, app)
    csrf_token = extract_csrf_token(client.get("/resume/upload"))

    fake_text_file = io.BytesIO(b"This is not a PDF file.")
    data = {
        "resume": (fake_text_file, "resume.txt", "text/plain"),
    }

    response = client.post(
        "/resume/parse",
        headers={"X-CSRFToken": csrf_token},
        data=data,
        content_type="multipart/form-data",
    )
    assert response.status_code == 400
    assert "Only PDF" in response.get_json()["error"]


# 3. Invalid PDF header (fake extension)
def test_fake_pdf_header_rejected(client, app):
    """Verify that a non-PDF file renamed with a .pdf extension is rejected by magic byte check."""
    create_and_login_user(client, app)
    csrf_token = extract_csrf_token(client.get("/resume/upload"))

    fake_pdf = io.BytesIO(b"Fake content not starting with %PDF-")
    data = {
        "resume": (fake_pdf, "fake.pdf", "application/pdf"),
    }

    response = client.post(
        "/resume/parse",
        headers={"X-CSRFToken": csrf_token},
        data=data,
        content_type="multipart/form-data",
    )
    assert response.status_code == 400
    assert "%PDF-" in response.get_json()["error"] or "Invalid" in response.get_json()["error"]


# 4. Oversized file rejection (> 5MB)
def test_oversized_pdf_rejected(client, app):
    """Verify that files exceeding the 5MB upload limit are rejected."""
    create_and_login_user(client, app)
    csrf_token = extract_csrf_token(client.get("/resume/upload"))

    # 6MB mock payload starting with valid %PDF- magic header
    oversized = io.BytesIO(b"%PDF-1.4 " + (b"0" * (6 * 1024 * 1024)))
    data = {
        "resume": (oversized, "huge.pdf", "application/pdf"),
    }

    response = client.post(
        "/resume/parse",
        headers={"X-CSRFToken": csrf_token},
        data=data,
        content_type="multipart/form-data",
    )
    assert response.status_code in (400, 413)
    if response.status_code == 400:
        assert "5MB" in response.get_json()["error"]


# 5. Empty or scanned image-only PDF rejection
def test_empty_or_scanned_pdf_rejected(client, app):
    """Verify that blank or scanned PDFs lacking a text layer return an informative OCR error."""
    create_and_login_user(client, app)
    csrf_token = extract_csrf_token(client.get("/resume/upload"))

    empty_pdf = generate_empty_pdf_bytes()
    data = {
        "resume": (empty_pdf, "scanned.pdf", "application/pdf"),
    }

    response = client.post(
        "/resume/parse",
        headers={"X-CSRFToken": csrf_token},
        data=data,
        content_type="multipart/form-data",
    )
    assert response.status_code == 400
    assert "OCR" in response.get_json()["error"]


# 6. AI service errors during parsing
@patch.object(AIService, "_execute_prompt")
def test_ai_failure_handled_gracefully(mock_execute, client, app):
    """Test that Gemini API errors during resume structuring return a clean 503."""
    mock_execute.side_effect = AIServiceError("Gemini AI quota reached.")
    create_and_login_user(client, app)
    csrf_token = extract_csrf_token(client.get("/resume/upload"))

    pdf_stream = generate_valid_pdf_bytes()
    data = {"resume": (pdf_stream, "resume.pdf", "application/pdf")}

    response = client.post(
        "/resume/parse",
        headers={"X-CSRFToken": csrf_token},
        data=data,
        content_type="multipart/form-data",
    )
    assert response.status_code == 503
    assert "quota reached" in response.get_json()["error"]


# 7. Authentication requirements
def test_unauthenticated_resume_routes_blocked(client):
    """Verify that unauthenticated users cannot access resume routes."""
    # GET upload page
    get_res = client.get("/resume/upload", follow_redirects=False)
    assert get_res.status_code == 302
    assert "/login" in get_res.headers["Location"]

    # POST parse
    csrf_token = extract_csrf_token(client.get("/login"))
    post_res = client.post(
        "/resume/parse",
        headers={"X-CSRFToken": csrf_token},
        data={"resume": (generate_valid_pdf_bytes(), "resume.pdf", "application/pdf")},
        content_type="multipart/form-data",
        follow_redirects=False,
    )
    assert post_res.status_code in (302, 401)


# 8. Importing approved data into a NEW portfolio
def test_import_to_new_portfolio(client, app):
    """Test that reviewed resume data can be used to generate a new portfolio."""
    user_id = create_and_login_user(client, app, name="New Portfolio User", email="newp@test.com")
    csrf_token = extract_csrf_token(client.get("/resume/upload"))

    approved_data = {
        "full_name": "Elena Rostova",
        "email": "elena.rostova@test.com",
        "phone": "+1-555-8822",
        "location": "Boston, MA",
        "headline": "Lead Machine Learning Researcher",
        "about": "Specializing in deep learning interpretability.",
        "github_url": "https://github.com/erostova",
    }

    response = client.post(
        "/resume/import-portfolio",
        headers={"X-CSRFToken": csrf_token, "Content-Type": "application/json"},
        json={
            "create_new": True,
            "new_portfolio_title": "Elena's ML Portfolio",
            "approved_data": approved_data,
        },
    )
    assert response.status_code == 200
    res_json = response.get_json()
    assert res_json["success"] is True

    with app.app_context():
        p = db.session.get(Portfolio, res_json["portfolio_id"])
        assert p is not None
        assert p.user_id == user_id
        assert p.title == "Elena's ML Portfolio"
        assert p.full_name == "Elena Rostova"
        assert p.location == "Boston, MA"


# 9. Overwrite confirmation enforcement on EXISTING portfolio
def test_overwrite_confirmation_on_existing_portfolio(client, app):
    """Test that importing into an existing portfolio requires explicit overwrite confirmation."""
    user_id = create_and_login_user(client, app, name="Existing User", email="exist@test.com")

    with app.app_context():
        p = Portfolio(
            user_id=user_id,
            title="My Original Portfolio",
            full_name="Original Name",
            headline="Original Headline",
            about="Original bio.",
            email="exist@test.com",
        )
        db.session.add(p)
        db.session.commit()
        portfolio_id = p.id

    csrf_token = extract_csrf_token(client.get("/resume/upload"))
    approved_data = {
        "full_name": "Updated Name",
        "headline": "Updated Headline",
        "about": "Updated bio.",
        "email": "exist@test.com",
    }

    # First attempt: without overwrite=True -> Expect HTTP 409
    res_no_confirm = client.post(
        "/resume/import-portfolio",
        headers={"X-CSRFToken": csrf_token, "Content-Type": "application/json"},
        json={
            "create_new": False,
            "portfolio_id": portfolio_id,
            "overwrite": False,
            "approved_data": approved_data,
        },
    )
    assert res_no_confirm.status_code == 409
    assert res_no_confirm.get_json()["require_confirmation"] is True

    # Second attempt: with overwrite=True -> Expect HTTP 200
    res_confirmed = client.post(
        "/resume/import-portfolio",
        headers={"X-CSRFToken": csrf_token, "Content-Type": "application/json"},
        json={
            "create_new": False,
            "portfolio_id": portfolio_id,
            "overwrite": True,
            "approved_data": approved_data,
        },
    )
    assert res_confirmed.status_code == 200
    assert res_confirmed.get_json()["success"] is True

    with app.app_context():
        updated = db.session.get(Portfolio, portfolio_id)
        assert updated.full_name == "Updated Name"
        assert updated.headline == "Updated Headline"


# 10. Portfolio ownership protection on import
def test_prevent_import_into_another_users_portfolio(client, app):
    """Verify that User B cannot import resume data into User A's portfolio (HTTP 404)."""
    with app.app_context():
        user_a = User(name="User A", email="usera.res@test.com")
        user_a.set_password("Pass123!")
        db.session.add(user_a)
        db.session.commit()

        p_a = Portfolio(
            user_id=user_a.id,
            title="User A's Protected Portfolio",
            full_name="User A",
            headline="Headline A",
            about="Bio A.",
            email="usera.res@test.com",
        )
        db.session.add(p_a)
        db.session.commit()
        portfolio_a_id = p_a.id

    # Log in as User B
    create_and_login_user(client, app, name="User B", email="userb.res@test.com")
    csrf_token = extract_csrf_token(client.get("/resume/upload"))

    res_hack = client.post(
        "/resume/import-portfolio",
        headers={"X-CSRFToken": csrf_token, "Content-Type": "application/json"},
        json={
            "create_new": False,
            "portfolio_id": portfolio_a_id,
            "overwrite": True,
            "approved_data": {
                "full_name": "Hacker",
                "email": "hacker@test.com",
                "headline": "Hacked",
                "about": "Hacked",
            },
        },
    )
    assert res_hack.status_code == 404

    with app.app_context():
        p_check = db.session.get(Portfolio, portfolio_a_id)
        assert p_check.full_name == "User A"
        assert p_check.headline == "Headline A"

"""
PortfolioAI - Resume Parsing Blueprint Routes
Provides endpoints for PDF resume upload, AI-driven structured extraction,
human-in-the-loop review, and transactional portfolio import.
"""

import io
import json
from flask import render_template, request, jsonify, abort
from flask_login import login_required, current_user
from app.extensions import db, limiter
from app.models import Portfolio, Project
from app.resume import resume_bp
from app.resume.parser import (
    ResumeParser,
    ResumeParserError,
    InvalidPDFError,
    EncryptedPDFError,
    EmptyPDFError,
)
from app.ai.service import AIServiceError


@resume_bp.route("/")
@resume_bp.route("/upload")
@login_required
def upload_page():
    """Render the resume upload and interactive review page."""
    portfolios = (
        Portfolio.query.filter_by(user_id=current_user.id)
        .order_by(Portfolio.updated_at.desc())
        .all()
    )
    return render_template("resume_upload.html", portfolios=portfolios)


@resume_bp.route("/parse", methods=["POST"])
@login_required
@limiter.limit("15 per minute")
def parse_resume():
    """
    Handle uploaded PDF resume: validate size & headers, extract text via pypdf,
    and convert to structured JSON using Gemini AI.
    """
    if "resume" not in request.files:
        return jsonify({"success": False, "error": "No resume file was uploaded."}), 400

    file = request.files["resume"]
    filename = file.filename or ""

    if not filename.lower().endswith(".pdf"):
        return jsonify({"success": False, "error": "Invalid file type. Only PDF (.pdf) documents are accepted."}), 400

    # Read file stream into memory
    file_bytes = file.read()
    file_stream = io.BytesIO(file_bytes)

    try:
        # 1. Text extraction & PDF validation
        raw_text, page_count = ResumeParser.validate_and_extract_text(file_stream, filename)

        # 2. AI Structured Extraction
        parsed_data = ResumeParser.parse_with_ai(raw_text)

        return jsonify({
            "success": True,
            "data": parsed_data,
            "page_count": page_count,
            "filename": filename,
        }), 200

    except (InvalidPDFError, EncryptedPDFError, EmptyPDFError) as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except ResumeParserError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except AIServiceError as e:
        return jsonify({"success": False, "error": str(e)}), 503
    except Exception:
        return jsonify({"success": False, "error": "An unexpected error occurred while processing your resume."}), 500
    finally:
        file_stream.close()


@resume_bp.route("/import-portfolio", methods=["POST"])
@login_required
def import_to_portfolio():
    """
    Import human-reviewed resume fields into an existing or newly created portfolio.
    Enforces strict user ownership checks and explicit overwrite approvals.
    """
    data = request.get_json(silent=True) or request.form
    approved = data.get("approved_data", {})
    portfolio_id = data.get("portfolio_id")
    create_new = str(data.get("create_new", "false")).lower() in ("true", "1", "yes")
    new_title = (data.get("new_portfolio_title") or "").strip()
    overwrite = str(data.get("overwrite", "false")).lower() in ("true", "1", "yes")

    if not approved or not isinstance(approved, dict):
        return jsonify({"success": False, "error": "Approved resume details are required."}), 400

    full_name = (approved.get("full_name") or current_user.name).strip()
    email = (approved.get("email") or current_user.email).strip().lower()
    headline = (approved.get("headline") or "Software Engineer & Technology Specialist").strip()
    about = (approved.get("about") or approved.get("summary") or "Passionate software engineer.").strip()
    phone = (approved.get("phone") or "").strip() or None
    location = (approved.get("location") or "").strip() or None
    github_url = (approved.get("github_url") or "").strip() or None
    linkedin_url = (approved.get("linkedin_url") or "").strip() or None

    # Format skills, experience, education, certifications
    skills_raw = approved.get("technical_skills") or approved.get("skills")
    if isinstance(skills_raw, list):
        skills_str = ", ".join([str(s).strip() for s in skills_raw if str(s).strip()])
    elif isinstance(skills_raw, str):
        skills_str = skills_raw.strip()
    else:
        skills_str = None

    exp_raw = approved.get("experience") or approved.get("work_experience")
    if isinstance(exp_raw, list):
        experience_str = json.dumps(exp_raw)
    elif isinstance(exp_raw, str):
        experience_str = exp_raw.strip()
    else:
        experience_str = None

    edu_raw = approved.get("education")
    if isinstance(edu_raw, list):
        education_str = json.dumps(edu_raw)
    elif isinstance(edu_raw, str):
        education_str = edu_raw.strip()
    else:
        education_str = None

    cert_raw = approved.get("certifications")
    if isinstance(cert_raw, list):
        certifications_str = json.dumps(cert_raw)
    elif isinstance(cert_raw, str):
        certifications_str = cert_raw.strip()
    else:
        certifications_str = None

    projects_raw = approved.get("projects") or []

    try:
        if create_new or not portfolio_id:
            # Create a brand new portfolio
            title = new_title or f"{full_name}'s Professional Portfolio"
            portfolio = Portfolio(
                user_id=current_user.id,
                title=title,
                full_name=full_name,
                email=email,
                headline=headline,
                about=about,
                phone=phone,
                location=location,
                github_url=github_url,
                linkedin_url=linkedin_url,
                skills=skills_str,
                experience=experience_str,
                education=education_str,
                certifications=certifications_str,
            )
            db.session.add(portfolio)
            db.session.flush()

            # Add projects extracted from resume
            if isinstance(projects_raw, list):
                for p in projects_raw:
                    if isinstance(p, dict) and p.get("title"):
                        proj_obj = Project(
                            portfolio_id=portfolio.id,
                            title=p.get("title", "").strip(),
                            description=p.get("description", "").strip() if p.get("description") else None,
                            technologies=p.get("technologies", "").strip() if p.get("technologies") else None,
                            github_url=p.get("link", "").strip() if p.get("link") else None,
                            import_source="resume",
                        )
                        db.session.add(proj_obj)

            db.session.commit()
            return jsonify({
                "success": True,
                "message": f"New portfolio '{portfolio.title}' created successfully from your resume!",
                "portfolio_id": portfolio.id,
            }), 200

        else:
            # Update an existing portfolio
            portfolio_id = int(portfolio_id)
            portfolio = db.session.get(Portfolio, portfolio_id)
            if portfolio is None or portfolio.user_id != current_user.id:
                return jsonify({"success": False, "error": "Portfolio not found or access denied."}), 404

            if not overwrite:
                return jsonify({
                    "success": False,
                    "require_confirmation": True,
                    "error": f"Importing will update fields in existing portfolio '{portfolio.title}'. Please confirm overwrite.",
                }), 409

            # Apply approved fields
            portfolio.full_name = full_name
            portfolio.email = email
            portfolio.headline = headline
            portfolio.about = about
            if phone:
                portfolio.phone = phone
            if location:
                portfolio.location = location
            if github_url:
                portfolio.github_url = github_url
            if linkedin_url:
                portfolio.linkedin_url = linkedin_url
            if skills_str:
                portfolio.skills = skills_str
            if experience_str:
                portfolio.experience = experience_str
            if education_str:
                portfolio.education = education_str
            if certifications_str:
                portfolio.certifications = certifications_str

            # Add projects from resume if not already present
            if isinstance(projects_raw, list):
                existing_titles = {p.title.lower() for p in portfolio.projects}
                for p in projects_raw:
                    if isinstance(p, dict) and p.get("title"):
                        title_clean = p.get("title", "").strip()
                        if title_clean and title_clean.lower() not in existing_titles:
                            proj_obj = Project(
                                portfolio_id=portfolio.id,
                                title=title_clean,
                                description=p.get("description", "").strip() if p.get("description") else None,
                                technologies=p.get("technologies", "").strip() if p.get("technologies") else None,
                                github_url=p.get("link", "").strip() if p.get("link") else None,
                                import_source="resume",
                            )
                            db.session.add(proj_obj)

            db.session.commit()
            return jsonify({
                "success": True,
                "message": f"Portfolio '{portfolio.title}' updated successfully with extracted resume data!",
                "portfolio_id": portfolio.id,
            }), 200

    except Exception:
        db.session.rollback()
        return jsonify({"success": False, "error": "Database error while importing resume details."}), 500

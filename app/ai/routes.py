"""
PortfolioAI - AI Blueprint Routes
Exposes authenticated JSON endpoints and UI for Gemini-powered summaries,
About Me bios, STAR project bullets, skills gap analysis, and career advice.
"""

from flask import render_template, request, jsonify, abort
from flask_login import login_required, current_user
from app.extensions import db, limiter
from app.models import Portfolio, AIGeneration
from app.ai import ai_bp
from app.ai.service import AIService, AIServiceError


@ai_bp.route("/")
@ai_bp.route("/studio")
@login_required
def studio():
    """Render the interactive AI Portfolio Content Studio UI."""
    portfolios = (
        Portfolio.query.filter_by(user_id=current_user.id)
        .order_by(Portfolio.updated_at.desc())
        .all()
    )
    saved_generations = (
        AIGeneration.query.filter_by(user_id=current_user.id)
        .order_by(AIGeneration.created_at.desc())
        .limit(10)
        .all()
    )
    return render_template(
        "ai_generator.html",
        portfolios=portfolios,
        saved_generations=saved_generations,
    )


@ai_bp.route("/generate-summary", methods=["POST"])
@login_required
@limiter.limit("20 per minute")
def generate_summary():
    """Generate a recruiter-ready professional summary."""
    data = request.get_json(silent=True) or request.form
    name = (data.get("name") or current_user.name or "").strip()
    skills = (data.get("skills") or "").strip()
    education = (data.get("education") or "").strip()
    experience = (data.get("experience") or "").strip()
    career_goals = (data.get("career_goals") or "").strip()
    level = (data.get("level") or "intermediate").strip().lower()

    if not name:
        return jsonify({"success": False, "error": "Candidate name is required."}), 400
    if not skills:
        return jsonify({"success": False, "error": "Please provide your technical skills."}), 400
    if len(skills) > 1500 or len(experience) > 2500 or len(education) > 1000:
        return jsonify({"success": False, "error": "Input exceeds allowable character limit."}), 400
    if level not in ("beginner", "intermediate", "experienced"):
        level = "intermediate"

    try:
        result = AIService.generate_professional_summary(
            name=name,
            skills=skills,
            education=education,
            experience=experience,
            career_goals=career_goals,
            level=level,
        )
        return jsonify({"success": True, "result": result}), 200
    except AIServiceError as e:
        return jsonify({"success": False, "error": str(e)}), 503
    except Exception:
        return jsonify({"success": False, "error": "An unexpected error occurred while generating content."}), 500


@ai_bp.route("/generate-about", methods=["POST"])
@login_required
@limiter.limit("20 per minute")
def generate_about():
    """Generate a personalized About Me portfolio section."""
    data = request.get_json(silent=True) or request.form
    name = (data.get("name") or current_user.name or "").strip()
    headline = (data.get("headline") or "").strip()
    background = (data.get("background") or "").strip()
    interests = (data.get("interests") or "").strip()
    tone = (data.get("tone") or "creative").strip().lower()

    if not name:
        return jsonify({"success": False, "error": "Name is required."}), 400
    if not headline:
        return jsonify({"success": False, "error": "Professional headline is required."}), 400
    if len(background) > 2500 or len(interests) > 1500:
        return jsonify({"success": False, "error": "Input exceeds allowable character limit."}), 400
    if tone not in ("formal", "creative", "concise"):
        tone = "creative"

    try:
        result = AIService.generate_about_me(
            name=name,
            headline=headline,
            background=background,
            interests=interests,
            tone=tone,
        )
        return jsonify({"success": True, "result": result}), 200
    except AIServiceError as e:
        return jsonify({"success": False, "error": str(e)}), 503
    except Exception:
        return jsonify({"success": False, "error": "An unexpected error occurred while generating content."}), 500


@ai_bp.route("/generate-project", methods=["POST"])
@login_required
@limiter.limit("20 per minute")
def generate_project():
    """Generate STAR-formatted project description based strictly on facts."""
    data = request.get_json(silent=True) or request.form
    title = (data.get("title") or "").strip()
    technologies = (data.get("technologies") or "").strip()
    purpose = (data.get("purpose") or "").strip()
    key_details = (data.get("key_details") or "").strip()
    format_style = (data.get("format_style") or "star").strip().lower()

    if not title:
        return jsonify({"success": False, "error": "Project title is required."}), 400
    if not technologies:
        return jsonify({"success": False, "error": "Technologies used are required."}), 400
    if not purpose:
        return jsonify({"success": False, "error": "Project purpose or problem solved is required."}), 400
    if len(key_details) > 3000 or len(purpose) > 1500:
        return jsonify({"success": False, "error": "Input exceeds allowable character limit."}), 400

    try:
        result = AIService.generate_project_description(
            title=title,
            technologies=technologies,
            purpose=purpose,
            key_details=key_details,
            format_style=format_style,
        )
        return jsonify({"success": True, "result": result}), 200
    except AIServiceError as e:
        return jsonify({"success": False, "error": str(e)}), 503
    except Exception:
        return jsonify({"success": False, "error": "An unexpected error occurred while generating content."}), 500


@ai_bp.route("/analyze-skills", methods=["POST"])
@login_required
@limiter.limit("20 per minute")
def analyze_skills():
    """Analyze user skills against target role and suggest prioritized learning."""
    data = request.get_json(silent=True) or request.form
    current_skills = (data.get("current_skills") or "").strip()
    target_role = (data.get("target_role") or "").strip()
    career_goal = (data.get("career_goal") or "").strip()

    if not current_skills:
        return jsonify({"success": False, "error": "Please provide your current technical skills."}), 400
    if not target_role:
        return jsonify({"success": False, "error": "Target job title or role is required."}), 400
    if len(current_skills) > 2000 or len(target_role) > 200:
        return jsonify({"success": False, "error": "Input exceeds allowable character limit."}), 400

    try:
        result = AIService.analyze_skills(
            current_skills=current_skills,
            target_role=target_role,
            career_goal=career_goal,
        )
        return jsonify({"success": True, "result": result}), 200
    except AIServiceError as e:
        return jsonify({"success": False, "error": str(e)}), 503
    except Exception:
        return jsonify({"success": False, "error": "An unexpected error occurred during skills analysis."}), 500


@ai_bp.route("/recommend-careers", methods=["POST"])
@login_required
@limiter.limit("20 per minute")
def recommend_careers():
    """Recommend career paths and actionable next steps based on user background."""
    data = request.get_json(silent=True) or request.form
    background = (data.get("background") or "").strip()
    skills = (data.get("skills") or "").strip()
    interests = (data.get("interests") or "").strip()

    if not background:
        return jsonify({"success": False, "error": "Background and education info is required."}), 400
    if not skills:
        return jsonify({"success": False, "error": "Skills profile is required."}), 400
    if len(background) > 2000 or len(skills) > 2000:
        return jsonify({"success": False, "error": "Input exceeds allowable character limit."}), 400

    try:
        result = AIService.recommend_careers(
            background=background,
            skills=skills,
            interests=interests,
        )
        return jsonify({"success": True, "result": result}), 200
    except AIServiceError as e:
        return jsonify({"success": False, "error": str(e)}), 503
    except Exception:
        return jsonify({"success": False, "error": "An unexpected error occurred while recommending careers."}), 500


@ai_bp.route("/save-content", methods=["POST"])
@login_required
def save_content():
    """
    Save AI-generated content to database and optionally associate/update a user's portfolio.
    Enforces strict portfolio ownership validation.
    """
    data = request.get_json(silent=True) or request.form
    feature_type = (data.get("feature_type") or "").strip().lower()
    generated_text = (data.get("generated_text") or "").strip()
    prompt_input = (data.get("prompt_input") or "").strip()
    portfolio_id = data.get("portfolio_id")
    apply_to_portfolio = str(data.get("apply_to_portfolio", "false")).lower() in ("true", "1", "yes")

    if not feature_type or feature_type not in ("summary", "about", "project", "skills", "career"):
        return jsonify({"success": False, "error": "Invalid or missing feature type."}), 400
    if not generated_text:
        return jsonify({"success": False, "error": "Generated text content cannot be empty."}), 400
    if len(generated_text) > 10000:
        return jsonify({"success": False, "error": "Generated text exceeds 10,000 characters."}), 400

    target_portfolio = None
    if portfolio_id:
        try:
            portfolio_id = int(portfolio_id)
            target_portfolio = db.session.get(Portfolio, portfolio_id)
            if target_portfolio is None or target_portfolio.user_id != current_user.id:
                return jsonify({"success": False, "error": "Portfolio not found or access denied."}), 404
        except (ValueError, TypeError):
            return jsonify({"success": False, "error": "Invalid portfolio ID."}), 400

    try:
        # Create persistent record
        record = AIGeneration(
            user_id=current_user.id,
            portfolio_id=target_portfolio.id if target_portfolio else None,
            feature_type=feature_type,
            prompt_input=prompt_input[:500] if prompt_input else None,
            generated_text=generated_text,
        )
        db.session.add(record)

        # Optionally apply directly to portfolio About section
        if apply_to_portfolio and target_portfolio and feature_type in ("about", "summary"):
            target_portfolio.about = generated_text

        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Content saved successfully to your profile!",
            "id": record.id,
            "applied": apply_to_portfolio and target_portfolio is not None,
        }), 200

    except Exception:
        db.session.rollback()
        return jsonify({"success": False, "error": "Database error while saving content."}), 500

"""
PortfolioAI - Portfolio Management Blueprint Routes
Provides CRUD endpoints for user portfolios with strict ownership verification.
"""

from flask import render_template, redirect, url_for, flash, abort, request, jsonify, send_file
import json
import re
from flask_login import login_required, current_user
from app.extensions import db
from app.models import (
    Portfolio,
    Project,
    ALLOWED_THEMES,
    ALLOWED_ACCENT_COLORS,
    ALLOWED_FONTS,
    ALLOWED_LAYOUTS,
    DEFAULT_SECTION_VISIBILITY,
)
from app.portfolio import portfolio_bp
from app.portfolio.forms import PortfolioForm
from app.portfolio.pdf_generator import PortfolioPDFGenerator, PDFGenerationError
from app.portfolio.qr_service import PortfolioQRService, PortfolioUnpublishedError, QRCodeError


def get_user_portfolio_or_404(portfolio_id: int) -> Portfolio:
    """
    Fetch a portfolio by ID ensuring it belongs to the authenticated user.
    Returns HTTP 404 if not found or if owned by another user.
    """
    portfolio = db.session.get(Portfolio, portfolio_id)
    if portfolio is None or portfolio.user_id != current_user.id:
        abort(404)
    return portfolio


@portfolio_bp.route("")
@portfolio_bp.route("/")
@login_required
def index():
    """List all portfolios owned by the authenticated user."""
    portfolios = (
        Portfolio.query.filter_by(user_id=current_user.id)
        .order_by(Portfolio.updated_at.desc())
        .all()
    )
    return render_template("portfolios.html", portfolios=portfolios)


@portfolio_bp.route("/create", methods=["GET", "POST"])
@login_required
def create():
    """Display form and process new portfolio creation."""
    form = PortfolioForm()

    # Pre-fill defaults on GET request for faster workflow
    if request.method == "GET":
        form.full_name.data = current_user.name
        form.email.data = current_user.email

    if form.validate_on_submit():
        portfolio = Portfolio(
            user_id=current_user.id,
            title=form.title.data.strip(),
            full_name=form.full_name.data.strip(),
            headline=form.headline.data.strip(),
            about=form.about.data.strip(),
            email=form.email.data.strip().lower(),
            phone=form.phone.data.strip() if form.phone.data else None,
            location=form.location.data.strip() if form.location.data else None,
            github_url=form.github_url.data.strip() if form.github_url.data else None,
            linkedin_url=form.linkedin_url.data.strip() if form.linkedin_url.data else None,
            profile_image=form.profile_image.data.strip() if form.profile_image.data else None,
            skills=form.skills.data.strip() if form.skills.data else None,
            experience=form.experience.data.strip() if form.experience.data else None,
            education=form.education.data.strip() if form.education.data else None,
            certifications=form.certifications.data.strip() if form.certifications.data else None,
        )

        try:
            db.session.add(portfolio)
            db.session.commit()
            flash(f"Portfolio '{portfolio.title}' created successfully!", "success")
            return redirect(url_for("portfolio.index"))
        except Exception:
            db.session.rollback()
            flash("An error occurred while creating your portfolio. Please try again.", "danger")

    return render_template("portfolio_form.html", form=form, is_edit=False)


@portfolio_bp.route("/<int:portfolio_id>/edit", methods=["GET", "POST"])
@login_required
def edit(portfolio_id: int):
    """Edit an existing portfolio owned by the current user."""
    portfolio = get_user_portfolio_or_404(portfolio_id)
    form = PortfolioForm(obj=portfolio)

    if request.method == "GET":
        if portfolio.skills:
            s_list = portfolio.get_skills_list()
            form.skills.data = ", ".join(s_list) if s_list else portfolio.skills
        if portfolio.experience:
            form.experience.data = portfolio.experience
        if portfolio.education:
            form.education.data = portfolio.education
        if portfolio.certifications:
            c_list = portfolio.get_certifications_list()
            form.certifications.data = ", ".join(c_list) if (c_list and all(isinstance(x, str) for x in c_list)) else portfolio.certifications

    if form.validate_on_submit():
        portfolio.title = form.title.data.strip()
        portfolio.full_name = form.full_name.data.strip()
        portfolio.headline = form.headline.data.strip()
        portfolio.about = form.about.data.strip()
        portfolio.email = form.email.data.strip().lower()
        portfolio.phone = form.phone.data.strip() if form.phone.data else None
        portfolio.location = form.location.data.strip() if form.location.data else None
        portfolio.github_url = form.github_url.data.strip() if form.github_url.data else None
        portfolio.linkedin_url = form.linkedin_url.data.strip() if form.linkedin_url.data else None
        portfolio.profile_image = form.profile_image.data.strip() if form.profile_image.data else None
        portfolio.skills = form.skills.data.strip() if form.skills.data else None
        portfolio.experience = form.experience.data.strip() if form.experience.data else None
        portfolio.education = form.education.data.strip() if form.education.data else None
        portfolio.certifications = form.certifications.data.strip() if form.certifications.data else None

        try:
            db.session.commit()
            flash(f"Portfolio '{portfolio.title}' updated successfully!", "success")
            return redirect(url_for("portfolio.index"))
        except Exception:
            db.session.rollback()
            flash("An error occurred while updating your portfolio. Please try again.", "danger")

    return render_template(
        "portfolio_form.html",
        form=form,
        is_edit=True,
        portfolio=portfolio,
    )


@portfolio_bp.route("/<int:portfolio_id>/delete", methods=["POST"])
@login_required
def delete(portfolio_id: int):
    """Delete a portfolio owned by the current user after CSRF validation."""
    portfolio = get_user_portfolio_or_404(portfolio_id)
    title = portfolio.title

    try:
        db.session.delete(portfolio)
        db.session.commit()
        flash(f"Portfolio '{title}' has been deleted successfully.", "info")
    except Exception:
        db.session.rollback()
        flash("Failed to delete portfolio. Please try again.", "danger")

    return redirect(url_for("portfolio.index"))


@portfolio_bp.route("/<int:portfolio_id>")
@login_required
def preview(portfolio_id: int):
    """View a preview of the specified portfolio owned by the current user."""
    portfolio = get_user_portfolio_or_404(portfolio_id)
    return render_template("portfolio_preview.html", portfolio=portfolio)


@portfolio_bp.route("/<int:portfolio_id>/projects/<int:project_id>/delete", methods=["POST"])
@login_required
def delete_project(portfolio_id: int, project_id: int):
    """Delete a single project associated with an owned portfolio."""
    portfolio = get_user_portfolio_or_404(portfolio_id)
    project = db.session.get(Project, project_id)
    if project is None or project.portfolio_id != portfolio.id:
        abort(404)

    title = project.title
    try:
        db.session.delete(project)
        db.session.commit()
        flash(f"Project '{title}' was removed from portfolio.", "info")
    except Exception:
        db.session.rollback()
        flash("Failed to delete project. Please try again.", "danger")

    return redirect(url_for("portfolio.preview", portfolio_id=portfolio.id))


@portfolio_bp.route("/<int:portfolio_id>/theme", methods=["GET"])
@login_required
def theme_editor(portfolio_id: int):
    """Render the theme customizer and live builder interface."""
    portfolio = get_user_portfolio_or_404(portfolio_id)
    return render_template(
        "theme_editor.html",
        portfolio=portfolio,
        allowed_themes=ALLOWED_THEMES,
        allowed_colors=ALLOWED_ACCENT_COLORS,
        allowed_fonts=ALLOWED_FONTS,
        allowed_layouts=ALLOWED_LAYOUTS,
    )


@portfolio_bp.route("/<int:portfolio_id>/theme", methods=["POST"])
@login_required
def save_theme(portfolio_id: int):
    """
    Validate and save theme customization preferences for an owned portfolio.
    Rejects invalid themes, fonts, colors, or layouts with HTTP 400.
    """
    portfolio = get_user_portfolio_or_404(portfolio_id)
    data = request.get_json(silent=True) or request.form

    theme = (data.get("theme") or portfolio.theme).strip()
    accent_color = (data.get("accent_color") or portfolio.accent_color).strip().lower()
    font_family = (data.get("font_family") or portfolio.font_family).strip()
    layout_style = (data.get("layout_style") or portfolio.layout_style).strip()
    visible_sections = data.get("visible_sections")

    # Validate Theme
    if theme not in ALLOWED_THEMES:
        return jsonify({
            "success": False,
            "error": f"Invalid theme '{theme}'. Must be one of: {', '.join(ALLOWED_THEMES)}."
        }), 400

    # Validate Accent Color
    if accent_color not in [c.lower() for c in ALLOWED_ACCENT_COLORS]:
        import re
        if not re.match(r"^#(?:[0-9a-fA-F]{3}){1,2}$", accent_color):
            return jsonify({
                "success": False,
                "error": f"Invalid accent color '{accent_color}'. Must be a valid hex color code."
            }), 400

    # Validate Font Family
    if font_family not in ALLOWED_FONTS:
        return jsonify({
            "success": False,
            "error": f"Invalid font family '{font_family}'. Must be one of: {', '.join(ALLOWED_FONTS)}."
        }), 400

    # Validate Layout Style
    if layout_style not in ALLOWED_LAYOUTS:
        return jsonify({
            "success": False,
            "error": f"Invalid layout style '{layout_style}'. Must be one of: {', '.join(ALLOWED_LAYOUTS)}."
        }), 400

    # Process and sanitize section visibility
    clean_visibility = dict(DEFAULT_SECTION_VISIBILITY)
    if isinstance(visible_sections, dict):
        for k in clean_visibility.keys():
            if k in visible_sections:
                clean_visibility[k] = bool(visible_sections[k])
    elif isinstance(visible_sections, str):
        try:
            parsed = json.loads(visible_sections)
            if isinstance(parsed, dict):
                for k in clean_visibility.keys():
                    if k in parsed:
                        clean_visibility[k] = bool(parsed[k])
        except Exception:
            pass

    # Apply and commit
    try:
        portfolio.theme = theme
        portfolio.accent_color = accent_color
        portfolio.font_family = font_family
        portfolio.layout_style = layout_style
        portfolio.section_visibility = json.dumps(clean_visibility)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Theme preferences saved successfully!",
            "portfolio": portfolio.to_dict(),
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "error": f"Failed to save theme settings: {str(e)}",
        }), 500


@portfolio_bp.route("/<int:portfolio_id>/theme/reset", methods=["POST"])
@login_required
def reset_theme(portfolio_id: int):
    """Reset portfolio theme preferences back to default values."""
    portfolio = get_user_portfolio_or_404(portfolio_id)
    try:
        portfolio.theme = "modern-dark"
        portfolio.accent_color = "#6366f1"
        portfolio.font_family = "plus-jakarta-sans"
        portfolio.layout_style = "standard"
        portfolio.section_visibility = json.dumps(DEFAULT_SECTION_VISIBILITY)
        db.session.commit()
        return jsonify({
            "success": True,
            "message": "Theme preferences reset to default values.",
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@portfolio_bp.route("/<int:portfolio_id>/live", methods=["GET"])
@login_required
def live_portfolio(portfolio_id: int):
    """
    Renders the live, responsive themed portfolio showcase.
    Supports query parameter overrides (?theme=...&accent=...&font=...&layout=...)
    for instantaneous live previews.
    """
    portfolio = get_user_portfolio_or_404(portfolio_id)

    # Allow query parameter overrides for live testing and preview
    theme = request.args.get("theme", portfolio.theme)
    if theme not in ALLOWED_THEMES:
        theme = portfolio.theme

    accent_color = request.args.get("accent", portfolio.accent_color)
    import re
    if not re.match(r"^#(?:[0-9a-fA-F]{3}){1,2}$", accent_color):
        accent_color = portfolio.accent_color

    font_family = request.args.get("font", portfolio.font_family)
    if font_family not in ALLOWED_FONTS:
        font_family = portfolio.font_family

    layout_style = request.args.get("layout", portfolio.layout_style)
    if layout_style not in ALLOWED_LAYOUTS:
        layout_style = portfolio.layout_style

    return render_template(
        "themes/portfolio_render.html",
        portfolio=portfolio,
        theme=theme,
        accent_color=accent_color,
        font_family=font_family,
        layout_style=layout_style,
        visible_sections=portfolio.get_section_visibility(),
        skills_list=portfolio.get_skills_list(),
        experience_list=portfolio.get_experience_list(),
        education_list=portfolio.get_education_list(),
        certifications_list=portfolio.get_certifications_list(),
    )


@portfolio_bp.route("/<int:portfolio_id>/export/pdf", methods=["GET"])
@login_required
def export_pdf(portfolio_id: int):
    """
    Generate and stream downloadable portfolio PDF for owned portfolio.
    Sets safe attachment filename and caching headers.
    """
    portfolio = get_user_portfolio_or_404(portfolio_id)

    try:
        pdf_buffer = PortfolioPDFGenerator.generate(portfolio)
    except PDFGenerationError as e:
        flash(f"Failed to generate portfolio PDF: {str(e)}", "danger")
        return redirect(url_for("portfolio.preview", portfolio_id=portfolio.id))
    except Exception as e:
        flash("An unexpected error occurred while compiling your PDF. Please try again.", "danger")
        return redirect(url_for("portfolio.preview", portfolio_id=portfolio.id))

    safe_name = re.sub(r'[^a-zA-Z0-9_-]+', '_', portfolio.full_name or 'portfolio').strip('_')
    if not safe_name:
        safe_name = f"portfolio_{portfolio.id}"
    filename = f"{safe_name}_portfolio.pdf"

    response = send_file(
        pdf_buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename,
    )
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    return response


@portfolio_bp.route("/<int:portfolio_id>/publish", methods=["POST"])
@login_required
def toggle_publish(portfolio_id: int):
    """
    Toggle or set portfolio publication status.
    Ensures a public slug is generated when published.
    """
    portfolio = get_user_portfolio_or_404(portfolio_id)
    data = request.get_json(silent=True) or request.form

    if "publish" in data:
        publish_val = str(data.get("publish")).lower() in ("true", "1", "yes")
        portfolio.is_published = publish_val
    else:
        portfolio.is_published = not portfolio.is_published

    if portfolio.is_published:
        portfolio.ensure_slug()

    try:
        db.session.commit()
        state_str = "published live" if portfolio.is_published else "set to private draft"
        msg = f"Portfolio '{portfolio.title}' has been {state_str}!"

        if request.is_json:
            return jsonify({
                "success": True,
                "is_published": portfolio.is_published,
                "slug": portfolio.slug,
                "public_url": portfolio.get_public_url() if portfolio.is_published else None,
                "message": msg,
            }), 200

        flash(msg, "success" if portfolio.is_published else "info")
        return redirect(url_for("portfolio.preview", portfolio_id=portfolio.id))
    except Exception as e:
        db.session.rollback()
        if request.is_json:
            return jsonify({"success": False, "error": str(e)}), 500
        flash("Failed to update publication status. Please try again.", "danger")
        return redirect(url_for("portfolio.preview", portfolio_id=portfolio.id))


@portfolio_bp.route("/<int:portfolio_id>/qr", methods=["GET"])
@login_required
def get_qr_code(portfolio_id: int):
    """
    Generate and stream high-resolution PNG QR code for a published portfolio.
    Returns HTTP 400 if the portfolio is not published.
    Supports ?download=1 to force attachment download.
    """
    portfolio = get_user_portfolio_or_404(portfolio_id)

    if not portfolio.is_published:
        if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
            return jsonify({
                "success": False,
                "error": "Portfolio must be published before generating a public QR code."
            }), 400
        flash("Portfolio must be published before generating a public QR code.", "warning")
        return redirect(url_for("portfolio.preview", portfolio_id=portfolio.id))

    try:
        qr_buffer = PortfolioQRService.generate_qr_png(portfolio)
    except PortfolioUnpublishedError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except QRCodeError as e:
        return jsonify({"success": False, "error": str(e)}), 500

    download_mode = str(request.args.get("download", "0")).lower() in ("1", "true", "yes")
    safe_slug = portfolio.slug or f"portfolio_{portfolio.id}"
    filename = f"{safe_slug}_qr.png"

    response = send_file(
        qr_buffer,
        mimetype="image/png",
        as_attachment=download_mode,
        download_name=filename,
    )
    response.headers["Cache-Control"] = "public, max-age=300"
    return response

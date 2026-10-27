"""
PortfolioAI - Portfolio Management Blueprint Routes
Provides CRUD endpoints for user portfolios with strict ownership verification.
"""

from flask import render_template, redirect, url_for, flash, abort, request
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Portfolio, Project
from app.portfolio import portfolio_bp
from app.portfolio.forms import PortfolioForm


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

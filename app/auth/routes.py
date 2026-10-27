"""
PortfolioAI - Authentication Routes
Handles user registration, login, session state, and secure logout.
"""

from urllib.parse import urlsplit
from flask import render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, current_user, login_required
from app.extensions import db
from app.models import User
from app.auth import auth_bp
from app.auth.forms import RegistrationForm, LoginForm


def is_safe_redirect_url(target: str) -> bool:
    """Validate that the redirect target is a safe internal relative path."""
    if not target:
        return False
    parsed = urlsplit(target)
    return parsed.netloc == "" and parsed.path.startswith("/")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """Handle new user registration with server-side validation and auto-login."""
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    form = RegistrationForm()
    if form.validate_on_submit():
        normalized_email = form.email.data.strip().lower()

        # Extra safety check against race-condition duplicates
        existing = User.query.filter_by(email=normalized_email).first()
        if existing:
            flash("An account with this email address already exists. Please sign in instead.", "danger")
            return render_template("register.html", form=form)

        try:
            user = User(
                name=form.name.data.strip(),
                email=normalized_email,
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()

            # Automatically log in the user upon registration
            login_user(user)
            flash(f"Welcome to PortfolioAI, {user.name}! Your account has been created successfully.", "success")
            return redirect(url_for("dashboard.index"))

        except Exception:
            db.session.rollback()
            flash("An unexpected error occurred while saving your account. Please try again.", "danger")

    return render_template("register.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Handle user authentication with generic failure messages and open-redirect protection."""
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    form = LoginForm()
    if form.validate_on_submit():
        normalized_email = form.email.data.strip().lower()
        user = User.query.filter_by(email=normalized_email).first()

        # Generic authentication failure to prevent account enumeration
        if user is None or not user.check_password(form.password.data):
            flash("Invalid email address or password. Please verify your credentials.", "danger")
            return render_template("login.html", form=form), 401

        # Establish authenticated session
        login_user(user, remember=form.remember_me.data)
        flash(f"Welcome back, {user.name}!", "success")

        # Handle safe 'next' redirect
        next_page = request.args.get("next")
        if next_page and is_safe_redirect_url(next_page):
            return redirect(next_page)

        return redirect(url_for("dashboard.index"))

    return render_template("login.html", form=form)


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    """Terminate the authenticated session via CSRF-protected POST request."""
    logout_user()
    session.clear()
    flash("You have been signed out successfully.", "info")
    return redirect(url_for("main.index"))

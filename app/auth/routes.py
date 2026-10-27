from flask import render_template, redirect, url_for, flash
from app.auth import auth_bp

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Sign-in route (Phase 1 view / ready for Phase 2)."""
    return render_template("login.html")

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """User registration route (Phase 1 view / ready for Phase 2)."""
    return render_template("register.html")

@auth_bp.route("/logout")
def logout():
    """User sign-out route."""
    flash("You have been signed out successfully.", "info")
    return redirect(url_for("main.index"))

from flask import render_template, redirect, url_for
from flask_login import login_required, current_user
from app.dashboard import dashboard_bp

@dashboard_bp.route("/")
def index():
    """User workspace dashboard."""
    if not current_user.is_authenticated:
        return redirect(url_for("auth.login"))
    return render_template("dashboard.html")

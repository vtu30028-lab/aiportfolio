"""
PortfolioAI - User Dashboard Routes
Manages protected workspace overview, account statistics, and portfolio placeholders.
"""

from flask import render_template
from flask_login import login_required, current_user
from app.dashboard import dashboard_bp


@dashboard_bp.route("/")
@login_required
def index():
    """
    Protected workspace dashboard.
    Displays user account details, completeness indicators, and empty portfolio states.
    """
    return render_template(
        "dashboard.html",
        user=current_user,
    )

"""
PortfolioAI - Third-Party Integrations Package
Encapsulates external service connectors (GitHub, LinkedIn, etc.)
"""

from flask import Blueprint

github_bp = Blueprint("github", __name__, url_prefix="/github")

from app.integrations import routes  # noqa: E402, F401

from flask import Blueprint

resume_bp = Blueprint("resume", __name__, url_prefix="/resume")

from app.resume import routes  # noqa: E402, F401

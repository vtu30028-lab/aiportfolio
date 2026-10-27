import os
from flask import Flask, render_template
from config import config_by_name
from app.extensions import db, migrate, login_manager, csrf, limiter


def create_app(config_name=None):
    """Application factory for PortfolioAI."""
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development")

    app = Flask(__name__)
    app.config.from_object(config_by_name.get(config_name, config_by_name["default"]))

    # Ensure upload and export directories exist
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["EXPORTS_FOLDER"], exist_ok=True)

    # Initialize Flask extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    # Import models and register user loader for Flask-Login
    from app.models import User, Portfolio, AIGeneration, Project

    @login_manager.user_loader
    def load_user(user_id):
        try:
            return db.session.get(User, int(user_id))
        except Exception:
            return None

    # Register blueprints
    from app.main import main_bp
    from app.auth import auth_bp
    from app.dashboard import dashboard_bp
    from app.portfolio import portfolio_bp
    from app.ai import ai_bp
    from app.resume import resume_bp
    from app.integrations import github_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(portfolio_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(resume_bp)
    app.register_blueprint(github_bp)

    # Create tables automatically in development or testing if using SQLite
    with app.app_context():
        if app.config.get("TESTING") or "sqlite" in app.config.get("SQLALCHEMY_DATABASE_URI", ""):
            db.create_all()

    # Global context processors for templates
    @app.context_processor
    def inject_global_template_vars():
        return {
            "app_name": "PortfolioAI",
            "app_version": "1.0.0",
            "app_tagline": "AI-Powered Portfolio Generator",
            "current_year": 2026,
        }

    # Custom HTTP error handlers
    @app.errorhandler(404)
    def handle_not_found(error):
        return render_template("errors/404.html", error=error), 404

    @app.errorhandler(413)
    def handle_payload_too_large(error):
        return render_template(
            "errors/413.html",
            error="File size exceeds the allowable limit. Please upload a PDF under 5MB.",
        ), 413

    @app.errorhandler(429)
    def handle_rate_limit(error):
        return render_template(
            "errors/429.html",
            error="Too many requests. Please slow down and try again shortly.",
        ), 429

    @app.errorhandler(500)
    def handle_internal_server_error(error):
        return render_template("errors/500.html", error=error), 500

    return app

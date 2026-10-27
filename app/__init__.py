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

    # Create tables automatically in development, testing, or cloud deployment
    with app.app_context():
        db.create_all()
        # Non-destructive SQLite schema upgrade for Phase 7/8 columns if table already existed
        try:
            from sqlalchemy import text
            inspector = db.inspect(db.engine)
            if "portfolios" in inspector.get_table_names():
                existing_cols = {col["name"] for col in inspector.get_columns("portfolios")}
                new_cols = [
                    ("theme", "VARCHAR(50) DEFAULT 'modern-dark'"),
                    ("accent_color", "VARCHAR(20) DEFAULT '#6366f1'"),
                    ("font_family", "VARCHAR(50) DEFAULT 'plus-jakarta-sans'"),
                    ("layout_style", "VARCHAR(50) DEFAULT 'standard'"),
                    ("section_visibility", "TEXT"),
                    ("skills", "TEXT"),
                    ("experience", "TEXT"),
                    ("education", "TEXT"),
                    ("certifications", "TEXT"),
                    ("is_published", "BOOLEAN DEFAULT 0"),
                    ("slug", "VARCHAR(120)"),
                ]
                for col_name, col_def in new_cols:
                    if col_name not in existing_cols:
                        try:
                            db.session.execute(text(f"ALTER TABLE portfolios ADD COLUMN {col_name} {col_def}"))
                            db.session.commit()
                        except Exception:
                            db.session.rollback()
        except Exception:
            db.session.rollback()

    # Reverse proxy support in production (Render, AWS, Heroku)
    if config_name == "production" or os.environ.get("RENDER"):
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    # Phase 9: Global HTTP Security Headers
    @app.after_request
    def set_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        # Content Security Policy (allows CDNs, Google Fonts, and self-hosted frames)
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
            "font-src 'self' https://cdn.jsdelivr.net https://fonts.gstatic.com data:; "
            "img-src 'self' data: https: blob:; "
            "frame-src 'self'; "
            "connect-src 'self';"
        )
        response.headers["Content-Security-Policy"] = csp
        return response

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

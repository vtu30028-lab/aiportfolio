import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory of the application
BASE_DIR = Path(__file__).resolve().parent

# Load environment variables from .env file
load_dotenv(BASE_DIR / ".env")


class Config:
    """Base application configuration."""

    # Security
    SECRET_KEY = os.environ.get(
        "SECRET_KEY", "fallback-dev-secret-key-change-in-production"
    )
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600  # 1 hour CSRF token validity

    # Database
    db_url = os.environ.get("DATABASE_URL", f"sqlite:///{BASE_DIR / 'portfolio.db'}")
    # Fix for SQLAlchemy 2.0+ which deprecates 'postgres://' scheme
    if db_url and db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_DATABASE_URI = db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
    }

    # Uploads & Exports
    UPLOAD_FOLDER = BASE_DIR / "uploads"
    EXPORTS_FOLDER = BASE_DIR / "exports"
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH_MB", 10)) * 1024 * 1024  # 10 MB
    ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg"}

    # Gemini AI
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
    GEMINI_MODEL = "gemini-2.5-flash"

    # Rate Limiting
    RATELIMIT_DEFAULT = "200 per day; 50 per hour"
    RATELIMIT_STORAGE_URI = "memory://"

    # Session & Cookie Security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = False  # Set to True in ProductionConfig with HTTPS


class DevelopmentConfig(Config):
    """Development environment configuration."""
    DEBUG = True
    TESTING = False


class TestingConfig(Config):
    """Testing environment configuration."""
    TESTING = True
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    RATELIMIT_ENABLED = False


class ProductionConfig(Config):
    """Production environment configuration."""
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_SAMESITE = "Strict"


# Configuration dictionary lookup
config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}

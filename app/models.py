"""
PortfolioAI - Relational Database Models
Defines schema for Users, Portfolios, authentication, and core domain entities.
"""

from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db


class User(UserMixin, db.Model):
    """
    User account model for authentication, portfolio ownership,
    and profile settings.
    """
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, index=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # 1-to-many relationship: One user can own multiple portfolios
    portfolios = db.relationship(
        "Portfolio",
        backref="owner",
        lazy=True,
        cascade="all, delete-orphan",
        order_by="desc(Portfolio.updated_at)",
    )

    def set_password(self, password: str) -> None:
        """Hash and store the given password securely using Werkzeug."""
        if not password:
            raise ValueError("Password cannot be empty.")
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Verify password against the stored password hash."""
        if not self.password_hash or not password:
            return False
        return check_password_hash(self.password_hash, password)

    def to_safe_dict(self) -> dict:
        """Return safe user profile dictionary excluding credentials."""
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "portfolios_count": len(self.portfolios),
        }

    def __repr__(self) -> str:
        return f"<User id={self.id} email='{self.email}'>"


class Portfolio(db.Model):
    """
    Portfolio entity storing user personal details, contact links,
    professional headline, and biography.
    """
    __tablename__ = "portfolios"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    title = db.Column(db.String(150), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    headline = db.Column(db.String(200), nullable=False)
    about = db.Column(db.Text, nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(30), nullable=True)
    location = db.Column(db.String(100), nullable=True)
    github_url = db.Column(db.String(255), nullable=True)
    linkedin_url = db.Column(db.String(255), nullable=True)
    profile_image = db.Column(db.String(255), nullable=True)

    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    def to_dict(self) -> dict:
        """Serialize portfolio fields to a dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "full_name": self.full_name,
            "headline": self.headline,
            "about": self.about,
            "email": self.email,
            "phone": self.phone,
            "location": self.location,
            "github_url": self.github_url,
            "linkedin_url": self.linkedin_url,
            "profile_image": self.profile_image,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        return f"<Portfolio id={self.id} title='{self.title}' user_id={self.user_id}>"

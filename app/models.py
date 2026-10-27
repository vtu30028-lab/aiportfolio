"""
PortfolioAI - Relational Database Models
Defines schema for Users, authentication, and core domain entities.
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
        }

    def __repr__(self) -> str:
        return f"<User id={self.id} email='{self.email}'>"

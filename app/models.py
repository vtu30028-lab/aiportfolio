"""
PortfolioAI - Relational Database Models
Defines schema for Users, Portfolios, AI Generations, and core domain entities.
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

    # 1-to-many relationship: One user can have multiple saved AI generations
    ai_generations = db.relationship(
        "AIGeneration",
        backref="user",
        lazy=True,
        cascade="all, delete-orphan",
        order_by="desc(AIGeneration.created_at)",
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

    # Saved AI content linked to this portfolio
    ai_generations = db.relationship(
        "AIGeneration",
        backref="portfolio",
        lazy=True,
    )

    # 1-to-many relationship: One portfolio can have multiple projects
    projects = db.relationship(
        "Project",
        backref="portfolio",
        lazy=True,
        cascade="all, delete-orphan",
        order_by="desc(Project.created_at)",
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
            "projects_count": len(self.projects),
            "projects": [p.to_dict() for p in self.projects],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        return f"<Portfolio id={self.id} title='{self.title}' user_id={self.user_id}>"


class AIGeneration(db.Model):
    """
    Stores AI-generated content (summary, about me, project descriptions,
    skills analysis, career advice) saved to a user's portfolio.
    """
    __tablename__ = "ai_generations"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    portfolio_id = db.Column(
        db.Integer,
        db.ForeignKey("portfolios.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    feature_type = db.Column(db.String(50), nullable=False)  # summary, about, project, skills, career
    prompt_input = db.Column(db.Text, nullable=True)  # Safe summary of inputs
    generated_text = db.Column(db.Text, nullable=False)
    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    def to_dict(self) -> dict:
        """Serialize AI generation record to a dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "portfolio_id": self.portfolio_id,
            "feature_type": self.feature_type,
            "prompt_input": self.prompt_input,
            "generated_text": self.generated_text,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<AIGeneration id={self.id} feature='{self.feature_type}' user_id={self.user_id}>"


class Project(db.Model):
    """
    Represents a technical project associated with a Portfolio.
    Can be created manually or imported from GitHub / Resume.
    """
    __tablename__ = "projects"

    id = db.Column(db.Integer, primary_key=True)
    portfolio_id = db.Column(
        db.Integer,
        db.ForeignKey("portfolios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    technologies = db.Column(db.String(255), nullable=True)
    github_url = db.Column(db.String(255), nullable=True)
    live_url = db.Column(db.String(255), nullable=True)
    import_source = db.Column(db.String(50), default="manual", nullable=False)  # github, manual, resume
    stars_count = db.Column(db.Integer, default=0, nullable=False)
    forks_count = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def to_dict(self) -> dict:
        """Serialize project fields to a dictionary."""
        return {
            "id": self.id,
            "portfolio_id": self.portfolio_id,
            "title": self.title,
            "description": self.description,
            "technologies": self.technologies,
            "github_url": self.github_url,
            "live_url": self.live_url,
            "import_source": self.import_source,
            "stars_count": self.stars_count,
            "forks_count": self.forks_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        return f"<Project id={self.id} title='{self.title}' portfolio_id={self.portfolio_id}>"

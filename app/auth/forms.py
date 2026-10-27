"""
PortfolioAI - Authentication WTForms
Provides server-side validation, email normalization, and CSRF protection.
"""

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError
from app.models import User


class RegistrationForm(FlaskForm):
    """User registration form with strict input validation."""
    name = StringField(
        "Full Name",
        validators=[
            DataRequired(message="Please enter your full name."),
            Length(min=2, max=100, message="Name must be between 2 and 100 characters."),
        ],
    )
    email = StringField(
        "Email Address",
        validators=[
            DataRequired(message="Please enter your email address."),
            Email(message="Please enter a valid email address."),
            Length(max=120, message="Email cannot exceed 120 characters."),
        ],
    )
    password = PasswordField(
        "Password",
        validators=[
            DataRequired(message="Please choose a password."),
            Length(min=8, message="Password must be at least 8 characters long."),
        ],
    )
    confirm_password = PasswordField(
        "Confirm Password",
        validators=[
            DataRequired(message="Please confirm your password."),
            EqualTo("password", message="Passwords do not match."),
        ],
    )
    terms = BooleanField(
        "Terms and Privacy Acknowledgement",
        validators=[
            DataRequired(message="You must acknowledge the Terms of Service and Privacy Policy."),
        ],
    )
    submit = SubmitField("Create Free Account")

    def validate_email(self, field):
        """Reject registration if the email already exists."""
        normalized_email = field.data.strip().lower() if field.data else ""
        user = User.query.filter_by(email=normalized_email).first()
        if user:
            raise ValidationError(
                "An account with this email address already exists. Please sign in instead."
            )


class LoginForm(FlaskForm):
    """User login form with credential fields and remember-me checkbox."""
    email = StringField(
        "Email Address",
        validators=[
            DataRequired(message="Please enter your email address."),
            Email(message="Please enter a valid email address."),
        ],
    )
    password = PasswordField(
        "Password",
        validators=[
            DataRequired(message="Please enter your password."),
        ],
    )
    remember_me = BooleanField("Remember Me")
    submit = SubmitField("Sign In")

"""
PortfolioAI - Portfolio WTForms
Defines form fields and server-side validation for creating and editing portfolios.
"""

from urllib.parse import urlparse
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Email, Length, Optional, ValidationError


def validate_web_url(form, field):
    """Custom validator ensuring optional URL fields have a valid http/https scheme and domain."""
    if not field.data:
        return
    url = field.data.strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        # Prepend https if omitted for user convenience
        url = "https://" + url
        field.data = url

    parsed = urlparse(url)
    if not (parsed.scheme in ("http", "https") and parsed.netloc and "." in parsed.netloc):
        raise ValidationError("Please provide a valid URL (e.g., https://github.com/username).")


class PortfolioForm(FlaskForm):
    """Form for creating and editing user portfolios."""

    title = StringField(
        "Portfolio Title",
        validators=[
            DataRequired(message="Please provide a portfolio title."),
            Length(min=2, max=150, message="Title must be between 2 and 150 characters."),
        ],
    )
    full_name = StringField(
        "Professional Name",
        validators=[
            DataRequired(message="Please enter your full professional name."),
            Length(min=2, max=100, message="Name must be between 2 and 100 characters."),
        ],
    )
    headline = StringField(
        "Professional Headline",
        validators=[
            DataRequired(message="Please enter a headline."),
            Length(min=5, max=200, message="Headline must be between 5 and 200 characters."),
        ],
    )
    about = TextAreaField(
        "About Me Description",
        validators=[
            DataRequired(message="Please provide a brief bio or description."),
            Length(min=10, max=5000, message="Bio must be between 10 and 5000 characters."),
        ],
    )
    email = StringField(
        "Contact Email",
        validators=[
            DataRequired(message="Please provide a contact email."),
            Email(message="Please provide a valid email address."),
            Length(max=120, message="Email cannot exceed 120 characters."),
        ],
    )
    phone = StringField(
        "Phone Number",
        validators=[
            Optional(),
            Length(max=30, message="Phone number cannot exceed 30 characters."),
        ],
    )
    location = StringField(
        "Location",
        validators=[
            Optional(),
            Length(max=100, message="Location cannot exceed 100 characters."),
        ],
    )
    github_url = StringField(
        "GitHub Profile URL",
        validators=[
            Optional(),
            Length(max=255, message="GitHub URL cannot exceed 255 characters."),
            validate_web_url,
        ],
    )
    linkedin_url = StringField(
        "LinkedIn Profile URL",
        validators=[
            Optional(),
            Length(max=255, message="LinkedIn URL cannot exceed 255 characters."),
            validate_web_url,
        ],
    )
    profile_image = StringField(
        "Profile Image URL (Optional)",
        validators=[
            Optional(),
            Length(max=255, message="Profile image URL cannot exceed 255 characters."),
            validate_web_url,
        ],
    )
    skills = TextAreaField(
        "Technical & Professional Skills",
        validators=[
            Optional(),
            Length(max=5000, message="Skills cannot exceed 5000 characters."),
        ],
    )
    experience = TextAreaField(
        "Work Experience & Internships",
        validators=[
            Optional(),
            Length(max=10000, message="Experience cannot exceed 10,000 characters."),
        ],
    )
    education = TextAreaField(
        "Education & Academic Background",
        validators=[
            Optional(),
            Length(max=10000, message="Education cannot exceed 10,000 characters."),
        ],
    )
    certifications = TextAreaField(
        "Licenses & Certifications",
        validators=[
            Optional(),
            Length(max=5000, message="Certifications cannot exceed 5000 characters."),
        ],
    )
    submit = SubmitField("Save Portfolio")

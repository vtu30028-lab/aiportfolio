from flask import render_template, jsonify, abort
from app.main import main_bp
from app.models import Portfolio

@main_bp.route("/")
def index():
    """Render the high-impact modern SaaS landing page."""
    featured_stats = {
        "portfolios_generated": "10,000+",
        "match_rate": "94.8%",
        "active_themes": 3,
        "avg_creation_time": "3 mins",
    }
    
    themes_preview = [
        {
            "id": "modern",
            "name": "Modern Tech",
            "badge": "Popular",
            "description": "Sleek dark gradient theme tailored for full-stack developers, AI engineers, and tech innovators.",
            "accent": "#6366f1",
            "tags": ["Dark Mode", "Interactive Badges", "GitHub Cards"],
        },
        {
            "id": "minimal",
            "name": "Clean Minimalist",
            "badge": "Executive",
            "description": "Ultra-clean typographical layout focused on clear readability, impactful projects, and research papers.",
            "accent": "#0ea5e9",
            "tags": ["Monochrome Accents", "Timeline View", "High Legibility"],
        },
        {
            "id": "creative",
            "name": "Creative Studio",
            "badge": "Bold",
            "description": "Dynamic colorful design with glassmorphic cards and animated gradients for UI/UX designers and creative coders.",
            "accent": "#ec4899",
            "tags": ["Glassmorphism", "Gradients", "Showcase Grid"],
        },
    ]

    return render_template(
        "index.html",
        stats=featured_stats,
        themes=themes_preview,
    )


@main_bp.route("/health")
def health():
    """Application health check endpoint for monitoring and cloud hosting."""
    return jsonify({
        "status": "healthy",
        "service": "PortfolioAI — AI-Powered Portfolio Generator",
        "version": "1.0.0",
        "environment": "production-ready"
    }), 200


@main_bp.route("/p/<slug>")
def public_portfolio(slug: str):
    """
    Publicly accessible portfolio showcase endpoint.
    No login required. Accessible only if portfolio.is_published is True.
    """
    portfolio = Portfolio.query.filter_by(slug=slug).first()
    if portfolio is None or not portfolio.is_published:
        abort(404)

    return render_template(
        "themes/portfolio_render.html",
        portfolio=portfolio,
        theme=portfolio.theme,
        accent_color=portfolio.accent_color,
        font_family=portfolio.font_family,
        layout_style=portfolio.layout_style,
        visible_sections=portfolio.get_section_visibility(),
        skills_list=portfolio.get_skills_list(),
        experience_list=portfolio.get_experience_list(),
        education_list=portfolio.get_education_list(),
        certifications_list=portfolio.get_certifications_list(),
    )

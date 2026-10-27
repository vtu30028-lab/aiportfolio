from flask import render_template, jsonify
from app.main import main_bp

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

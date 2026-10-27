"""
PortfolioAI - Production WSGI Application Entry Point
Supports local development, production gunicorn, and cloud container deployments.
"""

import os
from app import create_app

# Instantiate application using environment configuration
env = os.environ.get("FLASK_ENV", "production" if os.environ.get("RENDER") else "development")
app = create_app(env)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    # Never run with debug=True in production
    is_debug = env == "development" and not os.environ.get("RENDER")
    host = os.environ.get("HOST", "127.0.0.1" if is_debug else "0.0.0.0")
    app.run(host=host, port=port, debug=is_debug)

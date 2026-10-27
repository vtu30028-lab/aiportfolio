"""
PortfolioAI - GitHub Integration Blueprint Routes
Endpoints for searching public GitHub repositories, generating AI descriptions,
and importing selected repositories into user portfolios with ownership isolation.
"""

import re
from urllib.parse import urlparse
from flask import render_template, request, jsonify, abort
from flask_login import login_required, current_user
from app.extensions import db, limiter
from app.models import Portfolio, Project
from app.integrations import github_bp
from app.integrations.github_service import (
    GitHubService,
    GitHubUsernameInvalidError,
    GitHubUserNotFoundError,
    GitHubRateLimitError,
    GitHubNetworkError,
    GitHubServiceError,
)
from app.ai.service import AIService, AIServiceError


def _normalize_github_url(url: str) -> str:
    """Normalize GitHub repository URL for duplicate matching."""
    if not url:
        return ""
    cleaned = url.strip().rstrip("/").lower()
    return cleaned


@github_bp.route("/import", methods=["GET"])
@login_required
def import_page():
    """
    Renders the GitHub repository import interface.
    Accepts optional ?portfolio_id=<id> query parameter.
    """
    portfolios = (
        Portfolio.query.filter_by(user_id=current_user.id)
        .order_by(Portfolio.updated_at.desc())
        .all()
    )

    selected_portfolio_id = request.args.get("portfolio_id", type=int)
    selected_portfolio = None

    if selected_portfolio_id:
        selected_portfolio = db.session.get(Portfolio, selected_portfolio_id)
        if selected_portfolio and selected_portfolio.user_id != current_user.id:
            # Prevent snooping other users' portfolios
            selected_portfolio = None
            selected_portfolio_id = None

    if not selected_portfolio and portfolios:
        selected_portfolio = portfolios[0]
        selected_portfolio_id = selected_portfolio.id

    # Extract default username from the portfolio's github_url if available
    default_username = ""
    if selected_portfolio and selected_portfolio.github_url:
        try:
            parsed = urlparse(selected_portfolio.github_url)
            path_parts = [p for p in parsed.path.split("/") if p]
            if path_parts:
                default_username = path_parts[0]
        except Exception:
            default_username = ""

    return render_template(
        "github_import.html",
        portfolios=portfolios,
        selected_portfolio=selected_portfolio,
        selected_portfolio_id=selected_portfolio_id,
        default_username=default_username,
    )


@github_bp.route("/fetch", methods=["POST"])
@login_required
@limiter.limit("30 per minute")
def fetch_repos():
    """
    Fetch public repositories for a given GitHub username.
    Annotates each repo with already-imported status for the target portfolio.
    """
    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        return jsonify({"success": False, "error": "Invalid JSON body provided."}), 400

    raw_username = data.get("username", "").strip()
    portfolio_id = data.get("portfolio_id")

    if not raw_username:
        return jsonify({"success": False, "error": "Please provide a GitHub username."}), 400

    if not portfolio_id:
        return jsonify({"success": False, "error": "A target portfolio must be selected."}), 400

    # Strict Portfolio ownership verification
    portfolio = db.session.get(Portfolio, portfolio_id)
    if portfolio is None or portfolio.user_id != current_user.id:
        return jsonify({"success": False, "error": "Target portfolio not found or access denied."}), 404

    # Fetch from GitHub Service
    try:
        result = GitHubService.fetch_user_repositories(raw_username)
    except GitHubUsernameInvalidError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except GitHubUserNotFoundError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    except GitHubRateLimitError as e:
        return jsonify({"success": False, "error": str(e)}), 429
    except GitHubNetworkError as e:
        return jsonify({"success": False, "error": str(e)}), 504
    except GitHubServiceError as e:
        return jsonify({"success": False, "error": str(e)}), 502
    except Exception as e:
        return jsonify({"success": False, "error": f"An unexpected error occurred: {str(e)}"}), 500

    # Cross-reference existing projects in this portfolio to identify duplicates
    existing_urls = {
        _normalize_github_url(p.github_url): p.id
        for p in portfolio.projects
        if p.github_url
    }
    existing_titles = {
        p.title.strip().lower(): p.id
        for p in portfolio.projects
    }

    repos = result.get("repositories", [])
    for repo in repos:
        norm_url = _normalize_github_url(repo.get("html_url", ""))
        norm_title = repo.get("name", "").strip().lower()

        if norm_url and norm_url in existing_urls:
            repo["already_imported"] = True
            repo["existing_project_id"] = existing_urls[norm_url]
        elif norm_title in existing_titles:
            repo["already_imported"] = True
            repo["existing_project_id"] = existing_titles[norm_title]
        else:
            repo["already_imported"] = False
            repo["existing_project_id"] = None

    return jsonify({
        "success": True,
        "username": result["username"],
        "total_count": result["total_count"],
        "repositories": repos,
    }), 200


@github_bp.route("/generate-description", methods=["POST"])
@login_required
@limiter.limit("15 per minute")
def generate_repo_description():
    """
    Generate professional AI portfolio description for a specific repository
    using only verified repository metadata.
    """
    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        return jsonify({"success": False, "error": "Invalid JSON body provided."}), 400

    repo_name = data.get("name", "").strip()
    raw_description = data.get("description", "").strip()
    language = data.get("language", "").strip()
    topics = data.get("topics", [])

    if not repo_name:
        return jsonify({"success": False, "error": "Repository name is required."}), 400

    if not isinstance(topics, list):
        topics = []

    try:
        polished_description = AIService.generate_github_repo_description(
            repo_name=repo_name,
            description=raw_description,
            language=language,
            topics=topics,
        )
        return jsonify({
            "success": True,
            "repo_name": repo_name,
            "generated_description": polished_description,
        }), 200
    except AIServiceError as e:
        return jsonify({"success": False, "error": str(e)}), 500
    except Exception as e:
        return jsonify({"success": False, "error": f"AI generation error: {str(e)}"}), 500


@github_bp.route("/import", methods=["POST"])
@login_required
def import_selected_projects():
    """
    Imports one or more selected GitHub repositories into the specified portfolio.
    Enforces ownership isolation, validates inputs, and detects duplicate imports.
    Returns HTTP 409 if a duplicate exists without confirm_overwrite.
    """
    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        return jsonify({"success": False, "error": "Invalid JSON payload."}), 400

    portfolio_id = data.get("portfolio_id")
    projects_to_import = data.get("projects", [])
    confirm_overwrite = bool(data.get("confirm_overwrite", False))

    if not portfolio_id:
        return jsonify({"success": False, "error": "Portfolio ID is required."}), 400

    if not projects_to_import or not isinstance(projects_to_import, list):
        return jsonify({"success": False, "error": "Please select at least one project to import."}), 400

    # Strict Portfolio ownership verification
    portfolio = db.session.get(Portfolio, portfolio_id)
    if portfolio is None or portfolio.user_id != current_user.id:
        return jsonify({"success": False, "error": "Portfolio not found or access denied."}), 404

    # Build map of existing projects in this portfolio
    existing_by_url = {
        _normalize_github_url(p.github_url): p
        for p in portfolio.projects
        if p.github_url
    }
    existing_by_title = {
        p.title.strip().lower(): p
        for p in portfolio.projects
    }

    # Check for duplicate collisions if confirm_overwrite is False
    if not confirm_overwrite:
        conflicts = []
        for item in projects_to_import:
            raw_url = item.get("github_url", "")
            raw_title = item.get("title", "")
            norm_url = _normalize_github_url(raw_url)
            norm_title = raw_title.strip().lower()

            if norm_url and norm_url in existing_by_url:
                conflicts.append({
                    "title": raw_title,
                    "url": raw_url,
                    "existing_title": existing_by_url[norm_url].title,
                })
            elif norm_title in existing_by_title:
                conflicts.append({
                    "title": raw_title,
                    "url": raw_url,
                    "existing_title": existing_by_title[norm_title].title,
                })

        if conflicts:
            return jsonify({
                "success": False,
                "error": "conflict",
                "message": (
                    f"'{conflicts[0]['title']}' already exists in this portfolio. "
                    "Do you want to overwrite it with updated repository details?"
                ),
                "conflicts": conflicts,
            }), 409

    # Process imports / updates transactionally
    imported_count = 0
    updated_count = 0

    try:
        for item in projects_to_import:
            title = (item.get("title") or "").strip()
            if not title:
                continue

            description = (item.get("description") or "").strip()
            technologies = (item.get("technologies") or "").strip()
            github_url = (item.get("github_url") or "").strip()
            live_url = (item.get("live_url") or "").strip()
            stars_count = int(item.get("stars_count", 0))
            forks_count = int(item.get("forks_count", 0))

            norm_url = _normalize_github_url(github_url)
            norm_title = title.lower()

            existing_proj = None
            if norm_url and norm_url in existing_by_url:
                existing_proj = existing_by_url[norm_url]
            elif norm_title in existing_by_title:
                existing_proj = existing_by_title[norm_title]

            if existing_proj and confirm_overwrite:
                # Update existing record
                existing_proj.title = title
                existing_proj.description = description
                existing_proj.technologies = technologies
                existing_proj.github_url = github_url or existing_proj.github_url
                if live_url:
                    existing_proj.live_url = live_url
                existing_proj.stars_count = stars_count
                existing_proj.forks_count = forks_count
                updated_count += 1
            else:
                # Create new Project
                new_project = Project(
                    portfolio_id=portfolio.id,
                    title=title,
                    description=description,
                    technologies=technologies,
                    github_url=github_url or None,
                    live_url=live_url or None,
                    import_source="github",
                    stars_count=stars_count,
                    forks_count=forks_count,
                )
                db.session.add(new_project)
                imported_count += 1

        db.session.commit()

        msg_parts = []
        if imported_count:
            msg_parts.append(f"{imported_count} project(s) imported")
        if updated_count:
            msg_parts.append(f"{updated_count} project(s) updated")
        msg = f"Successfully {' and '.join(msg_parts)} to '{portfolio.title}'."

        return jsonify({
            "success": True,
            "message": msg,
            "imported_count": imported_count,
            "updated_count": updated_count,
            "portfolio_id": portfolio.id,
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "error": f"Failed to save projects to portfolio: {str(e)}",
        }), 500

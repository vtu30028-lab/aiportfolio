"""
PortfolioAI - GitHub REST API Service
Fetches public repository metadata, handles pagination, rate limits,
network errors, and formats repository data for portfolio import.
"""

import os
import re
import requests
from typing import List, Dict, Any, Optional
from flask import current_app


# GitHub Username validation regex (1-39 chars, alphanumeric or single hyphens, no start/end hyphens)
GITHUB_USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9](?:[a-zA-Z0-9]|-(?=[a-zA-Z0-9])){0,38}$")


class GitHubServiceError(Exception):
    """Base exception for all GitHub API service errors."""
    pass


class GitHubUsernameInvalidError(GitHubServiceError):
    """Raised when the supplied GitHub username violates naming rules."""
    pass


class GitHubUserNotFoundError(GitHubServiceError):
    """Raised when the specified GitHub user does not exist (HTTP 404)."""
    pass


class GitHubRateLimitError(GitHubServiceError):
    """Raised when GitHub API rate limits are exceeded (HTTP 403)."""
    pass


class GitHubNetworkError(GitHubServiceError):
    """Raised when requests timeout or encounter network connection issues."""
    pass


class GitHubService:
    """Encapsulates GitHub REST API operations."""

    @staticmethod
    def validate_username(username: str) -> str:
        """
        Validate and normalize GitHub username.
        Raises GitHubUsernameInvalidError if username does not conform.
        """
        if not username or not isinstance(username, str):
            raise GitHubUsernameInvalidError("GitHub username cannot be empty.")

        cleaned = username.strip()
        if cleaned.startswith("@"):
            cleaned = cleaned[1:]

        if not GITHUB_USERNAME_REGEX.match(cleaned):
            raise GitHubUsernameInvalidError(
                f"Invalid GitHub username '{cleaned}'. Usernames may contain only alphanumeric "
                "characters and single hyphens, and cannot start or end with a hyphen (max 39 characters)."
            )
        return cleaned

    @classmethod
    def get_headers(cls) -> Dict[str, str]:
        """Construct HTTP headers with User-Agent and optional server-side token."""
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "PortfolioAI-App/1.0",
        }

        token = ""
        try:
            token = (
                current_app.config.get("GITHUB_TOKEN")
                or os.environ.get("GITHUB_TOKEN", "")
            ).strip()
        except RuntimeError:
            token = os.environ.get("GITHUB_TOKEN", "").strip()

        if token:
            headers["Authorization"] = f"Bearer {token}"

        return headers

    @classmethod
    def fetch_user_repositories(
        cls,
        username: str,
        page: int = 1,
        per_page: int = 100,
        sort: str = "updated",
        direction: str = "desc",
    ) -> Dict[str, Any]:
        """
        Fetch public repositories for a given GitHub username.

        Returns a dictionary:
        {
            "username": "...",
            "total_count": int,
            "repositories": [ {...}, ... ]
        }
        """
        valid_username = cls.validate_username(username)
        base_url = "https://api.github.com"
        try:
            base_url = current_app.config.get("GITHUB_API_BASE_URL", "https://api.github.com")
        except RuntimeError:
            pass

        url = f"{base_url}/users/{valid_username}/repos"
        headers = cls.get_headers()
        params = {
            "page": max(1, page),
            "per_page": min(100, max(1, per_page)),
            "sort": sort,
            "direction": direction,
            "type": "public",
        }

        try:
            response = requests.get(url, headers=headers, params=params, timeout=8)
        except requests.exceptions.Timeout:
            raise GitHubNetworkError(
                "Connection to GitHub API timed out (8 seconds). Please check your internet connection."
            )
        except requests.exceptions.RequestException as e:
            raise GitHubNetworkError(
                f"Network error while connecting to GitHub API: {str(e)}"
            )

        # Handle HTTP status codes
        if response.status_code == 200:
            repos_data = response.json()
            if not isinstance(repos_data, list):
                repos_data = []

            transformed: List[Dict[str, Any]] = []
            for r in repos_data:
                transformed.append(cls._format_repository(r))

            return {
                "username": valid_username,
                "total_count": len(transformed),
                "repositories": transformed,
            }

        elif response.status_code == 404:
            raise GitHubUserNotFoundError(
                f"GitHub user '{valid_username}' was not found on GitHub."
            )

        elif response.status_code == 403:
            remaining = response.headers.get("X-RateLimit-Remaining", "")
            if remaining == "0" or "rate limit" in response.text.lower():
                raise GitHubRateLimitError(
                    "GitHub API rate limit reached for unauthenticated requests. "
                    "Please wait a few minutes before trying again or configure a GITHUB_TOKEN."
                )
            raise GitHubServiceError(
                f"GitHub access forbidden (HTTP 403): {response.text[:200]}"
            )

        else:
            raise GitHubServiceError(
                f"GitHub API returned unexpected status {response.status_code}. Please try again."
            )

    @classmethod
    def _format_repository(cls, raw: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize raw GitHub repository JSON into application domain format."""
        topics = raw.get("topics") or []
        if not isinstance(topics, list):
            topics = []

        description = (raw.get("description") or "").strip()
        language = raw.get("language") or "Other"
        homepage = (raw.get("homepage") or "").strip()

        return {
            "name": raw.get("name", "Untitled Repo"),
            "full_name": raw.get("full_name", ""),
            "description": description,
            "html_url": raw.get("html_url", ""),
            "language": language,
            "stars": int(raw.get("stargazers_count", 0)),
            "forks": int(raw.get("forks_count", 0)),
            "topics": topics,
            "updated_at": raw.get("updated_at", ""),
            "homepage": homepage if (homepage.startswith("http://") or homepage.startswith("https://")) else None,
            "is_fork": bool(raw.get("fork", False)),
            "default_branch": raw.get("default_branch", "main"),
        }

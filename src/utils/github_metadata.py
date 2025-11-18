#!/usr/bin/env python3
import logging

logger = logging.getLogger(__name__)
"""
GitHub Metadata Extractor
Fetches repository information from GitHub API
"""

import re
from datetime import datetime
from typing import Any, Dict, Optional

import httpx


def extract_github_url_parts(url: str) -> Optional[tuple]:
    """
    Extract owner and repo from GitHub URL

    Args:
        url: GitHub URL

    Returns:
        Tuple of (owner, repo) or None
    """
    patterns = [
        r"github\.com/([^/]+)/([^/]+)",
        r"github\.com/([^/]+)/([^/?#]+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            owner, repo = match.groups()
            # Clean repo name (remove .git, trailing slashes, etc)
            repo = repo.replace(".git", "").strip("/")
            return owner, repo

    return None


def get_github_metadata(url: str, timeout: int = 5) -> Dict[str, Any]:
    """
    Fetch GitHub repository metadata

    Args:
        url: GitHub repository URL
        timeout: Request timeout in seconds

    Returns:
        Dictionary with repo metadata
    """
    # Extract owner/repo
    parts = extract_github_url_parts(url)
    if not parts:
        return {
            "name": "Unknown",
            "url": url,
            "stars": 0,
            "description": "GitHub repository",
            "language": "Unknown",
            "topics": [],
            "error": "Could not parse GitHub URL",
        }

    owner, repo = parts

    try:
        # GitHub API endpoint
        api_url = f"https://api.github.com/repos/{owner}/{repo}"

        # Make request
        response = httpx.get(api_url, timeout=timeout, follow_redirects=True)

        if response.status_code != 200:
            return {
                "name": repo,
                "url": url,
                "stars": 0,
                "description": f"GitHub repository by {owner}",
                "language": "Unknown",
                "topics": [],
                "error": f"API returned {response.status_code}",
            }

        data = response.json()

        # Extract metadata
        metadata = {
            "name": data.get("name", repo),
            "full_name": data.get("full_name", f"{owner}/{repo}"),
            "url": url,
            "api_url": api_url,
            "homepage": data.get("homepage"),
            # Stats
            "stars": data.get("stargazers_count", 0),
            "forks": data.get("forks_count", 0),
            "watchers": data.get("watchers_count", 0),
            "open_issues": data.get("open_issues_count", 0),
            # Info
            "description": data.get("description", "No description provided"),
            "language": data.get("language", "Unknown"),
            "topics": data.get("topics", []),
            # Meta
            "created_at": data.get("created_at"),
            "updated_at": data.get("updated_at"),
            "pushed_at": data.get("pushed_at"),
            # License
            "license": data.get("license", {}).get("name", "No license")
            if data.get("license")
            else "No license",
            # Owner
            "owner": owner,
            "owner_type": data.get("owner", {}).get("type", "User"),
            # Status
            "archived": data.get("archived", False),
            "disabled": data.get("disabled", False),
            # Categorization
            "category": categorize_repo(data),
            "use_cases": generate_use_cases(data),
            "why_matters": generate_why_matters(data),
        }

        return metadata

    except httpx.TimeoutException:
        logger.error(f"Error: {e}")
        return {
            "name": repo,
            "url": url,
            "stars": 0,
            "description": f"GitHub repository by {owner}",
            "language": "Unknown",
            "topics": [],
            "error": "Request timeout",
        }
    except Exception as e:
        logger.error(f"Error: {e}")
        return {
            "name": repo,
            "url": url,
            "stars": 0,
            "description": f"GitHub repository by {owner}",
            "language": "Unknown",
            "topics": [],
            "error": str(e),
        }


def categorize_repo(data: Dict[str, Any]) -> str:
    """Categorize repository based on metadata"""

    topics = data.get("topics", [])
    language = data.get("language", "").lower()
    description = data.get("description", "").lower()

    # Check topics and description for category hints
    if any(
        topic in ["ai", "ml", "machine-learning", "deep-learning", "llm"]
        for topic in topics
    ):
        return "AI/ML"
    elif any(
        topic in ["web", "frontend", "react", "vue", "angular"] for topic in topics
    ):
        return "Web Development"
    elif any(topic in ["devops", "ci-cd", "kubernetes", "docker"] for topic in topics):
        return "DevOps"
    elif any(topic in ["data", "database", "sql"] for topic in topics):
        return "Data"
    elif any(topic in ["security", "cryptography"] for topic in topics):
        return "Security"
    elif "framework" in description or "library" in description:
        return "Framework/Library"
    elif "tool" in description:
        return "Tool"
    else:
        return "General"


def generate_use_cases(data: Dict[str, Any]) -> str:
    """Generate use cases based on repo metadata"""

    topics = data.get("topics", [])
    description = data.get("description", "").lower()

    use_cases = []

    # AI/ML
    if any(word in description for word in ["model", "training", "inference", "llm"]):
        use_cases.append("Training and deploying ML models")

    # Web dev
    if any(word in description for word in ["web", "frontend", "ui", "react"]):
        use_cases.append("Building web applications")

    # DevOps
    if any(word in description for word in ["deploy", "ci/cd", "automation"]):
        use_cases.append("Automating deployments")

    # API/Backend
    if any(word in description for word in ["api", "backend", "server"]):
        use_cases.append("Building APIs and backends")

    if not use_cases:
        # Generic based on category
        category = categorize_repo(data)
        if category == "Framework/Library":
            use_cases.append("Development framework")
        elif category == "Tool":
            use_cases.append("Developer tooling")
        else:
            use_cases.append("Software development")

    return " • ".join(use_cases)


def generate_why_matters(data: Dict[str, Any]) -> str:
    """Generate 'why this matters' explanation"""

    stars = data.get("stargazers_count", 0)
    topics = data.get("topics", [])
    description = data.get("description", "")

    reasons = []

    # Popularity
    if stars > 50000:
        reasons.append("extremely popular")
    elif stars > 10000:
        reasons.append("widely adopted")
    elif stars > 1000:
        reasons.append("growing community")

    # Innovation
    if any(
        word in description.lower()
        for word in ["first", "revolutionary", "breakthrough", "innovative"]
    ):
        reasons.append("innovative approach")

    # Industry adoption
    if any(
        word in description.lower() for word in ["production", "enterprise", "industry"]
    ):
        reasons.append("production-ready")

    # Active development
    if data.get("open_issues_count", 0) > 100:
        reasons.append("actively maintained")

    if not reasons:
        return "Useful tool for developers"

    return f"Notable for being {' and '.join(reasons)}"


def format_github_display(metadata: Dict[str, Any]) -> str:
    """
    Format GitHub metadata for display

    Args:
        metadata: Repository metadata

    Returns:
        Formatted string for display
    """
    lines = [
        f"🛠️  **{metadata['full_name']}**",
        f"⭐ {metadata['stars']:,} stars | {metadata['language']} | {metadata['category']}",
        "",
        metadata["description"],
        "",
        f"**Use Cases:**",
        f"• {metadata['use_cases']}",
        "",
        f"**Why This Matters:**",
        f"{metadata['why_matters']}",
    ]

    if metadata.get("topics"):
        lines.append("")
        lines.append(f"**Topics:** {', '.join(metadata['topics'][:5])}")

    if metadata.get("homepage"):
        lines.append("")
        lines.append(f"🌐 {metadata['homepage']}")

    lines.append("")
    lines.append(f"🔗 {metadata['url']}")

    return "\n".join(lines)


def test_github_metadata():
    """Test GitHub metadata extraction"""

    test_urls = [
        "https://github.com/microsoft/vscode",
        "https://github.com/openai/whisper",
        "https://github.com/vercel/next.js",
    ]

    logger.info("🧪 Testing GitHub Metadata Extraction\n")

    for url in test_urls:
        logger.info(f"Testing: {url}")
        metadata = get_github_metadata(url)

        logger.info(f"  Name: {metadata['name']}")
        logger.info(f"  Stars: {metadata['stars']:,}")
        logger.info(f"  Language: {metadata['language']}")
        logger.info(f"  Category: {metadata.get('category', 'Unknown')}")
        logger.info(f"  Description: {metadata['description'][:60]}...")
        logger.info()

    logger.info("✅ Test complete!")


if __name__ == "__main__":
    test_github_metadata()

#!/usr/bin/env python3
"""
GitHub Research Agent
Deep analysis of GitHub repositories to provide actionable intelligence
"""

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class GitHubResearchAgent:
    """
    Deep GitHub repository analysis agent

    Capabilities:
    - README analysis
    - Code structure review
    - Usage guide generation
    - Related tools discovery
    - Quality assessment
    - Implementation guidance
    """

    def __init__(self):
        self.github_token = None  # Add if available for higher rate limits
        self.base_url = "https://api.github.com"

    async def research_repo(self, repo_url: str) -> Dict[str, Any]:
        """
        Deep research on a GitHub repository

        Args:
            repo_url: GitHub repo URL (e.g., https://github.com/owner/repo)

        Returns:
            Comprehensive analysis with actionable intelligence
        """
        logger.info(f"🔬 Deep research: {repo_url}")

        # Extract owner/repo
        match = re.search(r"github\.com/([^/]+)/([^/]+)", repo_url)
        if not match:
            return {"error": "Invalid GitHub URL"}

        owner, repo = match.groups()
        repo = repo.replace(".git", "")

        try:
            # Phase 1: Basic metadata
            metadata = await self._fetch_metadata(owner, repo)

            # Phase 2: README analysis
            readme = await self._analyze_readme(owner, repo)

            # Phase 3: Code structure
            structure = await self._analyze_structure(owner, repo)

            # Phase 4: Community metrics
            community = await self._analyze_community(owner, repo)

            # Phase 5: Related ecosystem
            ecosystem = await self._discover_ecosystem(owner, repo, metadata)

            # Phase 6: Usage guide generation
            usage_guide = self._generate_usage_guide(readme, metadata)

            # Phase 7: Quality assessment
            assessment = self._assess_quality(metadata, community, readme)

            # Compile comprehensive report
            report = {
                "repo_url": repo_url,
                "name": f"{owner}/{repo}",
                "analyzed_at": datetime.now().isoformat(),
                # Core info
                "description": metadata.get("description", ""),
                "language": metadata.get("language", ""),
                "stars": metadata.get("stargazers_count", 0),
                "forks": metadata.get("forks_count", 0),
                "watchers": metadata.get("watchers_count", 0),
                "open_issues": metadata.get("open_issues_count", 0),
                # Analysis
                "readme_analysis": readme,
                "code_structure": structure,
                "community_metrics": community,
                "ecosystem": ecosystem,
                # Content for rewriting
                "tldr": self._generate_tldr(metadata, readme, assessment),
                "use_cases": self._extract_use_cases(readme, metadata),
                "key_features": self._extract_key_features(readme, metadata),
                "why_matters": self._generate_why_matters(metadata, assessment),
                "target_audience": self._identify_target_audience(metadata, readme),
                # Quality metadata
                "quality_assessment": assessment,
                "implementation_ready": assessment["production_ready"],
                # Rewrite angles
                "rewrite_angles": self._generate_rewrite_angles(
                    metadata, readme, assessment
                ),
            }

            logger.info(f"✅ Research complete: {repo}")
            return report

        except Exception as e:
            logger.error(f"❌ Research failed: {e}")
            return {"error": str(e), "repo_url": repo_url}

    async def _fetch_metadata(self, owner: str, repo: str) -> Dict[str, Any]:
        """Fetch repository metadata from GitHub API"""

        headers = {}
        if self.github_token:
            headers["Authorization"] = f"token {self.github_token}"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/repos/{owner}/{repo}", headers=headers, timeout=10
                )

                if response.status_code == 200:
                    return response.json()

                return {}

        except Exception as e:
            logger.warning(f"Failed to fetch metadata: {e}")
            return {}

    async def _analyze_readme(self, owner: str, repo: str) -> Dict[str, Any]:
        """Analyze README for key information"""

        headers = {"Accept": "application/vnd.github.raw"}
        if self.github_token:
            headers["Authorization"] = f"token {self.github_token}"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/repos/{owner}/{repo}/readme",
                    headers=headers,
                    timeout=10,
                )

                if response.status_code != 200:
                    return {"error": "README not found"}

                readme_text = response.text

                # Parse README
                analysis = {
                    "length": len(readme_text),
                    "has_installation": bool(
                        re.search(
                            r"##?\s*(Install|Installation|Setup)", readme_text, re.I
                        )
                    ),
                    "has_usage": bool(
                        re.search(
                            r"##?\s*(Usage|Getting Started|Quick Start)",
                            readme_text,
                            re.I,
                        )
                    ),
                    "has_examples": bool(
                        re.search(r"##?\s*(Example|Examples|Demo)", readme_text, re.I)
                    ),
                    "has_docs": bool(
                        re.search(r"##?\s*(Documentation|Docs)", readme_text, re.I)
                    ),
                    "has_contributing": bool(
                        re.search(
                            r"##?\s*(Contributing|Development)", readme_text, re.I
                        )
                    ),
                    "code_blocks": len(re.findall(r"```", readme_text)) // 2,
                    "sections": len(re.findall(r"^##?\s+", readme_text, re.M)),
                    "badges": len(re.findall(r"\[!\[.*?\]\(.*?\)\]", readme_text)),
                }

                # Extract installation instructions
                install_match = re.search(
                    r"##?\s*Install.*?\n(.*?)(?=\n##|$)", readme_text, re.I | re.S
                )
                if install_match:
                    analysis["installation"] = install_match.group(1).strip()[:500]

                # Extract quick start
                usage_match = re.search(
                    r"##?\s*(Usage|Getting Started|Quick Start).*?\n(.*?)(?=\n##|$)",
                    readme_text,
                    re.I | re.S,
                )
                if usage_match:
                    analysis["quick_start"] = usage_match.group(2).strip()[:500]

                # Extract first code example
                code_match = re.search(
                    r"```(?:python|javascript|js|typescript|ts)?\n(.*?)```",
                    readme_text,
                    re.S,
                )
                if code_match:
                    analysis["first_code_example"] = code_match.group(1).strip()[:300]

                return analysis

        except Exception as e:
            logger.warning(f"README analysis failed: {e}")
            return {"error": str(e)}

    async def _analyze_structure(self, owner: str, repo: str) -> Dict[str, Any]:
        """Analyze code structure"""

        headers = {}
        if self.github_token:
            headers["Authorization"] = f"token {self.github_token}"

        try:
            async with httpx.AsyncClient() as client:
                # Get repository contents
                response = await client.get(
                    f"{self.base_url}/repos/{owner}/{repo}/contents",
                    headers=headers,
                    timeout=10,
                )

                if response.status_code != 200:
                    return {}

                contents = response.json()

                structure = {
                    "has_tests": any(
                        item["name"] in ["tests", "test", "__tests__", "spec"]
                        for item in contents
                        if item["type"] == "dir"
                    ),
                    "has_docs": any(
                        item["name"] in ["docs", "documentation"]
                        for item in contents
                        if item["type"] == "dir"
                    ),
                    "has_examples": any(
                        item["name"] in ["examples", "demos", "sample"]
                        for item in contents
                        if item["type"] == "dir"
                    ),
                    "has_ci": any(
                        item["name"] == ".github"
                        for item in contents
                        if item["type"] == "dir"
                    ),
                    "has_package_json": any(
                        item["name"] == "package.json" for item in contents
                    ),
                    "has_requirements": any(
                        item["name"]
                        in ["requirements.txt", "setup.py", "pyproject.toml"]
                        for item in contents
                    ),
                    "has_dockerfile": any(
                        item["name"] in ["Dockerfile", "docker-compose.yml"]
                        for item in contents
                    ),
                    "has_license": any(
                        "license" in item["name"].lower() for item in contents
                    ),
                    "file_count": len(
                        [item for item in contents if item["type"] == "file"]
                    ),
                    "dir_count": len(
                        [item for item in contents if item["type"] == "dir"]
                    ),
                }

                return structure

        except Exception as e:
            logger.warning(f"Structure analysis failed: {e}")
            return {}

    async def _analyze_community(self, owner: str, repo: str) -> Dict[str, Any]:
        """Analyze community health"""

        headers = {}
        if self.github_token:
            headers["Authorization"] = f"token {self.github_token}"

        try:
            async with httpx.AsyncClient() as client:
                # Get recent commits
                commits_response = await client.get(
                    f"{self.base_url}/repos/{owner}/{repo}/commits",
                    headers=headers,
                    params={"per_page": 10},
                    timeout=10,
                )

                # Get contributors
                contributors_response = await client.get(
                    f"{self.base_url}/repos/{owner}/{repo}/contributors",
                    headers=headers,
                    params={"per_page": 10},
                    timeout=10,
                )

                # Get recent issues
                issues_response = await client.get(
                    f"{self.base_url}/repos/{owner}/{repo}/issues",
                    headers=headers,
                    params={"state": "all", "per_page": 20},
                    timeout=10,
                )

                commits = (
                    commits_response.json()
                    if commits_response.status_code == 200
                    else []
                )
                contributors = (
                    contributors_response.json()
                    if contributors_response.status_code == 200
                    else []
                )
                issues = (
                    issues_response.json() if issues_response.status_code == 200 else []
                )

                # Calculate metrics
                recent_commits = (
                    len([c for c in commits if c]) if isinstance(commits, list) else 0
                )

                closed_issues = len(
                    [
                        i
                        for i in issues
                        if isinstance(i, dict) and i.get("state") == "closed"
                    ]
                )
                total_issues = len(issues)
                issue_close_rate = (
                    (closed_issues / total_issues * 100) if total_issues > 0 else 0
                )

                return {
                    "active_contributors": len(contributors)
                    if isinstance(contributors, list)
                    else 0,
                    "recent_commit_count": recent_commits,
                    "issue_close_rate": round(issue_close_rate, 1),
                    "total_recent_issues": total_issues,
                    "community_score": self._calculate_community_score(
                        recent_commits,
                        len(contributors) if isinstance(contributors, list) else 0,
                        issue_close_rate,
                    ),
                }

        except Exception as e:
            logger.warning(f"Community analysis failed: {e}")
            return {}

    def _calculate_community_score(
        self, commits: int, contributors: int, close_rate: float
    ) -> float:
        """Calculate community health score (0-10)"""

        score = 0.0

        # Commit activity (0-4 points)
        score += min(commits / 2.5, 4.0)

        # Contributor count (0-3 points)
        score += min(contributors / 3.3, 3.0)

        # Issue close rate (0-3 points)
        score += (close_rate / 100) * 3.0

        return round(score, 1)

    async def _discover_ecosystem(
        self, owner: str, repo: str, metadata: Dict
    ) -> Dict[str, List[str]]:
        """Discover related tools and alternatives"""

        # Extract topics/tags
        topics = metadata.get("topics", [])
        language = metadata.get("language", "")

        ecosystem = {
            "topics": topics,
            "language": language,
            "related_tools": [],
            "alternatives": [],
            "complements": [],
        }

        # TODO: Could enhance with GitHub search API to find similar repos
        # For now, return basic ecosystem info

        return ecosystem

    def _generate_usage_guide(self, readme: Dict, metadata: Dict) -> Dict[str, Any]:
        """Generate practical usage guide"""

        guide = {
            "installation": readme.get("installation", ""),
            "quick_start": readme.get("quick_start", ""),
            "code_example": readme.get("first_code_example", ""),
            "requirements": [],
        }

        # Add language-specific install commands
        language = metadata.get("language", "").lower()
        repo_name = metadata.get("name", "")

        if language == "python":
            guide["install_command"] = f"pip install {repo_name}"
        elif language in ["javascript", "typescript"]:
            guide["install_command"] = f"npm install {repo_name}"
        elif language == "rust":
            guide["install_command"] = f"cargo add {repo_name}"
        elif language == "go":
            guide[
                "install_command"
            ] = f"go get github.com/{metadata.get('full_name', '')}"

        return guide

    def _assess_quality(
        self, metadata: Dict, community: Dict, readme: Dict
    ) -> Dict[str, Any]:
        """Assess repository quality"""

        stars = metadata.get("stargazers_count", 0)
        has_license = "license" in metadata
        readme_score = self._score_readme(readme)
        community_score = community.get("community_score", 0)

        # Calculate overall scores
        popularity_score = min(stars / 10000, 10.0)  # 10K stars = 10/10
        documentation_score = readme_score
        maintenance_score = community_score

        overall_score = (
            popularity_score * 0.3 + documentation_score * 0.4 + maintenance_score * 0.3
        )

        assessment = {
            "popularity_score": round(popularity_score, 1),
            "documentation_score": round(documentation_score, 1),
            "maintenance_score": round(maintenance_score, 1),
            "overall_score": round(overall_score, 1),
            "has_license": has_license,
            "production_ready": overall_score >= 6.0 and has_license,
            "recommendation": self._get_recommendation(overall_score, has_license),
        }

        return assessment

    def _score_readme(self, readme: Dict) -> float:
        """Score README quality (0-10)"""

        if "error" in readme:
            return 0.0

        score = 0.0

        # Basic sections (5 points)
        score += 1.0 if readme.get("has_installation") else 0
        score += 1.5 if readme.get("has_usage") else 0
        score += 1.0 if readme.get("has_examples") else 0
        score += 0.5 if readme.get("has_docs") else 0
        score += 1.0 if readme.get("code_blocks", 0) > 0 else 0

        # Quality indicators (5 points)
        score += min(readme.get("sections", 0) / 10, 2.0)
        score += min(readme.get("length", 0) / 5000, 2.0)
        score += 1.0 if readme.get("badges", 0) > 0 else 0

        return round(min(score, 10.0), 1)

    def _get_recommendation(self, score: float, has_license: bool) -> str:
        """Get usage recommendation"""

        if not has_license:
            return "⚠️ Check license before using"
        elif score >= 8.0:
            return "✅ Excellent - Ready for production"
        elif score >= 6.0:
            return "✅ Good - Suitable for most projects"
        elif score >= 4.0:
            return "⚠️ Fair - Review before using"
        else:
            return "❌ Poor - Consider alternatives"

    def _generate_tldr(self, metadata: Dict, readme: Dict, assessment: Dict) -> str:
        """Generate TLDR summary"""

        description = metadata.get("description", "")
        stars = metadata.get("stargazers_count", 0)
        language = metadata.get("language", "")
        score = assessment["overall_score"]

        parts = []

        if description:
            parts.append(description[:100])

        if stars > 1000:
            parts.append(f"⭐ {stars:,} stars")

        if language:
            parts.append(f"Language: {language}")

        parts.append(f"Quality: {score}/10")

        return " • ".join(parts)

    def _extract_use_cases(self, readme: Dict, metadata: Dict) -> List[str]:
        """Extract practical use cases for rewriting"""

        use_cases = []
        description = metadata.get("description", "").lower()
        readme_text = str(readme.get("quick_start", "")).lower()

        # Pattern matching for common use cases
        use_case_patterns = {
            "web development": ["web", "frontend", "backend", "api", "server"],
            "data analysis": ["data", "analytics", "visualization", "processing"],
            "machine learning": ["ml", "ai", "model", "training", "inference"],
            "automation": ["automation", "script", "workflow", "ci/cd"],
            "mobile development": ["mobile", "ios", "android", "react native"],
            "developer tools": ["tool", "cli", "utility", "helper"],
            "testing": ["test", "testing", "qa", "automation"],
            "security": ["security", "encryption", "authentication", "auth"],
            "monitoring": ["monitor", "logging", "metrics", "observability"],
        }

        combined_text = f"{description} {readme_text}"

        for use_case, keywords in use_case_patterns.items():
            if any(keyword in combined_text for keyword in keywords):
                use_cases.append(use_case)

        return use_cases[:5] if use_cases else ["general development"]

    def _extract_key_features(self, readme: Dict, metadata: Dict) -> List[str]:
        """Extract key features for rewriting"""

        features = []

        # From description
        description = metadata.get("description", "")
        if description:
            features.append(description[:100])

        # From README
        if readme.get("has_examples"):
            features.append("Comprehensive examples included")

        if readme.get("has_docs"):
            features.append("Well-documented")

        if readme.get("code_blocks", 0) > 3:
            features.append("Easy to understand with code samples")

        # From metadata
        stars = metadata.get("stargazers_count", 0)
        if stars > 10000:
            features.append(f"Highly popular ({stars:,} stars)")
        elif stars > 1000:
            features.append(f"Popular in community ({stars:,} stars)")

        return features[:5]

    def _generate_why_matters(self, metadata: Dict, assessment: Dict) -> str:
        """Generate 'why this matters' for rewriting"""

        stars = metadata.get("stargazers_count", 0)
        language = metadata.get("language", "")
        score = assessment["overall_score"]

        reasons = []

        if stars > 50000:
            reasons.append("Industry-leading solution")
        elif stars > 10000:
            reasons.append("Widely adopted by developers")
        elif stars > 1000:
            reasons.append("Growing community adoption")

        if score >= 8:
            reasons.append("Excellent quality and documentation")
        elif score >= 6:
            reasons.append("Solid choice for most projects")

        if language:
            reasons.append(f"Built with {language}")

        return " • ".join(reasons) if reasons else "Useful development tool"

    def _identify_target_audience(self, metadata: Dict, readme: Dict) -> List[str]:
        """Identify target audience for persona-based rewriting"""

        audiences = []
        description = metadata.get("description", "").lower()
        language = metadata.get("language", "").lower()

        # Developer types
        if any(
            term in description for term in ["beginner", "getting started", "tutorial"]
        ):
            audiences.append("beginners")

        if any(term in description for term in ["production", "scale", "enterprise"]):
            audiences.append("senior developers")

        if any(term in description for term in ["startup", "mvp", "rapid"]):
            audiences.append("startup founders")

        # By language
        if language in ["python", "javascript", "typescript"]:
            audiences.append(f"{language} developers")

        # By role
        if any(term in description for term in ["devops", "infrastructure", "deploy"]):
            audiences.append("DevOps engineers")

        if any(term in description for term in ["data", "analytics", "ml"]):
            audiences.append("data scientists")

        if any(term in description for term in ["frontend", "ui", "react", "vue"]):
            audiences.append("frontend developers")

        return audiences[:3] if audiences else ["developers"]

    def _generate_rewrite_angles(
        self, metadata: Dict, readme: Dict, assessment: Dict
    ) -> List[Dict[str, str]]:
        """Generate different angles for persona-based rewriting"""

        angles = []

        # Technical angle (for dev community)
        angles.append(
            {
                "persona": "technical",
                "angle": "Deep dive into architecture and implementation",
                "hook": f"How {metadata.get('name', 'this tool')} achieves {metadata.get('description', 'its goals')}",
            }
        )

        # Practical angle (for builders)
        angles.append(
            {
                "persona": "builder",
                "angle": "Real-world applications and use cases",
                "hook": f"5 ways to use {metadata.get('name', 'this tool')} in your projects",
            }
        )

        # Beginner angle (for learners)
        angles.append(
            {
                "persona": "learner",
                "angle": "Getting started and learning path",
                "hook": f"Complete beginner's guide to {metadata.get('name', 'this tool')}",
            }
        )

        # Trend angle (for news/updates)
        if metadata.get("stargazers_count", 0) > 10000:
            angles.append(
                {
                    "persona": "trendsetter",
                    "angle": "Why everyone is talking about this",
                    "hook": f"Why {metadata.get('name', 'this tool')} is trending ({metadata.get('stargazers_count', 0):,} stars)",
                }
            )

        return angles


# Singleton instance
_github_agent = None


def get_github_agent() -> GitHubResearchAgent:
    """Get global GitHub research agent"""
    global _github_agent
    if _github_agent is None:
        _github_agent = GitHubResearchAgent()
    return _github_agent


async def test_agent():
    """Test GitHub research agent"""

    logger.info("🧪 Testing GitHub Research Agent\n")

    agent = get_github_agent()

    # Test with a popular repo
    repo_url = "https://github.com/openai/whisper"

    logger.info(f"Researching: {repo_url}\n")

    report = await agent.research_repo(repo_url)

    logger.info("=" * 70)
    logger.info("📊 RESEARCH REPORT")
    print("=" * 70)
    logger.info()
    logger.info(f"Repo: {report['name']}")
    logger.info(f"Description: {report['description']}")
    logger.info(f"Stars: {report['stars']:,}")
    logger.info(f"Language: {report['language']}")
    logger.info()
    logger.info(f"TLDR: {report['tldr']}")
    logger.info()
    logger.info(f"Quality Assessment:")
    logger.info(f"  • Overall: {report['quality_assessment']['overall_score']}/10")
    logger.info(f"  • Recommendation: {report['quality_assessment']['recommendation']}")
    logger.info()
    logger.info(f"Action Items:")
    for action in report["action_items"]:
        logger.info(f"  {action}")
    logger.info()
    logger.info("✅ Agent working!")


if __name__ == "__main__":
    import asyncio

    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_agent())

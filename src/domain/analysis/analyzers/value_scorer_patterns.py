#!/usr/bin/env python3
"""
Value Scorer Patterns for BEYONDLINES
Contains pattern definitions and analysis helpers for value scoring
"""

import re
from typing import Any, Dict, List


class ValueScorerPatterns:
    """Pattern definitions and analysis helpers for value scoring"""

    def __init__(self):
        self.quality_indicators = self._load_quality_patterns()
        self.learning_keywords = self._load_learning_keywords()
        self.spam_indicators = self._load_spam_patterns()

    def _load_quality_patterns(self) -> List[str]:
        """Load quality indicator patterns"""
        return [
            # Technical and educational content
            "tutorial",
            "guide",
            "how to",
            "explanation",
            "analysis",
            "research",
            "study",
            "data",
            "statistics",
            "insights",
            "findings",
            "results",
            "methodology",
            "framework",
            "architecture",
            "design",
            "implementation",
            # Professional and business content
            "strategy",
            "best practices",
            "case study",
            "industry",
            "market",
            "trends",
            "innovation",
            "leadership",
            "management",
            "productivity",
            "efficiency",
            "optimization",
            "scalability",
            "performance",
            # Knowledge sharing
            "learned",
            "discovered",
            "realized",
            "understanding",
            "concept",
            "principle",
            "theory",
            "practice",
            "experience",
            "lesson",
            "takeaway",
            "insight",
            "perspective",
            "opinion",
            "thoughts",
            # Problem-solving
            "solution",
            "problem",
            "challenge",
            "issue",
            "fix",
            "resolve",
            "improve",
            "enhance",
            "optimize",
            "streamline",
            "automate",
            "debug",
            "troubleshoot",
            "diagnose",
            "identify",
            "address",
        ]

    def _load_learning_keywords(self) -> List[str]:
        """Load learning potential keywords"""
        return [
            # Educational content
            "learn",
            "teach",
            "educate",
            "explain",
            "demonstrate",
            "show",
            "illustrate",
            "example",
            "instance",
            "sample",
            "template",
            "pattern",
            "approach",
            "method",
            "technique",
            "strategy",
            # Knowledge transfer
            "share",
            "knowledge",
            "wisdom",
            "expertise",
            "experience",
            "insight",
            "understanding",
            "comprehension",
            "grasp",
            "mastery",
            "skill",
            "ability",
            "capability",
            "competence",
            "proficiency",
            # Development and growth
            "develop",
            "improve",
            "enhance",
            "advance",
            "progress",
            "evolve",
            "grow",
            "expand",
            "extend",
            "upgrade",
            "refine",
            "polish",
            "perfect",
            "optimize",
            "maximize",
            "minimize",
            "streamline",
            # Innovation and creativity
            "innovate",
            "create",
            "invent",
            "design",
            "build",
            "construct",
            "develop",
            "engineer",
            "architect",
            "craft",
            "forge",
            "shape",
            "mold",
            "form",
            "establish",
            "found",
            "initiate",
            "launch",
        ]

    def _load_spam_patterns(self) -> List[str]:
        """Load spam indicator patterns"""
        return [
            # Promotional content
            "buy now",
            "click here",
            "limited time",
            "act now",
            "don't miss",
            "exclusive offer",
            "special deal",
            "discount",
            "sale",
            "promotion",
            "free trial",
            "sign up",
            "subscribe",
            "join now",
            "get started",
            # Spammy language
            "make money",
            "earn cash",
            "work from home",
            "get rich",
            "quick cash",
            "easy money",
            "guaranteed",
            "no risk",
            "100% free",
            "instant",
            "miracle",
            "secret",
            "hidden",
            "exposed",
            "revealed",
            "shocking",
            # Low-quality indicators
            "lol",
            "haha",
            "omg",
            "wtf",
            "fml",
            "smh",
            "tbh",
            "imo",
            "imo",
            "btw",
            "fyi",
            "asap",
            "ttyl",
            "brb",
            "gtg",
            "idk",
            "idc",
            "idgaf",
            # Repetitive content
            "follow for follow",
            "f4f",
            "like for like",
            "l4l",
            "comment for comment",
            "c4c",
            "share for share",
            "s4s",
            "tag for tag",
            "t4t",
            "dm for dm",
        ]

    def has_good_structure(self, content: str) -> bool:
        """Check if content has good structure"""
        if not content:
            return False

        # Check for paragraphs
        paragraphs = content.split("\n\n")
        if len(paragraphs) < 2:
            return False

        # Check for proper sentence structure
        sentences = re.split(r"[.!?]+", content)
        if len(sentences) < 3:
            return False

        # Check for variety in sentence length
        sentence_lengths = [len(s.strip()) for s in sentences if s.strip()]
        if len(sentence_lengths) < 2:
            return False

        # Check for reasonable sentence length variation
        avg_length = sum(sentence_lengths) / len(sentence_lengths)
        if avg_length < 20 or avg_length > 200:
            return False

        return True

    def has_technical_depth(self, content: str) -> bool:
        """Check if content has technical depth"""
        if not content:
            return False

        # Technical terms and concepts
        technical_terms = [
            "algorithm",
            "data structure",
            "database",
            "API",
            "framework",
            "architecture",
            "design pattern",
            "optimization",
            "scalability",
            "performance",
            "security",
            "authentication",
            "authorization",
            "encryption",
            "compression",
            "caching",
            "load balancing",
            "microservices",
            "containerization",
            "deployment",
            "CI/CD",
            "testing",
            "debugging",
            "monitoring",
            "logging",
            "metrics",
        ]

        content_lower = content.lower()
        technical_count = sum(1 for term in technical_terms if term in content_lower)

        # Check for code snippets or technical examples
        code_indicators = [
            "```",
            "function",
            "class",
            "method",
            "variable",
            "import",
            "export",
        ]
        code_count = sum(
            1 for indicator in code_indicators if indicator in content_lower
        )

        # Check for technical explanations
        explanation_indicators = [
            "because",
            "therefore",
            "however",
            "moreover",
            "furthermore",
            "consequently",
        ]
        explanation_count = sum(
            1 for indicator in explanation_indicators if indicator in content_lower
        )

        # Score based on technical indicators
        technical_score = (technical_count * 2) + code_count + explanation_count

        return technical_score >= 3

    def analyze_content_quality(self, content: str) -> Dict[str, Any]:
        """Analyze content quality based on patterns"""
        if not content:
            return {"score": 0.0, "indicators": [], "issues": []}

        content_lower = content.lower()
        quality_score = 0.0
        quality_indicators = []
        issues = []

        # Check for quality indicators
        for indicator in self.quality_indicators:
            if indicator in content_lower:
                quality_indicators.append(indicator)
                quality_score += 0.1

        # Check for learning keywords
        learning_count = sum(
            1 for keyword in self.learning_keywords if keyword in content_lower
        )
        if learning_count > 0:
            quality_score += min(learning_count * 0.05, 0.3)
            quality_indicators.append(f"{learning_count} learning keywords")

        # Check for spam indicators
        spam_count = sum(1 for spam in self.spam_indicators if spam in content_lower)
        if spam_count > 0:
            quality_score -= min(spam_count * 0.1, 0.5)
            issues.append(f"{spam_count} spam indicators")

        # Check structure
        if self.has_good_structure(content):
            quality_score += 0.2
            quality_indicators.append("good structure")
        else:
            issues.append("poor structure")

        # Check technical depth
        if self.has_technical_depth(content):
            quality_score += 0.3
            quality_indicators.append("technical depth")

        # Normalize score
        quality_score = max(0.0, min(1.0, quality_score))

        return {
            "score": quality_score,
            "indicators": quality_indicators,
            "issues": issues,
        }

    def get_pattern_stats(self) -> Dict[str, Any]:
        """Get statistics about loaded patterns"""
        return {
            "quality_indicators": len(self.quality_indicators),
            "learning_keywords": len(self.learning_keywords),
            "spam_indicators": len(self.spam_indicators),
            "total_patterns": len(self.quality_indicators)
            + len(self.learning_keywords)
            + len(self.spam_indicators),
        }

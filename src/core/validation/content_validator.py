"""
Content validation and quality checks for scraped data
"""

import hashlib
import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from .content_quality_metrics import ContentQualityMetrics

logger = logging.getLogger(__name__)


class ContentValidator:
    """Validates content quality and structure"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.quality_metrics = ContentQualityMetrics()
        self.duplicate_cache = {}
        self.validation_history = []

    def validate_content(self, content_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate content data and return validation results

        Args:
            content_data: Dictionary containing content to validate

        Returns:
            Dictionary with validation results
        """
        result = {
            "valid": True,
            "score": 0.0,
            "issues": [],
            "warnings": [],
            "timestamp": datetime.now().isoformat(),
        }

        try:
            # Validate structure
            structure_score = self._validate_structure(content_data, result)

            # Validate quality
            quality_score = self._validate_quality(content_data, result)

            # Check for duplicates
            duplicate_score = self._check_duplicates(content_data, result)

            # Validate metadata
            metadata_score = self._validate_metadata(content_data, result)

            # Calculate overall score
            scores = [
                s
                for s in [
                    structure_score,
                    quality_score,
                    duplicate_score,
                    metadata_score,
                ]
                if s is not None
            ]
            if scores:
                result["score"] = sum(scores) / len(scores)

            # Determine if content is valid
            result["valid"] = (
                result["score"] >= 0.6
                and len(result["issues"]) == 0
                and len(result["warnings"]) <= 2
            )

            # Log validation
            self.validation_history.append(
                {
                    "content_id": content_data.get("id", "unknown"),
                    "score": result["score"],
                    "valid": result["valid"],
                    "timestamp": result["timestamp"],
                }
            )

            logger.info(
                f"Content validation: score={result['score']:.2f}, valid={result['valid']}"
            )

        except Exception as e:
            logger.error(f"Error validating content: {e}")
            result["valid"] = False
            result["score"] = 0.0
            result["issues"].append(f"Validation error: {str(e)}")

        return result

    def _validate_structure(
        self, content_data: Dict[str, Any], result: Dict[str, Any]
    ) -> float:
        """Validate content structure"""
        score = 1.0

        # Check required fields
        required_fields = ["content", "title", "author"]
        for field in required_fields:
            if field not in content_data or not content_data[field]:
                result["issues"].append(f"Missing required field: {field}")
                score -= 0.3

        # Check content type
        if "content" in content_data:
            content = content_data["content"]
            if not isinstance(content, str):
                result["issues"].append("Content must be a string")
                score -= 0.5
            elif len(content.strip()) < 10:
                result["warnings"].append("Content is very short")
                score -= 0.1

        return max(0.0, score)

    def _validate_quality(
        self, content_data: Dict[str, Any], result: Dict[str, Any]
    ) -> float:
        """Validate content quality"""
        content = content_data.get("content", "")
        title = content_data.get("title", "")

        if not content:
            return 0.0

        # Get quality score from metrics
        quality_result = self.quality_metrics.get_quality_score(content, title)

        # Add issues and warnings
        result["issues"].extend(quality_result["issues"])

        if quality_result["score"] < 0.8:
            result["warnings"].append(
                f"Low quality score: {quality_result['score']:.2f}"
            )

        return quality_result["score"]

    def _check_duplicates(
        self, content_data: Dict[str, Any], result: Dict[str, Any]
    ) -> float:
        """Check for duplicate content"""
        content = content_data.get("content", "")
        content_id = content_data.get("id", "")

        if not content:
            return 0.0

        # Create content hash
        content_hash = hashlib.md5(content.encode()).hexdigest()

        # Check if we've seen this content before
        if content_hash in self.duplicate_cache:
            result["warnings"].append("Potential duplicate content detected")
            return 0.5

        # Add to cache
        self.duplicate_cache[content_hash] = {
            "id": content_id,
            "timestamp": datetime.now(),
        }

        return 1.0

    def _validate_metadata(
        self, content_data: Dict[str, Any], result: Dict[str, Any]
    ) -> float:
        """Validate content metadata"""
        score = 1.0

        # Check URL if present
        url = content_data.get("url", "")
        if url:
            try:
                parsed = urlparse(url)
                if not parsed.scheme or not parsed.netloc:
                    result["warnings"].append("Invalid URL format")
                    score -= 0.1
            except Exception as e:
                logger.error(f"Error: {e}")
                result["warnings"].append("Malformed URL")
                score -= 0.2

        # Check timestamp if present
        timestamp = content_data.get("created_at", "")
        if timestamp:
            try:
                if isinstance(timestamp, str):
                    datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                elif isinstance(timestamp, datetime):
                    pass  # Already a datetime object
                else:
                    result["warnings"].append("Invalid timestamp format")
                    score -= 0.1
            except Exception as e:
                logger.error(f"Error: {e}")
                result["warnings"].append("Malformed timestamp")
                score -= 0.2

        # Check author if present
        author = content_data.get("author", "")
        if author and len(author.strip()) < 2:
            result["warnings"].append("Author name seems too short")
            score -= 0.1

        return max(0.0, score)

    def batch_validate(
        self, content_list: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Validate multiple content items"""
        results = []

        for content_data in content_list:
            result = self.validate_content(content_data)
            results.append(result)

        return results

    def get_validation_summary(
        self, validation_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Get summary of validation results"""
        if not validation_results:
            return {"total": 0, "valid": 0, "invalid": 0, "average_score": 0.0}

        total = len(validation_results)
        valid = sum(1 for r in validation_results if r["valid"])
        invalid = total - valid
        average_score = sum(r["score"] for r in validation_results) / total

        # Count issues and warnings
        total_issues = sum(len(r["issues"]) for r in validation_results)
        total_warnings = sum(len(r["warnings"]) for r in validation_results)

        return {
            "total": total,
            "valid": valid,
            "invalid": invalid,
            "average_score": average_score,
            "total_issues": total_issues,
            "total_warnings": total_warnings,
            "validity_rate": valid / total if total > 0 else 0.0,
        }

    def clear_duplicate_cache(self):
        """Clear the duplicate content cache"""
        self.duplicate_cache.clear()
        logger.info("Cleared duplicate content cache")

    def get_validation_stats(self) -> Dict[str, Any]:
        """Get validation statistics"""
        if not self.validation_history:
            return {"total_validations": 0, "average_score": 0.0, "validity_rate": 0.0}

        total = len(self.validation_history)
        valid = sum(1 for h in self.validation_history if h["valid"])
        average_score = sum(h["score"] for h in self.validation_history) / total

        return {
            "total_validations": total,
            "average_score": average_score,
            "validity_rate": valid / total,
            "duplicate_cache_size": len(self.duplicate_cache),
        }

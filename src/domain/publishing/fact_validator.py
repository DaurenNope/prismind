"""
Fact Preservation Validator

Extracts key facts (entities, numbers, dates) from source content and validates
they're preserved in rewritten output.
"""

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Set

logger = logging.getLogger(__name__)


class FactValidator:
    """
    Validate that key facts from source are preserved in rewritten content.

    Extracts and validates:
    - Named entities (people, companies, products)
    - Numbers (percentages, amounts, statistics)
    - Dates and times
    - URLs and references
    """

    def __init__(self):
        """Initialize fact validator"""
        # Common tech companies, products, people for quick matching
        self.known_entities = {
            # Companies
            "openai",
            "anthropic",
            "google",
            "microsoft",
            "meta",
            "apple",
            "amazon",
            "tesla",
            "twitter",
            "x.com",
            "threads",
            "instagram",
            "facebook",
            # Products
            "chatgpt",
            "claude",
            "gemini",
            "gpt-4",
            "dall-e",
            "midjourney",
            "copilot",
            "cursor",
            "github",
            "gitlab",
            # People (common in tech)
            "sam altman",
            "elon musk",
            "mark zuckerberg",
            "satya nadella",
            "sundar pichai",
            "jeff bezos",
        }

    def extract_facts(self, content: str) -> Dict[str, Any]:
        """
        Extract key facts from content

        Args:
            content: Source text

        Returns:
            Dict with extracted facts:
            {
                'numbers': List[str],
                'percentages': List[str],
                'dates': List[str],
                'entities': List[str],
                'urls': List[str]
            }
        """
        facts = {
            "numbers": self._extract_numbers(content),
            "percentages": self._extract_percentages(content),
            "dates": self._extract_dates(content),
            "entities": self._extract_entities(content),
            "urls": self._extract_urls(content),
        }

        return facts

    def _extract_numbers(self, text: str) -> List[str]:
        """Extract significant numbers (not years or common words)"""
        # Match numbers with optional commas, decimals, K/M/B suffixes
        pattern = r"\b\d+(?:,\d{3})*(?:\.\d+)?(?:[KMB])?\b"
        numbers = re.findall(pattern, text, re.IGNORECASE)

        # Filter out years (1900-2099)
        numbers = [n for n in numbers if not (n.isdigit() and 1900 <= int(n) <= 2099)]

        # Filter out common meaningless numbers
        numbers = [n for n in numbers if n not in ["1", "2", "3", "10"]]

        return list(set(numbers))

    def _extract_percentages(self, text: str) -> List[str]:
        """Extract percentages"""
        pattern = r"\b\d+(?:\.\d+)?%"
        return list(set(re.findall(pattern, text)))

    def _extract_dates(self, text: str) -> List[str]:
        """Extract dates in various formats"""
        dates = []

        # Month Day, Year (e.g., "October 27, 2024")
        pattern1 = r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b"
        dates.extend(re.findall(pattern1, text, re.IGNORECASE))

        # ISO format (2024-10-27)
        pattern2 = r"\b\d{4}-\d{2}-\d{2}\b"
        dates.extend(re.findall(pattern2, text))

        # Relative dates (e.g., "yesterday", "last week")
        pattern3 = (
            r"\b(?:yesterday|today|tomorrow|last\s+week|next\s+week|this\s+week)\b"
        )
        dates.extend(re.findall(pattern3, text, re.IGNORECASE))

        return list(set(dates))

    def _extract_entities(self, text: str) -> List[str]:
        """
        Extract named entities (simple pattern matching)

        Uses:
        1. Known entities list
        2. Capitalized words (likely proper nouns)
        3. @mentions
        """
        entities = []

        # Known entities from our list
        text_lower = text.lower()
        for entity in self.known_entities:
            if entity in text_lower:
                # Find original casing in text
                pattern = re.compile(re.escape(entity), re.IGNORECASE)
                matches = pattern.findall(text)
                if matches:
                    entities.append(matches[0])

        # Capitalized words (potential proper nouns)
        # Pattern: Word starting with capital, not at sentence start
        capitalized = re.findall(
            r"(?<!^)(?<!\. )\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", text
        )
        entities.extend(capitalized)

        # @mentions
        mentions = re.findall(r"@\w+", text)
        entities.extend(mentions)

        # Remove common words that are capitalized but not entities
        common_words = {
            "The",
            "This",
            "That",
            "These",
            "Those",
            "A",
            "An",
            "It",
            "He",
            "She",
        }
        entities = [e for e in entities if e not in common_words]

        return list(set(entities))

    def _extract_urls(self, text: str) -> List[str]:
        """Extract URLs"""
        pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        return list(set(re.findall(pattern, text)))

    def validate_preservation(
        self, source: str, output: str, critical_threshold: float = 0.8
    ) -> Dict[str, Any]:
        """
        Validate that key facts from source are preserved in output

        Args:
            source: Original source content
            output: Rewritten output
            critical_threshold: Minimum preservation rate for critical facts (0-1)

        Returns:
            Dict with validation results:
            {
                'valid': bool,
                'preservation_score': float (0-100),
                'missing_facts': Dict[str, List[str]],
                'preserved_facts': Dict[str, List[str]],
                'warnings': List[str]
            }
        """
        source_facts = self.extract_facts(source)
        output_lower = output.lower()

        missing = {
            "numbers": [],
            "percentages": [],
            "dates": [],
            "entities": [],
            "urls": [],
        }

        preserved = {
            "numbers": [],
            "percentages": [],
            "dates": [],
            "entities": [],
            "urls": [],
        }

        warnings = []

        # Check each fact type
        for fact_type, facts in source_facts.items():
            if not facts:
                continue

            for fact in facts:
                # Check if fact appears in output (case-insensitive for most)
                if fact_type == "urls":
                    # URLs must match exactly
                    found = fact in output
                else:
                    # Other facts case-insensitive
                    found = fact.lower() in output_lower

                if found:
                    preserved[fact_type].append(fact)
                else:
                    missing[fact_type].append(fact)

        # Calculate preservation score
        total_facts = sum(len(facts) for facts in source_facts.values())
        total_preserved = sum(len(facts) for facts in preserved.values())

        if total_facts == 0:
            # No facts to preserve
            preservation_score = 100.0
        else:
            preservation_score = (total_preserved / total_facts) * 100

        # Check critical facts (numbers, percentages, entities)
        critical_facts = (
            len(source_facts["numbers"])
            + len(source_facts["percentages"])
            + len(source_facts["entities"])
        )
        critical_preserved = (
            len(preserved["numbers"])
            + len(preserved["percentages"])
            + len(preserved["entities"])
        )

        if critical_facts > 0:
            critical_preservation_rate = critical_preserved / critical_facts
        else:
            critical_preservation_rate = 1.0

        # Generate warnings
        if missing["numbers"]:
            warnings.append(
                f"Missing {len(missing['numbers'])} numbers: {', '.join(missing['numbers'][:3])}"
            )

        if missing["percentages"]:
            warnings.append(
                f"Missing {len(missing['percentages'])} percentages: {', '.join(missing['percentages'])}"
            )

        if missing["entities"]:
            warnings.append(
                f"Missing {len(missing['entities'])} entities: {', '.join(missing['entities'][:3])}"
            )

        if missing["dates"]:
            warnings.append(
                f"Missing {len(missing['dates'])} dates: {', '.join(missing['dates'][:2])}"
            )

        if missing["urls"]:
            warnings.append(f"Missing {len(missing['urls'])} URLs")

        # Determine if valid
        valid = critical_preservation_rate >= critical_threshold

        result = {
            "valid": valid,
            "preservation_score": round(preservation_score, 1),
            "critical_preservation_rate": round(critical_preservation_rate * 100, 1),
            "total_facts": total_facts,
            "preserved_facts": preserved,
            "missing_facts": missing,
            "warnings": warnings,
        }

        # Log results
        if not valid:
            logger.warning(
                f"❌ Fact preservation below threshold: {critical_preservation_rate*100:.1f}% < {critical_threshold*100}%"
            )
            for warning in warnings:
                logger.warning(f"   {warning}")
        else:
            logger.info(
                f"✅ Fact preservation: {preservation_score:.1f}% ({total_preserved}/{total_facts} facts)"
            )

        return result


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    validator = FactValidator()

    # Test case
    source = """
    BREAKING: Leaked October 27 letter from OpenAI to White House shows that
    OpenAI had begun asking for Federal guarantees over a week ago.
    Sam Altman's 85% confidence claim was false. The company has raised $6.6B
    and expects 200% revenue growth next year.
    """

    output_good = """
    OpenAI запросила гарантии 27 октября. Сэм Альтман ошибся с 85%.
    Компания привлекла $6.6B и ожидает рост 200%.
    """

    output_bad = """
    OpenAI запросила гарантии от правительства. Руководство компании
    ожидает значительный рост в следующем году.
    """

    logger.info("=" * 80)
    logger.info("TEST 1: Good Output (facts preserved)")
    logger.info("=" * 80)
    result = validator.validate_preservation(source, output_good)
    logger.info(f"Valid: {result['valid']}")
    logger.info(f"Score: {result['preservation_score']}")
    logger.warning(f"Warnings: {result['warnings']}")

    logger.info("\n" + "=" * 80)
    logger.warning("TEST 2: Bad Output (facts missing)")
    logger.info("=" * 80)
    result = validator.validate_preservation(source, output_bad)
    logger.info(f"Valid: {result['valid']}")
    logger.info(f"Score: {result['preservation_score']}")
    logger.warning(f"Warnings: {result['warnings']}")

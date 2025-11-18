#!/usr/bin/env python3
import logging

logger = logging.getLogger(__name__)
"""
Academic research integration module.
This module provides capabilities to research academic papers and integrate them with our research engine.
"""

import asyncio
import os
import sys
from dataclasses import dataclass
from typing import Dict, List, Optional

import requests

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


@dataclass
class AcademicPaper:
    """Represents an academic paper."""

    title: str
    authors: List[str]
    abstract: str
    url: str
    published_date: str
    journal: Optional[str] = None
    keywords: Optional[List[str]] = None


class ArXivResearcher:
    """Researcher for arXiv papers."""

    def __init__(self):
        self.base_url = "http://export.arxiv.org/api/query"

    async def search_papers(
        self, query: str, max_results: int = 5
    ) -> List[AcademicPaper]:
        """
        Search for academic papers on arXiv.

        Args:
            query: Search query
            max_results: Maximum number of results to return

        Returns:
            List of AcademicPaper objects
        """
        # Build the search parameters
        params = {
            "search_query": query,
            "start": 0,
            "max_results": max_results,
            "sortBy": "relevance",
            "sortOrder": "descending",
        }

        try:
            # Make the request
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()

            # Parse the XML response
            papers = self._parse_arxiv_response(response.text)
            return papers

        except Exception as e:
            logger.error(f"Error searching arXiv: {e}")
            # Return empty list as fallback
            return []

    def _parse_arxiv_response(self, xml_content: str) -> List[AcademicPaper]:
        """
        Parse the arXiv XML response.

        Args:
            xml_content: XML content from arXiv API

        Returns:
            List of AcademicPaper objects
        """
        try:
            import xml.etree.ElementTree as ET
        except ImportError:
            logger.info("XML parsing library not available")
            return []

        try:
            root = ET.fromstring(xml_content)

            # Define namespaces
            namespaces = {
                "atom": "http://www.w3.org/2005/Atom",
                "arxiv": "http://arxiv.org/schemas/atom",
            }

            papers = []

            # Find all entries
            entries = root.findall("atom:entry", namespaces)

            for entry in entries:
                try:
                    # Extract title
                    title_elem = entry.find("atom:title", namespaces)
                    title = (
                        title_elem.text if title_elem is not None else "Unknown Title"
                    )

                    # Extract authors
                    authors = []
                    author_elems = entry.findall("atom:author", namespaces)
                    for author_elem in author_elems:
                        name_elem = author_elem.find("atom:name", namespaces)
                        if name_elem is not None and name_elem.text:
                            authors.append(name_elem.text)

                    # Extract abstract
                    summary_elem = entry.find("atom:summary", namespaces)
                    abstract = summary_elem.text if summary_elem is not None else ""

                    # Extract URL
                    id_elem = entry.find("atom:id", namespaces)
                    url = id_elem.text if id_elem is not None else ""

                    # Extract published date
                    published_elem = entry.find("atom:published", namespaces)
                    published_date = (
                        published_elem.text if published_elem is not None else ""
                    )

                    # Extract categories/keywords
                    categories = []
                    category_elems = entry.findall("atom:category", namespaces)
                    for category_elem in category_elems:
                        term = category_elem.get("term")
                        if term:
                            categories.append(term)

                    # Create paper object
                    paper = AcademicPaper(
                        title=title,
                        authors=authors,
                        abstract=abstract,
                        url=url,
                        published_date=published_date,
                        keywords=categories,
                    )

                    papers.append(paper)

                except Exception as e:
                    logger.error(f"Error parsing individual paper entry: {e}")
                    continue

            return papers

        except Exception as e:
            logger.error(f"Error parsing arXiv response: {e}")
            return []


class AcademicResearchEngine:
    """Main academic research engine that integrates multiple sources."""

    def __init__(self):
        self.arxiv_researcher = ArXivResearcher()

    async def research_academic_topic(
        self, topic: str, max_papers: int = 5
    ) -> List[AcademicPaper]:
        """
        Research an academic topic across multiple sources.

        Args:
            topic: Research topic
            max_papers: Maximum number of papers to return

        Returns:
            List of AcademicPaper objects
        """
        # For now, we'll just use arXiv
        papers = await self.arxiv_researcher.search_papers(topic, max_papers)
        return papers

    def format_papers_for_research_engine(self, papers: List[AcademicPaper]) -> str:
        """
        Format academic papers for integration with our research engine.

        Args:
            papers: List of AcademicPaper objects

        Returns:
            Formatted string for research engine
        """
        if not papers:
            return "No academic papers found for this topic."

        formatted_output = "Academic Research Results:\n\n"

        for i, paper in enumerate(papers, 1):
            formatted_output += f"{i}. {paper.title}\n"
            formatted_output += f"   Authors: {', '.join(paper.authors[:3])}{' et al.' if len(paper.authors) > 3 else ''}\n"
            formatted_output += f"   Published: {paper.published_date[:10]}\n"
            formatted_output += f"   URL: {paper.url}\n"
            formatted_output += f"   Abstract: {paper.abstract[:200]}...\n"

            if paper.keywords:
                formatted_output += f"   Keywords: {', '.join(paper.keywords[:5])}\n"

            formatted_output += "\n"

        return formatted_output


# Example usage
async def main():
    """Example usage of the academic research engine."""
    logger.info("Academic Research Engine Demo")
    logger.info("=" * 30)

    # Create the research engine
    engine = AcademicResearchEngine()

    # Research a topic
    topic = "large language models"
    logger.info(f"Researching academic papers on: {topic}\n")

    papers = await engine.research_academic_topic(topic, max_papers=3)

    # Format the results
    formatted_results = engine.format_papers_for_research_engine(papers)
    logger.info(formatted_results)


if __name__ == "__main__":
    asyncio.run(main())

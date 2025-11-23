#!/usr/bin/env python3
import logging

logger = logging.getLogger(__name__)
"""
Async research engine with improved performance and reduced latency.
"""

import asyncio
import concurrent.futures
import os
import sys
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

try:
    from examples.standalone_llm_enhanced_dashboard import (
        PerplexityResult,
        StandaloneLLMEnhancedPerplexityAgent,
    )

    DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Warning: Could not import research agent: {e}")
    DEPENDENCIES_AVAILABLE = False


@dataclass
class ResearchResponse:
    """Structured response from the research engine."""

    query: str
    answer: str
    sources: List[Dict[str, Any]]
    follow_up_questions: List[str]
    search_results: List[Dict[str, Any]]
    success: bool
    execution_time: float
    error_message: Optional[str] = None


class AsyncResearchEngine:
    """Async research engine with improved performance."""

    def __init__(self, serpapi_key: Optional[str] = None, llm_provider: str = "ollama"):
        """
        Initialize the research engine.

        Args:
            serpapi_key: SerpAPI key for real web search (optional)
            llm_provider: LLM provider to use ("ollama", "gemini", "mistral", "deep_research")
        """
        self.serpapi_key = serpapi_key
        self.llm_provider = llm_provider
        self.dependencies_available = DEPENDENCIES_AVAILABLE
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)

    async def research_async(self, query: str) -> ResearchResponse:
        """
        Perform research asynchronously with improved performance.

        Args:
            query: The research query

        Returns:
            ResearchResponse with the results
        """
        start_time = time.time()

        if not self.dependencies_available:
            return ResearchResponse(
                query=query,
                answer="Research engine dependencies not available.",
                sources=[],
                follow_up_questions=[],
                search_results=[],
                success=False,
                execution_time=time.time() - start_time,
                error_message="Dependencies not available",
            )

        try:
            # Create the research agent
            agent = StandaloneLLMEnhancedPerplexityAgent(
                serpapi_key=self.serpapi_key, llm_provider=self.llm_provider
            )

            # Perform the research in a separate thread to avoid blocking
            loop = asyncio.get_event_loop()
            result: PerplexityResult = await loop.run_in_executor(
                self.executor, lambda: asyncio.run(agent.research(query))
            )

            # Convert to ResearchResponse
            response = ResearchResponse(
                query=result.query,
                answer=result.answer,
                sources=[
                    {
                        "url": source.url,
                        "title": source.title,
                        "content": source.content,
                        "source_type": source.source_type,
                    }
                    for source in result.sources
                ],
                follow_up_questions=result.follow_up_questions,
                search_results=[
                    {
                        "url": search_result.url,
                        "title": search_result.title,
                        "snippet": search_result.snippet,
                        "source_type": search_result.source_type,
                        "relevance_score": search_result.relevance_score,
                    }
                    for search_result in result.search_results
                ],
                success=True,
                execution_time=time.time() - start_time,
            )

            return response

        except Exception as e:
            logger.error(f"Error: {e}")
            return ResearchResponse(
                query=query,
                answer="",
                sources=[],
                follow_up_questions=[],
                search_results=[],
                success=False,
                execution_time=time.time() - start_time,
                error_message=str(e),
            )

    async def research_multiple_async(
        self, queries: List[str]
    ) -> List[ResearchResponse]:
        """
        Perform multiple research queries concurrently.

        Args:
            queries: List of research queries

        Returns:
            List of ResearchResponse objects
        """
        # Create tasks for all queries
        tasks = [self.research_async(query) for query in queries]

        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle any exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(
                    ResearchResponse(
                        query=queries[i],
                        answer="",
                        sources=[],
                        follow_up_questions=[],
                        search_results=[],
                        success=False,
                        execution_time=0.0,
                        error_message=str(result),
                    )
                )
            else:
                processed_results.append(result)

        return processed_results

    def research_sync(self, query: str) -> ResearchResponse:
        """
        Perform research synchronously.

        Args:
            query: The research query

        Returns:
            ResearchResponse with the results
        """
        return asyncio.run(self.research_async(query))

    def format_response(self, response: ResearchResponse) -> str:
        """
        Format the response for display.

        Args:
            response: The ResearchResponse to format

        Returns:
            Formatted string representation
        """
        if not response.success:
            return f"Error: {response.error_message}"

        # Format sources
        formatted_sources = (
            "\n".join(
                [
                    f"  {i+1}. {source['title']} ({source['source_type']}): {source['url']}"
                    for i, source in enumerate(response.sources[:5])
                ]
            )
            if response.sources
            else "  No sources found."
        )

        # Format follow-up questions
        formatted_questions = (
            "\n".join(
                [
                    f"  {i+1}. {question}"
                    for i, question in enumerate(response.follow_up_questions[:5])
                ]
            )
            if response.follow_up_questions
            else "  No follow-up questions generated."
        )

        # Create the formatted result
        formatted_result = f"""
RESEARCH RESULTS
================

Query: {response.query}
Execution Time: {response.execution_time:.2f} seconds

Answer:
{response.answer}

Sources:
{formatted_sources}

Follow-up Questions:
{formatted_questions}
"""

        return formatted_result


# CLI interface
async def main():
    """CLI interface for the async research engine."""
    if len(sys.argv) < 2:
        logger.info("Usage: python async_research_engine.py <query>")
        logger.info(
            "Example: python async_research_engine.py 'Compare Qwen2.5 and Llama3'"
        )
        return

    query = " ".join(sys.argv[1:])

    logger.info("Initializing async research engine...")
    engine = AsyncResearchEngine()

    logger.info(f"Researching: {query}")
    response = await engine.research_async(query)

    logger.info(engine.format_response(response))


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""
FastAPI-based API layer for the research engine.
"""

import sys
import os
from typing import List, Optional
from pydantic import BaseModel

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Import our research engine
try:
    from src.core.unified_interface import UnifiedResearchEngine, ResearchResponse
    RESEARCH_ENGINE_AVAILABLE = True
except ImportError:
    RESEARCH_ENGINE_AVAILABLE = False
    print("Warning: Research engine not available")

# Create FastAPI app
app = FastAPI(
    title="PrisMind Research API",
    description="API for the PrisMind research engine",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for API
class ResearchRequest(BaseModel):
    query: str
    llm_provider: str = "ollama"
    serpapi_key: Optional[str] = None

class ResearchResult(BaseModel):
    query: str
    answer: str
    sources: List[dict]
    follow_up_questions: List[str]
    search_results: List[dict]
    success: bool
    error_message: Optional[str] = None

# Initialize research engine
if RESEARCH_ENGINE_AVAILABLE:
    research_engine = UnifiedResearchEngine()
else:
    research_engine = None

@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "PrisMind Research API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "research_engine_available": RESEARCH_ENGINE_AVAILABLE
    }

@app.post("/research", response_model=ResearchResult)
async def perform_research(request: ResearchRequest):
    """Perform research on a given query."""
    if not RESEARCH_ENGINE_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Research engine not available"
        )
    
    try:
        # Perform research
        response = research_engine.research_sync(request.query)
        
        # Convert to API response model
        return ResearchResult(
            query=response.query,
            answer=response.answer,
            sources=response.sources,
            follow_up_questions=response.follow_up_questions,
            search_results=response.search_results,
            success=response.success,
            error_message=response.error_message
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error performing research: {str(e)}"
        )

@app.get("/providers")
async def get_llm_providers():
    """Get available LLM providers."""
    return {
        "providers": [
            "ollama",
            "gemini",
            "mistral"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
#!/usr/bin/env python3
"""
Frontend API for Persona Management and Content Generation

This module provides REST API endpoints for the frontend to:
1. Create personas from uploaded examples
2. Generate content using dynamic personas
3. Get performance analytics
4. Manage persona optimization
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from src.domain.publishing.dynamic_rewriter import DynamicRewriter
from src.domain.publishing.learning_loop import learning_analyzer

logger = logging.getLogger(__name__)

# Create API router
router = APIRouter(prefix="/api/personas", tags=["personas"])

# Initialize the dynamic rewriter
try:
    rewriter = DynamicRewriter()
    logger.info("✅ Persona API initialized with DynamicRewriter")
except Exception as e:
    logger.error(f"Failed to initialize DynamicRewriter: {e}")
    rewriter = None


# Pydantic models for API requests/responses
class PersonaCreateRequest(BaseModel):
    name: str
    handle: str
    description: str
    platforms: List[str]
    examples: List[str]


class PersonaResponse(BaseModel):
    id: str
    name: str
    handle: str
    description: str
    platforms: List[str]
    quality_metrics: Dict[str, float]
    created_at: str


class ContentGenerationRequest(BaseModel):
    persona_id: str
    topic: str
    category: Optional[str] = "general"
    platform: str = "twitter"
    options: Optional[Dict[str, Any]] = {}


class ContentGenerationResponse(BaseModel):
    success: bool
    persona_id: str
    persona_name: str
    platform: str
    content: Optional[str] = None
    quality_score: Optional[float] = None
    length: Optional[int] = None
    generated_at: str
    error: Optional[str] = None


class VoiceAnalysisRequest(BaseModel):
    examples: List[str]


class VoiceAnalysisResponse(BaseModel):
    patterns: Dict[str, Any]
    quality_metrics: Dict[str, float]
    recommendations: List[str]


# In-memory storage for development (replace with database in production)
personas_db: Dict[str, Dict[str, Any]] = {}


@router.post("/create", response_model=PersonaResponse)
async def create_persona(request: PersonaCreateRequest):
    """
    Create a new persona from uploaded examples
    """
    if not rewriter:
        raise HTTPException(status_code=500, detail="Rewriter service not available")

    try:
        logger.info(f"🎭 Creating persona: {request.name}")

        # Generate unique ID
        persona_id = f"persona_{datetime.now().timestamp()}_{len(personas_db)}"

        persona_info = {
            'id': persona_id,
            'name': request.name,
            'handle': request.handle,
            'description': request.description,
            'platforms': request.platforms
        }

        # Create persona using DynamicRewriter
        persona_data = rewriter.create_persona_from_examples(
            request.examples,
            persona_info
        )

        # Store persona (in production, use database)
        personas_db[persona_id] = persona_data

        logger.info(f"✅ Persona created successfully: {request.name}")

        return PersonaResponse(
            id=persona_data['id'],
            name=persona_data['name'],
            handle=persona_data['handle'],
            description=persona_data['description'],
            platforms=persona_data['platforms'],
            quality_metrics=persona_data['quality_metrics'],
            created_at=persona_data['created_at']
        )

    except Exception as e:
        logger.error(f"Persona creation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Persona creation failed: {str(e)}")


@router.get("/list", response_model=List[PersonaResponse])
async def list_personas():
    """
    List all available personas
    """
    try:
        personas = []
        for persona_data in personas_db.values():
            personas.append(PersonaResponse(
                id=persona_data['id'],
                name=persona_data['name'],
                handle=persona_data['handle'],
                description=persona_data['description'],
                platforms=persona_data['platforms'],
                quality_metrics=persona_data['quality_metrics'],
                created_at=persona_data['created_at']
            ))
        return personas
    except Exception as e:
        logger.error(f"Failed to list personas: {e}")
        raise HTTPException(status_code=500, detail="Failed to list personas")


@router.get("/{persona_id}", response_model=PersonaResponse)
async def get_persona(persona_id: str):
    """
    Get specific persona details
    """
    if persona_id not in personas_db:
        raise HTTPException(status_code=404, detail="Persona not found")

    persona_data = personas_db[persona_id]
    return PersonaResponse(
        id=persona_data['id'],
        name=persona_data['name'],
        handle=persona_data['handle'],
        description=persona_data['description'],
        platforms=persona_data['platforms'],
        quality_metrics=persona_data['quality_metrics'],
        created_at=persona_data['created_at']
    )


@router.post("/{persona_id}/generate", response_model=ContentGenerationResponse)
async def generate_content(persona_id: str, request: ContentGenerationRequest):
    """
    Generate content using a specific persona
    """
    if not rewriter:
        raise HTTPException(status_code=500, detail="Rewriter service not available")

    if persona_id not in personas_db:
        raise HTTPException(status_code=404, detail="Persona not found")

    try:
        logger.info(f"📝 Generating content for persona {persona_id}")

        persona_data = personas_db[persona_id]

        content_data = {
            'topic': request.topic,
            'category': request.category,
            'options': request.options or {}
        }

        # Generate content using DynamicRewriter
        result = await rewriter.generate_content(
            persona_data,
            content_data,
            request.platform
        )

        return ContentGenerationResponse(**result)

    except Exception as e:
        logger.error(f"Content generation failed: {e}")
        return ContentGenerationResponse(
            success=False,
            persona_id=persona_id,
            persona_name=personas_db[persona_id]['name'],
            platform=request.platform,
            content=None,
            quality_score=None,
            length=None,
            generated_at=datetime.now().isoformat(),
            error=str(e)
        )


@router.post("/{persona_id}/analyze", response_model=VoiceAnalysisResponse)
async def analyze_voice(persona_id: str, request: VoiceAnalysisRequest):
    """
    Analyze voice patterns from examples (for persona tuning)
    """
    if not rewriter or not rewriter.voice_analyzer:
        raise HTTPException(status_code=500, detail="Voice analyzer not available")

    try:
        logger.info(f"🔍 Analyzing voice patterns for persona {persona_id}")

        # Analyze voice patterns
        patterns = rewriter.voice_analyzer.extract_patterns(request.examples)

        # Create quality metrics
        quality_metrics = {
            'voice_consistency': rewriter._calculate_voice_consistency(patterns),
            'authenticity_prediction': rewriter._predict_authenticity(patterns),
            'engagement_potential': rewriter._predict_engagement(patterns)
        }

        # Generate recommendations
        recommendations = _generate_voice_recommendations(patterns, quality_metrics)

        return VoiceAnalysisResponse(
            patterns=patterns,
            quality_metrics=quality_metrics,
            recommendations=recommendations
        )

    except Exception as e:
        logger.error(f"Voice analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Voice analysis failed: {str(e)}")


@router.post("/{persona_id}/test")
async def test_persona(persona_id: str, topic: str = Form(...), platform: str = Form("twitter")):
    """
    Test persona with a sample topic
    """
    if not rewriter:
        raise HTTPException(status_code=500, detail="Rewriter service not available")

    if persona_id not in personas_db:
        raise HTTPException(status_code=404, detail="Persona not found")

    try:
        logger.info(f"🧪 Testing persona {persona_id} with topic: {topic}")

        persona_data = personas_db[persona_id]

        content_data = {
            'topic': topic,
            'category': 'test',
            'options': {}
        }

        # Generate test content
        result = await rewriter.generate_content(
            persona_data,
            content_data,
            platform
        )

        return {
            'success': result['success'],
            'content': result.get('content', ''),
            'quality_score': result.get('quality_score', 0),
            'length': result.get('length', 0),
            'recommendations': _generate_content_recommendations(result.get('content', ''), result.get('quality_score', 0))
        }

    except Exception as e:
        logger.error(f"Persona test failed: {e}")
        raise HTTPException(status_code=500, detail=f"Persona test failed: {str(e)}")


@router.get("/{persona_id}/analytics")
async def get_persona_analytics(persona_id: str):
    """
    Get performance analytics for a persona
    """
    if persona_id not in personas_db:
        raise HTTPException(status_code=404, detail="Persona not found")

    try:
        persona_data = personas_db[persona_id]

        # In production, this would pull from database
        # For now, return mock analytics
        analytics = {
            'persona_id': persona_id,
            'persona_name': persona_data['name'],
            'total_posts': 0,  # Would come from database
            'avg_engagement': 0,  # Would come from database
            'quality_trend': [0.85, 0.87, 0.89],  # Would come from database
            'top_performing_content': [],  # Would come from database
            'voice_consistency_score': persona_data['quality_metrics']['voice_consistency'],
            'authenticity_score': persona_data['quality_metrics']['authenticity_prediction'],
            'engagement_potential': persona_data['quality_metrics']['engagement_potential'],
            'last_updated': datetime.now().isoformat()
        }

        return analytics

    except Exception as e:
        logger.error(f"Analytics retrieval failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve analytics")


@router.post("/{persona_id}/optimize")
async def optimize_persona(persona_id: str):
    """
    Apply AI-suggested optimizations to improve persona performance
    """
    if not rewriter:
        raise HTTPException(status_code=500, detail="Rewriter service not available")

    if persona_id not in personas_db:
        raise HTTPException(status_code=404, detail="Persona not found")

    try:
        persona_data = personas_db[persona_id]

        # Generate optimization suggestions
        optimizations = _generate_persona_optimizations(persona_data)

        return {
            'persona_id': persona_id,
            'optimizations': optimizations,
            'predicted_improvement': '+15% authenticity',
            'confidence': 0.87
        }

    except Exception as e:
        logger.error(f"Optimization failed: {e}")
        raise HTTPException(status_code=500, detail="Optimization failed")


def _generate_voice_recommendations(patterns: Dict[str, Any], quality_metrics: Dict[str, float]) -> List[str]:
    """Generate recommendations based on voice analysis"""
    recommendations = []

    # Check consistency
    if quality_metrics.get('voice_consistency', 0) < 0.7:
        recommendations.append("Consider using more consistent sentence structures for better flow")

    # Check authenticity
    if quality_metrics.get('authenticity_prediction', 0) < 0.7:
        recommendations.append("Add more personal experiences and specific details to increase authenticity")

    # Check engagement potential
    if quality_metrics.get('engagement_potential', 0) < 0.6:
        recommendations.append("Include more questions or hooks to improve engagement")

    # Check vocabulary
    vocab = patterns.get('vocabulary_profile', {})
    if vocab.get('technical_density', 0) < 0.1 and vocab.get('casual_density', 0) < 0.1:
        recommendations.append("Balance technical terms with casual language for better readability")

    # Check language mixing
    language_mixing = patterns.get('language_mixing', {})
    if not language_mixing.get('natural_switching', False):
        recommendations.append("Consider natural language mixing if it fits your persona")

    # Check emotional markers
    emotional = patterns.get('emotional_markers', {})
    if emotional.get('emotional_intensity', 0) < 0.2:
        recommendations.append("Add more emotional expression to make content more engaging")

    return recommendations


def _generate_content_recommendations(content: str, quality_score: float) -> List[str]:
    """Generate recommendations for improving content"""
    recommendations = []

    if quality_score < 0.8:
        recommendations.append("Quality score could be improved - consider reviewing voice consistency")

    if len(content) < 50:
        recommendations.append("Content is quite short - consider adding more context or detail")
    elif len(content) > 500:
        recommendations.append("Content is quite long - consider breaking it down or being more concise")

    # Check for engagement elements
    if '?' not in content:
        recommendations.append("Consider adding a question to encourage engagement")

    if not any(word in content.lower() for word in ['i', 'i\'m', 'я', 'мне']):
        recommendations.append("Consider adding more personal perspective")

    return recommendations


def _generate_persona_optimizations(persona_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate optimization suggestions for persona"""
    optimizations = []

    # Analyze current patterns
    patterns = persona_data.get('patterns', {})
    strategy = persona_data.get('strategy', {})

    # Voice consistency optimization
    sentence_structure = patterns.get('sentence_structure', {})
    if sentence_structure.get('sentence_length_variance', 0) > 500:
        optimizations.append({
            'type': 'voice_consistency',
            'description': 'Reduce sentence length variation for more consistent voice',
            'impact': '+10% authenticity',
            'action': 'Aim for sentence lengths between 20-60 characters'
        })

    # Engagement optimization
    engagement = patterns.get('engagement_patterns', {})
    if engagement.get('engagement_optimization', 0) < 0.3:
        optimizations.append({
            'type': 'engagement',
            'description': 'Add more hooks and questions to increase engagement',
            'impact': '+15% engagement',
            'action': 'Start with attention-grabbing hooks and include 1-2 questions per post'
        })

    # Authenticity optimization
    authenticity = patterns.get('authenticity_signals', {})
    if authenticity.get('personal_experiences', 0) < 0.2:
        optimizations.append({
            'type': 'authenticity',
            'description': 'Include more personal experiences and specific details',
            'impact': '+20% authenticity',
            'action': 'Use phrases like "I tried", "I tested", "I noticed" with specific examples'
        })

    return optimizations


# RAG-related endpoints
@router.get("/rag/stats")
async def get_rag_stats():
    """Get RAG system statistics"""
    if not rewriter:
        raise HTTPException(status_code=503, detail="RAG system not available")

    try:
        rag_stats = rewriter.get_rag_stats()
        return {
            'status': 'success',
            'rag_stats': rag_stats,
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get RAG stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get RAG stats: {str(e)}")


@router.post("/{persona_id}/search-examples")
async def search_similar_examples(persona_id: str, query: str = Form(...), k: int = Form(3)):
    """Search for similar examples using RAG"""
    if not rewriter:
        raise HTTPException(status_code=503, detail="RAG system not available")

    try:
        # Search vector database
        search_results = rewriter.vector_db.search_similar(
            query=query,
            persona_id=persona_id,
            k=k,
            threshold=0.1
        )

        # Format results
        formatted_results = []
        for result in search_results:
            formatted_results.append({
                'content': result['content'],
                'score': result['score'],
                'metadata': result.get('metadata', {}),
                'example_id': result['example'].example_id
            })

        return {
            'status': 'success',
            'query': query,
            'persona_id': persona_id,
            'results_count': len(formatted_results),
            'results': formatted_results,
            'timestamp': datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to search examples: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to search examples: {str(e)}")


@router.get("/{persona_id}/examples")
async def get_persona_examples(persona_id: str):
    """Get all examples for a specific persona"""
    if not rewriter:
        raise HTTPException(status_code=503, detail="RAG system not available")

    try:
        examples = rewriter.vector_db.get_persona_examples(persona_id)

        formatted_examples = []
        for example in examples:
            formatted_examples.append({
                'example_id': example.example_id,
                'content': example.content,
                'created_at': example.created_at,
                'metadata': example.metadata
            })

        return {
            'status': 'success',
            'persona_id': persona_id,
            'examples_count': len(formatted_examples),
            'examples': formatted_examples,
            'timestamp': datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to get persona examples: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get persona examples: {str(e)}")


@router.get("/rewrites/latest")
async def get_latest_rewrites(persona_key: str, limit: int = 5):
    """Return the latest rewritten samples for a persona (ordered by creation time)"""
    if not rewriter:
        raise HTTPException(status_code=503, detail="RAG system not available")

    try:
        examples = rewriter.vector_db.get_persona_examples(persona_key)

        def _sort_key(example) -> datetime:
            raw = getattr(example, "created_at", None) or example.metadata.get("generated_at")
            try:
                return datetime.fromisoformat(raw)
            except Exception:
                return datetime.min

        sorted_examples = sorted(examples, key=_sort_key, reverse=True)
        trimmed = sorted_examples[: max(1, min(limit, 20))]

        formatted = []
        for example in trimmed:
            formatted.append(
                {
                    "example_id": example.example_id,
                    "content": example.content,
                    "created_at": example.created_at,
                    "metadata": example.metadata,
                }
            )

        return {
            "status": "success",
            "persona_key": persona_key,
            "count": len(formatted),
            "rewrites": formatted,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as exc:
        logger.error(f"Failed to load latest rewrites: {exc}")
        raise HTTPException(status_code=500, detail=f"Failed to load latest rewrites: {str(exc)}")


# Learning Loop endpoints
@router.post("/{persona_id}/track-performance")
async def track_content_performance(persona_id: str, performance_data: Dict[str, Any]):
    """Track performance of generated content"""
    try:
        # Add persona_id to performance data
        performance_data['persona_id'] = persona_id

        # Track with learning analyzer
        content_id = learning_analyzer.track_content_performance(performance_data)

        if content_id:
            return {
                'status': 'success',
                'content_id': content_id,
                'persona_id': persona_id,
                'message': 'Performance tracking started',
                'timestamp': datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to track performance")

    except Exception as e:
        logger.error(f"Failed to track performance: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to track performance: {str(e)}")


@router.put("/{persona_id}/update-engagement/{content_id}")
async def update_engagement_metrics(persona_id: str, content_id: str, metrics: Dict[str, int]):
    """Update engagement metrics for content"""
    try:
        # Update metrics in learning analyzer
        learning_analyzer.update_engagement_metrics(content_id, metrics)

        return {
            'status': 'success',
            'content_id': content_id,
            'persona_id': persona_id,
            'updated_metrics': metrics,
            'timestamp': datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to update engagement metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update engagement metrics: {str(e)}")


@router.get("/{persona_id}/performance-analysis")
async def get_persona_performance_analysis(persona_id: str):
    """Get performance analysis for a specific persona"""
    try:
        analysis = learning_analyzer.analyze_persona_performance(persona_id)

        return {
            'status': 'success',
            'analysis': analysis,
            'timestamp': datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to get performance analysis: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get performance analysis: {str(e)}")


@router.get("/learning/stats")
async def get_learning_loop_stats():
    """Get overall learning loop statistics"""
    try:
        stats = learning_analyzer.get_learning_stats()

        return {
            'status': 'success',
            'learning_stats': stats,
            'timestamp': datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to get learning stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get learning stats: {str(e)}")


# Health check endpoint
@router.get("/health")
async def health_check():
    """Check if the persona API is healthy"""
    rag_stats = {}

    if rewriter:
        try:
            rag_stats = rewriter.get_rag_stats()
        except Exception as e:
            logger.warning(f"Failed to get RAG stats for health check: {e}")

    learning_stats = {}
    try:
        learning_stats = learning_analyzer.get_learning_stats()
    except Exception as e:
        logger.warning(f"Failed to get learning stats for health check: {e}")

    return {
        'status': 'healthy',
        'rewriter_available': rewriter is not None,
        'personas_count': len(personas_db),
        'rag_enabled': rag_stats.get('rag_enabled', False),
        'vector_db_stats': rag_stats.get('vector_database', {}),
        'learning_loop_active': learning_stats.get('learning_loop_active', False),
        'total_content_tracked': learning_stats.get('total_content_tracked', 0),
        'timestamp': datetime.now().isoformat()
    }


# ========== A/B TESTING ENDPOINTS ==========

# Pydantic models for A/B testing
class ABTestRequest(BaseModel):
    name: str
    description: str
    test_type: str
    platform: Optional[str] = None
    min_sample_size: int = 100
    confidence_threshold: float = 0.95

class ABTestVariantRequest(BaseModel):
    name: str
    description: str
    config: Dict[str, Any]
    variant_type: str = "treatment"
    traffic_allocation: float = 0.5

class ABTestGenerateRequest(BaseModel):
    persona_id: str
    topic: str
    content: str
    category: str = "general"
    platform: str = "twitter"
    user_id: Optional[str] = None
    test_id: Optional[str] = None


@router.post("/ab-tests/create")
async def create_ab_test(request: ABTestRequest):
    """
    Create a new A/B test
    """
    if not rewriter:
        raise HTTPException(status_code=500, detail="Rewriter service not available")

    try:
        logger.info(f"🧪 Creating A/B test: {request.name}")

        test_id = rewriter.create_ab_test(
            name=request.name,
            description=request.description,
            test_type=request.test_type,
            persona_id="",  # Will be set when adding to persona
            platform=request.platform,
            min_sample_size=request.min_sample_size,
            confidence_threshold=request.confidence_threshold
        )

        return {
            'success': True,
            'test_id': test_id,
            'message': 'A/B test created successfully'
        }

    except Exception as e:
        logger.error(f"Failed to create A/B test: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create A/B test: {str(e)}")


@router.post("/ab-tests/{test_id}/variants")
async def add_ab_test_variant(test_id: str, request: ABTestVariantRequest):
    """
    Add a variant to an existing A/B test
    """
    if not rewriter:
        raise HTTPException(status_code=500, detail="Rewriter service not available")

    try:
        logger.info(f"🧪 Adding variant to A/B test {test_id}: {request.name}")

        success = rewriter.add_ab_test_variant(
            test_id=test_id,
            name=request.name,
            description=request.description,
            config=request.config,
            variant_type=request.variant_type,
            traffic_allocation=request.traffic_allocation
        )

        if success:
            return {
                'success': True,
                'message': 'Variant added successfully'
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to add variant - test may not be in draft status")

    except Exception as e:
        logger.error(f"Failed to add A/B test variant: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to add variant: {str(e)}")


@router.post("/ab-tests/{test_id}/start")
async def start_ab_test(test_id: str):
    """
    Start an A/B test
    """
    if not rewriter:
        raise HTTPException(status_code=500, detail="Rewriter service not available")

    try:
        logger.info(f"🚀 Starting A/B test: {test_id}")

        success = rewriter.start_ab_test(test_id)

        if success:
            return {
                'success': True,
                'message': 'A/B test started successfully'
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to start test - check test configuration")

    except Exception as e:
        logger.error(f"Failed to start A/B test: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start test: {str(e)}")


@router.get("/ab-tests/{test_id}/results")
async def get_ab_test_results(test_id: str):
    """
    Get comprehensive results for an A/B test
    """
    if not rewriter:
        raise HTTPException(status_code=500, detail="Rewriter service not available")

    try:
        logger.info(f"📊 Getting A/B test results: {test_id}")

        results = rewriter.get_ab_test_results(test_id)

        return {
            'success': True,
            'results': results
        }

    except Exception as e:
        logger.error(f"Failed to get A/B test results: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get results: {str(e)}")


@router.get("/ab-tests/active")
async def get_active_ab_tests():
    """
    Get all active A/B tests
    """
    if not rewriter:
        raise HTTPException(status_code=500, detail="Rewriter service not available")

    try:
        logger.info(f"📋 Getting active A/B tests")

        active_tests = rewriter.get_active_ab_tests()

        return {
            'success': True,
            'active_tests': active_tests,
            'count': len(active_tests)
        }

    except Exception as e:
        logger.error(f"Failed to get active A/B tests: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get active tests: {str(e)}")


@router.post("/ab-tests/{test_id}/complete")
async def complete_ab_test(test_id: str, winning_variant_id: Optional[str] = None):
    """
    Complete an A/B test and optionally declare a winner
    """
    if not rewriter:
        raise HTTPException(status_code=500, detail="Rewriter service not available")

    try:
        logger.info(f"🏁 Completing A/B test: {test_id}")

        success = rewriter.complete_ab_test(test_id, winning_variant_id)

        if success:
            return {
                'success': True,
                'message': 'A/B test completed successfully'
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to complete test")

    except Exception as e:
        logger.error(f"Failed to complete A/B test: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to complete test: {str(e)}")


@router.post("/ab-tests/generate")
async def generate_content_with_ab_test(request: ABTestGenerateRequest):
    """
    Generate content with A/B testing integration
    """
    if not rewriter:
        raise HTTPException(status_code=500, detail="Rewriter service not available")

    if request.persona_id not in personas_db:
        raise HTTPException(status_code=404, detail="Persona not found")

    try:
        logger.info(f"🧪 Generating content with A/B test: {request.persona_id}")

        persona_data = personas_db[request.persona_id]
        content_data = {
            'topic': request.topic,
            'content': request.content,
            'category': request.category
        }

        # Generate content with A/B testing
        result = await rewriter.generate_content_with_ab_test(
            persona_data=persona_data,
            content=content_data,
            platform=request.platform,
            user_id=request.user_id,
            test_id=request.test_id
        )

        # Add persona info to response
        result['persona_name'] = persona_data['name']
        result['generated_at'] = datetime.now().isoformat()

        return ContentGenerationResponse(**result)

    except Exception as e:
        logger.error(f"Content generation with A/B test failed: {e}")
        raise HTTPException(status_code=500, detail=f"Content generation failed: {str(e)}")


@router.post("/{persona_id}/ab-tests/create-predefined")
async def create_predefined_ab_tests(persona_id: str, platform: Optional[str] = None):
    """
    Create predefined A/B tests for a persona
    """
    if not rewriter:
        raise HTTPException(status_code=500, detail="Rewriter service not available")

    if persona_id not in personas_db:
        raise HTTPException(status_code=404, detail="Persona not found")

    try:
        logger.info(f"🧪 Creating predefined A/B tests for persona: {persona_id}")

        created_tests = rewriter.create_predefined_tests(persona_id, platform)

        return {
            'success': True,
            'created_tests': created_tests,
            'count': len(created_tests),
            'message': f'Created {len(created_tests)} predefined A/B tests'
        }

    except Exception as e:
        logger.error(f"Failed to create predefined A/B tests: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create tests: {str(e)}")


@router.get("/{persona_id}/ab-tests/recommendations")
async def get_ab_test_recommendations(persona_id: str):
    """
    Get A/B test recommendations for a persona
    """
    if not rewriter:
        raise HTTPException(status_code=500, detail="Rewriter service not available")

    if persona_id not in personas_db:
        raise HTTPException(status_code=404, detail="Persona not found")

    try:
        logger.info(f"💡 Getting A/B test recommendations for persona: {persona_id}")

        recommendations = rewriter.get_ab_test_recommendations(persona_id)

        return {
            'success': True,
            'persona_id': persona_id,
            'recommendations': recommendations
        }

    except Exception as e:
        logger.error(f"Failed to get A/B test recommendations: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get recommendations: {str(e)}")
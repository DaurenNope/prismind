#!/usr/bin/env python3
"""
Persona Matcher Service

Matches analyzed posts to personas using:
1. Semantic similarity (primary) - embeddings comparison
2. Topic/expertise overlap (secondary)
3. Rewrite angle quality (tertiary)
4. Keywords (fallback only)

This is NOT a full "agent" - just a service/function integrated into analysis.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import numpy as np

from src.core.indexing.embedding_service import EmbeddingService
from src.core.research.semantic_encoder import SemanticEncoder

logger = logging.getLogger(__name__)


class PersonaMatcher:
    """Matches posts to personas using semantic similarity and topic overlap"""
    
    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.semantic_encoder = SemanticEncoder() if self.embedding_service.is_available() else None
        self.personas = self._load_personas()
        self._persona_embeddings = {}  # Cache for persona expertise embeddings
        
    def _load_personas(self) -> List[Dict[str, Any]]:
        """Load all personas from config/personas/*.json"""
        personas = []
        personas_dir = Path("config/personas")
        
        if not personas_dir.exists():
            logger.warning(f"Personas directory not found: {personas_dir}")
            return personas
        
        for persona_file in personas_dir.glob("*.json"):
            try:
                with open(persona_file, 'r') as f:
                    persona = json.load(f)
                    persona['key'] = persona.get('key') or persona_file.stem
                    personas.append(persona)
                    logger.info(f"Loaded persona: {persona['key']}")
            except Exception as e:
                logger.error(f"Failed to load persona {persona_file}: {e}")
        
        logger.info(f"Loaded {len(personas)} personas")
        return personas
    
    def _get_persona_expertise_embedding(self, persona: Dict[str, Any]) -> Optional[np.ndarray]:
        """Get or compute embedding for persona expertise"""
        persona_key = persona.get('key')
        
        # Check cache
        if persona_key in self._persona_embeddings:
            return self._persona_embeddings[persona_key]
        
        # Check if pre-computed in persona file
        matching = persona.get('matching', {})
        if 'expertise_embedding' in matching and matching['expertise_embedding']:
            embedding = np.array(matching['expertise_embedding'])
            self._persona_embeddings[persona_key] = embedding
            return embedding
        
        # Compute embedding from expertise
        if not self.semantic_encoder or not self.semantic_encoder.is_available():
            return None
        
        expertise = persona.get('expertise', [])
        if not expertise:
            return None
        
        # Combine expertise into text
        expertise_text = ", ".join(expertise)
        expertise_text += f". {persona.get('voice_description', '')}"
        
        # Generate embedding
        embedding = self.semantic_encoder.encode_text(expertise_text)
        if embedding is not None:
            self._persona_embeddings[persona_key] = embedding
        
        return embedding
    
    def _calculate_topic_overlap(self, post: Dict[str, Any], persona: Dict[str, Any]) -> float:
        """Calculate topic/expertise overlap score"""
        post_topics = post.get('topics', []) or []
        post_concepts = post.get('key_concepts', []) or []
        persona_expertise = persona.get('expertise', []) or []
        
        # Normalize to lowercase for comparison
        post_items = [str(item).lower() for item in post_topics + post_concepts]
        persona_items = [str(item).lower() for item in persona_expertise]
        
        if not post_items or not persona_items:
            return 0.0
        
        # Calculate overlap
        post_set = set(post_items)
        persona_set = set(persona_items)
        
        overlap = post_set.intersection(persona_set)
        
        if not overlap:
            return 0.0
        
        # Score: overlap ratio weighted by persona expertise size
        overlap_score = len(overlap) / max(len(persona_set), 1)
        
        # Normalize to 0-1 range (capped at 1.0)
        return min(overlap_score, 1.0)
    
    def _calculate_rewrite_angle_quality(self, post: Dict[str, Any], persona: Dict[str, Any]) -> float:
        """Check if rewrite_angles have good quality for this persona"""
        rewrite_angles = post.get('rewrite_angles', []) or []
        
        if not rewrite_angles:
            return 0.0
        
        # Generic persona mapping (from analysis) to real personas
        # This is approximate - analysis uses generic personas, we have real ones
        persona_key = persona.get('key', '').lower()
        
        # Map real personas to generic personas from analysis
        persona_to_generic = {
            'cryptoniard': 'technical',  # Could also be 'builder'
            'qronoya': 'builder',
            'skeptical_builder': 'builder',
            'claimzilla': 'technical',
            'practical_skeptic': 'thought_leader',
            'observational_writer': 'learner',
            'aspandead': 'learner'
        }
        
        generic_persona = persona_to_generic.get(persona_key)
        if not generic_persona:
            return 0.3  # Default medium score if no mapping
        
        # Find matching rewrite angle
        matching_angle = None
        for angle in rewrite_angles:
            if angle.get('persona', '').lower() == generic_persona:
                matching_angle = angle
                break
        
        if not matching_angle:
            return 0.0
        
        # Score based on angle quality
        estimated_engagement = matching_angle.get('estimated_engagement', 'low')
        engagement_scores = {'high': 1.0, 'medium': 0.6, 'low': 0.3}
        return engagement_scores.get(estimated_engagement.lower(), 0.3)
    
    def _calculate_keyword_fallback(self, post: Dict[str, Any], persona: Dict[str, Any]) -> float:
        """Fallback keyword matching (only used if semantic fails)"""
        matching = persona.get('matching', {})
        keywords = matching.get('fallback_keywords', [])
        
        if not keywords:
            return 0.0
        
        # Get post content
        content = (post.get('content', '') or '').lower()
        title = (post.get('title', '') or '').lower()
        combined = f"{title} {content}"
        
        # Count keyword matches
        matches = sum(1 for keyword in keywords if keyword.lower() in combined)
        
        if not matches:
            return 0.0
        
        # Score: matches / total keywords (capped at 1.0)
        return min(matches / len(keywords), 1.0) * 0.5  # Max 0.5 for fallback
    
    def _check_quality_thresholds(self, post: Dict[str, Any], persona: Dict[str, Any]) -> bool:
        """Check if post meets persona quality thresholds"""
        thresholds = persona.get('quality_thresholds', {})
        
        post_value_score = post.get('value_score') or post.get('intelligent_value_score') or 0.0
        post_quality_score = post.get('content_quality_score') or post.get('quality_score') or 0.0
        
        min_value = thresholds.get('min_value_score', 0.0)
        min_quality = thresholds.get('min_content_quality', 0.0)
        
        return post_value_score >= min_value and post_quality_score >= min_quality
    
    def match_post_to_personas(
        self, 
        post: Dict[str, Any], 
        min_match_score: float = 0.65,
        use_semantic: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Match a post to personas and return ranked matches
        
        Args:
            post: Analyzed post with topics, key_concepts, embeddings, etc.
            min_match_score: Minimum match score threshold
            use_semantic: Whether to use semantic matching (primary method)
            
        Returns:
            List of matches with scores, sorted by score descending
        """
        matches = []
        
        # Get post embedding
        post_embedding = None
        if use_semantic and self.semantic_encoder and self.semantic_encoder.is_available():
            # Combine post content for embedding
            content_parts = []
            if post.get('content'):
                content_parts.append(post['content'])
            if post.get('summary'):
                content_parts.append(post['summary'])
            if post.get('topics'):
                content_parts.append(", ".join(post['topics']))
            if post.get('key_concepts'):
                content_parts.append(", ".join(post['key_concepts']))
            
            post_text = " ".join(content_parts)
            post_embedding = self.semantic_encoder.encode_text(post_text)
        
        # Match against each persona
        for persona in self.personas:
            persona_key = persona.get('key')
            
            # Check quality thresholds first
            if not self._check_quality_thresholds(post, persona):
                continue
            
            match_score = 0.0
            match_reasons = []
            
            # 1. Semantic similarity (primary, weight: 0.5)
            if post_embedding is not None:
                persona_embedding = self._get_persona_expertise_embedding(persona)
                if persona_embedding is not None:
                    # Calculate cosine similarity
                    similarity = self.semantic_encoder.calculate_similarity(
                        post_embedding, 
                        persona_embedding.reshape(1, -1)
                    )[0]
                    
                    if similarity > 0:
                        semantic_score = float(similarity)
                        match_score += semantic_score * 0.5
                        match_reasons.append(f"Semantic similarity: {semantic_score:.2f}")
            
            # 2. Topic/expertise overlap (secondary, weight: 0.3)
            topic_score = self._calculate_topic_overlap(post, persona)
            if topic_score > 0:
                match_score += topic_score * 0.3
                match_reasons.append(f"Topic overlap: {topic_score:.2f}")
            
            # 3. Rewrite angle quality (tertiary, weight: 0.1)
            angle_score = self._calculate_rewrite_angle_quality(post, persona)
            if angle_score > 0:
                match_score += angle_score * 0.1
                match_reasons.append(f"Rewrite angle: {angle_score:.2f}")
            
            # 4. Keyword fallback (only if semantic failed, weight: 0.1)
            if match_score < 0.3:  # Only use keywords if score is low
                keyword_score = self._calculate_keyword_fallback(post, persona)
                if keyword_score > 0:
                    match_score += keyword_score * 0.1
                    match_reasons.append(f"Keyword fallback: {keyword_score:.2f}")
            
            # Only include if meets minimum threshold
            if match_score >= min_match_score:
                matches.append({
                    'persona_key': persona_key,
                    'persona_name': persona.get('name'),
                    'match_score': match_score,
                    'match_reasons': match_reasons,
                    'is_candidate': True
                })
        
        # Sort by score descending
        matches.sort(key=lambda x: x['match_score'], reverse=True)
        
        return matches
    
    def get_recommended_personas(
        self, 
        post: Dict[str, Any],
        top_k: int = 3,
        min_match_score: float = 0.65
    ) -> Dict[str, Any]:
        """
        Get recommended personas for a post
        
        Returns:
            {
                'recommended_personas': ['persona1', 'persona2'],
                'persona_match_scores': {'persona1': 0.85, 'persona2': 0.72},
                'persona_candidacy': {
                    'persona1': {
                        'is_candidate': True,
                        'match_reason': '...',
                        'fit_score': 0.85
                    }
                }
            }
        """
        matches = self.match_post_to_personas(post, min_match_score=min_match_score)
        
        # Get top K
        top_matches = matches[:top_k]
        
        recommended = [m['persona_key'] for m in top_matches]
        match_scores = {m['persona_key']: m['match_score'] for m in top_matches}
        candidacy = {
            m['persona_key']: {
                'is_candidate': m['is_candidate'],
                'match_reason': '; '.join(m['match_reasons']),
                'fit_score': m['match_score']
            }
            for m in top_matches
        }
        
        return {
            'recommended_personas': recommended,
            'persona_match_scores': match_scores,
            'persona_candidacy': candidacy
        }


# Singleton instance
_matcher = None

def get_persona_matcher() -> PersonaMatcher:
    """Get global persona matcher instance"""
    global _matcher
    if _matcher is None:
        _matcher = PersonaMatcher()
    return _matcher


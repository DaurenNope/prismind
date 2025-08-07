#!/usr/bin/env python3
"""
Test suite for FeedbackSystem
"""

import os
import sys
import pytest
import sqlite3
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.learning.feedback_system import FeedbackSystem

class TestFeedbackSystem:
    """Test suite for FeedbackSystem class"""
    
    @pytest.fixture
    def feedback_system(self, tmp_path):
        """Create a FeedbackSystem instance with a temporary database"""
        db_path = tmp_path / "test_feedback.db"
        system = FeedbackSystem(str(db_path))
        return system
    
    def test_init(self, tmp_path):
        """Test FeedbackSystem initialization"""
        db_path = tmp_path / "test_feedback.db"
        system = FeedbackSystem(str(db_path))
        
        # Check that the database file was created
        assert db_path.exists()
        
        # Check that tables were created
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_feedback'")
            assert cursor.fetchone() is not None
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='learning_patterns'")
            assert cursor.fetchone() is not None
    
    def test_add_feedback(self, feedback_system):
        """Test adding user feedback"""
        post_id = "test_post_123"
        feedback_type = "good"
        rating = 4
        user_notes = "This was helpful"
        
        result = feedback_system.add_feedback(post_id, feedback_type, rating, user_notes)
        
        # Should return True on success
        assert result is True
        
        # Verify feedback was added
        feedback = feedback_system.get_feedback_for_post(post_id)
        assert len(feedback) == 1
        assert feedback[0]['post_id'] == post_id
        assert feedback[0]['feedback_type'] == feedback_type
        assert feedback[0]['rating'] == rating
        assert feedback[0]['user_notes'] == user_notes
    
    def test_get_feedback_for_post(self, feedback_system):
        """Test getting feedback for a specific post"""
        post_id = "test_post_123"
        
        # Add some feedback
        feedback_system.add_feedback(post_id, "good", 4, "Helpful")
        feedback_system.add_feedback(post_id, "gold", 5, "Excellent")
        
        # Get feedback
        feedback = feedback_system.get_feedback_for_post(post_id)
        
        assert isinstance(feedback, list)
        assert len(feedback) == 2
        
        # Check that we have the expected feedback types
        feedback_types = [f['feedback_type'] for f in feedback]
        assert "good" in feedback_types
        assert "gold" in feedback_types
    
    def test_get_feedback_stats(self, feedback_system):
        """Test getting feedback statistics"""
        post_id = "test_post_123"
        
        # Add some feedback
        feedback_system.add_feedback(post_id, "good", 4, "Helpful")
        feedback_system.add_feedback(post_id, "poor", 2, "Not useful")
        feedback_system.add_feedback(post_id, "gold", 5, "Excellent")
        
        # Get stats
        stats = feedback_system.get_feedback_stats()
        
        assert isinstance(stats, dict)
        assert 'total_feedback' in stats
        assert 'feedback_by_type' in stats
        assert stats['total_feedback'] >= 3
    
    def test_update_learning_patterns(self, feedback_system):
        """Test updating learning patterns"""
        # Add some feedback first
        feedback_system.add_feedback("post_1", "gold", 5, "Excellent content about AI")
        feedback_system.add_feedback("post_2", "poor", 1, "Irrelevant content")
        
        # Update learning patterns
        result = feedback_system.update_learning_patterns()
        
        # Should return True on success
        assert result is True
    
    def test_get_content_recommendations(self, feedback_system):
        """Test getting content recommendations"""
        # Add some feedback
        feedback_system.add_feedback("post_1", "gold", 5, "Excellent content about AI")
        feedback_system.add_feedback("post_2", "good", 4, "Good content about ML")
        
        # Update learning patterns
        feedback_system.update_learning_patterns()
        
        # Get recommendations
        recommendations = feedback_system.get_content_recommendations(limit=5)
        
        # Should return a list (could be empty if no posts in DB)
        assert isinstance(recommendations, list)
    
    def test_get_user_preferences(self, feedback_system):
        """Test getting user preferences"""
        # Add some feedback
        feedback_system.add_feedback("post_1", "gold", 5, "Excellent content about AI")
        feedback_system.add_feedback("post_2", "good", 4, "Good content about ML")
        
        # Update learning patterns
        feedback_system.update_learning_patterns()
        
        # Get preferences
        preferences = feedback_system.get_user_preferences()
        
        assert isinstance(preferences, dict)
    
    def test_record_interaction(self, feedback_system):
        """Test recording user interaction"""
        post_id = "test_post_123"
        interaction_type = "view"
        
        result = feedback_system.record_interaction(post_id, interaction_type)
        
        # Should return True on success
        assert result is True

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
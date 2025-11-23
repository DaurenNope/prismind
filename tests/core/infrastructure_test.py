import pytest
import os
import asyncio
from src.application.orchestration.agent_graph import AgentGraph

@pytest.mark.asyncio
async def test_agent_graph_execution():
    """Test that AgentGraph runs through the full cycle."""
    from unittest.mock import MagicMock, AsyncMock, patch
    
    # Mock the collection service used by ScoutAgent
    with patch('src.services.unified_collection_service.UnifiedCollectionService') as MockService:
        mock_service_instance = MockService.return_value
        mock_service_instance.collect_all = AsyncMock(return_value={
            "twitter": MagicMock(posts_collected=1)
        })
        
        # Mock database manager used by ScoutAgent
        with patch('src.services.new_database_manager.NewDatabaseManager') as MockDB:
            mock_db_instance = MockDB.return_value
            mock_db_instance.get_unanalyzed_posts.return_value = [{
                "post_id": "test_123",
                "content": "Test content for analysis",
                "platform": "twitter"
            }]
            
            graph = AgentGraph()
            
            # Run the graph
            # We use a mock input
            inputs = "Start the cycle"
            
            # Collect outputs
            outputs = []
            async for output in graph.app.astream({
                "messages": [],
                "current_agent": "user",
                "next_agent": "director",
                "task_status": "started",
                "artifacts": {},
                "errors": []
            }):
                outputs.append(output)
                
            # Verify we hit the key nodes
            agents_hit = set()
            for out in outputs:
                for key in out.keys():
                    agents_hit.add(key)
                    
            # Check that we visited the specialized agents
            # Note: 'director' runs multiple times, so it will be in there
            assert "director" in agents_hit
            assert "scout" in agents_hit
            assert "analyst" in agents_hit
            assert "skeptic" in agents_hit
            assert "historian" in agents_hit

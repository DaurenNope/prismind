"""Test that AgentGraph progresses through all agents correctly"""
import pytest
from src.application.orchestration.agent_graph import AgentGraph
from langchain_core.messages import AIMessage

@pytest.mark.asyncio
async def test_director_progression():
    """Test Director correctly routes through all agents"""
    graph = AgentGraph()
    
    # Test progression from start -> scout
    state = {
        "task_status": "started",
        "artifacts": {},
        "messages": []
    }
    result = await graph._director_node(state)
    assert result["next_agent"] == "scout"

    # Test progression from scout -> analyst
    state = {
        "task_status": "scouting",
        "artifacts": {"current_post": {"content": "test"}},
        "messages": []
    }
    result = await graph._director_node(state)
    assert result["next_agent"] == "analyst"
    
    # Test progression from analyst -> skeptic
    state = {"task_status": "analysis_complete", "artifacts": {}, "messages": []}
    result = await graph._director_node(state)
    assert result["next_agent"] == "skeptic"
    
    # Test progression from skeptic -> historian
    state = {"task_status": "verification_complete", "artifacts": {}, "messages": []}
    result = await graph._director_node(state)
    assert result["next_agent"] == "historian"
    
    # Test progression from historian -> end
    state = {"task_status": "history_complete", "artifacts": {}, "messages": []}
    result = await graph._director_node(state)
    assert result["next_agent"] == "end"

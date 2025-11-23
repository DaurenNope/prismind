from fastapi import APIRouter, HTTPException, BackgroundTasks
from sse_starlette.sse import EventSourceResponse
import asyncio
import json
from src.core.orchestration.agent_graph import AgentGraph

router = APIRouter(prefix="/agents", tags=["agents"])

# Global graph instance (in a real app, manage this better)
agent_graph = AgentGraph()

@router.post("/run")
async def run_agent_cycle(input_text: str, background_tasks: BackgroundTasks):
    """
    Trigger a new agent cycle.
    """
    # In a real app, we'd store the run ID and stream updates for it.
    # For this demo, we'll just return success and let the SSE endpoint pick up global events
    # (Simplified for prototype)
    return {"status": "started", "message": "Agent cycle initiated"}

@router.get("/stream")
async def stream_agent_events():
    """
    Stream agent events to the frontend.
    """
    async def event_generator():
        # Mocking the stream for the prototype since we don't have a shared event bus yet
        # In production, this would subscribe to Redis or an internal event queue
        initial_state = {
            "messages": [],
            "current_agent": "user",
            "next_agent": "director",
            "task_status": "started",
            "artifacts": {},
            "errors": []
        }
        
        # Run a demo cycle for visualization
        async for output in agent_graph.app.astream(initial_state):
            for agent_name, state in output.items():
                data = {
                    "agent": agent_name,
                    "status": state.get("task_status"),
                    "message": state.get("messages")[-1].content if state.get("messages") else ""
                }
                yield json.dumps(data)
                await asyncio.sleep(1) # Slow down for visual effect

    return EventSourceResponse(event_generator())

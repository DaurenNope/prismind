from fastapi import APIRouter, HTTPException, BackgroundTasks, Body
from sse_starlette.sse import EventSourceResponse
import asyncio
import json
import time
from typing import Optional
from pydantic import BaseModel
from src.application.orchestration.agent_graph import AgentGraph

class RunAgentRequest(BaseModel):
    input_text: str = ""

router = APIRouter(prefix="/agents", tags=["agents"])

# Global graph instance (in a real app, manage this better)
agent_graph = AgentGraph()

# Simple in-memory event bus for sharing events between /run and /stream
# In production, use Redis or a proper message queue
_event_queue: Optional[asyncio.Queue] = None
_active_run_id: Optional[str] = None

def get_event_queue() -> asyncio.Queue:
    """Get or create the global event queue."""
    global _event_queue
    if _event_queue is None:
        _event_queue = asyncio.Queue()
    return _event_queue

@router.post("/run")
async def run_agent_cycle(request: RunAgentRequest, background_tasks: BackgroundTasks):
    """
    Trigger a new agent cycle.
    This is the ONLY endpoint that should execute agent cycles.
    """
    # Store run ID for tracking
    run_id = f"run_{int(time.time())}"
    global _active_run_id
    _active_run_id = run_id
    
    # Get event queue
    event_queue = get_event_queue()
    
    # Execute agent cycle in background
    async def run_cycle():
        try:
            initial_state = {
                "messages": [],
                "current_agent": "user",
                "next_agent": "director",
                "task_status": "started",
                "artifacts": {},
                "errors": [],
                "run_id": run_id
            }
            
            # Publish start event
            await event_queue.put({
                "agent": "system",
                "status": "started",
                "message": f"Agent cycle {run_id} initiated",
                "run_id": run_id
            })
            
            # Execute agent cycle and publish events
            async for output in agent_graph.app.astream(initial_state):
                for agent_name, state in output.items():
                    data = {
                        "agent": agent_name,
                        "status": state.get("task_status"),
                        "message": state.get("messages")[-1].content if state.get("messages") else "",
                        "run_id": run_id
                    }
                    await event_queue.put(data)
                    await asyncio.sleep(0.1)  # Small delay for visual effect
            
            # Publish completion event
            await event_queue.put({
                "agent": "system",
                "status": "complete",
                "message": f"Agent cycle {run_id} completed",
                "run_id": run_id
            })
        except Exception as e:
            # Publish error event
            await event_queue.put({
                "agent": "system",
                "status": "error",
                "message": f"Error in agent cycle {run_id}: {str(e)}",
                "run_id": run_id
            })
        finally:
            # Clear active run when done
            if _active_run_id == run_id:
                _active_run_id = None
    
    background_tasks.add_task(run_cycle)
    
    return {
        "status": "started",
        "message": "Agent cycle initiated",
        "run_id": run_id
    }

@router.get("/stream")
async def stream_agent_events():
    """
    Stream agent events to the frontend (read-only).
    Does NOT trigger agent cycles - use /agents/run for that.
    """
    async def event_generator():
        # Send connection message
        yield json.dumps({
            "agent": "system",
            "status": "connected",
            "message": "Connected to event stream. Use /agents/run to trigger agent cycles."
        })
        
        # Get event queue
        event_queue = get_event_queue()
        
        # Subscribe to events from the queue
        # Keep connection alive and stream events
        last_heartbeat = time.time()
        heartbeat_interval = 10  # Send heartbeat every 10 seconds
        
        while True:
            try:
                # Wait for event with timeout for heartbeat
                try:
                    event = await asyncio.wait_for(event_queue.get(), timeout=heartbeat_interval)
                    yield json.dumps(event)
                    last_heartbeat = time.time()
                except asyncio.TimeoutError:
                    # Send heartbeat to keep connection alive
                    current_time = time.time()
                    if current_time - last_heartbeat >= heartbeat_interval:
                        yield json.dumps({
                            "agent": "system",
                            "status": "idle",
                            "message": "Waiting for agent cycle..."
                        })
                        last_heartbeat = current_time
            except asyncio.CancelledError:
                break
            except Exception as e:
                yield json.dumps({
                    "agent": "system",
                    "status": "error",
                    "message": f"Stream error: {str(e)}"
                })
                await asyncio.sleep(1)
    
    return EventSourceResponse(event_generator())

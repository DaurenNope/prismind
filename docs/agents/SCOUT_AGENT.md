# Scout Agent

## Overview

The `ScoutAgent` is a specialized agent in the Multi-Agent System that discovers and collects new content from social media platforms. It replaces the previous mock implementation with real collection capabilities using the existing `CollectionOrchestratorAgent`.

## Features

### ✅ Real Content Collection
- Uses `CollectionOrchestratorAgent` for actual platform collection
- Collects from all configured platforms (Twitter, Reddit, Threads, etc.)
- Retrieves real posts from the database after collection
- Handles multiple posts per collection cycle

### ✅ Error Handling
- Gracefully handles collection failures
- Returns appropriate error messages in state
- Continues operation even if some platforms fail
- Logs errors for debugging

### ✅ State Management
- Returns collected posts in state artifacts
- Provides `current_post` for immediate processing
- Includes `all_posts` for batch processing
- Tracks collection results and metrics

### ✅ Integration
- Integrates seamlessly with `AgentGraph`
- Works with Director node for workflow orchestration
- Compatible with Analyst, Skeptic, and Historian agents
- Uses LangGraph state management

## Architecture

```
ScoutAgent
├── SpecializedAgent (inheritance)
│   ├── BaseAgent
│   │   ├── initialize()
│   │   ├── execute()
│   │   └── health_check()
│   └── process() [with retry logic]
│       └── _process_impl()
├── CollectionOrchestratorAgent (delegation)
│   └── collect_all()
└── Database Manager
    └── get_posts_by_platform()
```

## Usage

### Basic Usage

```python
from src.agents.specialized.scout_agent import ScoutAgent

# Initialize agent
scout = ScoutAgent()
await scout.initialize()

# Process state (typically called by AgentGraph)
state = {
    "messages": [],
    "artifacts": {},
    "task_status": "started"
}

result = await scout.process(state)
```

### Integration with AgentGraph

The Scout agent is automatically integrated into the `AgentGraph` workflow:

```python
from src.core.orchestration.agent_graph import AgentGraph

graph = AgentGraph()
# Scout is automatically initialized and used in the workflow
```

## State Format

### Input State
```python
{
    "messages": [],  # Optional: previous messages
    "artifacts": {},  # Optional: previous artifacts
    "task_status": "started"  # Current task status
}
```

### Output State (Success)
```python
{
    "messages": [
        AIMessage(content="Scout: Found 5 new post(s).")
    ],
    "artifacts": {
        "current_post": {...},  # First post for processing
        "all_posts": [...],  # All collected posts
        "posts_collected": 5,  # Total count
        "collection_result": {...}  # Full collection result
    },
    "current_agent": "scout",
    "task_status": "scouting"
}
```

### Output State (No Content)
```python
{
    "messages": [
        AIMessage(content="Scout: No new content found.")
    ],
    "artifacts": {
        "current_post": None,
        "posts_collected": 0
    },
    "current_agent": "scout",
    "task_status": "scouting"
}
```

### Output State (Error)
```python
{
    "messages": [
        AIMessage(content="Scout: Collection failed - <error message>")
    ],
    "artifacts": {
        "current_post": None,
        "posts_collected": 0
    },
    "errors": ["<error message>"],
    "current_agent": "scout",
    "task_status": "error"
}
```

## Workflow Integration

The Scout agent is part of the following workflow:

1. **Director** → Decides to call Scout when no posts are available
2. **Scout** → Collects content from platforms
3. **Director** → Routes to Analyst when posts are available
4. **Analyst** → Analyzes the collected content
5. **Skeptic** → Verifies the analysis
6. **Historian** → Adds historical context

## Implementation Details

### Collection Process

1. **Initialize Collection Agent**: Ensures `CollectionOrchestratorAgent` is initialized
2. **Collect from Platforms**: Calls `collect_all()` to gather content
3. **Extract Results**: Parses collection results to get platform counts
4. **Retrieve Posts**: Fetches actual post data from database using `get_posts_by_platform()`
5. **Format Response**: Returns posts in state format for downstream processing

### Error Handling

- Collection failures are caught and logged
- Error state is returned with appropriate messages
- Partial failures (some platforms succeed) are handled gracefully
- Database errors are caught and reported

### Retry Logic

The agent inherits automatic retry logic from `SpecializedAgent`:
- 3 retry attempts with exponential backoff
- Automatic retry on transient failures
- Error logging on final failure

## Testing

Tests are located in `tests/agents/test_scout_agent.py`:

- `test_scout_initialization`: Verifies agent initialization
- `test_scout_collects_content`: Tests successful content collection
- `test_scout_handles_no_content`: Tests empty collection handling
- `test_scout_handles_collection_error`: Tests error handling
- `test_scout_handles_partial_platform_results`: Tests partial failures

## Dependencies

- `CollectionOrchestratorAgent`: For platform collection
- `NewDatabaseManager`: For retrieving collected posts
- `SpecializedAgent`: Base class with retry logic
- `LangGraph`: For workflow integration

## Migration from Mock

The Scout agent replaces the previous mock implementation:

**Before (Mock)**:
```python
async def _scout_node(self, state: AgentState):
    mock_post = {
        "title": "New AI Model Released",
        "content": "...",
        "source": "techcrunch"
    }
    return {
        "messages": [AIMessage(content="Scout: Found 1 new item.")],
        "artifacts": {"current_post": mock_post},
        ...
    }
```

**After (Real)**:
```python
# Real collection using CollectionOrchestratorAgent
result = await self.collection_agent.collect_all()
# Retrieve actual posts from database
posts = db.get_posts_by_platform(platform, limit=count)
# Return real posts
```

## Acceptance Criteria

✅ Scout agent uses real collection  
✅ No mock data  
✅ Handles errors gracefully  
✅ Returns real posts from platforms  
✅ Test passes  
✅ AgentGraph uses real Scout  

All acceptance criteria have been met.


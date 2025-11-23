# Integrated Automation System

## Quick Start

Run the integrated automation system:

```bash
python main.py integrated
```

This starts the complete automation pipeline that combines:
- **AgentGraph** - Multi-agent analysis system
- **FullAutomationLoop** - Collection, analysis, transformation, and scheduling
- **PublisherWorker** - Automatic content posting

---

## Architecture

The integrated system consists of four main components:

### 1. IntegratedAutomationOrchestrator

**Location**: `src/core/orchestration/integrated_automation.py`

The main orchestrator that coordinates all components. It manages:

- **AgentGraph** initialization and execution
- **FullAutomationLoop** coordination
- **PublisherWorker** lifecycle
- Agent registration and messaging setup

**Key Methods**:
- `initialize()` - Sets up all systems and registers agents
- `run_cycle()` - Executes one complete automation cycle
- `run_forever()` - Runs continuously with configurable intervals
- `stop()` - Gracefully shuts down all components

**Usage**:
```python
from src.core.orchestration.integrated_automation import IntegratedAutomationOrchestrator

orchestrator = IntegratedAutomationOrchestrator()
await orchestrator.initialize()
await orchestrator.run_forever(interval_minutes=60, use_agent_graph=True)
```

---

### 2. AgentGraph

**Location**: `src/core/orchestration/agent_graph.py`

A LangGraph-based multi-agent system that orchestrates specialized agents for content analysis.

**Architecture**:
```
Director (Entry Point)
    ├── Scout Agent (Content Discovery)
    ├── Analyst Agent (Content Analysis)
    ├── Skeptic Agent (Verification)
    └── Historian Agent (Contextualization)
```

**Agent Flow**:
1. **Director** - Routes tasks to appropriate agents
2. **Scout** - Discovers and collects content
3. **Analyst** - Analyzes content quality and relevance
4. **Skeptic** - Verifies claims and fact-checks
5. **Historian** - Provides historical context

**State Management**:
- Uses `AgentState` TypedDict for shared state
- Tracks messages, artifacts, errors, and task status
- Agents communicate through state updates

**Usage**:
```python
from src.core.orchestration.agent_graph import AgentGraph

graph = AgentGraph()
result = await graph.run("Analyze this content...")
```

---

### 3. FullAutomationLoop

**Location**: `src/pipeline/full_automation_loop.py`

Orchestrates the complete content pipeline:

1. **Collection** - Gathers posts from multiple platforms
2. **Analysis** - Analyzes content (can use AgentGraph or existing system)
3. **Transformation** - Rewrites content for different personas
4. **Scheduling** - Schedules posts for optimal timing
5. **Publishing** - Automatic posting via PublisherWorker

**Key Methods**:
- `run_collection()` - Collects from all configured platforms
- `run_analysis()` - Analyzes unanalyzed posts
- `run_transformation_and_scheduling()` - Transforms and schedules posts

**Integration with AgentGraph**:
The orchestrator can use either:
- **AgentGraph** (new system) - Multi-agent analysis
- **Existing system** - Traditional analysis pipeline

Set `use_agent_graph=True` in `run_cycle()` to use AgentGraph.

---

### 4. PublisherWorker

**Location**: `src/publishing/worker.py`

Background service that automatically posts scheduled content.

**Features**:
- Checks for due posts every 15 seconds
- Posts to multiple platforms:
  - **Twitter** - Playwright (primary) or API (fallback)
  - **Threads** - Playwright only
  - **Telegram** - Bot API
- Tracks engagement metrics
- Handles posting errors gracefully

**Lifecycle**:
```python
from src.publishing.worker import get_publisher_worker

worker = get_publisher_worker()
worker.start()  # Starts background loop
# ... system runs ...
worker.stop()   # Graceful shutdown
```

---

## Agent Registration

### How Agents Are Registered

Agents are registered through the `AgentRegistry` system:

1. **Agent Creation** - Agents inherit from `BaseAgent`
2. **Registration** - Agents are registered with `AgentRegistry`
3. **Messaging Setup** - `AgentMessaging` is configured for inter-agent communication
4. **Health Checks** - Agents report their status to the registry

**Registration Flow**:
```python
from src.agents.registry import get_registry
from src.core.orchestration.agent_registration import register_specialized_agents

# Automatic registration (recommended)
agents = await register_specialized_agents()

# Manual registration
registry = get_registry()
registry.register(agent_instance)
```

### Specialized Agents

The system includes specialized agents:

- **AnalystAgent** (`analyst`) - Content analysis
- **SkepticAgent** (`skeptic`) - Verification and fact-checking
- **HistorianAgent** (`historian`) - Historical context

**Location**: `src/agents/specialized/`

### Messaging Setup

Agents communicate through Redis-based messaging:

**Configuration**:
```env
REDIS_URL=redis://localhost:6379
```

**Setup**:
```python
from src.agents.messaging import AgentMessaging

messaging = AgentMessaging(
    redis_url=os.getenv("REDIS_URL"),
    agent_id=agent.agent_id
)
await messaging.initialize()
agent.set_event_publisher(messaging.get_publisher())
```

**Features**:
- Pub/sub messaging between agents
- Event publishing for monitoring
- Health status broadcasting

### Health Checks

All agents implement health checks through `BaseAgent`:

```python
# Check individual agent health
health = await agent.check_health()
# Returns: {"status": "healthy", "details": {...}}

# Check all agents
registry = get_registry()
all_health = await registry.get_all_health()
```

**Health Status**:
- `healthy` - Agent is operational
- `degraded` - Agent has issues but is functional
- `unhealthy` - Agent is not operational

**Health Check Components**:
- Agent initialization status
- Dependency availability
- Resource usage
- Recent error rates

---

## Complete Automation Cycle

A full cycle consists of:

1. **Collection** (5-15 minutes)
   - Collects from Twitter, Reddit, Threads, Telegram
   - Stores raw posts in database

2. **Analysis** (10-30 minutes)
   - Uses AgentGraph or traditional analysis
   - Analyzes content quality, topics, personas
   - Stores analysis results

3. **Transformation** (5-10 minutes)
   - Matches posts to personas
   - Rewrites content for each persona
   - Generates scheduled posts

4. **Scheduling** (1-2 minutes)
   - Calculates optimal posting times
   - Schedules posts in database

5. **Publishing** (Continuous)
   - PublisherWorker checks every 15 seconds
   - Posts due content automatically
   - Tracks engagement

**Total Cycle Time**: ~20-60 minutes (depending on content volume)

---

## Configuration

### Environment Variables

Required:
```env
# Database
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key

# Redis (for agent messaging)
REDIS_URL=redis://localhost:6379

# AI Services (at least one)
MISTRAL_API_KEY=your_mistral_key
# OR
GEMINI_API_KEY=your_gemini_key
# OR
OLLAMA_URL=http://localhost:11434
```

Optional:
```env
# Telegram Bot
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Twitter/Threads (for posting)
TWITTER_USERNAME=your_username
TWITTER_PASSWORD=your_password
```

### Agent Configuration

Agents can be configured through:
- Environment variables
- Config files in `config/`
- Runtime parameters

---

## Monitoring

### Logs

All components log to:
- Console (stdout)
- Log files in `logs/` directory
- Structured JSON logs for parsing

**Log Levels**:
- `DEBUG` - Detailed debugging info
- `INFO` - General information
- `WARNING` - Non-critical issues
- `ERROR` - Errors that don't stop execution
- `CRITICAL` - Fatal errors

### Metrics

The system tracks:
- Posts collected per cycle
- Posts analyzed per cycle
- Posts scheduled per cycle
- Posts published per cycle
- Agent health status
- Error rates

### Health Monitoring

Check system health:
```python
from src.core.orchestration.integrated_automation import IntegratedAutomationOrchestrator

orchestrator = IntegratedAutomationOrchestrator()
health = await orchestrator.check_health()  # If implemented
```

---

## Troubleshooting

### Common Issues

**1. Agents not registering**
- Check Redis connection
- Verify agent initialization
- Check logs for registration errors

**2. PublisherWorker not posting**
- Verify worker is started: `worker._started == True`
- Check for due posts in database
- Verify platform credentials

**3. AgentGraph not analyzing**
- Check if `use_agent_graph=True` is set
- Verify AI service credentials
- Check agent state transitions in logs

**4. Collection failing**
- Verify platform credentials
- Check rate limits
- Review collection service logs

### Debug Mode

Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

---

## API Endpoints

The system exposes REST API endpoints (if API server is running):

**Agent Graph**:
- `GET /agents/status` - Get agent status
- `POST /agents/run` - Trigger agent cycle
- `GET /agents/stream` - SSE stream of agent events

**Automation**:
- `POST /automation/cycle` - Run one cycle
- `GET /automation/status` - Get automation status

---

## Next Steps

- See [Agent Framework Documentation](agents/AGENT_FRAMEWORK.md) for agent development
- See [Publishing Pipeline Architecture](PUBLISHING_PIPELINE_ARCHITECTURE.md) for publishing details
- See [Production Runbook](PRODUCTION_RUNBOOK.md) for deployment


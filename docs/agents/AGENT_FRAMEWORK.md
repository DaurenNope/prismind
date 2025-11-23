# Agent Framework Foundation

## Overview

The Agent Framework provides a robust foundation for building and managing autonomous agents in the Prismind system. It includes base classes, registry management, message queue integration, and configuration handling.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Agent Framework                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │  BaseAgent   │    │   Registry   │    │  Messaging   │  │
│  │              │    │              │    │              │  │
│  │ - Lifecycle  │    │ - Discovery  │    │ - Events     │  │
│  │ - Metrics    │    │ - Dependency │    │ - Tasks      │  │
│  │ - Health     │    │ - Health     │    │ - Retry      │  │
│  │ - Events     │    │ - Init Order │    │              │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│         │                    │                    │           │
│         └────────────────────┼────────────────────┘           │
│                              │                                │
│                    ┌─────────▼─────────┐                    │
│                    │   AgentConfig     │                    │
│                    │                   │                    │
│                    │ - YAML/JSON       │                    │
│                    │ - Env Overrides   │                    │
│                    │ - Feature Flags   │                    │
│                    │ - Rate Limits     │                    │
│                    └───────────────────┘                    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Components

### 1. BaseAgent

Abstract base class that all agents inherit from.

**Features:**
- Lifecycle management (initialize, execute, shutdown)
- Status tracking (IDLE, RUNNING, ERROR, STOPPED)
- Metrics collection
- Event publishing/subscribing
- Health checks
- Dependency management

**Example:**
```python
from src.agents import BaseAgent, AgentStatus

class MyAgent(BaseAgent):
    async def initialize(self) -> bool:
        # Setup resources
        return True
    
    async def execute(self, task: dict) -> dict:
        # Process task
        return {"result": "success"}
```

### 2. AgentRegistry

Central registry for agent discovery, registration, and dependency management.

**Features:**
- Agent registration and discovery
- Dependency resolution (topological sort)
- Health aggregation
- Initialization ordering

**Example:**
```python
from src.agents import AgentRegistry, get_registry

registry = get_registry()
registry.register(my_agent)
await registry.initialize_agent("my_agent")
health = await registry.aggregate_health()
```

### 3. AgentMessaging

Message queue integration for agents.

**Features:**
- Event publishing/subscribing
- Task queue management
- Retry logic
- Priority queuing

**Example:**
```python
from src.agents import AgentMessaging

messaging = AgentMessaging("redis://localhost", "my_agent")
await messaging.initialize()

# Publish event
publisher = messaging.get_publisher()
await publisher.publish("task.completed", {"task_id": "123"})

# Subscribe to events
subscriber = messaging.get_subscriber()
subscriber.subscribe("task.completed", handler_function)
```

### 4. AgentConfig

Configuration management with YAML/JSON support and environment overrides.

**Features:**
- YAML/JSON config loading
- Environment variable overrides
- Feature flags
- Rate limiting configuration

**Example:**
```python
from src.agents import AgentConfig, load_agent_config

# Load from file
config = load_agent_config("my_agent")

# Or create manually
config = AgentConfig(agent_id="my_agent")
config.load_config("config/my_agent.yaml")

# Access values
value = config.get("database.host")
is_enabled = config.is_feature_enabled("new_feature")
```

## Usage

### Creating an Agent

1. **Inherit from BaseAgent:**
```python
from src.agents import BaseAgent

class MyAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_id="my_agent",
            agent_name="My Agent",
            agent_version="1.0.0",
            dependencies=["other_agent"]
        )
    
    async def initialize(self) -> bool:
        # Initialize resources
        return True
    
    async def execute(self, task: dict) -> dict:
        # Process task
        return {"result": "success"}
```

2. **Register the agent:**
```python
from src.agents import get_registry

registry = get_registry()
agent = MyAgent()
registry.register(agent)
```

3. **Initialize and use:**
```python
await registry.initialize_agent("my_agent")
result = await agent.execute({"action": "test"})
```

### Configuration

Create a YAML configuration file:

```yaml
# config/agents/my_agent.yaml
database:
  host: localhost
  port: 5432

feature_flags:
  new_feature: true
  experimental: false

rate_limits:
  api_call:
    max_requests: 100
    window_seconds: 60
    burst: 10
```

Override with environment variables:
```bash
export AGENT_MY_AGENT_DATABASE_HOST=production_host
export AGENT_MY_AGENT_FEATURE_NEW_FEATURE=true
```

### Messaging

Set up messaging for event-driven communication:

```python
from src.agents import AgentMessaging

messaging = AgentMessaging("redis://localhost", "my_agent")
await messaging.initialize()

# Set up event publisher
publisher = messaging.get_publisher()
agent.set_event_publisher(publisher)

# Publish events
agent.publish_event("task.completed", {"task_id": "123"})

# Subscribe to events
subscriber = messaging.get_subscriber()

async def handle_event(event_data):
    print(f"Received event: {event_data}")

subscriber.subscribe("task.completed", handle_event)
await subscriber.start_consuming()
```

### Task Queue

Use task queue for asynchronous task processing:

```python
task_queue = messaging.get_task_queue()

async def process_task(task_data):
    # Process task
    return {"result": "success"}

task_queue.set_handler(process_task)
await task_queue.start_processing()

# Enqueue tasks
await task_queue.enqueue_task({"action": "process", "data": "test"})
```

## Health Checks

Monitor agent health:

```python
# Individual agent health
health = await agent.health_check()
print(health["healthy"])
print(health["metrics"])

# Aggregate health across all agents
registry = get_registry()
aggregate_health = await registry.aggregate_health()
print(aggregate_health["overall_healthy"])
print(aggregate_health["healthy_agents"])
```

## Metrics

Record and track metrics:

```python
# Record a metric
agent.record_metric("processing_time", 1.5, tags={"operation": "process"})

# Access metrics
metrics = agent.get_metrics()
print(metrics["processing_time"])
```

## Best Practices

1. **Always implement initialize() and execute()** - These are required abstract methods
2. **Handle errors gracefully** - Use try/except in execute() and return appropriate error responses
3. **Use dependency management** - Declare dependencies to ensure proper initialization order
4. **Publish events for important actions** - This enables event-driven architectures
5. **Record metrics** - Track performance and usage for observability
6. **Use configuration files** - Keep configuration separate from code
7. **Handle shutdown gracefully** - Clean up resources in shutdown()

## Testing

Run tests:

```bash
# Unit tests
pytest tests/agents/test_base_agent.py -v
pytest tests/agents/test_registry.py -v
pytest tests/agents/test_messaging.py -v
pytest tests/agents/test_config.py -v

# Integration tests
pytest tests/agents/integration/ -v -m integration

# With coverage
pytest tests/agents/ --cov=src/agents --cov-report=html
```

## Performance

Target performance metrics:
- Message throughput: >1000 events/sec
- Agent startup: <2 seconds
- Health check latency: <100ms

## Troubleshooting

### Agent fails to initialize
- Check dependencies are registered
- Verify configuration is correct
- Check logs for initialization errors

### Events not being received
- Verify messaging is initialized
- Check event subscriptions are set up
- Verify Redis connection

### Circular dependencies
- Review dependency graph
- Use registry.resolve_dependencies() to detect cycles

## API Reference

See the source code for detailed API documentation:
- `src/agents/base_agent.py` - BaseAgent class
- `src/agents/registry.py` - AgentRegistry class
- `src/agents/messaging.py` - Messaging classes
- `src/agents/config.py` - AgentConfig class




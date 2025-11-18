# System Status Page Explanation

## Overview

The System Status page (`/system`) provides real-time monitoring of:
- **System Health**: Overall system status (healthy/degraded/unhealthy)
- **Circuit Breakers**: Protection for external service calls
- **Observability Metrics**: Metrics, errors, and traces
- **Configuration**: Validation status

---

## Why Circuit Breakers Show "0 / 0"

**Circuit breakers are created on-demand** when external services are called. You'll see circuit breakers appear when:

1. **Supabase operations** are performed (creates `supabase` breaker)
2. **AI service calls** are made:
   - `mistral_ai` - When Mistral AI is used for analysis
   - `gemini_ai` - When Google Gemini is used
   - `ollama` - When Ollama is used for local analysis

### To See Circuit Breakers in Action

1. **Run Collection**: Start collecting posts from Twitter/Reddit/Threads
   - This will trigger Supabase saves → creates `supabase` breaker

2. **Run Analysis**: Analyze some posts
   - This will trigger AI service calls → creates `mistral_ai`, `gemini_ai`, or `ollama` breakers

3. **Monitor in Real-time**: The System Status page will show:
   - Circuit breaker states (closed = healthy, open = service failing)
   - Request/failure counts
   - Success rates

---

## Circuit Breaker States

- **CLOSED** (Green): Service is healthy, requests are allowed
- **HALF_OPEN** (Yellow): Testing if service has recovered after failure
- **OPEN** (Red): Service is failing, requests are blocked to prevent cascading failures

---

## Observability Metrics

- **Total Metrics**: Number of metrics tracked by the observability hub
- **Total Errors**: Number of errors captured
- **Active Traces**: Number of active distributed traces

These will populate as your system runs operations.

---

## Configuration Status

- **Valid**: All required configuration is correct
- **Invalid**: Configuration errors detected (check warnings)

---

## Auto-Refresh

The page automatically refreshes every 5 seconds to show real-time status. Toggle auto-refresh on/off with the checkbox.

---

## Expected Behavior

### When System is Idle (no operations)
- Circuit Breakers: 0 (no services called yet)
- Observability: All zeros (no operations to track)
- Configuration: Valid ✓

### When System is Active (operations running)
- Circuit Breakers: Will show breakers for active services
- Observability: Metrics and counts will increase
- Configuration: Should remain Valid ✓

---

## Testing Circuit Breakers

To test circuit breakers:

1. Start a collection operation
2. Watch the System Status page
3. Circuit breakers should appear for:
   - `supabase` - Database operations
   - `mistral_ai`, `gemini_ai`, `ollama` - AI analysis (if used)

If a service starts failing repeatedly:
- Circuit breaker will transition: CLOSED → OPEN
- Requests will be blocked
- Status will show "degraded"
- Circuit breaker can be manually reset via the API

---

## API Endpoints

- `GET /api/system/status` - Get overall system status
- `GET /api/system/circuit-breakers` - Get all circuit breakers
- `POST /api/system/circuit-breakers/{name}/reset` - Reset a circuit breaker
- `GET /api/observability/health` - Get observability health

---

## Next Steps

To see circuit breakers populate:
1. Navigate to **Collection** page
2. Start a collection (Twitter/Reddit/Threads)
3. Navigate back to **System** page
4. Watch circuit breakers appear and track metrics

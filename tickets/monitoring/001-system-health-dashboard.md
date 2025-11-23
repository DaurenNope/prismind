# MONITORING TICKET #001: System Health Dashboard

**Priority:** HIGH  
**Status:** ✅ COMPLETE  
**Estimated Time:** 3-4 hours  
**Assignee:** Completed

**Implementation Status:** ✅ COMPLETE
- ✅ System health service created (aggregates all health data)
- ✅ API endpoints implemented (`/api/system/health`, `/api/system/health/components`, `/api/system/health/metrics`)
- ✅ Frontend service functions added
- ✅ System health dashboard page created (`/system/health`)
- ✅ Component health, metrics, resources, and error summary displayed

## Problem

There's no centralized dashboard to monitor overall system health. Users can't see:
- System uptime
- Component health (database, AI services, collectors)
- Error rates
- Performance metrics
- Resource usage
- Recent issues

This makes it impossible to quickly assess system health and identify problems.

## Current State

**What Exists:**
- Health check endpoint (`/api/observability/health`)
- Metrics endpoint (`/api/observability/metrics`)
- Database health endpoint (`/api/database/health`)
- HealthMonitor service (`src/services/health.py`)

**What's Missing:**
- Unified health dashboard UI
- Real-time health updates
- Component status visualization
- Error rate tracking
- Performance metrics display
- Alert system

## Impact

- **Visibility:** Can't see system health at a glance
- **Debugging:** Hard to identify failing components
- **Monitoring:** Can't track system performance over time
- **Alerts:** No way to be notified of issues

## Requirements

Create a comprehensive system health dashboard showing:
1. Overall system status (healthy/degraded/critical)
2. Component health (database, AI services, collectors, etc.)
3. Performance metrics (response times, throughput)
4. Error rates and recent errors
5. Resource usage (CPU, memory, disk)
6. Recent activity and events

### API Endpoints Needed

1. `GET /api/system/health` - Get comprehensive health status
   - Returns: Overall status, component health, metrics

2. `GET /api/system/health/components` - Get component health
   - Returns: Health status for each component

3. `GET /api/system/health/metrics` - Get performance metrics
   - Returns: Response times, throughput, error rates

### Frontend Components Needed

1. System Health Dashboard Page (`/system/health`)
2. Health status card (overall)
3. Component health cards
4. Metrics charts
5. Error rate display
6. Resource usage display

## Checkpoints

### Checkpoint 1: Unified Health Service
- [ ] Review existing HealthMonitor service
- [ ] Enhance to aggregate all health data
- [ ] Include component health
- [ ] Include performance metrics
- [ ] Include error rates
- [ ] Calculate overall health score

**Health Service:**
```python
class SystemHealthService:
    def get_comprehensive_health(self) -> dict:
        """Get comprehensive system health"""
        components = self._check_all_components()
        metrics = self._get_performance_metrics()
        errors = self._get_error_rates()
        resources = self._get_resource_usage()
        
        overall_status = self._calculate_overall_status(
            components, metrics, errors
        )
        
        return {
            "status": overall_status,
            "uptime": self._get_uptime(),
            "components": components,
            "metrics": metrics,
            "errors": errors,
            "resources": resources,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
```

### Checkpoint 2: Component Health Checks
- [ ] Check database health
- [ ] Check AI services (Ollama, Mistral, Gemini)
- [ ] Check collection services
- [ ] Check publishing worker
- [ ] Check API endpoints
- [ ] Return status for each (healthy/degraded/critical)

**Component Checks:**
```python
def _check_all_components(self) -> dict:
    """Check health of all system components"""
    components = {}
    
    # Database
    try:
        posts = self.db.get_posts(limit=1)
        components["database"] = {
            "status": "healthy",
            "message": "Connected and responsive"
        }
    except Exception as e:
        components["database"] = {
            "status": "critical",
            "message": f"Error: {e}"
        }
    
    # AI Services
    components["ai_services"] = self._check_ai_services()
    
    # Collection Services
    components["collection"] = self._check_collection_services()
    
    # Publishing Worker
    components["publishing"] = self._check_publishing_worker()
    
    return components
```

### Checkpoint 3: Performance Metrics
- [ ] Track API response times
- [ ] Track collection rates
- [ ] Track analysis rates
- [ ] Track posting rates
- [ ] Calculate averages
- [ ] Store metrics history

### Checkpoint 4: Error Rate Tracking
- [ ] Track errors by component
- [ ] Calculate error rates
- [ ] Track recent errors
- [ ] Categorize errors (critical/warning/info)

### Checkpoint 5: Resource Usage
- [ ] Get CPU usage
- [ ] Get memory usage
- [ ] Get disk usage
- [ ] Get network usage (if applicable)
- [ ] Return current and historical data

### Checkpoint 6: Health API Endpoint
- [ ] Create `GET /api/system/health` endpoint
- [ ] Call health service
- [ ] Return comprehensive health data
- [ ] Cache for performance (5-10 seconds)
- [ ] Handle errors gracefully

### Checkpoint 7: Frontend Service
- [ ] Create `frontend/src/lib/services/systemHealth.ts`
- [ ] Implement `fetchSystemHealth()` function
- [ ] Implement `subscribeToHealthUpdates()` function (SSE)
- [ ] Add error handling
- [ ] Add TypeScript types

### Checkpoint 8: Health Dashboard Page
- [ ] Create `frontend/src/routes/system/health/+page.svelte`
- [ ] Display overall health status
- [ ] Display component health cards
- [ ] Display performance metrics
- [ ] Display error rates
- [ ] Display resource usage
- [ ] Connect to real-time updates
- [ ] Add loading state
- [ ] Add error handling

### Checkpoint 9: Overall Health Status Card
- [ ] Create status card component
- [ ] Display overall status (healthy/degraded/critical)
- [ ] Show uptime
- [ ] Show health score (0-100)
- [ ] Color code (green/yellow/red)
- [ ] Add icon
- [ ] Show last updated timestamp

### Checkpoint 10: Component Health Cards
- [ ] Create component health card component
- [ ] Display component name
- [ ] Display status (healthy/degraded/critical)
- [ ] Display status message
- [ ] Color code by status
- [ ] Add icon
- [ ] Show last checked timestamp
- [ ] Make clickable (link to component details)

### Checkpoint 11: Metrics Display
- [ ] Create metrics display component
- [ ] Show API response times (chart)
- [ ] Show throughput metrics
- [ ] Show error rates (chart)
- [ ] Show resource usage (charts)
- [ ] Add time range selector
- [ ] Use charts library (Chart.js, Recharts, etc.)

### Checkpoint 12: Error Rate Display
- [ ] Create error rate display component
- [ ] Show error rate over time (chart)
- [ ] Show errors by component
- [ ] Show recent errors list
- [ ] Color code by severity
- [ ] Add "View All Errors" link

### Checkpoint 13: Resource Usage Display
- [ ] Create resource usage component
- [ ] Show CPU usage (gauge/chart)
- [ ] Show memory usage (gauge/chart)
- [ ] Show disk usage (gauge/chart)
- [ ] Show usage trends
- [ ] Add warnings for high usage

### Checkpoint 14: Real-time Updates
- [ ] Integrate SSE stream for health updates
- [ ] Update health status in real-time
- [ ] Update component status
- [ ] Update metrics
- [ ] Handle connection errors
- [ ] Show connection status

### Checkpoint 15: Navigation Integration
- [ ] Add "System Health" link to System page
- [ ] Add to main navigation
- [ ] Update page title and meta
- [ ] Add breadcrumbs

### Checkpoint 16: Testing
- [ ] Test health endpoint
- [ ] Test component checks
- [ ] Test metrics collection
- [ ] Test error tracking
- [ ] Test resource usage
- [ ] Test real-time updates
- [ ] Test error handling

### Checkpoint 17: Documentation
- [ ] Document health system
- [ ] Document API endpoints
- [ ] Add usage examples
- [ ] Document health status values
- [ ] Add screenshots to docs

## Acceptance Criteria

- [ ] Health endpoint returns comprehensive health data
- [ ] Frontend displays health dashboard
- [ ] Component health displays correctly
- [ ] Performance metrics display correctly
- [ ] Error rates display correctly
- [ ] Resource usage displays correctly
- [ ] Real-time updates work
- [ ] Page is responsive
- [ ] Error handling works
- [ ] Loading states work

## API Response Format

**System Health:**
```json
{
  "status": "healthy",
  "uptime": "5d 12h 30m",
  "health_score": 95,
  "components": {
    "database": {
      "status": "healthy",
      "message": "Connected and responsive"
    },
    "ai_services": {
      "status": "degraded",
      "message": "Ollama unavailable"
    }
  },
  "metrics": {
    "api_response_time_avg": 120,
    "collection_rate": 15.0,
    "analysis_rate": 12.0
  },
  "errors": {
    "rate": 0.02,
    "recent": []
  },
  "resources": {
    "cpu": 45.2,
    "memory": 62.8,
    "disk": 78.5
  },
  "timestamp": "2025-11-23T10:00:00Z"
}
```

## Related Issues

- Ticket #015: Real-time Pipeline Status
- Ticket #013: Published Posts Dashboard

## Notes

- This is a high-priority monitoring feature
- Should integrate with existing health check endpoints
- Consider adding alerting system later
- Consider adding health history/trends
- Consider adding automated health checks


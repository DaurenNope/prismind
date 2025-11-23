<script lang="ts">
  import { onMount } from 'svelte';
  import {
    fetchSystemHealth,
    type SystemHealth
  } from '$lib/services/systemHealth';
  import LoadingSpinner from '$lib/components/LoadingSpinner.svelte';

  let health: SystemHealth | null = null;
  let loading = true;
  let error: string | null = null;
  let autoRefresh = true;
  let refreshInterval: ReturnType<typeof setInterval> | null = null;

  const loadData = async () => {
    try {
      const data = await fetchSystemHealth();
      health = data;
      error = null;
    } catch (err) {
      error = err instanceof Error ? err.message : 'Failed to load system health';
      console.error('Error loading system health:', err);
    } finally {
      loading = false;
    }
  };

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      healthy: 'bg-green-500',
      degraded: 'bg-yellow-500',
      critical: 'bg-red-500',
      unknown: 'bg-gray-500'
    };
    return colors[status] || 'bg-gray-500';
  };

  const getHealthScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-600';
    if (score >= 60) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getResourceColor = (percent: number) => {
    if (percent < 60) return 'text-green-600';
    if (percent < 80) return 'text-yellow-600';
    return 'text-red-600';
  };

  const formatBytes = (gb: number) => {
    if (gb < 1) return `${(gb * 1024).toFixed(0)} MB`;
    return `${gb.toFixed(2)} GB`;
  };

  onMount(() => {
    loadData();
    
    // Auto-refresh every 30 seconds
    refreshInterval = setInterval(() => {
      if (autoRefresh) {
        loadData();
      }
    }, 30000);
    
    return () => {
      if (refreshInterval) {
        clearInterval(refreshInterval);
      }
    };
  });
</script>

<svelte:head>
  <title>System Health - System</title>
</svelte:head>

<div class="container mx-auto px-4 py-8">
  <div class="mb-8 flex items-center justify-between">
    <div>
      <h1 class="text-3xl font-bold mb-2">System Health</h1>
      <p class="text-gray-600">Monitor overall system health and component status</p>
    </div>
    <div class="flex items-center gap-2">
      <label class="flex items-center gap-2 cursor-pointer">
        <input
          type="checkbox"
          bind:checked={autoRefresh}
          class="w-4 h-4"
        />
        <span class="text-sm text-gray-600">Auto-refresh</span>
      </label>
      <button
        on:click={loadData}
        class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
      >
        Refresh
      </button>
    </div>
  </div>

  {#if loading && !health}
    <LoadingSpinner />
  {:else if error}
    <div class="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
      <p class="text-red-800">{error}</p>
      <button
        on:click={loadData}
        class="mt-2 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
      >
        Retry
      </button>
    </div>
  {:else if health}
    <!-- Overall Health Status -->
    <div class="bg-white rounded-lg shadow p-6 mb-6">
      <div class="flex items-center justify-between mb-4">
        <div class="flex items-center gap-4">
          <div class={`w-16 h-16 rounded-full ${getStatusColor(health.status)} flex items-center justify-center`}>
            <span class="text-2xl text-white">
              {health.status === 'healthy' ? '✓' : health.status === 'degraded' ? '⚠' : '✕'}
            </span>
          </div>
          <div>
            <h2 class="text-2xl font-bold capitalize">{health.status}</h2>
            <p class="text-gray-600">Uptime: {health.uptime}</p>
          </div>
        </div>
        <div class="text-right">
          <div class="text-sm text-gray-600 mb-1">Health Score</div>
          <div class={`text-4xl font-bold ${getHealthScoreColor(health.health_score)}`}>
            {health.health_score}
          </div>
          <div class="text-xs text-gray-500">/ 100</div>
        </div>
      </div>
    </div>

    <!-- Component Health -->
    <div class="mb-6">
      <h2 class="text-xl font-semibold mb-4">Component Health</h2>
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {#each Object.entries(health.components) as [name, component]}
          <div class="bg-white rounded-lg shadow p-4">
            <div class="flex items-center justify-between mb-2">
              <h3 class="font-medium text-gray-800 capitalize">{name.replace('_', ' ')}</h3>
              <div class={`w-3 h-3 rounded-full ${getStatusColor(component.status)}`}></div>
            </div>
            <p class="text-sm text-gray-600">{component.message}</p>
            <div class="mt-2">
              <span class="px-2 py-1 rounded text-xs font-medium {getStatusColor(component.status)} text-white">
                {component.status}
              </span>
            </div>
          </div>
        {/each}
      </div>
    </div>

    <!-- Resource Usage -->
    <div class="mb-6">
      <h2 class="text-xl font-semibold mb-4">Resource Usage</h2>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <!-- CPU -->
        <div class="bg-white rounded-lg shadow p-4">
          <div class="flex items-center justify-between mb-2">
            <h3 class="font-medium text-gray-800">CPU</h3>
            <span class="text-sm font-bold {getResourceColor(health.resources.cpu.percent)}">
              {health.resources.cpu.percent.toFixed(1)}%
            </span>
          </div>
          <div class="w-full bg-gray-200 rounded-full h-2">
            <div
              class="bg-blue-600 h-2 rounded-full transition-all"
              style="width: {health.resources.cpu.percent}%"
            ></div>
          </div>
          <p class="text-xs text-gray-500 mt-1">Status: {health.resources.cpu.status}</p>
        </div>

        <!-- Memory -->
        <div class="bg-white rounded-lg shadow p-4">
          <div class="flex items-center justify-between mb-2">
            <h3 class="font-medium text-gray-800">Memory</h3>
            <span class="text-sm font-bold {getResourceColor(health.resources.memory.percent)}">
              {health.resources.memory.percent.toFixed(1)}%
            </span>
          </div>
          <div class="w-full bg-gray-200 rounded-full h-2">
            <div
              class="bg-blue-600 h-2 rounded-full transition-all"
              style="width: {health.resources.memory.percent}%"
            ></div>
          </div>
          <p class="text-xs text-gray-500 mt-1">
            {formatBytes(health.resources.memory.used_gb)} / {formatBytes(health.resources.memory.total_gb)}
          </p>
        </div>

        <!-- Disk -->
        <div class="bg-white rounded-lg shadow p-4">
          <div class="flex items-center justify-between mb-2">
            <h3 class="font-medium text-gray-800">Disk</h3>
            <span class="text-sm font-bold {getResourceColor(health.resources.disk.percent)}">
              {health.resources.disk.percent.toFixed(1)}%
            </span>
          </div>
          <div class="w-full bg-gray-200 rounded-full h-2">
            <div
              class="bg-blue-600 h-2 rounded-full transition-all"
              style="width: {health.resources.disk.percent}%"
            ></div>
          </div>
          <p class="text-xs text-gray-500 mt-1">
            {formatBytes(health.resources.disk.free_gb)} free
          </p>
        </div>
      </div>
    </div>

    <!-- Performance Metrics -->
    <div class="mb-6">
      <h2 class="text-xl font-semibold mb-4">Performance Metrics</h2>
      <div class="bg-white rounded-lg shadow p-4">
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <div class="text-sm text-gray-600 mb-1">API Response Time</div>
            <div class="text-2xl font-bold">{health.metrics.api_response_time_avg.toFixed(0)}ms</div>
          </div>
          <div>
            <div class="text-sm text-gray-600 mb-1">Collection Rate</div>
            <div class="text-2xl font-bold">{health.metrics.collection_rate.toFixed(1)}/hr</div>
          </div>
          <div>
            <div class="text-sm text-gray-600 mb-1">Analysis Rate</div>
            <div class="text-2xl font-bold">{health.metrics.analysis_rate.toFixed(1)}/hr</div>
          </div>
          <div>
            <div class="text-sm text-gray-600 mb-1">Error Rate</div>
            <div class="text-2xl font-bold {getResourceColor(health.metrics.error_rate * 100)}">
              {health.metrics.error_rate.toFixed(2)}/hr
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Error Summary -->
    {#if health.errors.total_errors > 0}
      <div class="mb-6">
        <h2 class="text-xl font-semibold mb-4">Error Summary</h2>
        <div class="bg-white rounded-lg shadow p-4">
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
            <div>
              <div class="text-sm text-gray-600 mb-1">Total Errors</div>
              <div class="text-2xl font-bold">{health.errors.total_errors}</div>
            </div>
            <div>
              <div class="text-sm text-gray-600 mb-1">Error Rate</div>
              <div class="text-2xl font-bold">{health.errors.rate.toFixed(2)}/hr</div>
            </div>
            <div>
              <a
                href="/system/errors"
                class="text-blue-600 hover:text-blue-800 underline"
              >
                View All Errors →
              </a>
            </div>
          </div>
          
          {#if health.errors.recent.length > 0}
            <div class="mt-4">
              <div class="text-sm font-medium text-gray-700 mb-2">Recent Errors</div>
              <div class="space-y-2">
                {#each health.errors.recent.slice(0, 5) as err}
                  <div class="flex items-center gap-2 text-sm">
                    <span class="px-2 py-0.5 rounded text-xs {getStatusColor(err.severity)} text-white">
                      {err.severity}
                    </span>
                    <span class="text-gray-600">{err.component}:</span>
                    <span class="text-gray-800 flex-1 truncate">{err.message}</span>
                  </div>
                {/each}
              </div>
            </div>
          {/if}
        </div>
      </div>
    {/if}

    <!-- Pipeline Status -->
    <div class="mb-6">
      <h2 class="text-xl font-semibold mb-4">Pipeline Status</h2>
      <div class="bg-white rounded-lg shadow p-4">
        <div class="flex items-center justify-between mb-4">
          <div class="flex items-center gap-2">
            <div class={`w-3 h-3 rounded-full ${getStatusColor(health.pipeline.health)}`}></div>
            <span class="font-medium capitalize">{health.pipeline.health}</span>
          </div>
          <a
            href="/system/pipeline"
            class="text-blue-600 hover:text-blue-800 underline text-sm"
          >
            View Details →
          </a>
        </div>
        
        <div class="grid grid-cols-5 gap-4">
          {#each Object.entries(health.pipeline.stages) as [stage, count]}
            <div class="text-center">
              <div class="text-2xl font-bold">{count}</div>
              <div class="text-xs text-gray-600 capitalize">{stage}</div>
            </div>
          {/each}
        </div>
        
        {#if health.pipeline.bottlenecks.length > 0}
          <div class="mt-4 pt-4 border-t">
            <div class="text-sm font-medium text-gray-700 mb-2">Bottlenecks</div>
            <div class="flex flex-wrap gap-2">
              {#each health.pipeline.bottlenecks as bottleneck}
                <span class="px-2 py-1 bg-yellow-100 text-yellow-800 rounded text-xs">
                  {bottleneck}
                </span>
              {/each}
            </div>
          </div>
        {/if}
      </div>
    </div>

    <!-- Last Updated -->
    <div class="text-xs text-gray-500 text-center">
      Last updated: {new Date(health.timestamp).toLocaleString()}
    </div>
  {/if}
</div>


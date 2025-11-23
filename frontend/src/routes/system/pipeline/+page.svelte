<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import {
    fetchPipelineStatus,
    subscribeToPipelineStatus,
    fetchPipelineMetrics,
    type PipelineStatusResponse,
    type PipelineMetrics
  } from '$lib/services/pipelineStatus';
  import LoadingSpinner from '$lib/components/LoadingSpinner.svelte';

  let statusData: PipelineStatusResponse | null = null;
  let metrics: PipelineMetrics | null = null;
  let loading = true;
  let error: string | null = null;
  let connected = false;
  let unsubscribe: (() => void) | null = null;
  let timeRange: '1h' | '24h' | '7d' = '1h';

  const loadData = async () => {
    try {
      const [status, metricsData] = await Promise.all([
        fetchPipelineStatus(),
        fetchPipelineMetrics(timeRange)
      ]);
      statusData = status;
      metrics = metricsData;
      error = null;
    } catch (err) {
      error = err instanceof Error ? err.message : 'Failed to load pipeline status';
      console.error('Error loading pipeline status:', err);
    } finally {
      loading = false;
    }
  };

  const formatRelativeTime = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffSecs = Math.floor(diffMs / 1000);
    const diffMins = Math.floor(diffSecs / 60);

    if (diffSecs < 10) return 'Just now';
    if (diffSecs < 60) return `${diffSecs}s ago`;
    if (diffMins < 60) return `${diffMins}m ago`;
    return date.toLocaleTimeString();
  };

  const getHealthColor = (health: string) => {
    const colors: Record<string, string> = {
      healthy: 'bg-green-500',
      degraded: 'bg-yellow-500',
      critical: 'bg-red-500',
      idle: 'bg-gray-500',
      unknown: 'bg-gray-400'
    };
    return colors[health] || 'bg-gray-400';
  };

  const getActivityIcon = (type: string) => {
    const icons: Record<string, string> = {
      collection: '📥',
      analysis: '🔍',
      rewrite: '✍️',
      post: '📤',
      error: '❌'
    };
    return icons[type] || '📋';
  };

  onMount(() => {
    loadData();

    // Subscribe to real-time updates
    unsubscribe = subscribeToPipelineStatus(
      (data) => {
        statusData = data;
        connected = true;
      },
      (err) => {
        console.error('SSE error:', err);
        connected = false;
      }
    );
  });

  onDestroy(() => {
    if (unsubscribe) {
      unsubscribe();
    }
  });

  $: if (timeRange) {
    fetchPipelineMetrics(timeRange).then(data => {
      metrics = data;
    }).catch(err => {
      console.error('Error fetching metrics:', err);
    });
  }
</script>

<svelte:head>
  <title>Pipeline Status - System</title>
</svelte:head>

<div class="container mx-auto px-4 py-8">
  <div class="mb-8 flex items-center justify-between">
    <div>
      <h1 class="text-3xl font-bold mb-2">Pipeline Status</h1>
      <p class="text-gray-600">Real-time pipeline activity and metrics</p>
    </div>
    <div class="flex items-center gap-2">
      <div class="flex items-center gap-2">
        <div class={`w-2 h-2 rounded-full ${connected ? 'bg-green-500' : 'bg-red-500'}`}></div>
        <span class="text-sm text-gray-600">{connected ? 'Connected' : 'Disconnected'}</span>
      </div>
      <button
        on:click={loadData}
        class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
      >
        Refresh
      </button>
    </div>
  </div>

  {#if loading && !statusData}
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
  {:else if statusData}
    <!-- Status Cards -->
    <div class="grid grid-cols-1 md:grid-cols-5 gap-4 mb-6">
      {#each [
        { key: 'collected', label: 'Collected', icon: '📥' },
        { key: 'analyzed', label: 'Analyzed', icon: '🔍' },
        { key: 'rewritten', label: 'Rewritten', icon: '✍️' },
        { key: 'scheduled', label: 'Scheduled', icon: '⏰' },
        { key: 'posted', label: 'Posted', icon: '📤' }
      ] as stage}
        {@const count = statusData.status.stages[stage.key]}
        {@const rate = stage.key === 'collected' ? statusData.status.rates.collection :
                      stage.key === 'analyzed' ? statusData.status.rates.analysis :
                      stage.key === 'posted' ? statusData.status.rates.posting : 0}
        <div class="bg-white rounded-lg shadow p-4">
          <div class="flex items-center justify-between mb-2">
            <span class="text-2xl">{stage.icon}</span>
            <span class="text-xs text-gray-500">{rate.toFixed(1)}/hr</span>
          </div>
          <div class="text-2xl font-bold mb-1">{count}</div>
          <div class="text-sm text-gray-600">{stage.label}</div>
        </div>
      {/each}
    </div>

    <!-- Health and Bottlenecks -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
      <div class="bg-white rounded-lg shadow p-4">
        <h2 class="text-lg font-semibold mb-3">System Health</h2>
        <div class="flex items-center gap-3">
          <div class={`w-4 h-4 rounded-full ${getHealthColor(statusData.status.health)}`}></div>
          <span class="text-lg font-medium capitalize">{statusData.status.health}</span>
        </div>
      </div>
      <div class="bg-white rounded-lg shadow p-4">
        <h2 class="text-lg font-semibold mb-3">Bottlenecks</h2>
        {#if statusData.status.bottlenecks.length === 0}
          <p class="text-gray-600">No bottlenecks detected</p>
        {:else}
          <div class="flex flex-wrap gap-2">
            {#each statusData.status.bottlenecks as bottleneck}
              <span class="px-2 py-1 bg-red-100 text-red-800 rounded text-sm">
                {bottleneck}
              </span>
            {/each}
          </div>
        {/if}
      </div>
    </div>

    <!-- Metrics -->
    {#if metrics}
      <div class="bg-white rounded-lg shadow p-4 mb-6">
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-lg font-semibold">Performance Metrics</h2>
          <select
            bind:value={timeRange}
            class="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="1h">Last Hour</option>
            <option value="24h">Last 24 Hours</option>
            <option value="7d">Last 7 Days</option>
          </select>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <div class="text-sm text-gray-600 mb-1">Collection Rate</div>
            <div class="text-2xl font-bold">{metrics.current.collection_rate.toFixed(1)} posts/hr</div>
          </div>
          <div>
            <div class="text-sm text-gray-600 mb-1">Analysis Rate</div>
            <div class="text-2xl font-bold">{metrics.current.analysis_rate.toFixed(1)} posts/hr</div>
          </div>
          <div>
            <div class="text-sm text-gray-600 mb-1">Posting Rate</div>
            <div class="text-2xl font-bold">{metrics.current.posting_rate.toFixed(1)} posts/hr</div>
          </div>
        </div>
      </div>
    {/if}

    <!-- Activity Feed -->
    <div class="bg-white rounded-lg shadow p-4">
      <h2 class="text-lg font-semibold mb-4">Recent Activity</h2>
      {#if statusData.activity.length === 0}
        <p class="text-gray-600">No recent activity</p>
      {:else}
        <div class="space-y-2 max-h-96 overflow-y-auto">
          {#each statusData.activity as activity}
            <div class="flex items-start gap-3 p-2 hover:bg-gray-50 rounded">
              <span class="text-xl">{getActivityIcon(activity.type)}</span>
              <div class="flex-1">
                <p class="text-sm text-gray-800">{activity.message}</p>
                <p class="text-xs text-gray-500">{formatRelativeTime(activity.timestamp)}</p>
              </div>
            </div>
          {/each}
        </div>
      {/if}
    </div>
  {/if}
</div>


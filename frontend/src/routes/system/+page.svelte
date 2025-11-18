<script lang="ts">
  import { onMount } from 'svelte';
  import {
    fetchSystemStatus,
    fetchCircuitBreakers,
    fetchObservabilityHealth,
    fetchCredentials,
    type SystemStatus,
    type CircuitBreakerStatus,
    type ObservabilityHealth,
    type CredentialsStatus
  } from '$lib/services/observability';

  let systemStatus: SystemStatus | null = null;
  let breakers: Record<string, CircuitBreakerStatus> = {};
  let observability: ObservabilityHealth | null = null;
  let credentials: CredentialsStatus | null = null;
  let loading = true;
  let error: string | null = null;
  let autoRefresh = true;
  let refreshInterval: ReturnType<typeof setInterval> | null = null;

  const loadData = async () => {
    try {
      [systemStatus, breakers, observability, credentials] = await Promise.all([
        fetchSystemStatus(),
        fetchCircuitBreakers(),
        fetchObservabilityHealth(),
        fetchCredentials()
      ]);
      error = null;
    } catch (e) {
      error = e instanceof Error ? e.message : 'Unknown error';
      console.error('Error loading system data:', e);
    } finally {
      loading = false;
    }
  };

  onMount(() => {
    loadData();
    if (autoRefresh) {
      refreshInterval = setInterval(loadData, 30000); // Refresh every 30 seconds
    }
    return () => {
      if (refreshInterval) clearInterval(refreshInterval);
    };
  });

  const getHealthColor = (health: string) => {
    switch (health) {
      case 'healthy':
        return 'text-emerald-400';
      case 'degraded':
        return 'text-amber-400';
      case 'unhealthy':
        return 'text-red-400';
      default:
        return 'text-slate-400';
    }
  };

  const getStateColor = (state: string) => {
    switch (state) {
      case 'closed':
        return 'text-emerald-400 bg-emerald-400/10 border-emerald-400/20';
      case 'half_open':
        return 'text-amber-400 bg-amber-400/10 border-amber-400/20';
      case 'open':
        return 'text-red-400 bg-red-400/10 border-red-400/20';
      default:
        return 'text-slate-400 bg-slate-400/10 border-slate-400/20';
    }
  };

  const formatNumber = (value: number | undefined) =>
    value === undefined ? '—' : value.toLocaleString();
</script>

<svelte:head>
  <title>System Status · BeyondLines</title>
  <meta name="description" content="System observability, circuit breakers, and health monitoring" />
</svelte:head>

<div class="space-y-8">
  <!-- HEADER -->
  <div class="flex items-center justify-between">
    <div>
      <h1 class="text-3xl font-semibold text-white">System Status</h1>
      <p class="text-sm text-slate-300 mt-2">Real-time observability, circuit breakers, and health monitoring</p>
    </div>
    <label class="flex items-center gap-2 text-sm text-slate-300">
      <input
        type="checkbox"
        bind:checked={autoRefresh}
        class="rounded border-white/20 bg-white/5"
      />
      Auto-refresh
    </label>
  </div>

  {#if loading}
    <div class="text-center py-12 text-slate-400">Loading system status...</div>
  {:else if error}
    <div class="rounded-2xl border border-red-400/20 bg-red-400/10 p-6 text-red-200">
      <p class="font-semibold">Error loading system status</p>
      <p class="text-sm mt-2">{error}</p>
    </div>
  {:else if systemStatus}
    <!-- OVERALL HEALTH -->
    <div class="rounded-3xl border border-white/10 bg-white/6 backdrop-blur-2xl p-6">
      <div class="flex items-center justify-between mb-6">
        <h2 class="text-xl font-semibold text-white">System Health</h2>
        <span class={`text-lg font-semibold uppercase ${getHealthColor(systemStatus.system_health)}`}>
          {systemStatus.system_health}
        </span>
      </div>

      <div class="grid gap-4 md:grid-cols-3">
        <div class="rounded-2xl border border-white/10 bg-white/5 p-4">
          <p class="text-xs uppercase tracking-wider text-slate-400 mb-2">Observability</p>
          <p class="text-2xl font-semibold text-white">{formatNumber(systemStatus.observability.metrics_count)}</p>
          <p class="text-xs text-slate-400 mt-1">Metrics · {formatNumber(systemStatus.observability.errors_count)} errors</p>
        </div>
        <div class="rounded-2xl border border-white/10 bg-white/5 p-4">
          <p class="text-xs uppercase tracking-wider text-slate-400 mb-2">Circuit Breakers</p>
          <p class="text-2xl font-semibold text-white">
            {systemStatus.circuit_breakers.closed} / {systemStatus.circuit_breakers.total}
          </p>
          <p class="text-xs text-slate-400 mt-1">
            {systemStatus.circuit_breakers.open} open · {systemStatus.circuit_breakers.half_open} half-open
          </p>
        </div>
        <div class="rounded-2xl border border-white/10 bg-white/5 p-4">
          <p class="text-xs uppercase tracking-wider text-slate-400 mb-2">Configuration</p>
          <p class="text-2xl font-semibold text-white">
            {systemStatus.configuration.is_valid ? '✓ Valid' : '✗ Invalid'}
          </p>
          <p class="text-xs text-slate-400 mt-1">
            {systemStatus.configuration.error_count} errors · {systemStatus.configuration.warning_count} warnings
          </p>
        </div>
      </div>
    </div>

    <!-- CIRCUIT BREAKERS -->
    <div class="rounded-3xl border border-white/10 bg-white/6 backdrop-blur-2xl p-6">
      <h2 class="text-xl font-semibold text-white mb-6">Circuit Breakers</h2>

      {#if Object.keys(breakers).length === 0}
        <p class="text-sm text-slate-400">No circuit breakers configured</p>
      {:else}
        <div class="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {#each Object.entries(breakers) as [name, breaker]}
            <div class="rounded-2xl border border-white/10 bg-white/5 p-4">
              <div class="flex items-center justify-between mb-3">
                <h3 class="font-semibold text-white capitalize">{name.replace('_', ' ')}</h3>
                <span class={`text-xs px-2 py-1 rounded-full border ${getStateColor(breaker.state)}`}>
                  {breaker.state}
                </span>
              </div>
              <div class="space-y-2 text-sm">
                <div class="flex justify-between">
                  <span class="text-slate-400">Requests</span>
                  <span class="text-white">{formatNumber(breaker.total_requests)}</span>
                </div>
                <div class="flex justify-between">
                  <span class="text-slate-400">Failures</span>
                  <span class="text-red-300">{formatNumber(breaker.total_failures)}</span>
                </div>
                <div class="flex justify-between">
                  <span class="text-slate-400">Success</span>
                  <span class="text-emerald-300">{formatNumber(breaker.success_count)}</span>
                </div>
                <div class="flex justify-between">
                  <span class="text-slate-400">Failure Rate</span>
                  <span class="text-white">{(breaker.failure_rate * 100).toFixed(1)}%</span>
                </div>
              </div>
            </div>
          {/each}
        </div>
      {/if}
    </div>

    <!-- OBSERVABILITY METRICS -->
    {#if observability}
      <div class="rounded-3xl border border-white/10 bg-white/6 backdrop-blur-2xl p-6">
        <h2 class="text-xl font-semibold text-white mb-6">Observability Metrics</h2>

        <div class="grid gap-4 md:grid-cols-3">
          <div class="rounded-2xl border border-white/10 bg-white/5 p-4">
            <p class="text-xs uppercase tracking-wider text-slate-400 mb-2">Total Metrics</p>
            <p class="text-2xl font-semibold text-white">{formatNumber(observability.metrics.total_metrics)}</p>
          </div>
          <div class="rounded-2xl border border-white/10 bg-white/5 p-4">
            <p class="text-xs uppercase tracking-wider text-slate-400 mb-2">Total Errors</p>
            <p class="text-2xl font-semibold text-red-300">{formatNumber(observability.errors.total_errors)}</p>
          </div>
          <div class="rounded-2xl border border-white/10 bg-white/5 p-4">
            <p class="text-xs uppercase tracking-wider text-slate-400 mb-2">Active Traces</p>
            <p class="text-2xl font-semibold text-blue-300">{formatNumber(observability.traces.active_traces ?? 0)}</p>
          </div>
        </div>

        {#if Object.keys(observability.errors.error_types).length > 0}
          <div class="mt-6">
            <h3 class="text-sm font-semibold text-white mb-3">Error Types</h3>
            <div class="space-y-2">
              {#each Object.entries(observability.errors.error_types) as [errorType, count]}
                <div class="flex items-center justify-between rounded-xl border border-white/10 bg-white/5 px-4 py-2">
                  <span class="text-sm text-slate-300">{errorType}</span>
                  <span class="text-sm font-semibold text-red-300">{formatNumber(count)}</span>
                </div>
              {/each}
            </div>
          </div>
        {/if}
      </div>
    {/if}

    <!-- CREDENTIALS STATUS -->
    {#if credentials}
      <div class="rounded-3xl border border-white/10 bg-white/6 backdrop-blur-2xl p-6">
        <h2 class="text-xl font-semibold text-white mb-6">Current Credentials</h2>

        <div class="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          <!-- Twitter -->
          <div class="rounded-2xl border border-white/10 bg-white/5 p-4">
            <h3 class="font-semibold text-white mb-3">Twitter</h3>
            <div class="space-y-2 text-sm">
              <div class="flex justify-between">
                <span class="text-slate-400">Username</span>
                <span class="text-white">{credentials.credentials.twitter.username}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-slate-400">Password</span>
                <span class={credentials.credentials.twitter.password === 'Set' ? 'text-emerald-300' : 'text-red-300'}>
                  {credentials.credentials.twitter.password}
                </span>
              </div>
              <div class="flex justify-between">
                <span class="text-slate-400">Cookie File</span>
                <span class={credentials.credentials.twitter.cookie_file_exists ? 'text-emerald-300' : 'text-red-300'}>
                  {credentials.credentials.twitter.cookie_file_exists ? '✓ Exists' : '✗ Missing'}
                </span>
              </div>
            </div>
          </div>

          <!-- Threads -->
          <div class="rounded-2xl border border-white/10 bg-white/5 p-4">
            <h3 class="font-semibold text-white mb-3">Threads</h3>
            <div class="space-y-2 text-sm">
              <div class="flex justify-between">
                <span class="text-slate-400">Username</span>
                <span class="text-white">{credentials.credentials.threads.username}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-slate-400">Password</span>
                <span class={credentials.credentials.threads.password === 'Set' ? 'text-emerald-300' : 'text-red-300'}>
                  {credentials.credentials.threads.password}
                </span>
              </div>
              <div class="flex justify-between">
                <span class="text-slate-400">Cookie File</span>
                <span class={credentials.credentials.threads.cookie_file_exists ? 'text-emerald-300' : 'text-red-300'}>
                  {credentials.credentials.threads.cookie_file_exists ? '✓ Exists' : '✗ Missing'}
                </span>
              </div>
              <div class="flex justify-between">
                <span class="text-slate-400">Allowed Handles</span>
                <span class="text-white text-xs">{credentials.credentials.threads.allowed_handles}</span>
              </div>
            </div>
          </div>

          <!-- Reddit -->
          <div class="rounded-2xl border border-white/10 bg-white/5 p-4">
            <h3 class="font-semibold text-white mb-3">Reddit</h3>
            <div class="space-y-2 text-sm">
              <div class="flex justify-between">
                <span class="text-slate-400">Client ID</span>
                <span class="text-white">{credentials.credentials.reddit.client_id}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-slate-400">Client Secret</span>
                <span class={credentials.credentials.reddit.client_secret === 'Set' ? 'text-emerald-300' : 'text-red-300'}>
                  {credentials.credentials.reddit.client_secret}
                </span>
              </div>
              <div class="flex justify-between">
                <span class="text-slate-400">Username</span>
                <span class="text-white">{credentials.credentials.reddit.username}</span>
              </div>
            </div>
          </div>

          <!-- Supabase -->
          <div class="rounded-2xl border border-white/10 bg-white/5 p-4">
            <h3 class="font-semibold text-white mb-3">Supabase</h3>
            <div class="space-y-2 text-sm">
              <div class="flex justify-between">
                <span class="text-slate-400">URL</span>
                <span class="text-white text-xs">{credentials.credentials.supabase.url}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-slate-400">Key</span>
                <span class={credentials.credentials.supabase.key === 'Set' ? 'text-emerald-300' : 'text-red-300'}>
                  {credentials.credentials.supabase.key}
                </span>
              </div>
            </div>
          </div>

          <!-- Telegram -->
          <div class="rounded-2xl border border-white/10 bg-white/5 p-4">
            <h3 class="font-semibold text-white mb-3">Telegram</h3>
            <div class="space-y-2 text-sm">
              <div class="flex justify-between">
                <span class="text-slate-400">Bot Token</span>
                <span class="text-white">{credentials.credentials.telegram.bot_token}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-slate-400">Chat ID</span>
                <span class="text-white">{credentials.credentials.telegram.chat_id}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    {/if}
  {/if}
</div>

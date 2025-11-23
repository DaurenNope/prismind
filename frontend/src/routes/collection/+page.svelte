<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { fetchCollectorStatus, fetchCollectionLogs } from '$lib/services/collection';
  import { API_BASE, getFetchOptions } from '$lib/config';
  import type { CollectorStatus, CollectionLogEntry, PostRecord } from '$lib/types';

  let collectors: CollectorStatus[] = [];
  let logs: CollectionLogEntry[] = [];
  let loadingSweep = false;
  let loadingData = true;
  let error: string | null = null;
  let runningPlatforms = new Set<string>();
  let autoRefresh = true;
  const refreshMs = 30_000;
  let refreshTimer: ReturnType<typeof setInterval> | null = null;

  // Latest Collections state
  let latestPosts: PostRecord[] = [];
  let loadingLatestPosts = false;
  let timeFilter: '1h' | '6h' | '24h' | '7d' | 'all' = '24h';
  let latestPostsError: string | null = null;

  const getTimeFilterDate = (filter: string): Date | null => {
    const now = new Date();
    switch (filter) {
      case '1h':
        return new Date(now.getTime() - 60 * 60 * 1000);
      case '6h':
        return new Date(now.getTime() - 6 * 60 * 60 * 1000);
      case '24h':
        return new Date(now.getTime() - 24 * 60 * 60 * 1000);
      case '7d':
        return new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
      case 'all':
      default:
        return null;
    }
  };

  const fetchLatestPosts = async () => {
    loadingLatestPosts = true;
    latestPostsError = null;
    try {
      const sinceDate = getTimeFilterDate(timeFilter);
      const params = new URLSearchParams({
        limit: '50',
        offset: '0'
      });

      // Note: The API doesn't support time filtering directly,
      // so we'll fetch and filter client-side
      const response = await fetch(`${API_BASE}/api/posts?${params.toString()}`, getFetchOptions());
      if (!response.ok) {
        throw new Error(`Failed to fetch posts: ${response.status}`);
      }
      const data = await response.json();
      let posts: PostRecord[] = data.posts || [];

      // Filter by time if needed
      if (sinceDate) {
        posts = posts.filter((post) => {
          if (!post.created_at) return false;
          const postDate = new Date(post.created_at);
          return postDate >= sinceDate;
        });
      }

      latestPosts = posts;
    } catch (err) {
      latestPostsError = err instanceof Error ? err.message : 'Failed to load latest posts';
      console.error('Error fetching latest posts:', err);
      latestPosts = [];
    } finally {
      loadingLatestPosts = false;
    }
  };

  const loadData = async () => {
    loadingData = true;
    error = null;
    try {
      // Fetch with individual timeouts (handled in service)
      const [statusData, logData] = await Promise.all([
        fetchCollectorStatus(),
        fetchCollectionLogs()
      ]);

      collectors = statusData;
      logs = logData;

      // Update running platforms based on status
      // If a platform is not in "idle" or "error" state, it might be running
      // But we'll use the status from the API to determine this
      // Clear running platforms that are now idle
      const activePlatforms = new Set(
        statusData
          .filter(c => c.status === 'running' || runningPlatforms.has(c.platform))
          .map(c => c.platform)
      );

      // Only clear platforms that are confirmed idle
      for (const platform of runningPlatforms) {
        const collector = statusData.find(c => c.platform === platform);
        if (collector && collector.status === 'idle' && !activePlatforms.has(platform)) {
          runningPlatforms.delete(platform);
        }
      }

      // Clear loadingSweep if all platforms are idle
      if (loadingSweep && statusData.every(c => c.status === 'idle' || c.status === 'error')) {
        loadingSweep = false;
        runningPlatforms.clear();
      }
    } catch (err) {
      const errMessage = err instanceof Error ? err.message : 'Failed to load collector data';
      // Provide more helpful error messages
      if (errMessage.includes('timeout')) {
        error = 'Request timed out. The backend may be busy processing collection. Retrying automatically...';
        // Auto-retry after 3 seconds
        setTimeout(() => {
          void loadData();
        }, 3000);
      } else {
        error = errMessage;
      }
      console.error('Collection data load error:', err);
      // Set empty arrays on error so UI doesn't stay stuck
      collectors = [];
      logs = [];
    } finally {
      loadingData = false;
    }
  };

  const triggerCollection = async (platform?: string) => {
    if (platform) {
      // Single platform - track it individually
      runningPlatforms.add(platform);
    } else {
      // Full sweep - disable the full sweep button but allow individual platforms
      loadingSweep = true;
      // Add all platforms to running set
      ['threads', 'twitter', 'reddit', 'telegram'].forEach(p => runningPlatforms.add(p));
    }

    error = null;
    try {
      const body = platform ? { platform } : {};
      const response = await fetch(`${API_BASE}/api/collection/start`, getFetchOptions({
        method: 'POST',
        body: JSON.stringify(body)
      }));
      if (!response.ok) {
        let detailMessage: string | undefined;
        try {
          const problem = await response.json();
          detailMessage = problem?.detail || problem?.message;
        } catch (parseError) {
          // ignore – response might be plain text
        }
        const statusText = detailMessage || response.statusText || 'Unknown error';
        throw new Error(`Collector responded with ${statusText} (HTTP ${response.status})`);
      }
      // Don't wait for completion - let it run in background
      // Refresh data after a short delay to show status
      setTimeout(() => {
        void loadData();
      }, 2000);
    } catch (err) {
      error = err instanceof Error ? err.message : 'Unexpected error spawning collector';
      // Remove from running set on error
      if (platform) {
        runningPlatforms.delete(platform);
      } else {
        ['threads', 'twitter', 'reddit', 'telegram'].forEach(p => runningPlatforms.delete(p));
        loadingSweep = false;
      }
    } finally {
      // Note: We don't clear runningPlatforms here because collections run in background
      // They'll be cleared when we detect completion via polling
      if (!platform) {
        // For full sweep, keep loadingSweep true until we detect completion
        // It will be cleared when loadData() shows all platforms are idle
      }
    }
  };

  const formatDate = (value?: string) => {
    if (!value) return '—';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleString(undefined, {
      hour: '2-digit',
      minute: '2-digit',
      month: 'short',
      day: 'numeric'
    });
  };

  const formatPlatform = (value: string) =>
    value
      .replace(/_/g, ' ')
      .split(' ')
      .map((part) => (part.length ? part[0].toUpperCase() + part.slice(1) : part))
      .join(' ');

  const groupPostsByPlatform = (posts: PostRecord[]): Record<string, PostRecord[]> => {
    const grouped: Record<string, PostRecord[]> = {};
    posts.forEach((post) => {
      const platform = post.platform || 'unknown';
      if (!grouped[platform]) {
        grouped[platform] = [];
      }
      grouped[platform].push(post);
    });
    return grouped;
  };

  const getContentPreview = (content: string | undefined, maxLength = 150): string => {
    if (!content) return 'No content';
    if (content.length <= maxLength) return content;
    return content.substring(0, maxLength).trim() + '...';
  };

  const handleTimeFilterChange = () => {
    void fetchLatestPosts();
  };

  const formatStatus = (message?: string, collected?: number, success = true) => {
    if (message) return message;
    if (typeof collected === 'number') {
      return success
        ? `Last sweep captured ${collected} posts`
        : `Sweep failed after collecting ${collected} posts`;
    }
    return success ? 'Ready for next sweep' : 'Collector reported an error';
  };

  onMount(() => {
    void loadData();
    void fetchLatestPosts();
    if (autoRefresh) startPolling();
  });

  onDestroy(() => {
    stopPolling();
  });

  const startPolling = () => {
    stopPolling();
    refreshTimer = setInterval(() => {
      void loadData();
      void fetchLatestPosts();
    }, refreshMs);
  };

  const stopPolling = () => {
    if (refreshTimer) {
      clearInterval(refreshTimer);
      refreshTimer = null;
    }
  };

  const toggleAutoRefresh = () => {
    autoRefresh = !autoRefresh;
    if (autoRefresh) {
      startPolling();
    } else {
      stopPolling();
    }
  };
</script>

<svelte:head>
  <title>BeyondLines · Collection Control</title>
  <meta name="description" content="Manage BeyondLines collectors" />
</svelte:head>

<div class="space-y-8">
  <section class="rounded-[32px] border border-white/10 bg-[rgba(11,20,34,0.85)] backdrop-blur-2xl px-8 py-10 shadow-[0_40px_150px_-100px_rgba(78,192,255,0.45)]">
    <div class="grid gap-8 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)] items-start">
      <div class="space-y-5">
        <p class="text-[11px] uppercase tracking-[0.45em] text-[color:var(--text-muted)]">Signal intake</p>
        <h1 class="text-[36px] md:text-[42px] font-semibold text-[color:var(--text-primary)] leading-tight">
          Coordinate BeyondLines collectors from a single command deck.
        </h1>
        <p class="text-sm md:text-base text-[color:var(--text-muted)]/85 max-w-2xl">
          Launch multi-platform sweeps, watch pipeline health, and inspect discovery logs without diving into shell scripts.
        </p>
      </div>
      <div class="rounded-3xl border border-white/10 bg-[rgba(15,29,46,0.9)] px-6 py-5 space-y-4">
        <div>
          <p class="text-[10px] uppercase tracking-[0.35em] text-[color:var(--text-muted)]">Signal cadence</p>
          <p class="text-lg font-semibold text-[color:var(--text-primary)] mt-1">Last full sweep · 21 minutes ago</p>
        </div>
        <div class="flex flex-wrap gap-3 text-sm text-[color:var(--text-muted)]">
          <span class="rounded-full border border-white/10 bg-white/8 px-3 py-1">Threads: 11 new</span>
          <span class="rounded-full border border-white/10 bg-white/8 px-3 py-1">Twitter: 7 new</span>
          <span class="rounded-full border border-white/10 bg-white/8 px-3 py-1">Reddit: 0 new</span>
        </div>
      </div>
    </div>
  </section>

  <section class="rounded-3xl border border-white/10 bg-[rgba(11,20,34,0.85)] backdrop-blur-xl p-6 space-y-5 shadow-[0_35px_120px_-80px_rgba(78,192,255,0.5)]">
    <div class="flex flex-wrap items-center justify-between gap-4">
      <div>
        <p class="text-[11px] uppercase tracking-[0.4em] text-[color:var(--text-muted)]">Controls</p>
        <h2 class="text-xl font-semibold text-[color:var(--text-primary)] mt-2">Collector automations</h2>
      </div>
      <div class="flex flex-wrap items-center gap-2">
        <button
          type="button"
          class="rounded-xl border border-[rgba(78,192,255,0.45)] bg-[linear-gradient(135deg,rgba(78,192,255,0.18),rgba(93,242,193,0.18))] px-4 py-2 text-sm font-semibold text-[color:var(--text-primary)] shadow-[0_12px_40px_-24px_rgba(78,192,255,0.6)] hover:shadow-[0_18px_60px_-24px_rgba(78,192,255,0.65)] transition-all"
          disabled={loadingSweep}
          on:click={() => triggerCollection()}
        >
          {loadingSweep ? 'Running full sweep…' : 'Run full sweep'}
        </button>
        <button
          type="button"
          class={`rounded-xl border px-4 py-2 text-xs font-semibold transition-colors ${
            autoRefresh
              ? 'border-[rgba(78,192,255,0.4)] bg-[rgba(78,192,255,0.15)] text-[rgba(78,192,255,0.9)]'
              : 'border-white/10 bg-white/5 text-[color:var(--text-muted)] hover:border-white/20'
          }`}
          aria-pressed={autoRefresh}
          on:click={toggleAutoRefresh}
        >
          {autoRefresh ? 'Auto-refresh on' : 'Auto-refresh off'}
        </button>
      </div>
    </div>

    <div class="flex flex-wrap items-center gap-6">
      <div class="flex flex-wrap items-center gap-3">
        <span class="text-xs uppercase tracking-[0.32em] text-[color:var(--text-muted)]">Status</span>
        <div class="flex flex-wrap items-center gap-2">
          <span class="text-[rgba(93,242,193,0.85)] font-semibold text-sm">Scheduler active</span>
          <span class="rounded-full border border-white/10 bg-white/10 px-3 py-1 text-[11px] text-[color:var(--text-muted)]">Next run 32m</span>
        </div>
      </div>
      <p class="text-[11px] text-[color:var(--text-muted)]/80 max-w-md">
        Executes Threads, Twitter, Reddit, and Telegram ingestion in sequence. Auto-stops when existing posts encountered.
      </p>
    </div>

    {#if error}
      <div class="rounded-2xl border border-red-400/40 bg-red-500/15 px-4 py-3 text-sm text-red-100">
        <p class="font-semibold">Error loading data</p>
        <p class="text-xs mt-1 opacity-90">{error}</p>
        <button
          type="button"
          class="mt-2 text-xs underline text-red-200 hover:text-red-100"
          on:click={() => void loadData()}
        >
          Retry
        </button>
      </div>
    {/if}
  </section>

  {#if error && !loadingData}
    <div class="rounded-3xl border border-red-400/40 bg-red-500/15 px-6 py-4 text-sm text-red-100">
      <p class="font-semibold">Unable to load collection data</p>
      <p class="text-xs mt-1 opacity-90">{error}</p>
      <button
        type="button"
        class="mt-3 rounded-xl border border-red-400/40 bg-red-500/20 px-4 py-2 text-sm hover:bg-red-500/30 transition-colors"
        on:click={() => void loadData()}
      >
        Retry loading
      </button>
    </div>
  {/if}

  <section class="space-y-6">
      <div class="grid gap-4 md:grid-cols-2">
        {#if loadingData}
          {#each Array.from({ length: 4 }) as _, index}
            <div class="animate-pulse rounded-2xl border border-white/10 bg-[rgba(15,29,46,0.85)] px-5 py-5 space-y-4" data-testid={`collector-skeleton-${index}`}>
              <div class="h-3 w-24 rounded-full bg-white/10"></div>
              <div class="h-6 w-3/4 rounded-full bg-white/10"></div>
              <div class="h-4 w-1/2 rounded-full bg-white/10"></div>
              <div class="h-9 rounded-xl bg-white/10"></div>
            </div>
          {/each}
        {:else if collectors.length === 0}
          <p class="text-sm text-[color:var(--text-muted)]/80">No collector telemetry yet. Run a sweep or wait for scheduled rotation.</p>
        {:else}
          {#each collectors as collector}
            <article class="rounded-2xl border border-white/10 bg-[rgba(15,29,46,0.9)] px-5 py-5 space-y-3 shadow-[0_20px_70px_-60px_rgba(78,192,255,0.45)]">
              <header class="flex items-center justify-between gap-3">
                <div>
                  <p class="text-[11px] uppercase tracking-[0.35em] text-[rgba(78,192,255,0.85)]">{formatPlatform(collector.platform)}</p>
                  <p class="text-sm text-[color:var(--text-muted)]">
                    {formatStatus(collector.message, collector.collected, collector.status !== 'error')}
                  </p>
                </div>
                <span class={`text-xs font-semibold uppercase tracking-[0.32em] ${collector.status === 'error' ? 'text-[rgba(245,182,120,0.9)]' : runningPlatforms.has(collector.platform) ? 'text-[rgba(78,192,255,0.9)]' : 'text-[color:var(--text-muted)]'}`}>
                  {runningPlatforms.has(collector.platform)
                    ? 'Running'
                    : collector.status === 'error'
                      ? 'Issue'
                      : 'Idle'}
                </span>
              </header>
              <div class="flex items-center gap-4 text-sm text-[color:var(--text-muted)]">
                <span>Last run · {formatDate(collector.last_run)}</span>
                <span>{collector.collected ?? 0} posts</span>
              </div>
              <button
                type="button"
                class="w-full rounded-xl border border-white/10 bg-white/10 px-4 py-2 text-sm text-[color:var(--text-primary)] hover:border-[rgba(78,192,255,0.5)] hover:text-[rgba(78,192,255,0.95)] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                disabled={runningPlatforms.has(collector.platform)}
                on:click={() => triggerCollection(collector.platform)}
              >
                {runningPlatforms.has(collector.platform) ? 'In progress…' : `Run ${collector.platform}`}
              </button>
            </article>
          {/each}
        {/if}
      </div>

      <div class="rounded-3xl border border-white/10 bg-[rgba(12,24,40,0.85)] backdrop-blur-xl p-6 space-y-4">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-[10px] uppercase tracking-[0.35em] text-[color:var(--text-muted)]">Log stream</p>
            <h3 class="text-lg font-semibold text-[color:var(--text-primary)] mt-1">Latest collector reports</h3>
          </div>
          <span class="text-[11px] font-semibold uppercase tracking-[0.32em] text-[rgba(78,192,255,0.85)]">Live</span>
        </div>
        <div class="space-y-3">
          {#if loadingData}
            {#each Array.from({ length: 4 }) as _, index}
              <div class="animate-pulse rounded-2xl border border-white/10 bg-[rgba(15,29,46,0.85)] px-4 py-3 space-y-3" data-testid={`log-skeleton-${index}`}>
                <div class="flex items-center justify-between">
                  <div class="h-3 w-20 rounded-full bg-white/10"></div>
                  <div class="h-3 w-10 rounded-full bg-white/10"></div>
                </div>
                <div class="h-4 w-3/4 rounded-full bg-white/10"></div>
                <div class="h-3 w-1/4 rounded-full bg-white/10"></div>
              </div>
            {/each}
          {:else if logs.length === 0}
            <p class="text-sm text-[color:var(--text-muted)]/80">No collector activity recorded yet.</p>
          {:else}
            {#each logs as log}
              <div class="rounded-2xl border border-white/10 bg-[rgba(15,29,46,0.9)] px-4 py-3 text-sm text-[color:var(--text-primary)]">
                <div class="flex items-center justify-between text-[11px] text-[color:var(--text-muted)]">
                  <span>{formatDate(log.timestamp)}</span>
                  <span class={`uppercase tracking-[0.3em] ${log.status === 'warning' ? 'text-[rgba(245,182,120,0.85)]' : log.status === 'error' ? 'text-[rgba(245,114,120,0.85)]' : 'text-[rgba(93,242,193,0.85)]'}`}>{log.status}</span>
                </div>
                <p class="mt-1 text-sm">{log.platform ? `${formatPlatform(log.platform)} · ${log.message}` : log.message}</p>
                {#if log.posts}
                  <p class="text-xs text-[color:var(--text-muted)] mt-1">Posts collected · {log.posts}</p>
                {/if}
              </div>
            {/each}
          {/if}
        </div>
      </div>
    </section>

  <!-- Latest Collections Section -->
  <section class="rounded-3xl border border-white/10 bg-[rgba(11,20,34,0.85)] backdrop-blur-xl p-6 space-y-5 shadow-[0_35px_120px_-80px_rgba(78,192,255,0.5)]">
    <div class="flex flex-wrap items-center justify-between gap-4">
      <div>
        <p class="text-[11px] uppercase tracking-[0.4em] text-[color:var(--text-muted)]">Recent Activity</p>
        <h2 class="text-xl font-semibold text-[color:var(--text-primary)] mt-2">Latest Collections</h2>
      </div>
      <div class="flex flex-wrap items-center gap-2">
        <select
          bind:value={timeFilter}
          on:change={handleTimeFilterChange}
          class="rounded-xl border border-white/10 bg-[rgba(15,29,46,0.9)] px-4 py-2 text-sm font-semibold text-[color:var(--text-primary)] hover:border-[rgba(78,192,255,0.5)] transition-colors focus:outline-none focus:ring-2 focus:ring-[rgba(78,192,255,0.5)]"
        >
          <option value="1h">Last Hour</option>
          <option value="6h">Last 6 Hours</option>
          <option value="24h">Last 24 Hours</option>
          <option value="7d">Last 7 Days</option>
          <option value="all">All Time</option>
        </select>
        <button
          type="button"
          class="rounded-xl border border-[rgba(78,192,255,0.45)] bg-[linear-gradient(135deg,rgba(78,192,255,0.18),rgba(93,242,193,0.18))] px-4 py-2 text-sm font-semibold text-[color:var(--text-primary)] shadow-[0_12px_40px_-24px_rgba(78,192,255,0.6)] hover:shadow-[0_18px_60px_-24px_rgba(78,192,255,0.65)] transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          disabled={loadingLatestPosts}
          on:click={() => fetchLatestPosts()}
        >
          {loadingLatestPosts ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>
    </div>

    {#if latestPostsError}
      <div class="rounded-2xl border border-red-400/40 bg-red-500/15 px-4 py-3 text-sm text-red-100">
        <p class="font-semibold">Error loading latest posts</p>
        <p class="text-xs mt-1 opacity-90">{latestPostsError}</p>
        <button
          type="button"
          class="mt-2 text-xs underline text-red-200 hover:text-red-100"
          on:click={() => fetchLatestPosts()}
        >
          Retry
        </button>
      </div>
    {/if}

    {#if loadingLatestPosts && latestPosts.length === 0}
      <div class="space-y-4">
        {#each Array.from({ length: 3 }) as _, index}
          <div class="animate-pulse rounded-2xl border border-white/10 bg-[rgba(15,29,46,0.85)] px-5 py-4 space-y-3">
            <div class="flex items-center justify-between">
              <div class="h-4 w-24 rounded-full bg-white/10"></div>
              <div class="h-3 w-16 rounded-full bg-white/10"></div>
            </div>
            <div class="h-5 w-3/4 rounded-full bg-white/10"></div>
            <div class="h-4 w-full rounded-full bg-white/10"></div>
            <div class="h-4 w-2/3 rounded-full bg-white/10"></div>
            <div class="h-9 w-24 rounded-xl bg-white/10"></div>
          </div>
        {/each}
      </div>
    {:else if latestPosts.length === 0}
      <div class="rounded-2xl border border-white/10 bg-[rgba(15,29,46,0.85)] px-6 py-8 text-center">
        <p class="text-sm text-[color:var(--text-muted)]/80">No posts collected in the selected time period.</p>
        <p class="text-xs text-[color:var(--text-muted)]/60 mt-2">Run a collection sweep to gather new content.</p>
      </div>
    {:else}
      {#each Object.entries(groupPostsByPlatform(latestPosts)) as [platform, posts]}
        <div class="space-y-3">
          <div class="flex items-center gap-2">
            <p class="text-[11px] uppercase tracking-[0.35em] text-[rgba(78,192,255,0.85)]">{formatPlatform(platform)}</p>
            <span class="text-xs text-[color:var(--text-muted)]">({posts.length} {posts.length === 1 ? 'post' : 'posts'})</span>
          </div>
          <div class="space-y-3">
            {#each posts as post}
              <article class="rounded-2xl border border-white/10 bg-[rgba(15,29,46,0.9)] px-5 py-4 space-y-3 shadow-[0_20px_70px_-60px_rgba(78,192,255,0.45)]">
                <div class="flex items-start justify-between gap-3">
                  <div class="flex-1 min-w-0">
                    {#if post.title}
                      <h3 class="text-sm font-semibold text-[color:var(--text-primary)] mb-1 line-clamp-2">
                        {post.title}
                      </h3>
                    {/if}
                    <p class="text-sm text-[color:var(--text-muted)] line-clamp-3">
                      {getContentPreview(post.content)}
                    </p>
                  </div>
                </div>
                <div class="flex items-center justify-between gap-4 text-xs text-[color:var(--text-muted)]">
                  <div class="flex items-center gap-3 flex-wrap">
                    {#if post.author}
                      <span class="flex items-center gap-1">
                        <span class="text-[10px] uppercase tracking-[0.3em]">By</span>
                        <span class="font-medium">{post.author}</span>
                      </span>
                    {/if}
                    {#if post.created_at}
                      <span>·</span>
                      <span>{formatDate(post.created_at)}</span>
                    {/if}
                  </div>
                  {#if post.url}
                    <a
                      href={post.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      class="rounded-xl border border-[rgba(78,192,255,0.45)] bg-[rgba(78,192,255,0.1)] px-3 py-1.5 text-xs font-semibold text-[rgba(78,192,255,0.9)] hover:bg-[rgba(78,192,255,0.2)] transition-colors"
                    >
                      View
                    </a>
                  {/if}
                </div>
              </article>
            {/each}
          </div>
        </div>
      {/each}
    {/if}
  </section>
</div>

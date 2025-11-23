<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { API_BASE } from '$lib/config';
  import type { PostRecord } from '$lib/types';

  const PLATFORMS = ['threads', 'twitter', 'reddit', 'telegram', 'rss'];

  let posts: PostRecord[] = [];
  let total = 0;
  let loading = true;
  let error: string | null = null;

  let platformFilter: 'all' | typeof PLATFORMS[number] = 'all';
  let analyzedFilter: 'all' | 'analyzed' | 'unanalyzed' = 'all';
  let searchTerm = '';

  const fetchPosts = async () => {
    loading = true;
    error = null;

    try {
      const params = new URLSearchParams({ limit: '100', offset: '0' });
      if (platformFilter !== 'all') params.set('platform', platformFilter);
      if (analyzedFilter !== 'all') params.set('analyzed', analyzedFilter === 'analyzed' ? 'true' : 'false');

      const res = await fetch(`${API_BASE}/api/posts?${params.toString()}`);
      if (!res.ok) throw new Error(`API error ${res.status}`);

      const data = await res.json();
      posts = data.posts ?? [];
      total = data.total ?? posts.length ?? 0;
    } catch (err) {
      error = err instanceof Error ? err.message : 'Unknown error fetching posts';
      posts = [];
      total = 0;
    } finally {
      loading = false;
    }
  };

  const formatDate = (value?: string) => {
    if (!value) return '—';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const filteredPosts = () => {
    const term = searchTerm.trim().toLowerCase();
    if (!term) return posts;
    return posts.filter((post) => {
      const haystacks = [post.title, post.content, post.author, post.ai_summary, post.url]
        .filter(Boolean)
        .map((item) => String(item).toLowerCase());
      return haystacks.some((value) => value.includes(term));
    });
  };

  const analyzedCounts = () => {
    const list = filteredPosts();
    const analyzed = list.filter((post) => !!(post.ai_summary ?? post.value_score)).length;
    return {
      analyzed,
      unanalyzed: list.length - analyzed
    };
  };

  let autoRefresh = true;
  let refreshTimer: ReturnType<typeof setInterval> | null = null;
  const refreshMs = 60_000;

  onMount(() => {
    void fetchPosts();
    if (autoRefresh) startPolling();
  });

  onDestroy(() => {
    stopPolling();
  });

  const startPolling = () => {
    stopPolling();
    refreshTimer = setInterval(() => {
      void fetchPosts();
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

  const setPlatform = (value: typeof platformFilter) => {
    if (platformFilter === value) return;
    platformFilter = value;
    void fetchPosts();
  };

  const setAnalyzed = (value: typeof analyzedFilter) => {
    if (analyzedFilter === value) return;
    analyzedFilter = value;
    void fetchPosts();
  };
</script>

<svelte:head>
  <title>BeyondLines · Signal Feed</title>
  <meta name="description" content="BeyondLines unified feed" />
</svelte:head>

<div class="space-y-6">
  <section class="rounded-3xl border border-white/10 bg-[rgba(11,20,34,0.85)] backdrop-blur-xl p-6 space-y-5 shadow-[0_35px_120px_-80px_rgba(78,192,255,0.5)]">
    <div class="flex flex-wrap items-center justify-between gap-4">
      <div>
        <p class="text-[11px] uppercase tracking-[0.4em] text-[color:var(--text-muted)]">Filters</p>
        <h2 class="text-xl font-semibold text-[color:var(--text-primary)] mt-2">Signal scope</h2>
      </div>
      <div class="flex flex-wrap items-center gap-2">
        <button
          type="button"
          class="rounded-xl border border-[rgba(78,192,255,0.4)] bg-[linear-gradient(135deg,rgba(78,192,255,0.2),rgba(93,242,193,0.18))] px-4 py-2 text-sm font-semibold text-[color:var(--text-primary)] shadow-[0_12px_40px_-24px_rgba(78,192,255,0.6)] hover:shadow-[0_18px_60px_-24px_rgba(78,192,255,0.65)] transition-all"
          on:click={fetchPosts}
        >
          Refresh feed
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

    <div class="flex flex-wrap gap-6">
      <div class="flex flex-wrap items-center gap-3">
        <span class="text-xs uppercase tracking-[0.32em] text-[color:var(--text-muted)]">Platform</span>
        <div class="flex flex-wrap gap-2">
          <button
            type="button"
            class={`px-3 py-1.5 rounded-full border transition-colors text-sm ${
              platformFilter === 'all'
                ? 'border-white/20 bg-white/10 text-[color:var(--text-primary)]'
                : 'border-white/8 bg-white/5 text-[color:var(--text-muted)] hover:border-white/20'
            }`}
            aria-pressed={platformFilter === 'all'}
            on:click={() => setPlatform('all')}
          >
            All
          </button>
          {#each PLATFORMS as platform}
            <button
              type="button"
              class={`px-3 py-1.5 rounded-full border transition-colors text-sm capitalize ${
                platformFilter === platform
                  ? 'border-white/20 bg-white/10 text-[color:var(--text-primary)]'
                  : 'border-white/8 bg-white/5 text-[color:var(--text-muted)] hover:border-white/20'
              }`}
              aria-pressed={platformFilter === platform}
              on:click={() => setPlatform(platform)}
            >
              {platform}
            </button>
          {/each}
        </div>
      </div>

      <div class="flex flex-wrap items-center gap-3">
        <span class="text-xs uppercase tracking-[0.32em] text-[color:var(--text-muted)]">Status</span>
        <div class="flex flex-wrap gap-2">
          {#each [
            { label: 'All', value: 'all' },
            { label: 'Analyzed', value: 'analyzed' },
            { label: 'Awaiting AI', value: 'unanalyzed' }
          ] as option}
            <button
              type="button"
              class={`px-3 py-1.5 rounded-full border text-sm transition-colors ${
                analyzedFilter === option.value
                  ? 'border-[rgba(93,242,193,0.4)] bg-[rgba(93,242,193,0.12)] text-[color:var(--text-primary)]'
                  : 'border-white/8 bg-white/5 text-[color:var(--text-muted)] hover:border-white/20'
              }`}
              aria-pressed={analyzedFilter === option.value}
              on:click={() => setAnalyzed(option.value as typeof analyzedFilter)}
            >
              {option.label}
            </button>
          {/each}
        </div>
      </div>
    </div>

    <div class="w-full sm:max-w-sm space-y-2">
      <label for="signal-search" class="text-xs uppercase tracking-[0.32em] text-[color:var(--text-muted)]">Search</label>
      <input
        id="signal-search"
        type="search"
        placeholder="Filter by title, content, author…"
        class="w-full rounded-xl border border-white/10 bg-[rgba(14,26,43,0.9)] px-4 py-2.5 text-sm text-[color:var(--text-primary)] placeholder:text-[color:var(--text-muted)]/70 focus:outline-none focus:border-[rgba(78,192,255,0.5)] focus:ring-2 focus:ring-[rgba(78,192,255,0.25)]"
        bind:value={searchTerm}
      />
      <p class="text-[11px] text-[color:var(--text-muted)]">Use keywords to surface precise signals.</p>
    </div>
  </section>

  <section class="rounded-3xl border border-white/10 bg-[rgba(12,24,40,0.85)] backdrop-blur-xl px-6 py-5 flex flex-wrap items-center justify-between gap-4">
    <div>
      <p class="text-[11px] uppercase tracking-[0.35em] text-[color:var(--text-muted)]">Unified feed</p>
      <h2 class="text-lg font-semibold text-[color:var(--text-primary)] mt-1">
        {platformFilter === 'all' ? 'All platforms' : platformFilter.toUpperCase()} · {filteredPosts().length} shown
      </h2>
    </div>
    <div class="flex flex-wrap items-center gap-3 text-sm text-[color:var(--text-muted)]">
      <span class="rounded-full border border-white/10 bg-white/5 px-3 py-1">Analyzed {analyzedCounts().analyzed}</span>
      <span class="rounded-full border border-white/10 bg-white/5 px-3 py-1">Awaiting AI {analyzedCounts().unanalyzed}</span>
      <span class="rounded-full border border-white/10 bg-white/5 px-3 py-1">Fetched {total}</span>
    </div>
  </section>

  {#if loading}
    <div class="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      {#each Array.from({ length: 6 }) as _, index}
        <div class="animate-pulse rounded-2xl border border-white/10 bg-[rgba(14,26,43,0.9)] px-5 py-4 space-y-4" data-testid={`skeleton-${index}`}>
          <div class="h-3 w-20 rounded-full bg-white/10"></div>
          <div class="h-5 w-3/4 rounded-full bg-white/10"></div>
          <div class="h-12 rounded-xl bg-white/10"></div>
          <div class="flex gap-2">
            <div class="h-4 w-16 rounded-full bg-white/10"></div>
            <div class="h-4 w-10 rounded-full bg-white/10"></div>
          </div>
        </div>
      {/each}
    </div>
  {:else if error}
    <div class="rounded-3xl border border-red-400/40 bg-red-500/15 px-6 py-5 space-y-3">
      <div class="flex items-start gap-3">
        <span class="text-lg">❌</span>
        <div class="flex-1">
          <p class="text-sm font-semibold text-red-100 mb-1">Failed to load posts</p>
          <p class="text-sm text-red-200/80">{error}</p>
        </div>
      </div>
      <button
        type="button"
        on:click={() => fetchPosts()}
        class="rounded-xl border border-red-400/40 bg-red-500/20 px-4 py-2 text-sm font-semibold text-red-100 hover:bg-red-500/30 transition-colors"
      >
        Retry
      </button>
    </div>
  {:else if filteredPosts().length === 0}
    <div class="rounded-3xl border border-white/10 bg-[rgba(12,24,40,0.8)] px-6 py-12 text-center text-sm text-[color:var(--text-muted)]">
      No matching signals. Adjust filters or refresh the feed.
    </div>
  {:else}
    <div class="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      {#each filteredPosts() as post}
        <article class="rounded-2xl border border-white/10 bg-[rgba(14,26,43,0.9)] px-5 py-4 space-y-3 shadow-[0_22px_70px_-60px_rgba(78,192,255,0.45)]">
          <div class="flex items-center justify-between gap-3">
            <span class="text-xs uppercase tracking-[0.3em] text-[rgba(78,192,255,0.9)]">{post.platform}</span>
            <span class="text-[11px] text-[color:var(--text-muted)]">{formatDate(post.created_at)}</span>
          </div>
          <h3 class="text-base font-semibold text-[color:var(--text-primary)]">
            {#if post.title && post.title.trim()}
              {post.title}
            {:else if post.content && post.content.trim()}
              {post.content.slice(0, 90)}{post.content.length > 90 ? '…' : ''}
            {:else}
              <span class="text-[color:var(--text-muted)] italic">Untitled post</span>
            {/if}
          </h3>
          <p class="text-sm text-[color:var(--text-muted)]/85 max-h-28 overflow-hidden line-clamp-4">
            {#if post.ai_summary && post.ai_summary.trim()}
              {post.ai_summary}
            {:else if post.content && post.content.trim()}
              {@const cleanContent = (() => {
                let text = post.content || '';
                // Remove JSON code blocks
                text = text.replace(/```json\s*\{[\s\S]*?\}\s*```/gi, '');
                text = text.replace(/```\s*\{[\s\S]*?\}\s*```/g, '');
                // Remove JSON objects with analysis metadata
                text = text.replace(/\{[\s\S]*?"(?:ai_summary|tags|key_concepts|fit_categories|value_score|quality_score)"[\s\S]*?\}/g, '');
                // Remove comment markers
                text = text.replace(/===.*?TOP.*?COMMENTS.*?===.*$/gi, '');
                // Clean up whitespace
                text = text.replace(/\n{3,}/g, '\n\n').trim();
                return text;
              })()}
              {#if cleanContent}
                {cleanContent.slice(0, 200)}{cleanContent.length > 200 ? '…' : ''}
              {:else}
                <span class="italic text-[color:var(--text-muted)]/60">Content not available</span>
              {/if}
            {:else}
              <span class="italic text-[color:var(--text-muted)]/60">No content available. This post may not have been fully loaded.</span>
            {/if}
          </p>
          <div class="flex flex-wrap items-center gap-3 pt-2 border-t border-white/5">
            {#if post.author}
              <span class="text-xs text-[color:var(--text-muted)]">By {post.author}</span>
            {/if}
            {#if post.url}
              <a href={post.url} target="_blank" rel="noopener" class="text-xs font-semibold text-[rgba(78,192,255,0.9)] hover:text-[rgba(78,192,255,1)]">
                View original →
              </a>
            {/if}
          </div>
        </article>
      {/each}
    </div>
  {/if}
</div>

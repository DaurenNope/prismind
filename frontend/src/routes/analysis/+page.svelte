<script lang="ts">
  import { onMount } from 'svelte';
  import Toast from '$lib/components/Toast.svelte';
  import { fetchAnalysisStats, fetchRecentAnalysis, triggerAnalysisRun } from '$lib/services/analysis';
  import type { AnalysisStats, AnalyzedPost } from '$lib/types';

  let stats: AnalysisStats | null = null;
  let recent: AnalyzedPost[] = [];
  let loading = true;
  let refreshing = false;
  let runLimit = 25;
  let forceRun = false;
  let running = false;

  let toastMessage = '';
  let toastTone: 'success' | 'error' | 'info' = 'info';
  let toastVisible = false;
  let toastTimer: ReturnType<typeof setTimeout> | null = null;

  const showToast = (message: string, tone: 'success' | 'error' | 'info' = 'info') => {
    toastMessage = message;
    toastTone = tone;
    toastVisible = true;
    if (toastTimer) clearTimeout(toastTimer);
    toastTimer = setTimeout(() => {
      toastVisible = false;
    }, 3200);
  };

  const loadData = async () => {
    try {
      if (!stats) {
        loading = true;
      } else {
        refreshing = true;
      }
      const [statsResponse, recentResponse] = await Promise.all([
        fetchAnalysisStats(),
        fetchRecentAnalysis()
      ]);
      stats = statsResponse;
      recent = recentResponse;
      showToast('Analysis data refreshed', 'success');
    } catch (error) {
      console.error('Failed to load analysis data', error);
      showToast('Failed to load analysis data', 'error');
    } finally {
      loading = false;
      refreshing = false;
    }
  };

  const runAnalysis = async () => {
    if (running) return;
    running = true;
    try {
      const response = await triggerAnalysisRun(runLimit, forceRun);
      const analyzed = response.analyzed ?? 0;
      const message = response.message || `Analyzed ${analyzed} posts`;

      if (analyzed === 0) {
        showToast(message || 'No posts were analyzed. Check if there are unanalyzed posts available.', forceRun ? 'info' : 'info');
      } else {
        showToast(`✅ ${message}`, 'success');
      }

      console.log('Analysis response:', response);
      await loadData();
    } catch (error) {
      console.error('Failed to trigger analysis', error);
      const errorMsg = error instanceof Error ? error.message : 'Analysis run failed';
      showToast(`❌ ${errorMsg}`, 'error');
    } finally {
      running = false;
    }
  };

  const formatTimestamp = (value?: string | null) => {
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

  onMount(() => {
    void loadData();
  });
</script>

<svelte:head>
  <title>BeyondLines · Analysis</title>
  <meta name="description" content="Run AI analysis, review summaries, and monitor queue health." />
</svelte:head>

<div class="space-y-8">
  <section class="rounded-[32px] border border-white/10 bg-[rgba(11,20,34,0.85)] backdrop-blur-2xl px-8 py-10 shadow-[0_40px_150px_-100px_rgba(78,192,255,0.45)]">
    <div class="grid gap-6 lg:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]">
      <div class="space-y-4">
        <p class="text-[11px] uppercase tracking-[0.45em] text-[color:var(--text-muted)]">AI Workbench</p>
        <h1 class="text-[36px] md:text-[42px] font-semibold text-[color:var(--text-primary)] leading-tight">
          Inspect queued content, run AI analysis, and surface insights.
        </h1>
        <p class="text-sm md:text-base text-[color:var(--text-muted)]/85 max-w-2xl">
          Keep the BeyondLines intelligence engine sharp—monitor unanalyzed content, trigger batch runs,
          and review the freshest summaries with quality and sentiment context.
        </p>
      </div>
      <div class="rounded-3xl border border-white/10 bg-[rgba(15,29,46,0.9)] px-6 py-5 space-y-4">
        <div class="flex items-center justify-between">
          <span class="text-[10px] uppercase tracking-[0.35em] text-[color:var(--text-muted)]">Queue status</span>
          <span class="rounded-full border border-[rgba(93,242,193,0.35)] bg-[rgba(93,242,193,0.14)] px-3 py-1 text-[11px] uppercase tracking-[0.32em] text-[rgba(93,242,193,0.85)]">
            {refreshing ? 'Refreshing…' : 'Live'}
          </span>
        </div>
        <div class="grid grid-cols-2 gap-3 text-sm text-[color:var(--text-muted)]">
          <div class="rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
            <p class="text-[11px] uppercase tracking-[0.32em] text-[color:var(--text-muted)]/70">Unanalyzed</p>
            <p class="text-2xl font-semibold text-[color:var(--text-primary)]">
              {stats?.summary.unanalyzed_posts ?? '—'}
            </p>
          </div>
          <div class="rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
            <p class="text-[11px] uppercase tracking-[0.32em] text-[color:var(--text-muted)]/70">Last run</p>
            <p class="text-base font-medium text-[color:var(--text-primary)]">
              {stats ? formatTimestamp(stats.last_analysis_at) : '—'}
            </p>
          </div>
          <div class="rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
            <p class="text-[11px] uppercase tracking-[0.32em] text-[color:var(--text-muted)]/70">Avg quality</p>
            <p class="text-2xl font-semibold text-[rgba(93,242,193,0.9)]">
              {stats?.average_quality ?? '—'}
            </p>
          </div>
          <div class="rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
            <p class="text-[11px] uppercase tracking-[0.32em] text-[color:var(--text-muted)]/70">Analyzed total</p>
            <p class="text-2xl font-semibold text-[color:var(--text-primary)]">
              {stats?.summary.analyzed_posts ?? '—'}
            </p>
          </div>
        </div>
      </div>
    </div>
  </section>

  <section class="rounded-3xl border border-white/10 bg-[rgba(12,24,40,0.85)] backdrop-blur-xl p-6">
    <div class="flex flex-wrap items-center gap-4 mb-6">
      <div class="flex items-center gap-3 flex-1 min-w-[200px]">
        <label for="batch-size" class="text-xs uppercase tracking-[0.32em] text-[color:var(--text-muted)] whitespace-nowrap">Batch size</label>
        <input
          id="batch-size"
          type="range"
          min="5"
          max="100"
          step="5"
          bind:value={runLimit}
          class="flex-1 accent-[rgba(78,192,255,0.85)]"
        />
        <span class="text-sm text-[color:var(--text-primary)] min-w-[60px]">{runLimit} posts</span>
      </div>

      <div class="flex items-center gap-3">
        <label for="force-run" class="text-xs uppercase tracking-[0.32em] text-[color:var(--text-muted)]">Force re-analyze</label>
        <input
          id="force-run"
          type="checkbox"
          bind:checked={forceRun}
          class="h-4 w-4 rounded border-white/10 bg-white/5 text-[rgba(93,242,193,0.85)] focus:ring-[rgba(93,242,193,0.45)]"
        />
      </div>

      <button
        type="button"
        class="rounded-xl border border-[rgba(78,192,255,0.45)] bg-[linear-gradient(135deg,rgba(78,192,255,0.18),rgba(93,242,193,0.18))] px-4 py-2 text-sm font-semibold text-[color:var(--text-primary)] shadow-[0_18px_60px_-40px_rgba(78,192,255,0.6)] hover:shadow-[0_18px_60px_-30px_rgba(78,192,255,0.7)] transition-all disabled:cursor-not-allowed disabled:opacity-60"
        on:click={runAnalysis}
        disabled={running}
      >
        {running ? 'Running…' : 'Run AI analysis'}
      </button>

      <button
        type="button"
        class="rounded-xl border border-white/10 bg-white/5 px-4 py-2 text-sm text-[color:var(--text-primary)] hover:border-[rgba(78,192,255,0.45)]"
        on:click={() => void loadData()}
      >Refresh</button>
    </div>

    <div class="rounded-2xl border border-white/10 bg-[rgba(15,29,46,0.85)] px-4 py-3 text-xs text-[color:var(--text-muted)]/85">
      <p class="uppercase tracking-[0.32em] text-[color:var(--text-muted)]/70 mb-2">Queue snapshot</p>
      {#if stats?.queue_preview?.length}
        <div class="grid gap-2 md:grid-cols-2 lg:grid-cols-3">
          {#each stats.queue_preview as item}
            <div class="rounded-xl border border-white/10 bg-white/5 px-3 py-2">
              <p class="text-[10px] uppercase tracking-[0.3em] text-[rgba(78,192,255,0.85)]">{item.platform}</p>
              <p class="text-[color:var(--text-primary)] text-sm line-clamp-2">{item.content_preview}</p>
              <p class="text-[10px] uppercase tracking-[0.28em] text-[color:var(--text-muted)]/70 mt-1">{formatTimestamp(item.created_at)}</p>
            </div>
          {/each}
        </div>
      {:else}
        <p>All clear—no queue preview available.</p>
      {/if}
    </div>
  </section>

  <section class="space-y-8">
      <div class="rounded-3xl border border-white/10 bg-[rgba(12,24,40,0.85)] backdrop-blur-xl p-6 space-y-5">
        <div class="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p class="text-[10px] uppercase tracking-[0.35em] text-[color:var(--text-muted)]">Platform queue</p>
            <h2 class="text-lg font-semibold text-[color:var(--text-primary)] mt-1">Unanalyzed by source</h2>
          </div>
        </div>

        {#if loading}
          <div class="grid gap-3 md:grid-cols-2">
            {#each Array.from({ length: 4 }) as _, index}
              <div class="animate-pulse rounded-2xl border border-white/10 bg-[rgba(15,29,46,0.9)] px-4 py-4 space-y-3" data-testid={`analysis-skeleton-${index}`}>
                <div class="h-3 w-24 rounded-full bg-white/10"></div>
                <div class="h-4 w-12 rounded-full bg-white/10"></div>
              </div>
            {/each}
          </div>
        {:else if stats && Object.keys(stats.platform_queue).length === 0}
          <p class="text-sm text-[color:var(--text-muted)]/80">No unanalyzed content in queue—great job.</p>
        {:else if stats}
          <div class="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {#each Object.entries(stats.platform_queue) as [platform, count]}
              <div class="rounded-2xl border border-white/10 bg-[rgba(15,29,46,0.9)] px-5 py-4 space-y-2">
                <p class="text-[10px] uppercase tracking-[0.32em] text-[rgba(78,192,255,0.85)]">{platform}</p>
                <p class="text-3xl font-semibold text-[color:var(--text-primary)]">{count}</p>
                <p class="text-xs text-[color:var(--text-muted)]/70">Unanalyzed posts</p>
              </div>
            {/each}
          </div>
        {/if}
      </div>

      <div class="rounded-3xl border border-white/10 bg-[rgba(12,24,40,0.85)] backdrop-blur-xl p-6 space-y-5">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-[10px] uppercase tracking-[0.35em] text-[color:var(--text-muted)]">Recent analysis</p>
            <h3 class="text-lg font-semibold text-[color:var(--text-primary)] mt-1">Latest AI summaries</h3>
          </div>
          <button
            type="button"
            class="rounded-xl border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-[color:var(--text-primary)] hover:border-[rgba(78,192,255,0.45)]"
            on:click={() => void loadData()}
          >Reload</button>
        </div>

        {#if loading}
          <div class="space-y-3">
            {#each Array.from({ length: 3 }) as _, index}
              <div class="animate-pulse rounded-2xl border border-white/10 bg-[rgba(15,29,46,0.9)] px-4 py-4 space-y-3" data-testid={`analysis-recent-skeleton-${index}`}>
                <div class="h-3 w-24 rounded-full bg-white/10"></div>
                <div class="h-3 w-32 rounded-full bg-white/10"></div>
                <div class="h-20 rounded-xl bg-white/10"></div>
              </div>
            {/each}
          </div>
        {:else if recent.length === 0}
          <p class="text-sm text-[color:var(--text-muted)]/80">No analyzed posts yet. Run a batch to populate this list.</p>
        {:else}
          <div class="space-y-4">
            {#each recent as post}
              <article class="rounded-2xl border border-white/10 bg-[rgba(15,29,46,0.9)] px-5 py-5 space-y-3 shadow-[0_20px_70px_-60px_rgba(78,192,255,0.45)]">
                <header class="flex flex-wrap items-center justify-between gap-3">
                  <div class="space-y-1">
                    <p class="text-[11px] uppercase tracking-[0.28em] text-[color:var(--text-muted)] flex items-center gap-2">
                      <span class="rounded-full border border-white/10 bg-white/10 px-2 py-0.5 text-[10px] uppercase text-[rgba(93,242,193,0.85)]">{post.platform}</span>
                      <span class="text-[color:var(--text-primary)] text-xs font-semibold">{post.author ?? 'Unknown author'}</span>
                    </p>
                    <p class="text-xs text-[color:var(--text-muted)]/80">Analyzed {formatTimestamp(post.analysis_timestamp)}</p>
                  </div>
                  <div class="flex gap-3 text-xs">
                    <span class="rounded-full border border-[rgba(93,242,193,0.35)] bg-[rgba(93,242,193,0.15)] px-3 py-1 text-[rgba(93,242,193,0.9)]">Quality {post.quality_score ?? '—'}</span>
                    <span class="rounded-full border border-white/10 bg-white/10 px-3 py-1 text-[color:var(--text-muted)]">Sentiment {post.sentiment ?? '—'}</span>
                  </div>
                </header>
                <div class="space-y-3">
                  {#if post.ai_summary}
                    <div>
                      <p class="text-[10px] uppercase tracking-[0.28em] text-[color:var(--text-muted)]/70">Summary</p>
                      <p class="text-sm text-[color:var(--text-primary)]/90 whitespace-pre-line">{post.ai_summary}</p>
                    </div>
                  {/if}
                  <div>
                    <p class="text-[10px] uppercase tracking-[0.28em] text-[color:var(--text-muted)]/70">Original</p>
                    <p class="text-sm text-[color:var(--text-muted)]/85 whitespace-pre-line max-h-32 overflow-y-auto">{post.content}</p>
                  </div>
                  {#if post.key_concepts && post.key_concepts.length > 0}
                    <div class="flex flex-wrap gap-2 text-[10px] uppercase tracking-[0.3em] text-[rgba(78,192,255,0.85)]">
                      {#each post.key_concepts as tag}
                        <span class="rounded-full border border-white/10 bg-white/5 px-3 py-1">{tag}</span>
                      {/each}
                    </div>
                  {/if}
                </div>
              </article>
            {/each}
          </div>
        {/if}
      </div>
  </section>
</div>

{#if toastVisible}
  <Toast message={toastMessage} tone={toastTone} />
{/if}

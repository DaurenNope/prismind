<script lang="ts">
  import { onMount } from 'svelte';

  interface DashboardStats {
    total_posts: number;
    platforms: Record<string, number>;
    unanalyzed: number;
    analyzed: number;
  }

  interface ActivityLog {
    label: string;
    detail: string;
    timestamp: string;
    tone: 'positive' | 'alert' | 'informational';
  }

  const API_BASE = 'http://127.0.0.1:8000';

  let stats: DashboardStats | null = null;
  let loading = true;
  let error: string | null = null;

  const timeline: ActivityLog[] = [
    {
      label: 'Rewrites deployed',
      detail: 'Persona Qronoya shipped 3 posts to Threads + Telegram.',
      timestamp: '8 minutes ago',
      tone: 'positive'
    },
    {
      label: 'Collection cycle',
      detail: 'Threads saved feed sweep finished · 11 items ingested.',
      timestamp: '23 minutes ago',
      tone: 'informational'
    },
    {
      label: 'Twitter auth refresh',
      detail: 'Cookie rotation needed before next sweep.',
      timestamp: '1 hour ago',
      tone: 'alert'
    },
    {
      label: 'Telegram digest',
      detail: 'Founder brief delivered to BeyondLines HQ inbox.',
      timestamp: '2 hours ago',
      tone: 'positive'
    }
  ];

  onMount(async () => {
    try {
      const response = await fetch(`${API_BASE}/api/dashboard/stats`);
      if (!response.ok) throw new Error('Failed to fetch stats');
      stats = await response.json();
    } catch (e) {
      error = e instanceof Error ? e.message : 'Unknown error';
    } finally {
      loading = false;
    }
  });

  const formatNumber = (value: number | undefined) =>
    value === undefined ? '—' : value.toLocaleString();
</script>

<svelte:head>
  <title>BeyondLines · Dashboard</title>
</svelte:head>

<div class="space-y-8">
  <section class="grid gap-6 xl:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)]">
    <div class="rounded-4xl border border-white/12 bg-white/8 backdrop-blur-3xl shadow-[0_50px_180px_-80px_rgba(118,151,255,0.75)] p-8">
      <div class="flex flex-col gap-8">
        <div class="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,13rem)]">
          <div>
            <p class="text-[11px] uppercase tracking-[0.48em] text-slate-300">Mission status</p>
            <h1 class="text-3xl md:text-4xl font-semibold text-white leading-tight mt-2">
              BeyondLines intelligence center
            </h1>
            <p class="text-sm md:text-base text-slate-300/80 mt-4 max-w-2xl">
              Monitor signal intake, AI processing velocity, and persona readiness across the entire pipeline.
            </p>
          </div>
          <div class="rounded-3xl border border-white/12 bg-white/[0.08] px-5 py-4 h-fit">
            <p class="text-[10px] uppercase tracking-[0.42em] text-slate-300">Observer feed</p>
            <p class="text-sm font-semibold text-white mt-2">Next deep analysis window</p>
            <p class="text-xs text-blue-200 mt-1">Scheduled in 47 minutes</p>
          </div>
        </div>

        {#if loading}
          <div class="flex items-center gap-3 text-sm text-slate-300">
            <span class="inline-flex h-6 w-6 animate-spin rounded-full border-[3px] border-blue-300/70 border-t-transparent"></span>
            Syncing live metrics…
          </div>
        {:else if error}
          <div class="rounded-3xl border border-red-400/40 bg-red-500/20 px-5 py-4 text-sm text-red-100">
            {error}
          </div>
        {:else if stats}
          <div class="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <div class="rounded-3xl border border-white/12 bg-gradient-to-br from-indigo-500/20 via-blue-500/10 to-transparent px-6 py-6 shadow-[0_30px_70px_-60px_rgba(96,165,250,0.8)]">
              <p class="text-[10px] uppercase tracking-[0.42em] text-slate-300">Total corpus</p>
              <p class="text-4xl font-semibold text-white mt-3">{formatNumber(stats.total_posts)}</p>
              <p class="text-xs text-slate-300/80 mt-2">Combined multi-source intelligence</p>
            </div>
            <div class="rounded-3xl border border-white/12 bg-gradient-to-br from-emerald-500/25 via-emerald-500/10 to-transparent px-6 py-6 shadow-[0_30px_80px_-70px_rgba(74,222,128,0.9)]">
              <p class="text-[10px] uppercase tracking-[0.42em] text-slate-300">Analyzed</p>
              <p class="text-4xl font-semibold text-emerald-200 mt-3">{formatNumber(stats.analyzed)}</p>
              <p class="text-xs text-emerald-200/80 mt-2">Ready for persona distribution</p>
            </div>
            <div class="rounded-3xl border border-white/12 bg-gradient-to-br from-amber-500/22 via-amber-500/10 to-transparent px-6 py-6 shadow-[0_30px_80px_-70px_rgba(251,191,36,0.9)]">
              <p class="text-[10px] uppercase tracking-[0.42em] text-slate-300">Awaiting AI</p>
              <p class="text-4xl font-semibold text-amber-200 mt-3">{formatNumber(stats.unanalyzed)}</p>
              <p class="text-xs text-amber-100/80 mt-2">Queued for analyzer pipeline</p>
            </div>
            <div class="rounded-3xl border border-white/12 bg-gradient-to-br from-purple-500/24 via-purple-500/8 to-transparent px-6 py-6 shadow-[0_30px_80px_-70px_rgba(192,132,252,0.8)]">
              <p class="text-[10px] uppercase tracking-[0.42em] text-slate-300">Active channels</p>
              <p class="text-4xl font-semibold text-purple-200 mt-3">{Object.keys(stats.platforms).length}</p>
              <p class="text-xs text-purple-100/80 mt-2">Sources with fresh signal</p>
            </div>
          </div>
        {/if}
      </div>
    </div>

    <div class="rounded-4xl border border-white/12 bg-white/6 backdrop-blur-2xl shadow-[0_40px_160px_-90px_rgba(120,185,255,0.8)] p-6 space-y-4">
      <div class="flex items-center justify-between">
        <div>
          <p class="text-[10px] uppercase tracking-[0.42em] text-slate-300">Operations log</p>
          <h2 class="text-lg font-semibold text-white mt-1">Autonomy feed</h2>
        </div>
        <span class="text-[11px] font-semibold uppercase tracking-[0.35em] text-blue-200">Realtime</span>
      </div>
      <div class="space-y-3">
        {#each timeline as event}
          <div class={`rounded-3xl border px-4 py-3 flex items-start gap-3 ${
            event.tone === 'positive'
              ? 'border-emerald-400/30 bg-emerald-500/10'
              : event.tone === 'alert'
                ? 'border-amber-400/35 bg-amber-500/15'
                : 'border-blue-400/30 bg-blue-500/12'
          }`}>
            <div class="text-lg">
              {event.tone === 'positive' ? '✦' : event.tone === 'alert' ? '⚠' : '●'}
            </div>
            <div>
              <p class="text-sm font-semibold text-white">{event.label}</p>
              <p class="text-xs text-slate-200/80 mt-1">{event.detail}</p>
              <p class="text-[11px] uppercase tracking-[0.32em] text-slate-400 mt-2">{event.timestamp}</p>
            </div>
          </div>
        {/each}
      </div>
    </div>
  </section>

  <section class="grid gap-6 lg:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]">
    <div class="rounded-4xl border border-white/12 bg-white/5 backdrop-blur-2xl p-6 space-y-5 shadow-[0_30px_120px_-80px_rgba(120,144,255,0.65)]">
      <div class="flex items-center justify-between">
        <div>
          <p class="text-[10px] uppercase tracking-[0.42em] text-slate-300">Platform cadence</p>
          <h3 class="text-lg font-semibold text-white mt-1">Signal per channel</h3>
        </div>
        <button class="text-[11px] font-medium text-blue-200 hover:text-blue-100 transition-colors" type="button">
          Export data →
        </button>
      </div>
      {#if stats && Object.entries(stats.platforms).length}
        <div class="grid gap-3 sm:grid-cols-2">
          {#each Object.entries(stats.platforms) as [platform, count]}
            <div class="rounded-3xl border border-white/10 bg-white/6 px-5 py-4 flex items-center justify-between">
              <div>
                <p class="text-sm font-semibold text-white capitalize">{platform}</p>
                <p class="text-[11px] uppercase tracking-[0.3em] text-slate-400 mt-1">Last sync · 16m ago</p>
              </div>
              <span class="text-2xl font-semibold text-blue-200">{formatNumber(count)}</span>
            </div>
          {/each}
        </div>
      {:else}
        <p class="text-sm text-slate-300/80">No platform telemetry yet.</p>
      {/if}
    </div>

    <div class="rounded-4xl border border-white/12 bg-white/6 backdrop-blur-2xl p-6 space-y-5 shadow-[0_30px_110px_-85px_rgba(168,121,255,0.75)]">
      <div class="flex items-center justify-between">
        <div>
          <p class="text-[10px] uppercase tracking-[0.42em] text-slate-300">Automation cadence</p>
          <h3 class="text-lg font-semibold text-white mt-1">Workflow matrix</h3>
        </div>
        <span class="text-[11px] font-semibold uppercase tracking-[0.35em] text-emerald-200">Stable</span>
      </div>
      <div class="space-y-4 text-sm">
        <div class="rounded-3xl border border-white/10 bg-white/8 px-4 py-3 flex items-center justify-between">
          <div>
            <p class="font-semibold text-white">Rewrite automation</p>
            <p class="text-xs text-slate-300/80 mt-1">Runs every 6 hours · last run 41 minutes ago.</p>
          </div>
          <span class="text-xs font-semibold text-blue-200">Queued 14 posts</span>
        </div>
        <div class="rounded-3xl border border-white/10 bg-white/8 px-4 py-3 flex items-center justify-between">
          <div>
            <p class="font-semibold text-white">Collection sweep</p>
            <p class="text-xs text-slate-300/80 mt-1">Threads · Reddit · Telegram rotation sequence.</p>
          </div>
          <span class="text-xs font-semibold text-purple-200">Every 90 minutes</span>
        </div>
        <div class="rounded-3xl border border-white/10 bg-white/8 px-4 py-3 flex items-center justify-between">
          <div>
            <p class="font-semibold text-white">Engagement learner</p>
            <p class="text-xs text-slate-300/80 mt-1">Optimization active on last 42 published posts.</p>
          </div>
          <span class="text-xs font-semibold text-emerald-200">CTR up 18%</span>
        </div>
      </div>
    </div>
  </section>
</div>

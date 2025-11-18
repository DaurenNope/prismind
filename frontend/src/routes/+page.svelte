<script lang="ts">
  import { onMount } from 'svelte';
  import { fetchDashboardOverview } from '$lib/services/dashboard';
  import type { DashboardOverview, DashboardOperation } from '$lib/types';

  interface DashboardStats {
    total_posts: number;
    platforms: Record<string, number>;
    unanalyzed: number;
    analyzed: number;
  }

  const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

  let stats: DashboardStats | null = null;
  let overview: DashboardOverview | null = null;
  let loading = true;
  let error: string | null = null;
  let operations: DashboardOperation[] = [];

  onMount(async () => {
    try {
      const statsResponse = await fetch(`${API_BASE}/api/dashboard/stats`);
      if (!statsResponse.ok) throw new Error('Failed to fetch stats');
      stats = await statsResponse.json();

      try {
        overview = await fetchDashboardOverview();
        operations = overview.operations ?? [];
      } catch (overviewError) {
        console.warn('Dashboard overview unavailable', overviewError);
      }
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
  <title>BeyondLines · Intelligence Dashboard</title>
  <meta name="description" content="BeyondLines mission control" />
</svelte:head>

<div class="space-y-12">
  <!-- HERO -->
  <section class="relative overflow-hidden rounded-[32px] border border-white/10 bg-white/6 backdrop-blur-2xl shadow-[0_50px_180px_-110px_rgba(140,168,255,0.85)]">
    <div class="pointer-events-none absolute inset-0">
      <div class="absolute -left-24 top-[-90px] h-[320px] w-[320px] rounded-full bg-[rgba(78,192,255,0.28)] blur-[140px]"></div>
      <div class="absolute right-[-160px] top-[-60px] h-[320px] w-[320px] rounded-full bg-[rgba(93,242,193,0.2)] blur-[140px]"></div>
      <div class="absolute inset-x-16 bottom-[-220px] h-[340px] rounded-[360px] bg-[rgba(24,65,120,0.35)] blur-[150px]"></div>
    </div>

    <div class="relative grid gap-10 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)] items-start px-10 py-12">
      <div class="space-y-8">
        <div class="space-y-4">
          <p class="text-[11px] uppercase tracking-[0.48em] text-slate-300">Mission deck</p>
          <h1 class="text-[38px] md:text-[44px] font-semibold text-white leading-tight">
            BeyondLines intelligence studio for autonomous signal reconnaissance.
          </h1>
          <p class="text-sm md:text-base text-slate-200/80 max-w-2xl">
            Observe ingestion velocity, AI analysis throughput, and persona readiness. Launch collectors,
            spin up rewrites, or jump into any signal stream without leaving the dashboard.
          </p>
        </div>

        <div class="flex flex-wrap gap-4">
          <a
            href="/collection"
            class="group relative overflow-hidden rounded-2xl border border-white/10 px-5 py-4 text-sm font-medium text-white flex items-center justify-between gap-6 transition-all hover:-translate-y-1 hover:shadow-[0_25px_80px_-60px_rgba(78,192,255,0.6)]"
          >
            <span class="absolute inset-0 -z-10 bg-[linear-gradient(135deg,rgba(78,192,255,0.95),rgba(36,163,255,0.95))]"></span>
            <span>
              <span class="block text-[10px] uppercase tracking-[0.32em] text-white/70">Launch collectors</span>
              <span class="block mt-1 text-sm font-semibold">Trigger Reddit · Threads · Telegram capture loop</span>
            </span>
            <span class="text-lg">→</span>
          </a>
          <a
            href="/publishing"
            class="group relative overflow-hidden rounded-2xl border border-white/10 px-5 py-4 text-sm font-medium text-white flex items-center justify-between gap-6 transition-all hover:-translate-y-1 hover:shadow-[0_25px_80px_-60px_rgba(93,242,193,0.55)]"
          >
            <span class="absolute inset-0 -z-10 bg-[linear-gradient(135deg,rgba(93,242,193,0.9),rgba(245,182,120,0.9))]"></span>
            <span>
              <span class="block text-[10px] uppercase tracking-[0.32em] text-white/70">Spin up rewrites</span>
              <span class="block mt-1 text-sm font-semibold">Generate persona-ready copy from latest signals</span>
            </span>
            <span class="text-lg">→</span>
          </a>
        </div>
      </div>

      <div class="w-full rounded-3xl border border-white/10 bg-white/8 px-6 py-6 space-y-6">
        <div>
          <p class="text-[10px] uppercase tracking-[0.35em] text-slate-300">Signal summary</p>
          {#if loading}
            <p class="mt-4 text-sm text-slate-300">Loading metrics…</p>
          {:else if error}
            <p class="mt-4 text-sm text-red-200">{error}</p>
          {:else if stats}
            <div class="space-y-3 mt-4">
              <div class="flex items-center justify-between">
                <span class="text-xs uppercase tracking-[0.3em] text-slate-400">Total corpus</span>
                <span class="text-lg font-semibold text-white">{formatNumber(stats.total_posts)}</span>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-xs uppercase tracking-[0.3em] text-slate-400">Analyzed</span>
                <span class="text-lg font-semibold text-emerald-200">{formatNumber(stats.analyzed)}</span>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-xs uppercase tracking-[0.3em] text-slate-400">Queued</span>
                <span class="text-lg font-semibold text-amber-200">{formatNumber(stats.unanalyzed)}</span>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-xs uppercase tracking-[0.3em] text-slate-400">Active channels</span>
                <span class="text-lg font-semibold text-blue-200">{Object.keys(stats.platforms).length}</span>
              </div>
            </div>
          {:else}
            <p class="mt-4 text-sm text-slate-300">Metrics unavailable.</p>
          {/if}
        </div>

        <div class="rounded-2xl border border-white/10 bg-[linear-gradient(135deg,rgba(78,192,255,0.15),rgba(93,242,193,0.12))] px-4 py-4">
          <p class="text-[10px] uppercase tracking-[0.3em] text-[color:var(--text-muted)]">System heartbeat</p>
          {#if overview}
            <p class="text-sm text-[color:var(--text-primary)] mt-2">{overview.system_heartbeat.summary}</p>
            <p class="text-xs text-[rgba(93,242,193,0.85)] mt-2">Next cycle {overview.system_heartbeat.next_cycle_label}.</p>
          {:else}
            <p class="text-sm text-[color:var(--text-primary)] mt-2">Automation telemetry loading…</p>
            <p class="text-xs text-[rgba(93,242,193,0.85)] mt-2">Hold tight while we fetch realtime status.</p>
          {/if}
        </div>
      </div>
    </div>
  </section>

  <!-- METRIC GRID -->
  <section class="grid gap-6 md:grid-cols-2 xl:grid-cols-4">
    <div class="rounded-3xl border border-white/10 bg-[linear-gradient(135deg,rgba(62,132,255,0.32),rgba(18,83,194,0.18))] px-6 py-6 shadow-[0_30px_80px_-70px_rgba(72,142,255,0.55)]">
      <p class="text-[10px] uppercase tracking-[0.35em] text-[color:var(--text-muted)]">New today</p>
      <p class="text-[34px] font-semibold text-[color:var(--text-primary)] mt-3">{formatNumber(stats?.total_posts ?? 0)}</p>
      <p class="text-xs text-[color:var(--text-muted)]/70 mt-2">Combined multi-source intelligence</p>
    </div>
    <div class="rounded-3xl border border-white/10 bg-[linear-gradient(135deg,rgba(93,242,193,0.30),rgba(17,126,92,0.18))] px-6 py-6 shadow-[0_30px_80px_-70px_rgba(93,242,193,0.45)]">
      <p class="text-[10px] uppercase tracking-[0.35em] text-[color:var(--text-muted)]">Analyzed</p>
      <p class="text-[34px] font-semibold text-[rgba(93,242,193,0.95)] mt-3">{formatNumber(stats?.analyzed ?? 0)}</p>
      <p class="text-xs text-[rgba(93,242,193,0.75)] mt-2">Ready for persona deployment</p>
    </div>
    <div class="rounded-3xl border border-white/10 bg-[linear-gradient(135deg,rgba(245,182,120,0.32),rgba(148,93,52,0.18))] px-6 py-6 shadow-[0_30px_80px_-70px_rgba(245,182,120,0.45)]">
      <p class="text-[10px] uppercase tracking-[0.35em] text-[color:var(--text-muted)]">Awaiting AI</p>
      <p class="text-[34px] font-semibold text-[rgba(245,182,120,0.95)] mt-3">{formatNumber(stats?.unanalyzed ?? 0)}</p>
      <p class="text-xs text-[rgba(245,182,120,0.75)] mt-2">Queued for analyzer pipeline</p>
    </div>
    <div class="rounded-3xl border border-white/10 bg-[linear-gradient(135deg,rgba(78,192,255,0.28),rgba(29,90,180,0.18))] px-6 py-6 shadow-[0_30px_80px_-70px_rgba(78,192,255,0.45)]">
      <p class="text-[10px] uppercase tracking-[0.35em] text-[color:var(--text-muted)]">Signals live</p>
      <p class="text-[34px] font-semibold text-[rgba(78,192,255,0.95)] mt-3">{Object.keys(stats?.platforms ?? {}).length}</p>
      <p class="text-xs text-[rgba(78,192,255,0.75)] mt-2">Channels with fresh activity</p>
    </div>
  </section>

  <!-- LOWER GRID -->
  <section class="grid gap-6 xl:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]">
    <!-- Platform breakdown -->
    <div class="rounded-4xl border border-white/10 bg-[rgba(12,24,40,0.85)] backdrop-blur-2xl p-6 space-y-6 shadow-[0_35px_140px_-90px_rgba(72,150,255,0.5)]">
      <div class="flex items-center justify-between">
        <div>
          <p class="text-[10px] uppercase tracking-[0.35em] text-[color:var(--text-muted)]">Platform cadence</p>
          <h2 class="text-lg font-semibold text-[color:var(--text-primary)] mt-1">Signal by channel</h2>
        </div>
        <button class="text-[11px] font-medium text-[rgba(78,192,255,0.85)] hover:text-[rgba(78,192,255,1)] transition-colors" type="button">
          Export CSV →
        </button>
      </div>

      {#if stats && Object.entries(stats.platforms).length}
        <div class="grid gap-4 sm:grid-cols-2">
          {#each Object.entries(stats.platforms) as [platform, count]}
            <div class="relative overflow-hidden rounded-3xl border border-white/8 bg-[rgba(15,29,46,0.9)] px-5 py-4">
              <span class="absolute inset-0 -z-10 bg-[linear-gradient(135deg,rgba(78,192,255,0.12),rgba(93,242,193,0.1))]"></span>
              <div class="flex items-center justify-between">
                <div>
                  <p class="text-sm font-semibold text-[color:var(--text-primary)] capitalize">{platform}</p>
                  <p class="text-[11px] uppercase tracking-[0.28em] text-[color:var(--text-muted)] mt-1">Last sync · 16m ago</p>
                </div>
                <span class="text-2xl font-semibold text-[rgba(78,192,255,0.95)]">{formatNumber(count)}</span>
              </div>
            </div>
          {/each}
        </div>
      {:else}
        <p class="text-sm text-[color:var(--text-muted)]/80">No platform telemetry yet. Kick off discovery first.</p>
      {/if}
    </div>

    <!-- Activity log -->
    <div class="rounded-4xl border border-white/10 bg-[rgba(12,24,40,0.85)] backdrop-blur-2xl p-6 space-y-5 shadow-[0_35px_140px_-95px_rgba(93,242,193,0.45)]">
      <div class="flex items-center justify-between">
        <div>
          <p class="text-[10px] uppercase tracking-[0.35em] text-[color:var(--text-muted)]">Operations log</p>
          <h3 class="text-lg font-semibold text-[color:var(--text-primary)] mt-1">Autonomy feed</h3>
        </div>
        <span class="text-[11px] font-semibold uppercase tracking-[0.32em] text-[rgba(78,192,255,0.85)]">Live</span>
      </div>

      <div class="relative pl-6 space-y-4">
        <span class="absolute left-[11px] top-0 h-full w-px bg-[linear-gradient(to_bottom,rgba(78,192,255,0.35),transparent)]"></span>
        {#if operations.length === 0}
          <div class="rounded-3xl border border-white/10 bg-[rgba(15,29,46,0.9)] px-4 py-4 text-sm text-[color:var(--text-muted)]/80">
            Awaiting live automation events…
          </div>
        {:else}
          {#each operations as event}
            <div class="relative">
              <span class={`absolute left-[-18px] top-2 h-3 w-3 rounded-full border-2 border-white/25 ${
                event.tone === 'positive'
                  ? 'bg-[rgba(93,242,193,0.9)]'
                  : event.tone === 'alert'
                    ? 'bg-[rgba(245,182,120,0.9)]'
                    : 'bg-[rgba(78,192,255,0.9)]'
              }`}></span>
              <div class="rounded-3xl border border-white/10 bg-[rgba(15,29,46,0.9)] px-4 py-3 space-y-2">
                <div class="flex items-center justify-between gap-4">
                  <p class="text-sm font-semibold text-[color:var(--text-primary)]">{event.label}</p>
                  <span class="text-[11px] uppercase tracking-[0.28em] text-[color:var(--text-muted)]">{event.timestamp_label}</span>
                </div>
                <p class="text-xs text-[color:var(--text-muted)]/80">{event.detail}</p>
              </div>
            </div>
          {/each}
        {/if}
      </div>
    </div>
  </section>

  <!-- WORKFLOW MATRIX -->
  <section class="rounded-4xl border border-white/10 bg-[rgba(11,20,34,0.85)] backdrop-blur-2xl p-6 space-y-6 shadow-[0_35px_150px_-90px_rgba(78,192,255,0.5)]">
    <div class="flex items-center justify-between">
      <div>
        <p class="text-[10px] uppercase tracking-[0.35em] text-[color:var(--text-muted)]">Automation cadence</p>
        <h3 class="text-lg font-semibold text-[color:var(--text-primary)] mt-1">Workflow matrix</h3>
      </div>
      <span class="text-[11px] font-semibold uppercase tracking-[0.32em] text-[rgba(93,242,193,0.85)]">{overview ? 'Live' : 'Syncing'}</span>
    </div>

    <div class="grid gap-4 md:grid-cols-3">
      <div class="rounded-3xl border border-white/10 bg-[rgba(15,29,46,0.92)] px-5 py-4 space-y-3">
        <div class="inline-flex items-center gap-2 rounded-full border border-[rgba(78,192,255,0.4)] bg-[rgba(78,192,255,0.16)] px-3 py-1 text-[11px] uppercase tracking-[0.28em] text-[rgba(78,192,255,0.9)]">Rewrites</div>
        {#if overview}
          <p class="text-sm font-semibold text-[color:var(--text-primary)]">
            {overview.workflow.rewrites.queue} rewrites ready · {overview.workflow.rewrites.total_transformations} total transformations active.
          </p>
          <p class="text-xs text-[rgba(78,192,255,0.8)]">Last rewrite generated {overview.workflow.rewrites.last_activity}.</p>
        {:else}
          <p class="text-sm font-semibold text-[color:var(--text-primary)]">Loading rewrite telemetry…</p>
          <p class="text-xs text-[rgba(78,192,255,0.8)]">Queue status will appear shortly.</p>
        {/if}
      </div>
      <div class="rounded-3xl border border-white/10 bg-[rgba(15,29,46,0.92)] px-5 py-4 space-y-3">
        <div class="inline-flex items-center gap-2 rounded-full border border-[rgba(93,242,193,0.42)] bg-[rgba(93,242,193,0.16)] px-3 py-1 text-[11px] uppercase tracking-[0.28em] text-[rgba(93,242,193,0.85)]">Collectors</div>
        {#if overview}
          <p class="text-sm font-semibold text-[color:var(--text-primary)]">
            {overview.workflow.collectors.healthy} / {overview.workflow.collectors.platforms_monitored} channels healthy on last sweep.
          </p>
          <p class="text-xs text-[rgba(93,242,193,0.75)]">Most recent run completed {overview.workflow.collectors.last_activity}.</p>
        {:else}
          <p class="text-sm font-semibold text-[color:var(--text-primary)]">Loading collector telemetry…</p>
          <p class="text-xs text-[rgba(93,242,193,0.75)]">Next rotation ETA pending.</p>
        {/if}
      </div>
      <div class="rounded-3xl border border-white/10 bg-[rgba(15,29,46,0.92)] px-5 py-4 space-y-3">
        <div class="inline-flex items-center gap-2 rounded-full border border-[rgba(245,182,120,0.45)] bg-[rgba(245,182,120,0.16)] px-3 py-1 text-[11px] uppercase tracking-[0.28em] text-[rgba(245,182,120,0.85)]">Learning</div>
        {#if overview}
          <p class="text-sm font-semibold text-[color:var(--text-primary)]">
            Monitoring {overview.workflow.learning.with_engagement} engagement-rich posts out of {overview.workflow.learning.posted_total} total deployments.
          </p>
          <p class="text-xs text-[rgba(245,182,120,0.75)]">
            Last learning signal updated {overview.workflow.learning.last_posted ?? 'no recent deployment'}.
          </p>
        {:else}
          <p class="text-sm font-semibold text-[color:var(--text-primary)]">Learning telemetry syncing…</p>
          <p class="text-xs text-[rgba(245,182,120,0.75)]">Engagement insights will populate shortly.</p>
        {/if}
      </div>
    </div>
  </section>
</div>

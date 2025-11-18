<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import Toast from '$lib/components/Toast.svelte';
  import { fetchTransformations, fetchScheduledPosts, updateTransformation, schedulePost, deleteScheduledPost, publishNow, deleteTransformation, cleanupOldTransformations } from '$lib/services/publishing';
  import type { TransformationRecord, ScheduledPostRecord } from '$lib/types';

  let transformations: TransformationRecord[] = [];
  let scheduled: ScheduledPostRecord[] = [];
  let loading = true;
  let error: string | null = null;
  let personaFilter = 'all';
  let platformFilter = 'all';
  let readyOnly = false;
  let dateFilter: 'all' | '7d' | '30d' | '90d' = '30d'; // Default to last 30 days
  let editingId: number | null = null;
  let formContent = '';
  let schedulingId: number | null = null;
  let scheduledTime = '';
  let toastMessage = '';
  let toastTone: 'success' | 'error' | 'info' = 'info';
  let toastVisible = false;
  let toastTimer: ReturnType<typeof setTimeout> | null = null;

  const personas = ['qronoya', 'aspandead', 'beyondlines'];
  const platforms = ['threads', 'twitter', 'telegram'];
  const personaStyles: Record<string, string> = {
    qronoya: 'border-[rgba(93,242,193,0.45)] bg-[rgba(93,242,193,0.16)] text-[rgba(93,242,193,0.95)]',
    aspandead: 'border-[rgba(78,192,255,0.45)] bg-[rgba(78,192,255,0.16)] text-[rgba(78,192,255,0.95)]',
    beyondlines: 'border-[rgba(245,182,120,0.55)] bg-[rgba(245,182,120,0.2)] text-[rgba(245,182,120,0.95)]'
  };

  const loadData = async () => {
    loading = true;
    error = null;
    try {
      const persona = personaFilter === 'all' ? undefined : personaFilter;
      const platform = platformFilter === 'all' ? undefined : platformFilter;
      const [transData, schedData] = await Promise.all([
        fetchTransformations(persona, readyOnly),
        fetchScheduledPosts(persona, platform)
      ]);

      // Filter by date
      const cutoffDate = getDateCutoff(dateFilter);
      transformations = transData.filter(t => {
        if (!t.created_at) return false;
        const created = new Date(t.created_at);
        return created >= cutoffDate;
      });

      scheduled = schedData.filter(s => {
        if (!s.scheduled_time) return true; // Keep scheduled posts without time
        const scheduled = new Date(s.scheduled_time);
        // For scheduled posts, show if scheduled in the future or within date range
        return scheduled >= cutoffDate || scheduled >= new Date();
      });

      showToast('Publishing data refreshed');
    } catch (err) {
      error = err instanceof Error ? err.message : 'Failed to load publishing data';
      showToast('Failed to refresh publishing data', 'error');
    } finally {
      loading = false;
    }
  };

  const getDateCutoff = (filter: typeof dateFilter): Date => {
    const now = new Date();
    switch (filter) {
      case '7d':
        return new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
      case '30d':
        return new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
      case '90d':
        return new Date(now.getTime() - 90 * 24 * 60 * 60 * 1000);
      default:
        return new Date(0); // Show all
    }
  };

  const deleteOldTransformations = async () => {
    const deleteAll = confirm('Delete ALL transformations? This will clear all rewrites (including recent ones).\n\nClick OK to delete ALL, or Cancel to only delete old ones (>30 days).');

    try {
      let result;
      if (deleteAll) {
        if (!confirm('⚠️ WARNING: This will delete ALL transformations. This cannot be undone. Are you sure?')) {
          return;
        }
        result = await cleanupOldTransformations(30, true);
      } else {
        if (!confirm('Delete transformations older than 30 days? This will clear outdated rewrites from the old rewriter.')) {
          return;
        }
        result = await cleanupOldTransformations(30, false);
      }

      await loadData();
      showToast(result.message || `Deleted ${result.deleted_count || 0} transformations`, 'success');
    } catch (err) {
      error = err instanceof Error ? err.message : 'Failed to cleanup transformations';
      showToast('Failed to cleanup transformations', 'error');
      console.error('Cleanup error:', err);
    }
  };

  const removeTransformation = async (id: number) => {
    if (!confirm('Delete this transformation? This cannot be undone.')) {
      return;
    }

    try {
      await deleteTransformation(id);
      await loadData();
      showToast('Transformation deleted', 'success');
    } catch (err) {
      error = err instanceof Error ? err.message : 'Failed to delete transformation';
      showToast('Failed to delete transformation', 'error');
    }
  };

  const beginEdit = (record: TransformationRecord) => {
    editingId = record.id;
    formContent = record.content;
  };

  const cancelEdit = () => {
    editingId = null;
    formContent = '';
  };

  const saveEdit = async (record: TransformationRecord) => {
    try {
      await updateTransformation(record.id, {
        content: formContent,
        ready_for_posting: record.ready_for_posting
      });
      await loadData();
      cancelEdit();
      showToast('Transformation saved', 'success');
    } catch (err) {
      error = err instanceof Error ? err.message : 'Failed to save transformation';
      showToast('Failed to save transformation', 'error');
    }
  };

  const toggleReady = async (record: TransformationRecord, next: boolean) => {
    try {
      await updateTransformation(record.id, { ready_for_posting: next });
      await loadData();
      showToast(next ? 'Marked ready for posting' : 'Marked as draft', 'success');
    } catch (err) {
      error = err instanceof Error ? err.message : 'Failed to update readiness';
      showToast('Failed to update readiness', 'error');
    }
  };

  const scheduleFromTransformation = (record: TransformationRecord) => {
    schedulingId = record.id;
    scheduledTime = new Date(Date.now() + 1000 * 60 * 30).toISOString().slice(0, 16);
    formContent = record.content;
    showToast(`Scheduling for ${record.persona_key} → ${record.platform}`, 'info');
  };

  const confirmSchedule = async () => {
    if (!schedulingId) return;
    if (!scheduledTime || !formContent.trim()) {
      showToast('Content and time are required to schedule', 'error');
      return;
    }
    try {
      const record = transformations.find((item) => item.id === schedulingId);
      if (!record) return;
      await schedulePost({
        persona_key: record.persona_key,
        platform: record.platform,
        content: formContent,
        scheduled_time: new Date(scheduledTime).toISOString(),
        content_type: 'single_tweet'
      });
      schedulingId = null;
      formContent = '';
      await loadData();
      showToast('Post scheduled', 'success');
    } catch (err) {
      error = err instanceof Error ? err.message : 'Failed to schedule post';
      showToast('Scheduling failed', 'error');
    }
  };

  const cancelSchedule = () => {
    schedulingId = null;
    formContent = '';
    showToast('Scheduling cancelled', 'info');
  };

  const removeScheduled = async (id: number) => {
    try {
      await deleteScheduledPost(id);
      await loadData();
      showToast('Scheduled post cancelled', 'success');
    } catch (err) {
      error = err instanceof Error ? err.message : 'Failed to delete scheduled post';
      showToast('Unable to cancel scheduled post', 'error');
    }
  };

  const postNow = async (id: number) => {
    try {
      await publishNow(id);
      await loadData();
      showToast('Post dispatched', 'success');
    } catch (err) {
      error = err instanceof Error ? err.message : 'Failed to publish immediately';
      showToast('Failed to send post', 'error');
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

  const getAgeInDays = (value?: string): number | null => {
    if (!value) return null;
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return null;
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    return Math.floor(diffMs / (1000 * 60 * 60 * 24));
  };

  const getAgeLabel = (days: number | null): string => {
    if (days === null) return '';
    if (days === 0) return 'Today';
    if (days === 1) return 'Yesterday';
    if (days < 7) return `${days} days ago`;
    if (days < 30) return `${Math.floor(days / 7)} weeks ago`;
    if (days < 365) return `${Math.floor(days / 30)} months ago`;
    return `${Math.floor(days / 365)} years ago`;
  };

  onMount(() => {
    void loadData();
  });

  onDestroy(() => {
    if (toastTimer) clearTimeout(toastTimer);
  });

  const showToast = (message: string, tone: 'success' | 'error' | 'info' = 'info') => {
    toastMessage = message;
    toastTone = tone;
    toastVisible = true;
    if (toastTimer) clearTimeout(toastTimer);
    toastTimer = setTimeout(() => {
      toastVisible = false;
    }, 3000);
  };
</script>

<svelte:head>
  <title>BeyondLines · Publishing Pipeline</title>
  <meta name="description" content="Manage BeyondLines transformations and scheduled posts" />
</svelte:head>

<div class="space-y-8">
  <section class="rounded-[32px] border border-white/10 bg-[rgba(11,20,34,0.85)] backdrop-blur-2xl px-8 py-10 shadow-[0_40px_150px_-100px_rgba(78,192,255,0.45)]">
    <div class="grid gap-6 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
      <div class="space-y-4">
        <p class="text-[11px] uppercase tracking-[0.45em] text-[color:var(--text-muted)]">Publishing pipeline</p>
        <h1 class="text-[36px] md:text-[42px] font-semibold text-[color:var(--text-primary)] leading-tight">
          Curate, refine, and schedule BeyondLines persona output in one view.
        </h1>
        <p class="text-sm md:text-base text-[color:var(--text-muted)]/85 max-w-2xl">
          Review transformations generated by automation, approve readiness, and queue final posts for Threads, Twitter, or Telegram.
        </p>
      </div>
      <div class="rounded-3xl border border-white/10 bg-[rgba(15,29,46,0.9)] px-6 py-5 space-y-4">
        <div class="flex items-center justify-between">
          <span class="text-[10px] uppercase tracking-[0.35em] text-[color:var(--text-muted)]">Metrics</span>
          <span class="rounded-full border border-[rgba(78,192,255,0.45)] bg-[rgba(78,192,255,0.16)] px-3 py-1 text-[11px] uppercase tracking-[0.32em] text-[rgba(78,192,255,0.85)]">Live</span>
        </div>
        <div class="flex flex-wrap gap-3 text-sm text-[color:var(--text-muted)]">
          <span class="rounded-full border border-white/10 bg-white/8 px-3 py-1">Transformations · {transformations.length}</span>
          <span class="rounded-full border border-white/10 bg-white/8 px-3 py-1">Scheduled · {scheduled.length}</span>
        </div>
      </div>
    </div>
  </section>

  <section class="rounded-3xl border border-white/10 bg-[rgba(11,20,34,0.85)] backdrop-blur-xl p-6 space-y-5 shadow-[0_35px_120px_-80px_rgba(78,192,255,0.5)]">
    <div class="flex flex-wrap items-center justify-between gap-4">
      <div>
        <p class="text-[11px] uppercase tracking-[0.4em] text-[color:var(--text-muted)]">Filters</p>
        <h2 class="text-xl font-semibold text-[color:var(--text-primary)] mt-2">Persona + platform</h2>
      </div>
      <div class="flex flex-wrap items-center gap-2">
        <div class="flex flex-wrap items-center gap-2">
          <button
            type="button"
            class="rounded-xl border border-[rgba(78,192,255,0.45)] bg-[linear-gradient(135deg,rgba(78,192,255,0.18),rgba(93,242,193,0.18))] px-4 py-2 text-sm font-semibold text-[color:var(--text-primary)] shadow-[0_12px_40px_-24px_rgba(78,192,255,0.6)] hover:shadow-[0_18px_60px_-24px_rgba(78,192,255,0.65)] transition-all"
            on:click={() => void loadData()}
          >
            Refresh data
          </button>
          <button
            type="button"
            class="rounded-xl border border-[rgba(245,182,120,0.45)] bg-[rgba(245,182,120,0.15)] px-4 py-2 text-sm font-semibold text-[rgba(245,182,120,0.9)] hover:bg-[rgba(245,182,120,0.25)] transition-all"
            on:click={() => void deleteOldTransformations()}
            title="Delete transformations older than 30 days (outdated rewrites)"
          >
            Clear old rewrites
          </button>
        </div>
      </div>
    </div>

    <div class="flex flex-wrap items-center gap-6">
      <div class="flex flex-wrap items-center gap-3">
        <span class="text-xs uppercase tracking-[0.32em] text-[color:var(--text-muted)]">Persona</span>
        <div class="flex flex-wrap gap-2">
          <button
            type="button"
            class={`px-3 py-1.5 rounded-full border transition-colors text-sm ${personaFilter === 'all' ? 'border-white/20 bg-white/10 text-[color:var(--text-primary)]' : 'border-white/8 bg-white/5 text-[color:var(--text-muted)] hover:border-white/20'}`}
            on:click={() => {
              personaFilter = 'all';
              void loadData();
            }}
          >
            All personas
          </button>
          {#each personas as persona}
            <button
              type="button"
              class={`px-3 py-1.5 rounded-full border transition-colors text-sm capitalize ${personaFilter === persona ? 'border-white/20 bg-white/10 text-[color:var(--text-primary)]' : 'border-white/8 bg-white/5 text-[color:var(--text-muted)] hover:border-white/20'}`}
              on:click={() => {
                personaFilter = persona;
                void loadData();
              }}
            >
              {persona}
            </button>
          {/each}
        </div>
      </div>

      <div class="flex flex-wrap items-center gap-3">
        <span class="text-xs uppercase tracking-[0.32em] text-[color:var(--text-muted)]">Platform</span>
        <div class="flex flex-wrap gap-2">
          <button
            type="button"
            class={`px-3 py-1.5 rounded-full border transition-colors text-sm ${platformFilter === 'all' ? 'border-white/20 bg-white/10 text-[color:var(--text-primary)]' : 'border-white/8 bg-white/5 text-[color:var(--text-muted)] hover:border-white/20'}`}
            on:click={() => {
              platformFilter = 'all';
              void loadData();
            }}
          >
            All platforms
          </button>
          {#each platforms as platform}
            <button
              type="button"
              class={`px-3 py-1.5 rounded-full border transition-colors text-sm capitalize ${platformFilter === platform ? 'border-white/20 bg-white/10 text-[color:var(--text-primary)]' : 'border-white/8 bg-white/5 text-[color:var(--text-muted)] hover:border-white/20'}`}
              on:click={() => {
                platformFilter = platform;
                void loadData();
              }}
            >
              {platform}
            </button>
          {/each}
        </div>
      </div>

      <div class="flex items-center gap-3">
        <label for="ready-only" class="text-xs uppercase tracking-[0.32em] text-[color:var(--text-muted)]">Ready only</label>
        <input id="ready-only" type="checkbox" bind:checked={readyOnly} on:change={() => void loadData()} class="h-4 w-4 rounded border-white/10 bg-white/5 text-[rgba(78,192,255,0.85)] focus:ring-[rgba(78,192,255,0.45)]" />
      </div>

      <div class="flex flex-wrap items-center gap-3">
        <span class="text-xs uppercase tracking-[0.32em] text-[color:var(--text-muted)]">Date range</span>
        <div class="flex flex-wrap gap-2">
          {#each [
            { label: 'All', value: 'all' },
            { label: 'Last 7 days', value: '7d' },
            { label: 'Last 30 days', value: '30d' },
            { label: 'Last 90 days', value: '90d' }
          ] as option}
            <button
              type="button"
              class={`px-3 py-1.5 rounded-full border transition-colors text-sm ${
                dateFilter === option.value
                  ? 'border-white/20 bg-white/10 text-[color:var(--text-primary)]'
                  : 'border-white/8 bg-white/5 text-[color:var(--text-muted)] hover:border-white/20'
              }`}
              on:click={() => {
                dateFilter = option.value as typeof dateFilter;
                void loadData();
              }}
            >
              {option.label}
            </button>
          {/each}
        </div>
      </div>
    </div>

    {#if error}
      <div class="rounded-2xl border border-red-400/40 bg-red-500/15 px-4 py-3 text-sm text-red-100">
        {error}
      </div>
    {/if}
  </section>

  <section class="space-y-8">
      <div class="rounded-3xl border border-white/10 bg-[rgba(12,24,40,0.85)] backdrop-blur-xl p-6 space-y-4">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-[10px] uppercase tracking-[0.35em] text-[color:var(--text-muted)]">Transformation queue</p>
            <h2 class="text-lg font-semibold text-[color:var(--text-primary)] mt-1">Automation output</h2>
          </div>
          <span class="text-[11px] font-semibold uppercase tracking-[0.32em] text-[rgba(78,192,255,0.85)]">Live</span>
        </div>

        {#if loading}
          <div class="grid gap-4 md:grid-cols-2">
            {#each Array.from({ length: 4 }) as _, index}
              <div class="animate-pulse rounded-2xl border border-white/10 bg-[rgba(15,29,46,0.9)] px-5 py-5 space-y-4" data-testid={`trans-skeleton-${index}`}>
                <div class="h-3 w-24 rounded-full bg-white/10"></div>
                <div class="h-4 w-3/4 rounded-full bg-white/10"></div>
                <div class="h-20 rounded-xl bg-white/10"></div>
                <div class="h-8 rounded-xl bg-white/10"></div>
              </div>
            {/each}
          </div>
        {:else if transformations.length === 0}
          <p class="text-sm text-[color:var(--text-muted)]/80">No transformations available. Automation will populate this list after the next rewrite cycle.</p>
        {:else}
          <div class="grid gap-4 md:grid-cols-2">
            {#each transformations as record}
              {@const age = getAgeInDays(record.created_at)}
              <article class="rounded-2xl border border-white/10 bg-[rgba(15,29,46,0.9)] px-5 py-5 space-y-3 shadow-[0_20px_70px_-60px_rgba(78,192,255,0.45)]">
                <header class="flex items-center justify-between gap-3">
                  <div>
                    <p class="text-[11px] uppercase tracking-[0.28em] text-[color:var(--text-muted)] flex items-center gap-2">
                      <span class={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] capitalize ${personaStyles[record.persona_key] ?? 'border-white/12 bg-white/10 text-[color:var(--text-muted)]'}`}>{record.persona_key}</span>
                      →
                      <span class="rounded-full border border-white/10 bg-white/10 px-2 py-0.5 text-[10px] uppercase text-[rgba(93,242,193,0.85)]">{record.platform}</span>
                    </p>
                    <div class="flex items-center gap-2">
                      <p class="text-xs text-[color:var(--text-muted)]">{formatDate(record.created_at)}</p>
                      {#if age !== null && age > 30}
                        <span class="text-[10px] uppercase tracking-[0.2em] text-[rgba(245,182,120,0.85)] bg-[rgba(245,182,120,0.15)] px-2 py-0.5 rounded-full">
                          {getAgeLabel(age)}
                        </span>
                      {/if}
                    </div>
                  </div>
                  <label class="flex items-center gap-2 text-xs text-[color:var(--text-muted)]">
                    <input type="checkbox" checked={record.ready_for_posting ?? false} on:change={(event) => toggleReady(record, (event.target as HTMLInputElement).checked)} class="h-4 w-4 rounded border-white/10 bg-white/5 text-[rgba(78,192,255,0.85)] focus:ring-[rgba(78,192,255,0.35)]" /> Ready
                  </label>
                </header>
                {#if editingId === record.id}
                  <textarea bind:value={formContent} rows="6" class="w-full rounded-xl border border-white/10 bg-[rgba(13,23,37,0.95)] px-4 py-2 text-sm text-[color:var(--text-primary)] focus:outline-none focus:border-[rgba(78,192,255,0.45)] focus:ring-2 focus:ring-[rgba(78,192,255,0.25)]" placeholder="Enter content to post"></textarea>
                  <div class="flex items-center gap-3">
                    <button type="button" class="rounded-xl border border-[rgba(78,192,255,0.4)] bg-[rgba(78,192,255,0.18)] px-3 py-1.5 text-sm text-[color:var(--text-primary)]" on:click={() => saveEdit(record)}>Save</button>
                    <button type="button" class="rounded-xl border border-white/10 bg-white/5 px-3 py-1.5 text-sm text-[color:var(--text-muted)]" on:click={cancelEdit}>Cancel</button>
                  </div>
                {:else}
                  <p class="text-sm text-[color:var(--text-muted)]/85 whitespace-pre-line max-h-40 overflow-y-auto">
                    {record.content}
                  </p>
                  <div class="flex flex-wrap gap-3 text-xs">
                    <button type="button" class="rounded-xl border border-white/10 bg-white/10 px-3 py-1 text-[color:var(--text-primary)] hover:border-[rgba(78,192,255,0.45)]" on:click={() => beginEdit(record)}>Edit</button>
                    <button type="button" class="rounded-xl border border-[rgba(93,242,193,0.4)] bg-[rgba(93,242,193,0.15)] px-3 py-1 text-[rgba(93,242,193,0.9)]" on:click={() => scheduleFromTransformation(record)}>Schedule</button>
                    <button type="button" class="rounded-xl border border-[rgba(245,114,120,0.4)] bg-[rgba(245,114,120,0.15)] px-3 py-1 text-[rgba(245,114,120,0.9)] hover:bg-[rgba(245,114,120,0.25)]" on:click={() => removeTransformation(record.id)}>Delete</button>
                  </div>
                {/if}
              </article>
            {/each}
          </div>
        {/if}
      </div>

      <div class="rounded-3xl border border-white/10 bg-[rgba(12,24,40,0.85)] backdrop-blur-xl p-6 space-y-5">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-[10px] uppercase tracking-[0.35em] text-[color:var(--text-muted)]">Scheduled posts</p>
            <h3 class="text-lg font-semibold text-[color:var(--text-primary)] mt-1">Queue overview</h3>
          </div>
          <span class="text-[11px] font-semibold uppercase tracking-[0.32em] text-[rgba(93,242,193,0.85)]">Autonomous</span>
        </div>
        {#if loading}
          <div class="grid gap-3">
            {#each Array.from({ length: 4 }) as _, index}
              <div class="animate-pulse rounded-2xl border border-white/10 bg-[rgba(15,29,46,0.9)] px-4 py-3 space-y-3" data-testid={`schedule-skeleton-${index}`}>
                <div class="h-3 w-20 rounded-full bg-white/10"></div>
                <div class="h-4 w-3/4 rounded-full bg-white/10"></div>
                <div class="h-3 w-1/4 rounded-full bg-white/10"></div>
              </div>
            {/each}
          </div>
        {:else if scheduled.length === 0}
          <p class="text-sm text-[color:var(--text-muted)]/80">No posts queued at the moment. Approve a transformation to schedule one.</p>
        {:else}
          <div class="space-y-3">
            {#each scheduled as item}
              <div class="rounded-2xl border border-white/10 bg-[rgba(15,29,46,0.9)] px-4 py-3 text-sm text-[color:var(--text-primary)]">
                <div class="flex items-center justify-between gap-4">
                  <div>
                    <p class="text-[11px] uppercase tracking-[0.32em] text-[rgba(78,192,255,0.85)]">{item.persona_key ?? 'persona'} → {item.platform}</p>
                    <p class="text-xs text-[color:var(--text-muted)]">Scheduled {formatDate(item.scheduled_time)} · {item.status ?? 'scheduled'}</p>
                  </div>
                  <div class="flex gap-2 text-xs">
                    <button type="button" class="rounded-xl border border-white/10 bg-white/10 px-3 py-1 text-[color:var(--text-primary)]" on:click={() => postNow(item.id)}>Post now</button>
                    <button type="button" class="rounded-xl border border-white/10 bg-white/10 px-3 py-1 text-[rgba(245,182,120,0.85)]" on:click={() => removeScheduled(item.id)}>Cancel</button>
                  </div>
                </div>
                <p class="mt-2 text-sm text-[color:var(--text-muted)]/85 whitespace-pre-line">{item.content}</p>
              </div>
            {/each}
          </div>
        {/if}
      </div>
    </section>

  {#if schedulingId}
    <div class="fixed inset-0 z-50 flex items-center justify-center bg-[rgba(4,7,18,0.6)] backdrop-blur-sm">
      <div class="w-full max-w-lg rounded-3xl border border-white/10 bg-[rgba(12,24,40,0.92)] px-6 py-6 space-y-4 shadow-[0_30px_120px_-90px_rgba(78,192,255,0.55)]">
        <div class="flex items-center justify-between">
          <h3 class="text-lg font-semibold text-[color:var(--text-primary)]">Schedule transformation</h3>
          <button type="button" class="text-sm text-[color:var(--text-muted)] hover:text-[color:var(--text-primary)]" on:click={cancelSchedule}>✕</button>
        </div>
        <label for="scheduled-time" class="block text-xs uppercase tracking-[0.32em] text-[color:var(--text-muted)]">Scheduled time</label>
        <input id="scheduled-time" type="datetime-local" bind:value={scheduledTime} class="w-full rounded-xl border border-white/10 bg-[rgba(13,23,37,0.95)] px-4 py-2 text-sm text-[color:var(--text-primary)] focus:outline-none focus:border-[rgba(78,192,255,0.45)] focus:ring-2 focus:ring-[rgba(78,192,255,0.25)]" />
        <label for="form-content" class="block text-xs uppercase tracking-[0.32em] text-[color:var(--text-muted)]">Content</label>
        <textarea id="form-content" bind:value={formContent} rows="6" class="w-full rounded-xl border border-white/10 bg-[rgba(13,23,37,0.95)] px-4 py-2 text-sm text-[color:var(--text-primary)] focus:outline-none focus:border-[rgba(78,192,255,0.45)] focus:ring-2 focus:ring-[rgba(78,192,255,0.25)]"></textarea>
        <div class="flex items-center gap-3">
          <button type="button" class="rounded-xl border border-[rgba(78,192,255,0.45)] bg-[rgba(78,192,255,0.18)] px-3 py-1.5 text-sm text-[color:var(--text-primary)] disabled:opacity-50"
            on:click={confirmSchedule}
            disabled={!scheduledTime || !formContent.trim()}
          >Confirm schedule</button>
          <button type="button" class="rounded-xl border border-white/10 bg-white/5 px-3 py-1.5 text-sm text-[color:var(--text-muted)]" on:click={cancelSchedule}>Cancel</button>
        </div>
      </div>
    </div>
  {/if}

</div>

{#if toastVisible}
  <Toast message={toastMessage} tone={toastTone} />
{/if}

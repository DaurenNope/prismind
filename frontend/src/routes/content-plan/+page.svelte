<script lang="ts">
  import { onMount } from 'svelte';
  import ContentCalendar from '$lib/components/ContentCalendar.svelte';
  import ContentPlanStats from '$lib/components/ContentPlanStats.svelte';
  import { fetchScheduledPosts } from '$lib/services/publishing';
  import type { ScheduledPostRecord } from '$lib/types';

  let filters = {
    persona: 'all',
    platform: 'all',
    status: 'all',
    dateRange: { start: null as Date | null, end: null as Date | null }
  };

  let contentPlan: ScheduledPostRecord[] = [];
  let loading = false;
  let error: string | null = null;

  // Available personas and platforms
  let personas: string[] = [];
  let platforms: string[] = [];

  // Summary stats
  let stats = {
    total: 0,
    byPersona: {} as Record<string, number>,
    byPlatform: {} as Record<string, number>,
    byStatus: {} as Record<string, number>
  };

  // Load content plan
  const loadContentPlan = async () => {
    loading = true;
    error = null;
    try {
      const persona = filters.persona !== 'all' ? filters.persona : undefined;
      const platform = filters.platform !== 'all' ? filters.platform : undefined;
      let posts = await fetchScheduledPosts(persona, platform);

      // Filter by status
      if (filters.status && filters.status !== 'all') {
        posts = posts.filter(p => p.status === filters.status);
      }

      // Filter by date range
      if (filters.dateRange.start) {
        posts = posts.filter(p => {
          const postDate = new Date(p.scheduled_time || '');
          return postDate >= filters.dateRange.start!;
        });
      }
      if (filters.dateRange.end) {
        posts = posts.filter(p => {
          const postDate = new Date(p.scheduled_time || '');
          const endDate = new Date(filters.dateRange.end!);
          endDate.setHours(23, 59, 59, 999);
          return postDate <= endDate;
        });
      }

      contentPlan = posts;
      calculateStats();
      extractPersonasAndPlatforms();
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to load content plan';
      console.error('Error loading content plan:', e);
    } finally {
      loading = false;
    }
  };

  // Calculate summary statistics
  const calculateStats = () => {
    stats = {
      total: contentPlan.length,
      byPersona: {},
      byPlatform: {},
      byStatus: {}
    };

    contentPlan.forEach(post => {
      // By persona
      const persona = post.persona_key || 'unknown';
      stats.byPersona[persona] = (stats.byPersona[persona] || 0) + 1;

      // By platform
      const platform = post.platform || 'unknown';
      stats.byPlatform[platform] = (stats.byPlatform[platform] || 0) + 1;

      // By status
      const status = post.status || 'pending';
      stats.byStatus[status] = (stats.byStatus[status] || 0) + 1;
    });
  };

  // Extract unique personas and platforms
  const extractPersonasAndPlatforms = () => {
    const personaSet = new Set<string>();
    const platformSet = new Set<string>();

    contentPlan.forEach(post => {
      if (post.persona_key) personaSet.add(post.persona_key);
      if (post.platform) platformSet.add(post.platform);
    });

    personas = Array.from(personaSet).sort();
    platforms = Array.from(platformSet).sort();
  };

  onMount(() => {
    loadContentPlan();
  });

  // React to filter changes
  $: if (filters) {
    loadContentPlan();
  }

  // Persona colors for stats
  const personaColors: Record<string, string> = {
    qronoya: 'bg-teal-500',
    aspandead: 'bg-blue-500',
    beyondlines: 'bg-orange-500'
  };

  const getPersonaColor = (persona: string): string => {
    const key = persona?.toLowerCase() || '';
    return personaColors[key] || 'bg-gray-500';
  };

  // Status labels
  const statusLabels: Record<string, string> = {
    pending: 'Scheduled',
    posted: 'Posted',
    failed: 'Failed',
    retry: 'Retry'
  };

  // Clear date range
  const clearDateRange = () => {
    filters.dateRange = { start: null, end: null };
  };
</script>

<svelte:head>
  <title>Content Plan - Calendar</title>
</svelte:head>

<div class="content-plan-page min-h-screen bg-gray-50">
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
    <!-- Header -->
    <div class="mb-6">
      <h1 class="text-3xl font-bold text-gray-900">Content Calendar</h1>
      <p class="mt-2 text-sm text-gray-600">
        Visualize and manage your scheduled content across all personas and platforms
      </p>
    </div>

    <!-- Summary Stats -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      <!-- Total Posts -->
      <div class="bg-white rounded-lg shadow-sm p-4">
        <div class="text-sm text-gray-600 mb-1">Total Scheduled</div>
        <div class="text-2xl font-bold text-gray-900">{stats.total}</div>
      </div>

      <!-- By Persona -->
      <div class="bg-white rounded-lg shadow-sm p-4">
        <div class="text-sm text-gray-600 mb-2">By Persona</div>
        <div class="space-y-1">
          {#each Object.entries(stats.byPersona).slice(0, 3) as [persona, count]}
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <span class="w-3 h-3 rounded-full {getPersonaColor(persona)}"></span>
                <span class="text-sm text-gray-700">{persona}</span>
              </div>
              <span class="text-sm font-semibold text-gray-900">{count}</span>
            </div>
          {/each}
          {#if Object.keys(stats.byPersona).length > 3}
            <div class="text-xs text-gray-500 pt-1">
              +{Object.keys(stats.byPersona).length - 3} more
            </div>
          {/if}
        </div>
      </div>

      <!-- By Platform -->
      <div class="bg-white rounded-lg shadow-sm p-4">
        <div class="text-sm text-gray-600 mb-2">By Platform</div>
        <div class="space-y-1">
          {#each Object.entries(stats.byPlatform).slice(0, 3) as [platform, count]}
            <div class="flex items-center justify-between">
              <span class="text-sm text-gray-700 capitalize">{platform}</span>
              <span class="text-sm font-semibold text-gray-900">{count}</span>
            </div>
          {/each}
          {#if Object.keys(stats.byPlatform).length > 3}
            <div class="text-xs text-gray-500 pt-1">
              +{Object.keys(stats.byPlatform).length - 3} more
            </div>
          {/if}
        </div>
      </div>

      <!-- By Status -->
      <div class="bg-white rounded-lg shadow-sm p-4">
        <div class="text-sm text-gray-600 mb-2">By Status</div>
        <div class="space-y-1">
          {#each Object.entries(stats.byStatus) as [status, count]}
            <div class="flex items-center justify-between">
              <span class="text-sm text-gray-700">{statusLabels[status] || status}</span>
              <span class="text-sm font-semibold text-gray-900">{count}</span>
            </div>
          {/each}
        </div>
      </div>
    </div>

    <!-- Filters -->
    <div class="bg-white rounded-lg shadow-sm p-4 mb-6">
      <div class="flex flex-wrap items-end gap-4">
        <!-- Persona Filter -->
        <div class="flex-1 min-w-[150px]">
          <label for="persona-filter" class="block text-sm font-medium text-gray-700 mb-1">
            Persona
          </label>
          <select
            id="persona-filter"
            bind:value={filters.persona}
            class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 text-sm"
          >
            <option value="all">All Personas</option>
            {#each personas as persona}
              <option value={persona}>{persona}</option>
            {/each}
          </select>
        </div>

        <!-- Platform Filter -->
        <div class="flex-1 min-w-[150px]">
          <label for="platform-filter" class="block text-sm font-medium text-gray-700 mb-1">
            Platform
          </label>
          <select
            id="platform-filter"
            bind:value={filters.platform}
            class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 text-sm"
          >
            <option value="all">All Platforms</option>
            {#each platforms as platform}
              <option value={platform}>{platform}</option>
            {/each}
          </select>
        </div>

        <!-- Status Filter -->
        <div class="flex-1 min-w-[150px]">
          <label for="status-filter" class="block text-sm font-medium text-gray-700 mb-1">
            Status
          </label>
          <select
            id="status-filter"
            bind:value={filters.status}
            class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 text-sm"
          >
            <option value="all">All Statuses</option>
            <option value="pending">Scheduled</option>
            <option value="posted">Posted</option>
            <option value="failed">Failed</option>
            <option value="retry">Retry</option>
          </select>
        </div>

        <!-- Date Range Start -->
        <div class="flex-1 min-w-[150px]">
          <label for="date-start" class="block text-sm font-medium text-gray-700 mb-1">
            Start Date
          </label>
            <input
            id="date-start"
            type="date"
            value={filters.dateRange.start ? filters.dateRange.start.toISOString().split('T')[0] : ''}
            on:input={(e) => {
              filters.dateRange.start = e.currentTarget.value ? new Date(e.currentTarget.value) : null;
            }}
            class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 text-sm"
          />
        </div>

        <!-- Date Range End -->
        <div class="flex-1 min-w-[150px]">
          <label for="date-end" class="block text-sm font-medium text-gray-700 mb-1">
            End Date
          </label>
            <input
            id="date-end"
            type="date"
            value={filters.dateRange.end ? filters.dateRange.end.toISOString().split('T')[0] : ''}
            on:input={(e) => {
              filters.dateRange.end = e.currentTarget.value ? new Date(e.currentTarget.value) : null;
            }}
            class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 text-sm"
          />
        </div>

        <!-- Clear Filters -->
        <div>
          <button
            on:click={() => {
              filters = {
                persona: 'all',
                platform: 'all',
                status: 'all',
                dateRange: { start: null, end: null }
              };
            }}
            class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
          >
            Clear
          </button>
        </div>
      </div>
    </div>

    <!-- Statistics Panel -->
    <div class="bg-white rounded-lg shadow-sm p-6 mb-6">
      <h2 class="text-xl font-semibold text-gray-900 mb-4">Content Plan Statistics</h2>
      <ContentPlanStats {filters} />
    </div>

    <!-- Calendar Component -->
    <div class="bg-white rounded-lg shadow-sm p-6">
      {#if loading && contentPlan.length === 0}
        <div class="flex items-center justify-center py-12">
          <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
          <span class="ml-3 text-gray-600">Loading calendar...</span>
        </div>
      {:else if error && contentPlan.length === 0}
        <div class="bg-red-50 border border-red-200 rounded-lg p-4">
          <div class="flex items-center">
            <svg class="w-5 h-5 text-red-500 mr-2" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
            </svg>
            <span class="text-red-800">{error}</span>
          </div>
          <button
            on:click={loadContentPlan}
            class="mt-2 text-sm text-red-600 hover:text-red-800 underline"
          >
            Retry
          </button>
        </div>
      {:else}
        <ContentCalendar {filters} />
      {/if}
    </div>
  </div>
</div>

<style>
  .content-plan-page {
    font-family: system-ui, -apple-system, sans-serif;
  }
</style>


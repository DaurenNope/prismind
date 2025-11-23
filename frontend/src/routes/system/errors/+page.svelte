<script lang="ts">
  import { onMount } from 'svelte';
  import {
    fetchErrors,
    fetchErrorDetails,
    fetchErrorStats,
    resolveError,
    type SystemError,
    type ErrorStats
  } from '$lib/services/errors';
  import LoadingSpinner from '$lib/components/LoadingSpinner.svelte';
  import EmptyState from '$lib/components/EmptyState.svelte';

  let errors: SystemError[] = [];
  let stats: ErrorStats | null = null;
  let loading = true;
  let error: string | null = null;
  
  // Filters
  let componentFilter = 'all';
  let severityFilter = 'all';
  let statusFilter = 'all';
  let searchQuery = '';
  
  // Pagination
  let currentPage = 1;
  let pageSize = 50;
  let total = 0;

  // Detail modal
  let selectedError: SystemError | null = null;
  let showingDetails = false;

  // Resolve modal
  let resolvingId: string | null = null;
  let resolutionNotes = '';

  const components = ['database', 'ai', 'collection', 'publishing', 'api', 'frontend'];
  const severities = ['critical', 'error', 'warning', 'info'];
  const statuses = ['open', 'resolved', 'ignored'];

  const loadData = async () => {
    loading = true;
    error = null;
    try {
      const offset = (currentPage - 1) * pageSize;
      
      const [errorsData, statsData] = await Promise.all([
        fetchErrors({
          component: componentFilter === 'all' ? undefined : componentFilter,
          severity: severityFilter === 'all' ? undefined : severityFilter,
          status: statusFilter === 'all' ? undefined : statusFilter,
          limit: pageSize,
          offset
        }),
        fetchErrorStats()
      ]);

      errors = errorsData.errors;
      total = errorsData.total;
      stats = statsData;
      
      // Apply search filter if provided
      if (searchQuery) {
        const query = searchQuery.toLowerCase();
        errors = errors.filter(e => 
          e.message.toLowerCase().includes(query) ||
          e.error_type.toLowerCase().includes(query) ||
          e.component.toLowerCase().includes(query)
        );
      }
    } catch (err) {
      error = err instanceof Error ? err.message : 'Failed to load errors';
      console.error('Error loading errors:', err);
    } finally {
      loading = false;
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString();
  };

  const formatRelativeTime = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return formatDate(dateString);
  };

  const getSeverityColor = (severity: string) => {
    const colors: Record<string, string> = {
      critical: 'bg-red-600',
      error: 'bg-red-500',
      warning: 'bg-yellow-500',
      info: 'bg-blue-500'
    };
    return colors[severity] || 'bg-gray-500';
  };

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      open: 'bg-red-500',
      resolved: 'bg-green-500',
      ignored: 'bg-gray-500'
    };
    return colors[status] || 'bg-gray-500';
  };

  const handleViewDetails = async (errorId: string | number) => {
    try {
      const details = await fetchErrorDetails(String(errorId));
      selectedError = details;
      showingDetails = true;
    } catch (err) {
      error = err instanceof Error ? err.message : 'Failed to load error details';
    }
  };

  const handleResolve = async () => {
    if (!resolvingId) return;
    try {
      await resolveError(resolvingId, resolutionNotes || undefined);
      resolvingId = null;
      resolutionNotes = '';
      await loadData();
    } catch (err) {
      error = err instanceof Error ? err.message : 'Failed to resolve error';
    }
  };

  onMount(() => {
    loadData();
  });

  $: if (componentFilter || severityFilter || statusFilter) {
    currentPage = 1;
    loadData();
  }
</script>

<svelte:head>
  <title>Error Dashboard - System</title>
</svelte:head>

<div class="container mx-auto px-4 py-8">
  <div class="mb-8">
    <h1 class="text-3xl font-bold mb-2">Error Dashboard</h1>
    <p class="text-gray-600">View and manage system errors</p>
  </div>

  {#if loading && !stats}
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
  {:else}
    <!-- Stats Cards -->
    {#if stats}
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div class="bg-white rounded-lg shadow p-4">
          <div class="text-sm text-gray-600 mb-1">Total Errors</div>
          <div class="text-2xl font-bold">{stats.total_errors}</div>
        </div>
        <div class="bg-white rounded-lg shadow p-4">
          <div class="text-sm text-gray-600 mb-1">Resolution Rate</div>
          <div class="text-2xl font-bold">{(stats.resolution_rate * 100).toFixed(1)}%</div>
        </div>
        <div class="bg-white rounded-lg shadow p-4">
          <div class="text-sm text-gray-600 mb-1">Open Errors</div>
          <div class="text-2xl font-bold">{stats.by_status.open || 0}</div>
        </div>
        <div class="bg-white rounded-lg shadow p-4">
          <div class="text-sm text-gray-600 mb-1">Critical Errors</div>
          <div class="text-2xl font-bold text-red-600">{stats.by_severity.critical || 0}</div>
        </div>
      </div>

      <!-- Component Breakdown -->
      {#if Object.keys(stats.by_component).length > 0}
        <div class="bg-white rounded-lg shadow p-4 mb-6">
          <h2 class="text-lg font-semibold mb-3">Errors by Component</h2>
          <div class="flex flex-wrap gap-4">
            {#each Object.entries(stats.by_component) as [component, count]}
              <div class="flex items-center gap-2">
                <span class="px-2 py-1 rounded text-sm font-medium bg-blue-100 text-blue-800">
                  {component}
                </span>
                <span class="text-gray-700">{count}</span>
              </div>
            {/each}
          </div>
        </div>
      {/if}
    {/if}

    <!-- Filters -->
    <div class="bg-white rounded-lg shadow p-4 mb-6">
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Component</label>
          <select
            bind:value={componentFilter}
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">All Components</option>
            {#each components as component}
              <option value={component}>{component}</option>
            {/each}
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Severity</label>
          <select
            bind:value={severityFilter}
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">All Severities</option>
            {#each severities as severity}
              <option value={severity}>{severity}</option>
            {/each}
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Status</label>
          <select
            bind:value={statusFilter}
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">All Status</option>
            {#each statuses as status}
              <option value={status}>{status}</option>
            {/each}
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Search</label>
          <input
            type="text"
            bind:value={searchQuery}
            placeholder="Search errors..."
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            on:input={() => loadData()}
          />
        </div>
      </div>
    </div>

    <!-- Errors List -->
    {#if loading}
      <LoadingSpinner />
    {:else if errors.length === 0}
      <EmptyState
        title="No Errors Found"
        message="No errors match your current filters. Try adjusting your filters or check back later."
      />
    {:else}
      <div class="space-y-4">
        {#each errors as err}
          <div class="bg-white rounded-lg shadow p-4 hover:shadow-md transition-shadow">
            <div class="flex items-start justify-between mb-2">
              <div class="flex items-center gap-2 flex-wrap">
                <span class="px-2 py-1 rounded text-xs font-medium bg-purple-100 text-purple-800">
                  {err.component}
                </span>
                <span class="px-2 py-1 rounded text-xs font-medium {getSeverityColor(err.severity)} text-white">
                  {err.severity}
                </span>
                <span class="px-2 py-1 rounded text-xs font-medium {getStatusColor(err.status)} text-white">
                  {err.status}
                </span>
                {#if err.count > 1}
                  <span class="px-2 py-1 rounded text-xs font-medium bg-gray-100 text-gray-800">
                    {err.count}x
                  </span>
                {/if}
              </div>
              <div class="text-xs text-gray-500">
                {formatRelativeTime(err.created_at)}
              </div>
            </div>
            
            <div class="mb-2">
              <div class="text-sm font-medium text-gray-800 mb-1">{err.error_type}</div>
              <p class="text-sm text-gray-600 line-clamp-2">{err.message}</p>
            </div>
            
            <div class="flex items-center gap-2">
              <button
                on:click={() => handleViewDetails(String(err.id))}
                class="px-3 py-1.5 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
              >
                View Details
              </button>
              {#if err.status === 'open'}
                <button
                  on:click={() => { resolvingId = String(err.id); resolutionNotes = ''; }}
                  class="px-3 py-1.5 text-sm bg-green-600 text-white rounded hover:bg-green-700"
                >
                  Resolve
                </button>
              {/if}
            </div>
          </div>
        {/each}
      </div>

      <!-- Pagination -->
      {#if total > pageSize}
        <div class="mt-6 flex items-center justify-between">
          <div class="text-sm text-gray-600">
            Showing {(currentPage - 1) * pageSize + 1} to {Math.min(currentPage * pageSize, total)} of {total} errors
          </div>
          <div class="flex gap-2">
            <button
              on:click={() => {
                currentPage = Math.max(1, currentPage - 1);
                loadData();
              }}
              disabled={currentPage === 1}
              class="px-4 py-2 border border-gray-300 rounded-md disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
            >
              Previous
            </button>
            <button
              on:click={() => {
                currentPage = Math.min(Math.ceil(total / pageSize), currentPage + 1);
                loadData();
              }}
              disabled={currentPage >= Math.ceil(total / pageSize)}
              class="px-4 py-2 border border-gray-300 rounded-md disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
            >
              Next
            </button>
          </div>
        </div>
      {/if}
    {/if}
  {/if}
</div>

<!-- Error Details Modal -->
{#if showingDetails && selectedError}
  <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
    <div class="bg-white rounded-lg p-6 max-w-4xl w-full max-h-[90vh] overflow-y-auto">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-xl font-bold">Error Details</h2>
        <button
          on:click={() => { showingDetails = false; selectedError = null; }}
          class="text-gray-500 hover:text-gray-700"
        >
          ✕
        </button>
      </div>
      
      <div class="space-y-4">
        <div>
          <div class="text-sm font-medium text-gray-600 mb-1">Component</div>
          <div class="text-gray-800">{selectedError.component}</div>
        </div>
        
        <div>
          <div class="text-sm font-medium text-gray-600 mb-1">Error Type</div>
          <div class="text-gray-800 font-mono">{selectedError.error_type}</div>
        </div>
        
        <div>
          <div class="text-sm font-medium text-gray-600 mb-1">Message</div>
          <div class="text-gray-800">{selectedError.message}</div>
        </div>
        
        {#if selectedError.stack_trace}
          <div>
            <div class="text-sm font-medium text-gray-600 mb-1">Stack Trace</div>
            <pre class="bg-gray-100 p-3 rounded text-xs overflow-x-auto">{selectedError.stack_trace}</pre>
          </div>
        {/if}
        
        {#if selectedError.metadata}
          <div>
            <div class="text-sm font-medium text-gray-600 mb-1">Metadata</div>
            <pre class="bg-gray-100 p-3 rounded text-xs overflow-x-auto">{JSON.stringify(selectedError.metadata, null, 2)}</pre>
          </div>
        {/if}
        
        <div class="grid grid-cols-2 gap-4">
          <div>
            <div class="text-sm font-medium text-gray-600 mb-1">Severity</div>
            <span class="px-2 py-1 rounded text-sm {getSeverityColor(selectedError.severity)} text-white">
              {selectedError.severity}
            </span>
          </div>
          <div>
            <div class="text-sm font-medium text-gray-600 mb-1">Status</div>
            <span class="px-2 py-1 rounded text-sm {getStatusColor(selectedError.status)} text-white">
              {selectedError.status}
            </span>
          </div>
        </div>
        
        <div>
          <div class="text-sm font-medium text-gray-600 mb-1">Created At</div>
          <div class="text-gray-800">{formatDate(selectedError.created_at)}</div>
        </div>
        
        {#if selectedError.resolved_at}
          <div>
            <div class="text-sm font-medium text-gray-600 mb-1">Resolved At</div>
            <div class="text-gray-800">{formatDate(selectedError.resolved_at)}</div>
          </div>
        {/if}
        
        {#if selectedError.resolution_notes}
          <div>
            <div class="text-sm font-medium text-gray-600 mb-1">Resolution Notes</div>
            <div class="text-gray-800">{selectedError.resolution_notes}</div>
          </div>
        {/if}
        
        {#if selectedError.status === 'open'}
          <div class="pt-4 border-t">
            <button
              on:click={() => { resolvingId = String(selectedError.id); resolutionNotes = ''; showingDetails = false; }}
              class="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
            >
              Resolve Error
            </button>
          </div>
        {/if}
      </div>
    </div>
  </div>
{/if}

<!-- Resolve Modal -->
{#if resolvingId}
  <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
    <div class="bg-white rounded-lg p-6 max-w-md w-full mx-4">
      <h2 class="text-xl font-bold mb-4">Resolve Error</h2>
      <label class="block text-sm font-medium text-gray-700 mb-2">Resolution Notes (optional)</label>
      <textarea
        bind:value={resolutionNotes}
        class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 mb-4"
        rows="3"
        placeholder="Enter resolution notes..."
      ></textarea>
      <div class="flex justify-end gap-2">
        <button
          on:click={() => { resolvingId = null; resolutionNotes = ''; }}
          class="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
        >
          Cancel
        </button>
        <button
          on:click={handleResolve}
          class="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
        >
          Resolve
        </button>
      </div>
    </div>
  </div>
{/if}

<style>
  .line-clamp-2 {
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
</style>


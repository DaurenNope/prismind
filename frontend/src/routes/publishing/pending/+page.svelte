<script lang="ts">
  import { onMount } from 'svelte';
  import {
    fetchPendingApprovals,
    approveRewrite,
    rejectRewrite,
    bulkApproveRewrites,
    bulkRejectRewrites,
    updateRewriteContent,
    type PendingRewrite
  } from '$lib/services/publishing';
  import LoadingSpinner from '$lib/components/LoadingSpinner.svelte';
  import EmptyState from '$lib/components/EmptyState.svelte';

  let rewrites: PendingRewrite[] = [];
  let loading = true;
  let error: string | null = null;
  
  // Filters
  let personaFilter = 'all';
  let minQualityFilter = 0;
  
  // Pagination
  let currentPage = 1;
  let pageSize = 50;
  let total = 0;

  // Selection for bulk operations
  let selectedIds = new Set<number>();
  let selectAll = false;

  // Edit modal
  let editingId: number | null = null;
  let editingContent = '';

  // Reject modal
  let rejectingId: number | null = null;
  let rejectionReason = '';

  const personas = ['qronoya', 'aspandead', 'beyondlines'];

  const loadData = async () => {
    loading = true;
    error = null;
    try {
      const offset = (currentPage - 1) * pageSize;
      
      const data = await fetchPendingApprovals({
        persona: personaFilter === 'all' ? undefined : personaFilter,
        minQuality: minQualityFilter > 0 ? minQualityFilter : undefined,
        limit: pageSize,
        offset
      });

      rewrites = data.rewrites;
      total = data.total;
      selectedIds.clear();
      selectAll = false;
    } catch (err) {
      error = err instanceof Error ? err.message : 'Failed to load pending approvals';
      console.error('Error loading pending approvals:', err);
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

  const getQualityColor = (score?: number) => {
    if (!score) return 'bg-gray-500';
    if (score >= 0.8) return 'bg-green-500';
    if (score >= 0.6) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  const handleApprove = async (id: number) => {
    try {
      await approveRewrite(id);
      await loadData();
    } catch (err) {
      error = err instanceof Error ? err.message : 'Failed to approve rewrite';
    }
  };

  const handleReject = async () => {
    if (!rejectingId) return;
    try {
      await rejectRewrite(rejectingId, rejectionReason || undefined);
      rejectingId = null;
      rejectionReason = '';
      await loadData();
    } catch (err) {
      error = err instanceof Error ? err.message : 'Failed to reject rewrite';
    }
  };

  const handleBulkApprove = async () => {
    if (selectedIds.size === 0) return;
    try {
      await bulkApproveRewrites(Array.from(selectedIds));
      await loadData();
    } catch (err) {
      error = err instanceof Error ? err.message : 'Failed to bulk approve rewrites';
    }
  };

  const handleBulkReject = async () => {
    if (selectedIds.size === 0) return;
    try {
      const requests = Array.from(selectedIds).map(id => ({ id, reason: rejectionReason || undefined }));
      await bulkRejectRewrites(requests);
      rejectingId = null;
      rejectionReason = '';
      await loadData();
    } catch (err) {
      error = err instanceof Error ? err.message : 'Failed to bulk reject rewrites';
    }
  };

  const handleEdit = async () => {
    if (!editingId) return;
    try {
      await updateRewriteContent(editingId, editingContent);
      editingId = null;
      editingContent = '';
      await loadData();
    } catch (err) {
      error = err instanceof Error ? err.message : 'Failed to update rewrite';
    }
  };

  const toggleSelect = (id: number) => {
    if (selectedIds.has(id)) {
      selectedIds.delete(id);
    } else {
      selectedIds.add(id);
    }
    selectAll = selectedIds.size === rewrites.length;
  };

  const toggleSelectAll = () => {
    if (selectAll) {
      selectedIds.clear();
    } else {
      rewrites.forEach(r => selectedIds.add(r.id));
    }
    selectAll = !selectAll;
  };

  onMount(() => {
    loadData();
  });

  $: if (personaFilter || minQualityFilter) {
    currentPage = 1;
    loadData();
  }
</script>

<svelte:head>
  <title>Pending Approval Queue - Publishing</title>
</svelte:head>

<div class="container mx-auto px-4 py-8">
  <div class="mb-8">
    <h1 class="text-3xl font-bold mb-2">Pending Approval Queue</h1>
    <p class="text-gray-600">Review and approve rewrites waiting for posting</p>
  </div>

  {#if loading && rewrites.length === 0}
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
    <!-- Filters and Bulk Actions -->
    <div class="bg-white rounded-lg shadow p-4 mb-6">
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Persona</label>
          <select
            bind:value={personaFilter}
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">All Personas</option>
            {#each personas as persona}
              <option value={persona}>{persona}</option>
            {/each}
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Min Quality Score</label>
          <input
            type="number"
            min="0"
            max="1"
            step="0.1"
            bind:value={minQualityFilter}
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div class="flex items-end">
          <div class="text-sm text-gray-600">
            {total} pending {total === 1 ? 'rewrite' : 'rewrites'}
          </div>
        </div>
      </div>

      {#if selectedIds.size > 0}
        <div class="flex items-center gap-2 pt-4 border-t">
          <span class="text-sm text-gray-600">{selectedIds.size} selected</span>
          <button
            on:click={handleBulkApprove}
            class="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
          >
            Approve Selected
          </button>
          <button
            on:click={() => rejectingId = -1}
            class="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
          >
            Reject Selected
          </button>
          <button
            on:click={() => { selectedIds.clear(); selectAll = false; }}
            class="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
          >
            Clear Selection
          </button>
        </div>
      {/if}
    </div>

    <!-- Rewrites List -->
    {#if rewrites.length === 0}
      <EmptyState
        title="No Pending Approvals"
        message="All rewrites have been approved or there are no rewrites waiting for approval."
      />
    {:else}
      <div class="space-y-4">
        <div class="bg-white rounded-lg shadow p-4">
          <label class="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={selectAll}
              on:change={toggleSelectAll}
              class="w-4 h-4"
            />
            <span class="text-sm font-medium">Select All</span>
          </label>
        </div>

        {#each rewrites as rewrite}
          <div class="bg-white rounded-lg shadow p-4 hover:shadow-md transition-shadow">
            <div class="flex items-start gap-4 mb-3">
              <input
                type="checkbox"
                checked={selectedIds.has(rewrite.id)}
                on:change={() => toggleSelect(rewrite.id)}
                class="mt-1 w-4 h-4"
              />
              <div class="flex-1">
                <div class="flex items-center gap-2 mb-2">
                  <span class="px-2 py-1 rounded text-xs font-medium bg-purple-100 text-purple-800">
                    {rewrite.persona_key}
                  </span>
                  <span class="px-2 py-1 rounded text-xs font-medium bg-blue-100 text-blue-800">
                    {rewrite.platform}
                  </span>
                  <span class="text-xs text-gray-500">
                    {formatRelativeTime(rewrite.created_at)}
                  </span>
                </div>

                <!-- Quality Scores -->
                {#if rewrite.quality_score !== undefined || rewrite.voice_consistency_score !== undefined || rewrite.fact_preservation_score !== undefined}
                  <div class="flex items-center gap-4 mb-3 text-sm">
                    {#if rewrite.quality_score !== undefined}
                      <div class="flex items-center gap-1">
                        <span class="text-gray-600">Quality:</span>
                        <span class="px-2 py-0.5 rounded text-xs font-medium {getQualityColor(rewrite.quality_score)} text-white">
                          {(rewrite.quality_score * 100).toFixed(0)}%
                        </span>
                      </div>
                    {/if}
                    {#if rewrite.voice_consistency_score !== undefined}
                      <div class="flex items-center gap-1">
                        <span class="text-gray-600">Voice:</span>
                        <span class="px-2 py-0.5 rounded text-xs font-medium {getQualityColor(rewrite.voice_consistency_score)} text-white">
                          {(rewrite.voice_consistency_score * 100).toFixed(0)}%
                        </span>
                      </div>
                    {/if}
                    {#if rewrite.fact_preservation_score !== undefined}
                      <div class="flex items-center gap-1">
                        <span class="text-gray-600">Fact:</span>
                        <span class="px-2 py-0.5 rounded text-xs font-medium {getQualityColor(rewrite.fact_preservation_score)} text-white">
                          {(rewrite.fact_preservation_score * 100).toFixed(0)}%
                        </span>
                      </div>
                    {/if}
                  </div>
                {/if}

                <!-- Content -->
                <p class="text-gray-800 mb-3 whitespace-pre-wrap">{rewrite.content}</p>

                <!-- Original Post Context -->
                {#if rewrite.original_post}
                  <div class="mb-3 p-2 bg-gray-50 rounded border border-gray-200">
                    <div class="text-xs text-gray-600 mb-1">Original Post:</div>
                    <p class="text-sm text-gray-700 line-clamp-2">{rewrite.original_post.content || 'N/A'}</p>
                  </div>
                {/if}

                <!-- Actions -->
                <div class="flex items-center gap-2">
                  <button
                    on:click={() => { editingId = rewrite.id; editingContent = rewrite.content; }}
                    class="px-3 py-1.5 text-sm bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
                  >
                    Edit
                  </button>
                  <button
                    on:click={() => handleApprove(rewrite.id)}
                    class="px-3 py-1.5 text-sm bg-green-600 text-white rounded hover:bg-green-700"
                  >
                    Approve
                  </button>
                  <button
                    on:click={() => { rejectingId = rewrite.id; rejectionReason = ''; }}
                    class="px-3 py-1.5 text-sm bg-red-600 text-white rounded hover:bg-red-700"
                  >
                    Reject
                  </button>
                </div>
              </div>
            </div>
          </div>
        {/each}
      </div>

      <!-- Pagination -->
      {#if total > pageSize}
        <div class="mt-6 flex items-center justify-between">
          <div class="text-sm text-gray-600">
            Showing {(currentPage - 1) * pageSize + 1} to {Math.min(currentPage * pageSize, total)} of {total} rewrites
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

<!-- Edit Modal -->
{#if editingId}
  <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
    <div class="bg-white rounded-lg p-6 max-w-2xl w-full mx-4 max-h-[80vh] overflow-y-auto">
      <h2 class="text-xl font-bold mb-4">Edit Rewrite</h2>
      <textarea
        bind:value={editingContent}
        class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 mb-4"
        rows="10"
      ></textarea>
      <div class="flex justify-end gap-2">
        <button
          on:click={() => { editingId = null; editingContent = ''; }}
          class="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
        >
          Cancel
        </button>
        <button
          on:click={handleEdit}
          class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          Save
        </button>
      </div>
    </div>
  </div>
{/if}

<!-- Reject Modal -->
{#if rejectingId}
  <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
    <div class="bg-white rounded-lg p-6 max-w-md w-full mx-4">
      <h2 class="text-xl font-bold mb-4">
        {rejectingId === -1 ? 'Reject Selected Rewrites' : 'Reject Rewrite'}
      </h2>
      <label class="block text-sm font-medium text-gray-700 mb-2">Rejection Reason (optional)</label>
      <textarea
        bind:value={rejectionReason}
        class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 mb-4"
        rows="3"
        placeholder="Enter reason for rejection..."
      ></textarea>
      <div class="flex justify-end gap-2">
        <button
          on:click={() => { rejectingId = null; rejectionReason = ''; }}
          class="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
        >
          Cancel
        </button>
        <button
          on:click={rejectingId === -1 ? handleBulkReject : handleReject}
          class="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
        >
          Reject
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


<script lang="ts">
  import { onMount } from 'svelte';
  import { fetchPublishedPosts, fetchPublishedPostStats, type PublishedPost, type PublishedPostsStats } from '$lib/services/publishing';
  import LoadingSpinner from '$lib/components/LoadingSpinner.svelte';
  import EmptyState from '$lib/components/EmptyState.svelte';

  let posts: PublishedPost[] = [];
  let stats: PublishedPostsStats | null = null;
  let loading = true;
  let error: string | null = null;
  
  // Filters
  let platformFilter = 'all';
  let statusFilter = 'all';
  let dateRange: '24h' | '7d' | '30d' | 'all' = '7d';
  
  // Pagination
  let currentPage = 1;
  let pageSize = 50;
  let total = 0;

  const platforms = ['twitter', 'threads', 'telegram'];
  const statuses = ['posted', 'failed'];

  const getDateRange = () => {
    const now = new Date();
    let startDate: Date;
    
    switch (dateRange) {
      case '24h':
        startDate = new Date(now.getTime() - 24 * 60 * 60 * 1000);
        break;
      case '7d':
        startDate = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
        break;
      case '30d':
        startDate = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
        break;
      default:
        startDate = new Date(0); // All time
    }
    
    return {
      startDate: dateRange === 'all' ? undefined : startDate.toISOString(),
      endDate: dateRange === 'all' ? undefined : now.toISOString()
    };
  };

  const loadData = async () => {
    loading = true;
    error = null;
    try {
      const dateRangeParams = getDateRange();
      const offset = (currentPage - 1) * pageSize;
      
      const [postsData, statsData] = await Promise.all([
        fetchPublishedPosts({
          platform: platformFilter === 'all' ? undefined : platformFilter,
          status: statusFilter === 'all' ? undefined : statusFilter,
          startDate: dateRangeParams.startDate,
          endDate: dateRangeParams.endDate,
          limit: pageSize,
          offset
        }),
        fetchPublishedPostStats()
      ]);

      posts = postsData.posts;
      total = postsData.total;
      stats = statsData;
    } catch (err) {
      error = err instanceof Error ? err.message : 'Failed to load published posts';
      console.error('Error loading published posts:', err);
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

  const getPlatformColor = (platform: string) => {
    const colors: Record<string, string> = {
      twitter: 'bg-blue-500',
      threads: 'bg-black',
      telegram: 'bg-blue-400'
    };
    return colors[platform] || 'bg-gray-500';
  };

  const getStatusColor = (status?: string) => {
    if (!status || status === 'posted') return 'bg-green-500';
    if (status === 'failed') return 'bg-red-500';
    return 'bg-gray-500';
  };

  onMount(() => {
    loadData();
  });

  $: if (platformFilter || statusFilter || dateRange) {
    currentPage = 1;
    loadData();
  }
</script>

<svelte:head>
  <title>Published Posts - Publishing</title>
</svelte:head>

<div class="container mx-auto px-4 py-8">
  <div class="mb-8">
    <h1 class="text-3xl font-bold mb-2">Published Posts</h1>
    <p class="text-gray-600">View all posts that have been published to platforms</p>
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
          <div class="text-sm text-gray-600 mb-1">Total Published</div>
          <div class="text-2xl font-bold">{stats.total_published}</div>
        </div>
        <div class="bg-white rounded-lg shadow p-4">
          <div class="text-sm text-gray-600 mb-1">Success Rate</div>
          <div class="text-2xl font-bold">{(stats.success_rate * 100).toFixed(1)}%</div>
        </div>
        <div class="bg-white rounded-lg shadow p-4">
          <div class="text-sm text-gray-600 mb-1">Last 24h</div>
          <div class="text-2xl font-bold">{stats.last_24h}</div>
        </div>
        <div class="bg-white rounded-lg shadow p-4">
          <div class="text-sm text-gray-600 mb-1">Last 7 Days</div>
          <div class="text-2xl font-bold">{stats.last_7d}</div>
        </div>
      </div>

      <!-- Platform Breakdown -->
      <div class="bg-white rounded-lg shadow p-4 mb-6">
        <h2 class="text-lg font-semibold mb-3">By Platform</h2>
        <div class="flex gap-4">
          {#each Object.entries(stats.by_platform) as [platform, count]}
            <div class="flex items-center gap-2">
              <span class="px-2 py-1 rounded text-sm font-medium {getPlatformColor(platform)} text-white">
                {platform}
              </span>
              <span class="text-gray-700">{count}</span>
            </div>
          {/each}
        </div>
      </div>
    {/if}

    <!-- Filters -->
    <div class="bg-white rounded-lg shadow p-4 mb-6">
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Platform</label>
          <select
            bind:value={platformFilter}
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">All Platforms</option>
            {#each platforms as platform}
              <option value={platform}>{platform.charAt(0).toUpperCase() + platform.slice(1)}</option>
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
              <option value={status}>{status.charAt(0).toUpperCase() + status.slice(1)}</option>
            {/each}
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Date Range</label>
          <select
            bind:value={dateRange}
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="24h">Last 24 Hours</option>
            <option value="7d">Last 7 Days</option>
            <option value="30d">Last 30 Days</option>
            <option value="all">All Time</option>
          </select>
        </div>
      </div>
    </div>

    <!-- Posts List -->
    {#if loading}
      <LoadingSpinner />
    {:else if posts.length === 0}
      <EmptyState
        title="No Published Posts"
        message="No posts match your current filters. Try adjusting your filters or check back later."
      />
    {:else}
      <div class="space-y-4">
        {#each posts as post}
          <div class="bg-white rounded-lg shadow p-4 hover:shadow-md transition-shadow">
            <div class="flex items-start justify-between mb-2">
              <div class="flex items-center gap-2">
                <span class="px-2 py-1 rounded text-xs font-medium {getPlatformColor(post.platform)} text-white">
                  {post.platform}
                </span>
                <span class="px-2 py-1 rounded text-xs font-medium {getStatusColor(post.status)} text-white">
                  {post.status || 'posted'}
                </span>
                {#if post.persona_key}
                  <span class="px-2 py-1 rounded text-xs font-medium bg-purple-100 text-purple-800">
                    {post.persona_key}
                  </span>
                {/if}
              </div>
              <div class="text-sm text-gray-500">
                {formatRelativeTime(post.posted_at)}
              </div>
            </div>
            
            <p class="text-gray-800 mb-3 line-clamp-2">{post.content}</p>
            
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-4 text-sm text-gray-600">
                {#if post.post_url}
                  <a
                    href={post.post_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    class="text-blue-600 hover:text-blue-800 underline"
                  >
                    View Post →
                  </a>
                {/if}
                {#if post.engagement}
                  <div class="flex items-center gap-3">
                    {#if post.engagement.likes !== undefined}
                      <span>❤️ {post.engagement.likes}</span>
                    {/if}
                    {#if post.engagement.replies !== undefined}
                      <span>💬 {post.engagement.replies}</span>
                    {/if}
                    {#if post.engagement.views !== undefined}
                      <span>👁️ {post.engagement.views}</span>
                    {/if}
                  </div>
                {/if}
              </div>
              <div class="text-xs text-gray-500">
                {formatDate(post.posted_at)}
              </div>
            </div>
            
            {#if post.error_message}
              <div class="mt-2 p-2 bg-red-50 border border-red-200 rounded text-sm text-red-800">
                Error: {post.error_message}
              </div>
            {/if}
          </div>
        {/each}
      </div>

      <!-- Pagination -->
      {#if total > pageSize}
        <div class="mt-6 flex items-center justify-between">
          <div class="text-sm text-gray-600">
            Showing {(currentPage - 1) * pageSize + 1} to {Math.min(currentPage * pageSize, total)} of {total} posts
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

<style>
  .line-clamp-2 {
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
</style>


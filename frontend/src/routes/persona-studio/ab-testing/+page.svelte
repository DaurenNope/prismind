<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';

  // Types for A/B testing
  interface ABTest {
    id: string;
    name: string;
    description: string;
    type: string;
    status: string;
    platform?: string;
    created_at: string;
    started_at?: string;
    variants: ABTestVariant[];
    winner?: string;
    confidence?: number;
    recommendation?: string;
  }

  interface ABTestVariant {
    variant: {
      id: string;
      name: string;
      type: string;
      description: string;
      traffic_allocation: number;
    };
    metrics: {
      total_requests: number;
      successful_generations: number;
      avg_quality_score: number;
      avg_voice_consistency: number;
      avg_personality_consistency: number;
      avg_engagement_score: number;
      conversion_rate: number;
    };
  }

  // State
  let activeTests: ABTest[] = [];
  let loading = true;
  let error = '';
  let selectedTest: ABTest | null = null;
  let showCreateModal = false;
  let showVariantModal = false;
  let currentTestId = '';

  // Form state
  let newTest = {
    name: '',
    description: '',
    type: 'prompt_strategy',
    platform: '',
    minSampleSize: 100,
    confidenceThreshold: 0.95
  };

  let newVariant = {
    name: '',
    description: '',
    config: {},
    variantType: 'treatment',
    trafficAllocation: 0.5
  };

  // Test types
  const testTypes = [
    { value: 'prompt_strategy', label: 'Prompt Strategy' },
    { value: 'personality_variation', label: 'Personality Variation' },
    { value: 'platform_optimization', label: 'Platform Optimization' },
    { value: 'engagement_hooks', label: 'Engagement Hooks' },
    { value: 'temperature_testing', label: 'Temperature Testing' }
  ];

  // Fetch active tests on mount
  onMount(async () => {
    await fetchActiveTests();
  });

  function toErrorMessage(err: unknown): string {
    return err instanceof Error ? err.message : String(err);
  }

  function normalizeTestPayload(raw: any): ABTest {
    const base = raw?.test ?? raw ?? {};
    return {
      id: base.id ?? '',
      name: base.name ?? '',
      description: base.description ?? '',
      type: base.type ?? '',
      status: base.status ?? 'draft',
      platform: base.platform ?? raw?.platform ?? '',
      created_at: base.created_at ?? new Date().toISOString(),
      started_at: base.started_at ?? raw?.started_at,
      variants: raw?.variants ?? base.variants ?? [],
      winner: raw?.winner ?? base.winner,
      confidence: raw?.confidence ?? base.confidence,
      recommendation: raw?.recommendation ?? base.recommendation ?? '',
    };
  }

  function handleOverlayKey(event: KeyboardEvent, onClose: () => void) {
    if (event.key === 'Escape' || event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      onClose();
    }
  }

  function handleDialogKey(event: KeyboardEvent, onClose: () => void) {
    if (event.key === 'Escape') {
      event.preventDefault();
      event.stopPropagation();
      onClose();
    }
  }

  async function fetchActiveTests() {
    try {
      loading = true;
      const response = await fetch('/api/personas/ab-tests/active');
      const data = await response.json();

      if (data.success) {
        const list = Array.isArray(data.active_tests) ? data.active_tests : [];
        activeTests = list.map(normalizeTestPayload);
      } else {
        error = 'Failed to fetch active tests';
      }
    } catch (err) {
      error = 'Error fetching tests: ' + toErrorMessage(err);
    } finally {
      loading = false;
    }
  }

  async function createTest() {
    try {
      const response = await fetch('/api/personas/ab-tests/create', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: newTest.name,
          description: newTest.description,
          test_type: newTest.type,
          platform: newTest.platform || null,
          min_sample_size: newTest.minSampleSize,
          confidence_threshold: newTest.confidenceThreshold
        })
      });

      const data = await response.json();
      if (data.success) {
        showCreateModal = false;
        resetTestForm();
        await fetchActiveTests();
        currentTestId = data.test_id;
        showVariantModal = true;
      } else {
        error = data.error || 'Failed to create test';
      }
    } catch (err) {
      error = 'Error creating test: ' + toErrorMessage(err);
    }
  }

  async function addVariant(testId: string) {
    try {
      const response = await fetch(`/api/personas/ab-tests/${testId}/variants`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: newVariant.name,
          description: newVariant.description,
          config: newVariant.config,
          variant_type: newVariant.variantType,
          traffic_allocation: newVariant.trafficAllocation
        })
      });

      const data = await response.json();
      if (data.success) {
        showVariantModal = false;
        resetVariantForm();
        await fetchActiveTests();
      } else {
        error = data.error || 'Failed to add variant';
      }
    } catch (err) {
      error = 'Error adding variant: ' + toErrorMessage(err);
    }
  }

  async function startTest(testId: string) {
    try {
      const response = await fetch(`/api/personas/ab-tests/${testId}/start`, {
        method: 'POST'
      });

      const data = await response.json();
      if (data.success) {
        await fetchActiveTests();
      } else {
        error = data.error || 'Failed to start test';
      }
    } catch (err) {
      error = 'Error starting test: ' + toErrorMessage(err);
    }
  }

  async function completeTest(testId: string) {
    if (!confirm('Are you sure you want to complete this test? This will stop data collection.')) {
      return;
    }

    try {
      const response = await fetch(`/api/personas/ab-tests/${testId}/complete`, {
        method: 'POST'
      });

      const data = await response.json();
      if (data.success) {
        await fetchActiveTests();
      } else {
        error = data.error || 'Failed to complete test';
      }
    } catch (err) {
      error = 'Error completing test: ' + toErrorMessage(err);
    }
  }

  async function viewTestDetails(testId: string) {
    try {
      const response = await fetch(`/api/personas/ab-tests/${testId}/results`);
      const data = await response.json();

      if (data.success) {
        selectedTest = normalizeTestPayload(data.results?.test ?? data.results);
      } else {
        error = data.error || 'Failed to fetch test details';
      }
    } catch (err) {
      error = 'Error fetching test details: ' + toErrorMessage(err);
    }
  }

  function getStatusColor(status: string) {
    switch (status) {
      case 'active': return 'text-green-600';
      case 'completed': return 'text-blue-600';
      case 'paused': return 'text-yellow-600';
      case 'draft': return 'text-gray-600';
      default: return 'text-gray-600';
    }
  }

  function getConfidenceColor(confidence: number) {
    if (confidence >= 0.95) return 'text-green-600';
    if (confidence >= 0.8) return 'text-yellow-600';
    return 'text-red-600';
  }

  function formatNumber(num: number, decimals: number = 2) {
    return num.toFixed(decimals);
  }

  function resetTestForm() {
    newTest = {
      name: '',
      description: '',
      type: 'prompt_strategy',
      platform: '',
      minSampleSize: 100,
      confidenceThreshold: 0.95
    };
  }

  function resetVariantForm() {
    newVariant = {
      name: '',
      description: '',
      config: {},
      variantType: 'treatment',
      trafficAllocation: 0.5
    };
  }
</script>

<div class="min-h-screen bg-gradient-to-br from-purple-50 via-pink-50 to-blue-50">
  <div class="container mx-auto px-4 py-8">
    <!-- Header -->
    <div class="mb-8">
      <h1 class="text-4xl font-bold bg-gradient-to-r from-purple-600 to-pink-600 bg-clip-text text-transparent mb-2">
        A/B Testing Studio
      </h1>
      <p class="text-gray-600">Optimize your personas with data-driven A/B testing</p>
    </div>

    <!-- Actions -->
    <div class="mb-6 flex gap-4">
      <button
        on:click={() => showCreateModal = true}
        class="px-6 py-2 bg-gradient-to-r from-purple-500 to-pink-500 text-white rounded-lg hover:from-purple-600 hover:to-pink-600 transition-all duration-200 font-medium"
      >
        🧪 Create New Test
      </button>
      <button
        on:click={fetchActiveTests}
        class="px-6 py-2 bg-white text-gray-700 rounded-lg hover:bg-gray-50 transition-all duration-200 font-medium border border-gray-200"
      >
        🔄 Refresh
      </button>
    </div>

    <!-- Error Display -->
    {#if error}
      <div class="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
        {error}
      </div>
    {/if}

    <!-- Loading State -->
    {#if loading}
      <div class="flex justify-center py-12">
        <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500"></div>
      </div>
    {:else if activeTests.length === 0}
      <div class="text-center py-12">
        <div class="text-6xl mb-4">🧪</div>
        <h3 class="text-xl font-semibold text-gray-800 mb-2">No Active A/B Tests</h3>
        <p class="text-gray-600 mb-6">Start optimizing your personas by creating your first A/B test</p>
        <button
          on:click={() => showCreateModal = true}
          class="px-6 py-2 bg-gradient-to-r from-purple-500 to-pink-500 text-white rounded-lg hover:from-purple-600 hover:to-pink-600 transition-all duration-200 font-medium"
        >
          Create Your First Test
        </button>
      </div>
    {:else}
      <!-- Active Tests Grid -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {#each activeTests as test}
          <div class="bg-white/80 backdrop-blur-sm rounded-xl p-6 border border-white/20 hover:shadow-lg transition-all duration-200">
            <div class="mb-4">
              <div class="flex justify-between items-start mb-2">
                <h3 class="text-lg font-semibold text-gray-800">{test.name}</h3>
                <span class="px-2 py-1 text-xs rounded-full {getStatusColor(test.status)} bg-opacity-10">
                  {test.status}
                </span>
              </div>
              <p class="text-sm text-gray-600 mb-2">{test.description}</p>
              <div class="flex gap-2 text-xs">
                <span class="px-2 py-1 bg-purple-100 text-purple-700 rounded">
                  {testTypes.find(t => t.value === test.type)?.label || test.type}
                </span>
                {#if test.platform}
                  <span class="px-2 py-1 bg-blue-100 text-blue-700 rounded">
                    {test.platform}
                  </span>
                {/if}
              </div>
            </div>

            <!-- Test Stats -->
            <div class="mb-4">
              <div class="text-sm text-gray-600 mb-2">
                {test.variants?.length || 0} variants
              </div>
              {#if test.winner}
                <div class="text-sm">
                  <span class="font-medium text-green-600">Winner:</span> {test.winner}
                </div>
              {/if}
              {#if test.confidence}
                <div class="text-sm">
                  <span class="font-medium">Confidence:</span>
                  <span class={getConfidenceColor(test.confidence)}>
                    {formatNumber(test.confidence * 100)}%
                  </span>
                </div>
              {/if}
            </div>

            <!-- Actions -->
            <div class="flex gap-2">
              <button
                on:click={() => viewTestDetails(test.id)}
                class="px-3 py-1 bg-purple-100 text-purple-700 rounded hover:bg-purple-200 transition-colors text-sm"
              >
                📊 Details
              </button>
              {#if test.status === 'active'}
                <button
                  on:click={() => completeTest(test.id)}
                  class="px-3 py-1 bg-blue-100 text-blue-700 rounded hover:bg-blue-200 transition-colors text-sm"
                >
                  🏁 Complete
                </button>
              {/if}
            </div>
          </div>
        {/each}
      </div>
    {/if}

    <!-- Selected Test Details Modal -->
    {#if selectedTest}
      <div
        class="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 z-50"
        role="button"
        tabindex="0"
        aria-label="Close test details"
        on:click={() => selectedTest = null}
        on:keydown={(event) => handleOverlayKey(event, () => selectedTest = null)}
      >
        <div
          class="bg-white rounded-xl p-6 max-w-2xl w-full max-h-[90vh] overflow-y-auto"
          role="dialog"
          aria-modal="true"
          aria-label="A/B test details"
          tabindex="-1"
          on:click|stopPropagation
          on:keydown={(event) => handleDialogKey(event, () => selectedTest = null)}
        >
          <div class="flex justify-between items-start mb-6">
            <h2 class="text-2xl font-bold text-gray-800">{selectedTest.name}</h2>
            <button
              on:click={() => selectedTest = null}
              class="text-gray-500 hover:text-gray-700 text-2xl"
            >
              ×
            </button>
          </div>

          <div class="space-y-6">
            <!-- Test Info -->
            <div>
              <h3 class="font-semibold text-gray-800 mb-2">Test Information</h3>
              <div class="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span class="text-gray-600">Type:</span> {selectedTest.type}
                </div>
                <div>
                  <span class="text-gray-600">Status:</span>
                  <span class="{getStatusColor(selectedTest.status)}">{selectedTest.status}</span>
                </div>
                <div>
                  <span class="text-gray-600">Created:</span> {new Date(selectedTest.created_at).toLocaleDateString()}
                </div>
                {#if selectedTest.started_at}
                  <div>
                    <span class="text-gray-600">Started:</span> {new Date(selectedTest.started_at).toLocaleDateString()}
                  </div>
                {/if}
              </div>
            </div>

            <!-- Variants Performance -->
            <div>
              <h3 class="font-semibold text-gray-800 mb-4">Variant Performance</h3>
              <div class="space-y-3">
                {#each selectedTest.variants as variant}
                  <div class="bg-gray-50 rounded-lg p-4">
                    <div class="flex justify-between items-center mb-2">
                      <div>
                        <span class="font-medium text-gray-800">{variant.variant.name}</span>
                        <span class="ml-2 px-2 py-1 text-xs bg-white rounded">
                          {variant.variant.type}
                        </span>
                      </div>
                      <div class="text-sm text-gray-600">
                        {formatNumber(variant.variant.traffic_allocation * 100)}% traffic
                      </div>
                    </div>

                    <div class="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
                      <div>
                        <span class="text-gray-600">Quality Score:</span>
                        <span class="font-medium">{formatNumber(variant.metrics.avg_quality_score)}</span>
                      </div>
                      <div>
                        <span class="text-gray-600">Voice Consistency:</span>
                        <span class="font-medium">{formatNumber(variant.metrics.avg_voice_consistency)}</span>
                      </div>
                      <div>
                        <span class="text-gray-600">Conversion Rate:</span>
                        <span class="font-medium">{formatNumber(variant.metrics.conversion_rate * 100)}%</span>
                      </div>
                      <div>
                        <span class="text-gray-600">Total Requests:</span>
                        <span class="font-medium">{variant.metrics.total_requests}</span>
                      </div>
                      <div>
                        <span class="text-gray-600">Successful:</span>
                        <span class="font-medium">{variant.metrics.successful_generations}</span>
                      </div>
                      <div>
                        <span class="text-gray-600">Engagement:</span>
                        <span class="font-medium">{formatNumber(variant.metrics.avg_engagement_score)}</span>
                      </div>
                    </div>
                  </div>
                {/each}
              </div>
            </div>
          </div>
        </div>
      </div>
    {/if}

    <!-- Create Test Modal -->
    {#if showCreateModal}
      <div
        class="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 z-50"
        role="button"
        tabindex="0"
        aria-label="Close create test modal"
        on:click={() => showCreateModal = false}
        on:keydown={(event) => handleOverlayKey(event, () => showCreateModal = false)}
      >
        <div
          class="bg-white rounded-xl p-6 max-w-md w-full"
          role="dialog"
          aria-modal="true"
          aria-label="Create test"
          tabindex="-1"
          on:click|stopPropagation
          on:keydown={(event) => handleDialogKey(event, () => showCreateModal = false)}
        >
          <h2 class="text-2xl font-bold text-gray-800 mb-6">Create New A/B Test</h2>

          <form on:submit|preventDefault={createTest} class="space-y-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1" for="ab-test-name">Test Name</label>
              <input
                id="ab-test-name"
                bind:value={newTest.name}
                type="text"
                required
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                placeholder="My Optimization Test"
              />
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1" for="ab-test-description">Description</label>
              <textarea
                id="ab-test-description"
                bind:value={newTest.description}
                required
                rows="3"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                placeholder="What does this test optimize?"
              ></textarea>
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1" for="ab-test-type">Test Type</label>
              <select
                id="ab-test-type"
                bind:value={newTest.type}
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus-border-transparent"
              >
                {#each testTypes as type}
                  <option value={type.value}>{type.label}</option>
                {/each}
              </select>
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1" for="ab-test-platform">Platform (Optional)</label>
              <input
                id="ab-test-platform"
                bind:value={newTest.platform}
                type="text"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                placeholder="twitter, linkedin, threads, etc."
              />
            </div>

            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1" for="ab-test-sample">Min Sample Size</label>
                <input
                  id="ab-test-sample"
                  bind:value={newTest.minSampleSize}
                  type="number"
                  min="10"
                  class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus-border-transparent"
                />
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1" for="ab-test-confidence">Confidence Threshold</label>
                <input
                  id="ab-test-confidence"
                  bind:value={newTest.confidenceThreshold}
                  type="number"
                  min="0"
                  max="1"
                  step="0.05"
                  class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                />
              </div>
            </div>

            <div class="flex gap-3 pt-4">
              <button
                type="submit"
                class="flex-1 px-4 py-2 bg-gradient-to-r from-purple-500 to-pink-500 text-white rounded-lg hover:from-purple-600 hover:to-pink-600 transition-all duration-200 font-medium"
              >
                Create Test
              </button>
              <button
                type="button"
                on:click={() => {
                  showCreateModal = false;
                  resetTestForm();
                }}
                class="flex-1 px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors font-medium"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      </div>
    {/if}

    <!-- Add Variant Modal -->
    {#if showVariantModal}
      <div
        class="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 z-50"
        role="button"
        tabindex="0"
        aria-label="Close variant modal"
        on:click={() => showVariantModal = false}
        on:keydown={(event) => handleOverlayKey(event, () => showVariantModal = false)}
      >
        <div
          class="bg-white rounded-xl p-6 max-w-md w-full"
          role="dialog"
          aria-modal="true"
          aria-label="Add test variant"
          tabindex="-1"
          on:click|stopPropagation
          on:keydown={(event) => handleDialogKey(event, () => showVariantModal = false)}
        >
          <h2 class="text-2xl font-bold text-gray-800 mb-6">Add Test Variant</h2>

          <form on:submit|preventDefault={() => addVariant(currentTestId)} class="space-y-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1" for="variant-name">Variant Name</label>
              <input
                id="variant-name"
                bind:value={newVariant.name}
                type="text"
                required
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus-border-transparent"
                placeholder="Treatment Variant"
              />
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1" for="variant-description">Description</label>
              <textarea
                id="variant-description"
                bind:value={newVariant.description}
                required
                rows="3"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                placeholder="Describe this variant"
              ></textarea>
            </div>

            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1" for="variant-type">Type</label>
                <select
                  id="variant-type"
                  bind:value={newVariant.variantType}
                  class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                >
                  <option value="control">Control</option>
                  <option value="treatment">Treatment</option>
                </select>
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1" for="variant-traffic">Traffic %</label>
                <input
                  id="variant-traffic"
                  bind:value={newVariant.trafficAllocation}
                  type="number"
                  min="0"
                  max="1"
                  step="0.05"
                  class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                />
              </div>
            </div>

            <div class="flex gap-3 pt-4">
              <button
                type="submit"
                class="flex-1 px-4 py-2 bg-gradient-to-r from-purple-500 to-pink-500 text-white rounded-lg hover:from-purple-600 hover:to-pink-600 transition-all duration-200 font-medium"
              >
                Add Variant
              </button>
              <button
                type="button"
                on:click={() => {
                  showVariantModal = false;
                  resetVariantForm();
                }}
                class="flex-1 px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors font-medium"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      </div>
    {/if}
  </div>
</div>

<style>
  /* Glassmorphic background */
  .bg-white\/80 {
    background-color: rgba(255, 255, 255, 0.8);
    backdrop-filter: blur(10px);
  }
</style>
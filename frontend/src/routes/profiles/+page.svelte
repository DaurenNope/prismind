<script lang="ts">
  import { onMount } from 'svelte';
  import { API_BASE } from '$lib/config';
  import Toast from '$lib/components/Toast.svelte';

  interface Profile {
    key: string;
    name: string;
    handle?: string;
    platform: string;
    expertise: string[];
    created_at?: string;
  }

  interface ProfileFull extends Profile {
    voice_description?: string;
    platforms?: string[];
    filters?: Record<string, any>;
    quality_thresholds?: Record<string, any>;
    rewrite_preferences?: Record<string, any>;
    transformation_settings?: Record<string, any>;
    matching?: Record<string, any>;
  }

  let profiles: Profile[] = [];
  let loading = true;
  let error: string | null = null;
  let editingProfile: ProfileFull | null = null;
  let showCreateModal = false;
  let showEditModal = false;
  let toast: { message: string; type: 'success' | 'error' } | null = null;

  // Form data
  let formData: Partial<ProfileFull> = {
    key: '',
    name: '',
    handle: '',
    platform: 'twitter',
    voice_description: '',
    expertise: [],
    platforms: ['twitter', 'threads'],
    filters: {},
    quality_thresholds: {},
    rewrite_preferences: {},
    transformation_settings: {},
    matching: {}
  };

  let newExpertise = '';

  onMount(() => {
    loadProfiles();
  });

  async function loadProfiles() {
    loading = true;
    error = null;
    try {
      const res = await fetch(`${API_BASE}/api/profiles`);
      if (!res.ok) throw new Error(`Failed to load profiles: ${res.status}`);
      const data = await res.json();
      profiles = data.profiles || [];
    } catch (err) {
      error = err instanceof Error ? err.message : 'Failed to load profiles';
      showToast(error, 'error');
    } finally {
      loading = false;
    }
  }

  async function loadProfile(key: string): Promise<ProfileFull | null> {
    try {
      const res = await fetch(`${API_BASE}/api/profiles/${key}`);
      if (!res.ok) throw new Error(`Failed to load profile: ${res.status}`);
      return await res.json();
    } catch (err) {
      showToast(err instanceof Error ? err.message : 'Failed to load profile', 'error');
      return null;
    }
  }

  function openCreateModal() {
    formData = {
      key: '',
      name: '',
      handle: '',
      platform: 'twitter',
      voice_description: '',
      expertise: [],
      platforms: ['twitter', 'threads'],
      filters: {},
      quality_thresholds: {},
      rewrite_preferences: {},
      transformation_settings: {},
      matching: {}
    };
    newExpertise = '';
    showCreateModal = true;
  }

  async function openEditModal(profile: Profile) {
    const fullProfile = await loadProfile(profile.key);
    if (fullProfile) {
      editingProfile = fullProfile;
      formData = { ...fullProfile };
      newExpertise = '';
      showEditModal = true;
    }
  }

  async function createProfile() {
    if (!formData.key || !formData.name || !formData.voice_description) {
      showToast('Please fill in required fields (key, name, voice_description)', 'error');
      return;
    }

    try {
      const res = await fetch(`${API_BASE}/api/profiles`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || `Failed to create profile: ${res.status}`);
      }

      showToast('Profile created successfully', 'success');
      showCreateModal = false;
      await loadProfiles();
    } catch (err) {
      showToast(err instanceof Error ? err.message : 'Failed to create profile', 'error');
    }
  }

  async function updateProfile() {
    if (!editingProfile) return;

    try {
      const res = await fetch(`${API_BASE}/api/profiles/${editingProfile.key}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || `Failed to update profile: ${res.status}`);
      }

      showToast('Profile updated successfully', 'success');
      showEditModal = false;
      editingProfile = null;
      await loadProfiles();
    } catch (err) {
      showToast(err instanceof Error ? err.message : 'Failed to update profile', 'error');
    }
  }

  async function deleteProfile(key: string) {
    if (!confirm(`Are you sure you want to delete profile "${key}"? This cannot be undone.`)) {
      return;
    }

    try {
      const res = await fetch(`${API_BASE}/api/profiles/${key}`, {
        method: 'DELETE'
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || `Failed to delete profile: ${res.status}`);
      }

      showToast('Profile deleted successfully', 'success');
      await loadProfiles();
    } catch (err) {
      showToast(err instanceof Error ? err.message : 'Failed to delete profile', 'error');
    }
  }

  async function reloadProfile(key: string) {
    try {
      const res = await fetch(`${API_BASE}/api/profiles/${key}/reload`, {
        method: 'POST'
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || `Failed to reload profile: ${res.status}`);
      }

      showToast('Profile reloaded successfully', 'success');
      await loadProfiles();
    } catch (err) {
      showToast(err instanceof Error ? err.message : 'Failed to reload profile', 'error');
    }
  }

  function addExpertise() {
    if (newExpertise.trim() && formData.expertise) {
      formData.expertise = [...(formData.expertise || []), newExpertise.trim()];
      newExpertise = '';
    }
  }

  function removeExpertise(index: number) {
    if (formData.expertise) {
      formData.expertise = formData.expertise.filter((_, i) => i !== index);
    }
  }

  function showToast(message: string, type: 'success' | 'error') {
    toast = { message, type };
    setTimeout(() => (toast = null), 3000);
  }
</script>

<svelte:head>
  <title>BeyondLines · Profile Management</title>
  <meta name="description" content="Manage persona profiles" />
</svelte:head>

<div class="space-y-6">
  <section class="rounded-3xl border border-white/10 bg-[rgba(11,20,34,0.85)] backdrop-blur-xl p-6 space-y-5">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-semibold text-[color:var(--text-primary)]">Profile Management</h1>
        <p class="text-sm text-[color:var(--text-muted)] mt-1">
          Manage persona profiles for content matching and rewriting
        </p>
      </div>
      <button
        type="button"
        class="rounded-xl border border-[rgba(78,192,255,0.4)] bg-[linear-gradient(135deg,rgba(78,192,255,0.2),rgba(93,242,193,0.18))] px-4 py-2 text-sm font-semibold text-[color:var(--text-primary)] hover:shadow-[0_18px_60px_-24px_rgba(78,192,255,0.65)] transition-all"
        on:click={openCreateModal}
      >
        + Create Profile
      </button>
    </div>
  </section>

  {#if loading}
    <div class="text-center py-12 text-[color:var(--text-muted)]">Loading profiles...</div>
  {:else if error}
    <div class="rounded-3xl border border-red-500/20 bg-red-500/10 p-6 text-red-400">
      Error: {error}
    </div>
  {:else if profiles.length === 0}
    <div class="rounded-3xl border border-white/10 bg-[rgba(11,20,34,0.85)] p-12 text-center">
      <p class="text-[color:var(--text-muted)] mb-4">No profiles found</p>
      <button
        type="button"
        class="rounded-xl border border-[rgba(78,192,255,0.4)] bg-[rgba(78,192,255,0.15)] px-4 py-2 text-sm font-semibold"
        on:click={openCreateModal}
      >
        Create Your First Profile
      </button>
    </div>
  {:else}
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {#each profiles as profile}
        <div class="rounded-3xl border border-white/10 bg-[rgba(11,20,34,0.85)] backdrop-blur-xl p-6 space-y-4">
          <div class="flex items-start justify-between">
            <div>
              <h3 class="text-lg font-semibold text-[color:var(--text-primary)]">{profile.name}</h3>
              <p class="text-sm text-[color:var(--text-muted)]">@{profile.handle || profile.key}</p>
            </div>
            <span class="rounded-lg border border-white/10 bg-white/5 px-2 py-1 text-xs text-[color:var(--text-muted)]">
              {profile.platform}
            </span>
          </div>

          {#if profile.expertise && profile.expertise.length > 0}
            <div>
              <p class="text-xs text-[color:var(--text-muted)] mb-2">Expertise:</p>
              <div class="flex flex-wrap gap-2">
                {#each profile.expertise.slice(0, 3) as exp}
                  <span class="rounded-lg border border-white/10 bg-white/5 px-2 py-1 text-xs text-[color:var(--text-muted)]">
                    {exp}
                  </span>
                {/each}
                {#if profile.expertise.length > 3}
                  <span class="text-xs text-[color:var(--text-muted)]">+{profile.expertise.length - 3} more</span>
                {/if}
              </div>
            </div>
          {/if}

          <div class="flex gap-2 pt-2 border-t border-white/10">
            <button
              type="button"
              class="flex-1 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm font-medium text-[color:var(--text-primary)] hover:bg-white/10 transition-colors"
              on:click={() => openEditModal(profile)}
            >
              Edit
            </button>
            <button
              type="button"
              class="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm font-medium text-[color:var(--text-primary)] hover:bg-white/10 transition-colors"
              on:click={() => reloadProfile(profile.key)}
              title="Reload profile (refresh from file)"
            >
              ↻
            </button>
            <button
              type="button"
              class="rounded-lg border border-red-500/20 bg-red-500/10 px-3 py-2 text-sm font-medium text-red-400 hover:bg-red-500/20 transition-colors"
              on:click={() => deleteProfile(profile.key)}
            >
              Delete
            </button>
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>

<!-- Create Modal -->
{#if showCreateModal}
  <div class="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
    <div class="rounded-3xl border border-white/10 bg-[rgba(11,20,34,0.95)] backdrop-blur-xl p-6 max-w-2xl w-full max-h-[90vh] overflow-y-auto space-y-4">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-xl font-semibold text-[color:var(--text-primary)]">Create Profile</h2>
        <button
          type="button"
          class="text-[color:var(--text-muted)] hover:text-[color:var(--text-primary)]"
          on:click={() => (showCreateModal = false)}
        >
          ✕
        </button>
      </div>

      <div class="space-y-4">
        <div>
          <label for="create-key" class="block text-sm font-medium text-[color:var(--text-primary)] mb-2">
            Key <span class="text-red-400">*</span>
          </label>
          <input
            id="create-key"
            type="text"
            bind:value={formData.key}
            placeholder="e.g., my_profile"
            class="w-full rounded-lg border border-white/10 bg-white/5 px-4 py-2 text-[color:var(--text-primary)] focus:border-[rgba(78,192,255,0.4)] focus:outline-none"
          />
        </div>

        <div>
          <label for="create-name" class="block text-sm font-medium text-[color:var(--text-primary)] mb-2">
            Name <span class="text-red-400">*</span>
          </label>
          <input
            id="create-name"
            type="text"
            bind:value={formData.name}
            placeholder="Display name"
            class="w-full rounded-lg border border-white/10 bg-white/5 px-4 py-2 text-[color:var(--text-primary)] focus:border-[rgba(78,192,255,0.4)] focus:outline-none"
          />
        </div>

        <div>
          <label for="create-handle" class="block text-sm font-medium text-[color:var(--text-primary)] mb-2">
            Handle
          </label>
          <input
            id="create-handle"
            type="text"
            bind:value={formData.handle}
            placeholder="@username"
            class="w-full rounded-lg border border-white/10 bg-white/5 px-4 py-2 text-[color:var(--text-primary)] focus:border-[rgba(78,192,255,0.4)] focus:outline-none"
          />
        </div>

        <div>
          <label for="create-voice" class="block text-sm font-medium text-[color:var(--text-primary)] mb-2">
            Voice Description <span class="text-red-400">*</span>
          </label>
          <textarea
            id="create-voice"
            bind:value={formData.voice_description}
            placeholder="Describe the voice and style of this profile..."
            rows="4"
            class="w-full rounded-lg border border-white/10 bg-white/5 px-4 py-2 text-[color:var(--text-primary)] focus:border-[rgba(78,192,255,0.4)] focus:outline-none"
          ></textarea>
        </div>

        <div>
          <label for="create-expertise" class="block text-sm font-medium text-[color:var(--text-primary)] mb-2">
            Expertise
          </label>
          <div class="flex gap-2 mb-2">
            <input
              id="create-expertise"
              type="text"
              bind:value={newExpertise}
              placeholder="Add expertise area"
              on:keypress={(e) => e.key === 'Enter' && addExpertise()}
              class="flex-1 rounded-lg border border-white/10 bg-white/5 px-4 py-2 text-[color:var(--text-primary)] focus:border-[rgba(78,192,255,0.4)] focus:outline-none"
            />
            <button
              type="button"
              class="rounded-lg border border-white/10 bg-white/5 px-4 py-2 text-sm font-medium text-[color:var(--text-primary)] hover:bg-white/10 transition-colors"
              on:click={addExpertise}
            >
              Add
            </button>
          </div>
          {#if formData.expertise && formData.expertise.length > 0}
            <div class="flex flex-wrap gap-2">
              {#each formData.expertise as exp, i}
                <span class="rounded-lg border border-white/10 bg-white/5 px-2 py-1 text-sm text-[color:var(--text-primary)] flex items-center gap-2">
                  {exp}
                  <button
                    type="button"
                    class="text-red-400 hover:text-red-300"
                    on:click={() => removeExpertise(i)}
                  >
                    ×
                  </button>
                </span>
              {/each}
            </div>
          {/if}
        </div>
      </div>

      <div class="flex gap-3 pt-4 border-t border-white/10">
        <button
          type="button"
          class="flex-1 rounded-lg border border-[rgba(78,192,255,0.4)] bg-[rgba(78,192,255,0.15)] px-4 py-2 text-sm font-semibold text-[color:var(--text-primary)] hover:bg-[rgba(78,192,255,0.25)] transition-colors"
          on:click={createProfile}
        >
          Create
        </button>
        <button
          type="button"
          class="rounded-lg border border-white/10 bg-white/5 px-4 py-2 text-sm font-medium text-[color:var(--text-primary)] hover:bg-white/10 transition-colors"
          on:click={() => (showCreateModal = false)}
        >
          Cancel
        </button>
      </div>
    </div>
  </div>
{/if}

<!-- Edit Modal -->
{#if showEditModal && editingProfile}
  <div class="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
    <div class="rounded-3xl border border-white/10 bg-[rgba(11,20,34,0.95)] backdrop-blur-xl p-6 max-w-2xl w-full max-h-[90vh] overflow-y-auto space-y-4">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-xl font-semibold text-[color:var(--text-primary)]">
          Edit Profile: {editingProfile.name}
        </h2>
        <button
          type="button"
          class="text-[color:var(--text-muted)] hover:text-[color:var(--text-primary)]"
          on:click={() => {
            showEditModal = false;
            editingProfile = null;
          }}
        >
          ✕
        </button>
      </div>

      <div class="space-y-4">
        <div>
          <label for="edit-name" class="block text-sm font-medium text-[color:var(--text-primary)] mb-2">
            Name
          </label>
          <input
            id="edit-name"
            type="text"
            bind:value={formData.name}
            class="w-full rounded-lg border border-white/10 bg-white/5 px-4 py-2 text-[color:var(--text-primary)] focus:border-[rgba(78,192,255,0.4)] focus:outline-none"
          />
        </div>

        <div>
          <label for="edit-handle" class="block text-sm font-medium text-[color:var(--text-primary)] mb-2">
            Handle
          </label>
          <input
            id="edit-handle"
            type="text"
            bind:value={formData.handle}
            class="w-full rounded-lg border border-white/10 bg-white/5 px-4 py-2 text-[color:var(--text-primary)] focus:border-[rgba(78,192,255,0.4)] focus:outline-none"
          />
        </div>

        <div>
          <label for="edit-voice" class="block text-sm font-medium text-[color:var(--text-primary)] mb-2">
            Voice Description
          </label>
          <textarea
            id="edit-voice"
            bind:value={formData.voice_description}
            rows="4"
            class="w-full rounded-lg border border-white/10 bg-white/5 px-4 py-2 text-[color:var(--text-primary)] focus:border-[rgba(78,192,255,0.4)] focus:outline-none"
          ></textarea>
        </div>

        <div>
          <label for="edit-expertise" class="block text-sm font-medium text-[color:var(--text-primary)] mb-2">
            Expertise
          </label>
          <div class="flex gap-2 mb-2">
            <input
              id="edit-expertise"
              type="text"
              bind:value={newExpertise}
              placeholder="Add expertise area"
              on:keypress={(e) => e.key === 'Enter' && addExpertise()}
              class="flex-1 rounded-lg border border-white/10 bg-white/5 px-4 py-2 text-[color:var(--text-primary)] focus:border-[rgba(78,192,255,0.4)] focus:outline-none"
            />
            <button
              type="button"
              class="rounded-lg border border-white/10 bg-white/5 px-4 py-2 text-sm font-medium text-[color:var(--text-primary)] hover:bg-white/10 transition-colors"
              on:click={addExpertise}
            >
              Add
            </button>
          </div>
          {#if formData.expertise && formData.expertise.length > 0}
            <div class="flex flex-wrap gap-2">
              {#each formData.expertise as exp, i}
                <span class="rounded-lg border border-white/10 bg-white/5 px-2 py-1 text-sm text-[color:var(--text-primary)] flex items-center gap-2">
                  {exp}
                  <button
                    type="button"
                    class="text-red-400 hover:text-red-300"
                    on:click={() => removeExpertise(i)}
                  >
                    ×
                  </button>
                </span>
              {/each}
            </div>
          {/if}
        </div>
      </div>

      <div class="flex gap-3 pt-4 border-t border-white/10">
        <button
          type="button"
          class="flex-1 rounded-lg border border-[rgba(78,192,255,0.4)] bg-[rgba(78,192,255,0.15)] px-4 py-2 text-sm font-semibold text-[color:var(--text-primary)] hover:bg-[rgba(78,192,255,0.25)] transition-colors"
          on:click={updateProfile}
        >
          Save Changes
        </button>
        <button
          type="button"
          class="rounded-lg border border-white/10 bg-white/5 px-4 py-2 text-sm font-medium text-[color:var(--text-primary)] hover:bg-white/10 transition-colors"
          on:click={() => {
            showEditModal = false;
            editingProfile = null;
          }}
        >
          Cancel
        </button>
      </div>
    </div>
  </div>
{/if}

{#if toast}
  <Toast message={toast.message} tone={toast.type} />
{/if}

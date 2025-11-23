<script lang="ts">
  import { onMount } from 'svelte';
  import { fetchCredentials, saveCredentials, type PlatformCredentials } from '$lib/services/settings';
  import Toast from '$lib/components/Toast.svelte';

  const defaultPlatforms: PlatformCredentials[] = [
    {
      platform: 'threads',
      enabled: true
    },
    {
      platform: 'twitter',
      enabled: true
    },
    {
      platform: 'reddit',
      enabled: true
    },
    {
      platform: 'telegram',
      enabled: false
    }
  ];

  let configs: PlatformCredentials[] = [...defaultPlatforms];
  let activeTab = 'credentials';
  let toast: { message: string; type: 'success' | 'error' } | null = null;
  let loading = false;
  let loadingInitial = true;
  let error: string | null = null;
  let savingPlatforms = new Set<string>();
  let validationErrors: Record<string, string> = {};

  onMount(async () => {
    await loadConfigs();
  });

  // Real-time validation
  function validateField(platform: string, field: string, value: string | undefined): string | null {
    const key = `${platform}-${field}`;
    
    if (!value || value.trim() === '') {
      // Only validate required fields when enabled
      const config = configs.find(c => c.platform === platform);
      if (config?.enabled) {
        if (field === 'username' && (platform === 'threads' || platform === 'twitter' || platform === 'reddit')) {
          return 'Username is required when platform is enabled';
        }
        if (field === 'password' && (platform === 'threads' || platform === 'twitter' || platform === 'reddit')) {
          return 'Password is required when platform is enabled';
        }
        if (field === 'clientId' && platform === 'reddit') {
          return 'Client ID is required for Reddit';
        }
        if (field === 'clientSecret' && platform === 'reddit') {
          return 'Client Secret is required for Reddit';
        }
        if (field === 'accessToken' && platform === 'telegram') {
          return 'Bot Token is required for Telegram';
        }
      }
    }
    
    // Additional validation
    if (value) {
      if (field === 'username' && value.length < 2) {
        return 'Username must be at least 2 characters';
      }
      if (field === 'password' && value.length < 4) {
        return 'Password must be at least 4 characters';
      }
      if (field === 'accessToken' && platform === 'telegram' && !value.startsWith('')) {
        // Telegram tokens are typically long strings, just check length
        if (value.length < 20) {
          return 'Telegram bot token appears invalid';
        }
      }
    }
    
    return null;
  }

  function clearValidationError(platform: string, field: string) {
    const key = `${platform}-${field}`;
    delete validationErrors[key];
    validationErrors = { ...validationErrors };
  }

  async function loadConfigs() {
    loadingInitial = true;
    error = null;
    try {
      const saved = await fetchCredentials();
      if (saved && saved.length > 0) {
        // Merge with defaults to ensure all platforms are present
        const platformMap = new Map(saved.map(c => [c.platform, c]));
        configs = defaultPlatforms.map(defaultConfig => {
          const savedConfig = platformMap.get(defaultConfig.platform);
          return savedConfig || defaultConfig;
        });
      } else {
        // No saved configs, use defaults
        configs = [...defaultPlatforms];
      }
    } catch (e) {
      console.error('Failed to load configs:', e);
      error = e instanceof Error ? e.message : 'Failed to load credentials from server';
      // Fallback to localStorage for offline mode
      try {
        const saved = localStorage.getItem('beyondlines_configs');
        if (saved) {
          configs = JSON.parse(saved);
        }
      } catch (localError) {
        // If both fail, use defaults
        configs = [...defaultPlatforms];
      }
    } finally {
      loadingInitial = false;
    }
  }

  async function saveConfig(platform: string, config: Partial<PlatformCredentials>) {
    // Clear validation errors for this platform
    Object.keys(validationErrors).forEach(key => {
      if (key.startsWith(`${platform}-`)) {
        delete validationErrors[key];
      }
    });
    validationErrors = { ...validationErrors };
    
    // Validate before saving
    const index = configs.findIndex((c) => c.platform === platform);
    if (index >= 0) {
      const updatedConfig = { ...configs[index], ...config };
      
      // Validate all fields
      const fieldsToValidate: Array<{ field: string; value: string | undefined }> = [];
      if (updatedConfig.enabled) {
        if (platform === 'threads' || platform === 'twitter' || platform === 'reddit') {
          fieldsToValidate.push({ field: 'username', value: updatedConfig.username });
          fieldsToValidate.push({ field: 'password', value: updatedConfig.password });
        }
        if (platform === 'reddit') {
          fieldsToValidate.push({ field: 'clientId', value: updatedConfig.clientId });
          fieldsToValidate.push({ field: 'clientSecret', value: updatedConfig.clientSecret });
        }
        if (platform === 'telegram') {
          fieldsToValidate.push({ field: 'accessToken', value: updatedConfig.accessToken });
        }
      }
      
      // Check for validation errors
      for (const { field, value } of fieldsToValidate) {
        const error = validateField(platform, field, value);
        if (error) {
          validationErrors[`${platform}-${field}`] = error;
        }
      }
      
      // If there are validation errors, don't save
      const hasErrors = Object.keys(validationErrors).some(key => key.startsWith(`${platform}-`));
      if (hasErrors) {
        validationErrors = { ...validationErrors };
        toast = { 
          message: `Please fix validation errors for ${platform}`, 
          type: 'error' 
        };
        setTimeout(() => (toast = null), 5000);
        return;
      }
    }
    
    savingPlatforms.add(platform);
    loading = true;
    error = null;
    
    try {
      if (index >= 0) {
        // Update local state optimistically
        configs[index] = { ...configs[index], ...config };
      }

      // Save to backend API
      const credentialsToSave: PlatformCredentials = {
        platform,
        ...configs[index],
        ...config
      };

      await saveCredentials(credentialsToSave);

      // Also save to localStorage as backup
      try {
        localStorage.setItem('beyondlines_configs', JSON.stringify(configs));
      } catch (localError) {
        console.warn('Failed to save to localStorage:', localError);
      }

      toast = { message: `${platform} credentials saved successfully`, type: 'success' };
      setTimeout(() => (toast = null), 3000);
    } catch (e) {
      const errorMessage = e instanceof Error ? e.message : 'Failed to save credentials';
      error = errorMessage;
      toast = { 
        message: `Failed to save ${platform} config: ${errorMessage}`, 
        type: 'error' 
      };
      setTimeout(() => (toast = null), 5000);
      
      // Revert optimistic update on error
      await loadConfigs();
    } finally {
      loading = false;
      savingPlatforms.delete(platform);
    }
  }

  function handleFileUpload(platform: string, event: Event) {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = async (e) => {
      try {
        const content = e.target?.result as string;
        // In production, upload to backend storage
        const cookiePath = `config/${platform}_cookies.json`;
        await saveConfig(platform, { cookieFile: cookiePath });
        toast = { message: `Cookie file uploaded for ${platform}`, type: 'success' };
        setTimeout(() => (toast = null), 3000);
      } catch (err) {
        toast = { 
          message: `Failed to upload cookie file: ${err instanceof Error ? err.message : 'Unknown error'}`, 
          type: 'error' 
        };
        setTimeout(() => (toast = null), 5000);
      }
    };
    reader.onerror = () => {
      toast = { message: 'Failed to read cookie file', type: 'error' };
      setTimeout(() => (toast = null), 5000);
    };
    reader.readAsText(file);
  }
</script>

<div class="space-y-8">
  <div class="rounded-3xl border border-white/8 bg-[rgba(13,23,37,0.85)] backdrop-blur-xl p-8 shadow-[0_30px_100px_-70px_rgba(78,192,255,0.55)]">
    <div class="mb-6">
      <h1 class="text-3xl font-semibold text-[color:var(--text-primary)] mb-2">Settings</h1>
      <p class="text-sm text-[color:var(--text-muted)]">Manage authentication credentials and platform configurations</p>
    </div>

    {#if error && !loadingInitial}
      <div class="mb-6 rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-red-400 text-sm">
        <p class="font-semibold mb-1">Error loading settings</p>
        <p>{error}</p>
        <button
          on:click={() => loadConfigs()}
          class="mt-2 text-xs underline hover:no-underline"
        >
          Retry
        </button>
      </div>
    {/if}

    {#if loadingInitial}
      <div class="mb-6 rounded-xl border border-white/10 bg-white/5 p-6 text-center">
        <p class="text-[color:var(--text-muted)]">Loading settings...</p>
      </div>
    {/if}

    <div class="flex gap-2 mb-8 border-b border-white/10">
      <button
        class={`px-6 py-3 text-sm font-semibold transition-colors border-b-2 ${
          activeTab === 'credentials'
            ? 'border-[rgba(93,242,193,0.85)] text-[color:var(--text-primary)]'
            : 'border-transparent text-[color:var(--text-muted)] hover:text-[color:var(--text-primary)]'
        }`}
        on:click={() => (activeTab = 'credentials')}
      >
        Credentials
      </button>
      <button
        class={`px-6 py-3 text-sm font-semibold transition-colors border-b-2 ${
          activeTab === 'automation'
            ? 'border-[rgba(93,242,193,0.85)] text-[color:var(--text-primary)]'
            : 'border-transparent text-[color:var(--text-muted)] hover:text-[color:var(--text-primary)]'
        }`}
        on:click={() => (activeTab = 'automation')}
      >
        Automation
      </button>
      <button
        class={`px-6 py-3 text-sm font-semibold transition-colors border-b-2 ${
          activeTab === 'advanced'
            ? 'border-[rgba(93,242,193,0.85)] text-[color:var(--text-primary)]'
            : 'border-transparent text-[color:var(--text-muted)] hover:text-[color:var(--text-primary)]'
        }`}
        on:click={() => (activeTab = 'advanced')}
      >
        Advanced
      </button>
    </div>

    {#if activeTab === 'credentials'}
      {#if loadingInitial}
        <div class="space-y-6">
          {#each defaultPlatforms as config (config.platform)}
            <div class="rounded-2xl border border-white/10 bg-[rgba(15,29,46,0.85)] p-6 animate-pulse">
              <div class="h-20 bg-white/5 rounded"></div>
            </div>
          {/each}
        </div>
      {:else}
        <div class="space-y-6">
          {#each configs as config (config.platform)}
          <div class="rounded-2xl border border-white/10 bg-[rgba(15,29,46,0.85)] p-6">
            <div class="flex items-center justify-between mb-4">
              <div>
                <h3 class="text-lg font-semibold text-[color:var(--text-primary)] capitalize">{config.platform}</h3>
                <p class="text-xs text-[color:var(--text-muted)] mt-1">Configure {config.platform} authentication</p>
              </div>
              <label class="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={config.enabled}
                  on:change={(e) => saveConfig(config.platform, { enabled: e.currentTarget.checked })}
                  class="sr-only peer"
                />
                <div class="w-11 h-6 bg-white/10 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white peer-checked:bg-[rgba(93,242,193,0.85)] after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all"></div>
              </label>
            </div>

            {#if config.enabled}
              <div class="space-y-4 mt-6">
                {#if config.platform === 'threads' || config.platform === 'twitter'}
                  <div>
                    <label for="{config.platform}-username" class="block text-xs font-semibold text-[color:var(--text-muted)] mb-2 uppercase tracking-wider">
                      Username
                    </label>
                    <input
                      id="{config.platform}-username"
                      type="text"
                      bind:value={config.username}
                      disabled={savingPlatforms.has(config.platform)}
                      on:blur={() => {
                        clearValidationError(config.platform, 'username');
                        saveConfig(config.platform, { username: config.username });
                      }}
                      on:input={() => clearValidationError(config.platform, 'username')}
                      placeholder="Enter username"
                      class="w-full px-4 py-3 rounded-xl border ${
                        validationErrors[`${config.platform}-username`] 
                          ? 'border-red-500/50 bg-red-500/5' 
                          : 'border-white/10 bg-white/5'
                      } text-[color:var(--text-primary)] placeholder:text-[color:var(--text-muted)]/50 focus:outline-none focus:border-[rgba(93,242,193,0.5)] focus:ring-2 focus:ring-[rgba(93,242,193,0.2)] transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                    />
                    {#if validationErrors[`${config.platform}-username`]}
                      <p class="text-xs text-red-400 mt-1">{validationErrors[`${config.platform}-username`]}</p>
                    {/if}
                  </div>
                  <div>
                    <label for="{config.platform}-password" class="block text-xs font-semibold text-[color:var(--text-muted)] mb-2 uppercase tracking-wider">
                      Password
                    </label>
                    <input
                      id="{config.platform}-password"
                      type="password"
                      bind:value={config.password}
                      disabled={savingPlatforms.has(config.platform)}
                      on:blur={() => saveConfig(config.platform, { password: config.password })}
                      placeholder="Enter password"
                      class="w-full px-4 py-3 rounded-xl border border-white/10 bg-white/5 text-[color:var(--text-primary)] placeholder:text-[color:var(--text-muted)]/50 focus:outline-none focus:border-[rgba(93,242,193,0.5)] focus:ring-2 focus:ring-[rgba(93,242,193,0.2)] transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                    />
                  </div>
                  <div>
                    <label for="{config.platform}-cookies" class="block text-xs font-semibold text-[color:var(--text-muted)] mb-2 uppercase tracking-wider">
                      Cookie File
                    </label>
                    <div class="flex gap-3">
                      <input
                        id="{config.platform}-cookies"
                        type="file"
                        accept=".json"
                        on:change={(e) => handleFileUpload(config.platform, e)}
                        class="hidden"
                      />
                      <label
                        for="{config.platform}-cookies"
                        class="flex-1 px-4 py-3 rounded-xl border border-white/10 bg-white/5 text-[color:var(--text-primary)] cursor-pointer hover:bg-white/10 transition-colors text-center"
                      >
                        {config.cookieFile || 'Upload cookie file (.json)'}
                      </label>
                    </div>
                  </div>
                {:else if config.platform === 'reddit'}
                  <div>
                    <label for="reddit-client-id" class="block text-xs font-semibold text-[color:var(--text-muted)] mb-2 uppercase tracking-wider">
                      Client ID
                    </label>
                    <input
                      id="reddit-client-id"
                      type="text"
                      bind:value={config.clientId}
                      disabled={savingPlatforms.has(config.platform)}
                      on:blur={() => saveConfig(config.platform, { clientId: config.clientId })}
                      placeholder="Reddit API client ID"
                      class="w-full px-4 py-3 rounded-xl border border-white/10 bg-white/5 text-[color:var(--text-primary)] placeholder:text-[color:var(--text-muted)]/50 focus:outline-none focus:border-[rgba(93,242,193,0.5)] focus:ring-2 focus:ring-[rgba(93,242,193,0.2)] transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                    />
                  </div>
                  <div>
                    <label for="reddit-client-secret" class="block text-xs font-semibold text-[color:var(--text-muted)] mb-2 uppercase tracking-wider">
                      Client Secret
                    </label>
                    <input
                      id="reddit-client-secret"
                      type="password"
                      bind:value={config.clientSecret}
                      disabled={savingPlatforms.has(config.platform)}
                      on:blur={() => saveConfig(config.platform, { clientSecret: config.clientSecret })}
                      placeholder="Reddit API client secret"
                      class="w-full px-4 py-3 rounded-xl border border-white/10 bg-white/5 text-[color:var(--text-primary)] placeholder:text-[color:var(--text-muted)]/50 focus:outline-none focus:border-[rgba(93,242,193,0.5)] focus:ring-2 focus:ring-[rgba(93,242,193,0.2)] transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                    />
                  </div>
                  <div>
                    <label for="reddit-username" class="block text-xs font-semibold text-[color:var(--text-muted)] mb-2 uppercase tracking-wider">
                      Username
                    </label>
                    <input
                      id="reddit-username"
                      type="text"
                      bind:value={config.username}
                      disabled={savingPlatforms.has(config.platform)}
                      on:blur={() => saveConfig(config.platform, { username: config.username })}
                      placeholder="Reddit username"
                      class="w-full px-4 py-3 rounded-xl border border-white/10 bg-white/5 text-[color:var(--text-primary)] placeholder:text-[color:var(--text-muted)]/50 focus:outline-none focus:border-[rgba(93,242,193,0.5)] focus:ring-2 focus:ring-[rgba(93,242,193,0.2)] transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                    />
                  </div>
                  <div>
                    <label for="reddit-password" class="block text-xs font-semibold text-[color:var(--text-muted)] mb-2 uppercase tracking-wider">
                      Password
                    </label>
                    <input
                      id="reddit-password"
                      type="password"
                      bind:value={config.password}
                      disabled={savingPlatforms.has(config.platform)}
                      on:blur={() => saveConfig(config.platform, { password: config.password })}
                      placeholder="Reddit password"
                      class="w-full px-4 py-3 rounded-xl border border-white/10 bg-white/5 text-[color:var(--text-primary)] placeholder:text-[color:var(--text-muted)]/50 focus:outline-none focus:border-[rgba(93,242,193,0.5)] focus:ring-2 focus:ring-[rgba(93,242,193,0.2)] transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                    />
                  </div>
                {:else if config.platform === 'telegram'}
                  <div>
                    <label for="telegram-token" class="block text-xs font-semibold text-[color:var(--text-muted)] mb-2 uppercase tracking-wider">
                      Bot Token
                    </label>
                    <input
                      id="telegram-token"
                      type="password"
                      bind:value={config.accessToken}
                      disabled={savingPlatforms.has(config.platform)}
                      on:blur={() => saveConfig(config.platform, { accessToken: config.accessToken })}
                      placeholder="Telegram bot API token"
                      class="w-full px-4 py-3 rounded-xl border border-white/10 bg-white/5 text-[color:var(--text-primary)] placeholder:text-[color:var(--text-muted)]/50 focus:outline-none focus:border-[rgba(93,242,193,0.5)] focus:ring-2 focus:ring-[rgba(93,242,193,0.2)] transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                    />
                  </div>
                {/if}
              </div>
            {/if}
          </div>
        {/each}
      </div>
      {/if}
    {:else if activeTab === 'automation'}
      <div class="space-y-6">
        <div class="rounded-2xl border border-white/10 bg-[rgba(15,29,46,0.85)] p-6">
          <h3 class="text-lg font-semibold text-[color:var(--text-primary)] mb-4">Collection Schedule</h3>
          <div class="space-y-4">
            <div>
              <label for="collection-interval" class="block text-xs font-semibold text-[color:var(--text-muted)] mb-2 uppercase tracking-wider">
                Collection Interval (minutes)
              </label>
              <input
                id="collection-interval"
                type="number"
                value="90"
                min="15"
                max="1440"
                class="w-full px-4 py-3 rounded-xl border border-white/10 bg-white/5 text-[color:var(--text-primary)] focus:outline-none focus:border-[rgba(93,242,193,0.5)] focus:ring-2 focus:ring-[rgba(93,242,193,0.2)] transition-all"
              />
            </div>
            <div>
              <label for="rewrite-interval" class="block text-xs font-semibold text-[color:var(--text-muted)] mb-2 uppercase tracking-wider">
                Rewrite Cycle (hours)
              </label>
              <input
                id="rewrite-interval"
                type="number"
                value="6"
                min="1"
                max="24"
                class="w-full px-4 py-3 rounded-xl border border-white/10 bg-white/5 text-[color:var(--text-primary)] focus:outline-none focus:border-[rgba(93,242,193,0.5)] focus:ring-2 focus:ring-[rgba(93,242,193,0.2)] transition-all"
              />
            </div>
          </div>
        </div>
      </div>
    {:else if activeTab === 'advanced'}
      <div class="space-y-6">
        <div class="rounded-2xl border border-white/10 bg-[rgba(15,29,46,0.85)] p-6">
          <h3 class="text-lg font-semibold text-[color:var(--text-primary)] mb-4">API Configuration</h3>
          <div class="space-y-4">
            <div>
              <label for="supabase-url" class="block text-xs font-semibold text-[color:var(--text-muted)] mb-2 uppercase tracking-wider">
                Supabase URL
              </label>
              <input
                id="supabase-url"
                type="url"
                placeholder="https://your-project.supabase.co"
                class="w-full px-4 py-3 rounded-xl border border-white/10 bg-white/5 text-[color:var(--text-primary)] placeholder:text-[color:var(--text-muted)]/50 focus:outline-none focus:border-[rgba(93,242,193,0.5)] focus:ring-2 focus:ring-[rgba(93,242,193,0.2)] transition-all"
              />
            </div>
            <div>
              <label for="supabase-key" class="block text-xs font-semibold text-[color:var(--text-muted)] mb-2 uppercase tracking-wider">
                Supabase Service Key
              </label>
              <input
                id="supabase-key"
                type="password"
                placeholder="Enter service role key"
                class="w-full px-4 py-3 rounded-xl border border-white/10 bg-white/5 text-[color:var(--text-primary)] placeholder:text-[color:var(--text-muted)]/50 focus:outline-none focus:border-[rgba(93,242,193,0.5)] focus:ring-2 focus:ring-[rgba(93,242,193,0.2)] transition-all"
              />
            </div>
          </div>
        </div>
        <div class="rounded-2xl border border-white/10 bg-[rgba(15,29,46,0.85)] p-6">
          <h3 class="text-lg font-semibold text-[color:var(--text-primary)] mb-4">Danger Zone</h3>
          <div class="space-y-3">
            <button
              class="px-6 py-3 rounded-xl border border-red-500/30 bg-red-500/10 text-red-400 hover:bg-red-500/20 transition-colors font-semibold"
            >
              Clear All Cookies
            </button>
            <button
              class="px-6 py-3 rounded-xl border border-red-500/30 bg-red-500/10 text-red-400 hover:bg-red-500/20 transition-colors font-semibold"
            >
              Reset Configuration
            </button>
          </div>
        </div>
      </div>
    {/if}
  </div>
</div>

{#if toast}
  <Toast message={toast.message} tone={toast.type} />
{/if}

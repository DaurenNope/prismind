<script lang="ts">
  import { onMount } from 'svelte';
  import { API_BASE } from '$lib/config';
  import Toast from '$lib/components/Toast.svelte';

  interface PlatformConfig {
    platform: string;
    username?: string;
    password?: string;
    cookieFile?: string;
    accessToken?: string;
    clientId?: string;
    clientSecret?: string;
    userAgent?: string;
    enabled: boolean;
  }

  const platforms: PlatformConfig[] = [
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

  let configs = [...platforms];
  let activeTab = 'credentials';
  let toast: { message: string; type: 'success' | 'error' } | null = null;
  let loading = false;

  onMount(async () => {
    await loadConfigs();
  });

  async function loadConfigs() {
    try {
      // In a real implementation, this would fetch from the backend
      // For now, we'll use localStorage as a fallback
      const saved = localStorage.getItem('beyondlines_configs');
      if (saved) {
        configs = JSON.parse(saved);
      }
    } catch (e) {
      console.error('Failed to load configs:', e);
    }
  }

  async function saveConfig(platform: string, config: Partial<PlatformConfig>) {
    loading = true;
    try {
      const index = configs.findIndex((c) => c.platform === platform);
      if (index >= 0) {
        configs[index] = { ...configs[index], ...config };
      }

      // Save to localStorage (in production, this would POST to backend)
      localStorage.setItem('beyondlines_configs', JSON.stringify(configs));

      // TODO: POST to backend API endpoint like /api/settings/credentials
      // const response = await fetch(`${API_BASE}/api/settings/credentials`, {
      //   method: 'POST',
      //   headers: { 'Content-Type': 'application/json' },
      //   body: JSON.stringify({ platform, config })
      // });

      toast = { message: `${platform} credentials saved`, type: 'success' };
      setTimeout(() => (toast = null), 3000);
    } catch (e) {
      toast = { message: `Failed to save ${platform} config: ${e}`, type: 'error' };
      setTimeout(() => (toast = null), 5000);
    } finally {
      loading = false;
    }
  }

  function handleFileUpload(platform: string, event: Event) {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
      const content = e.target?.result as string;
      // In production, upload to backend storage
      const cookiePath = `config/${platform}_cookies.json`;
      saveConfig(platform, { cookieFile: cookiePath });
      toast = { message: `Cookie file uploaded for ${platform}`, type: 'success' };
      setTimeout(() => (toast = null), 3000);
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
                      on:blur={() => saveConfig(config.platform, { username: config.username })}
                      placeholder="Enter username"
                      class="w-full px-4 py-3 rounded-xl border border-white/10 bg-white/5 text-[color:var(--text-primary)] placeholder:text-[color:var(--text-muted)]/50 focus:outline-none focus:border-[rgba(93,242,193,0.5)] focus:ring-2 focus:ring-[rgba(93,242,193,0.2)] transition-all"
                    />
                  </div>
                  <div>
                    <label for="{config.platform}-password" class="block text-xs font-semibold text-[color:var(--text-muted)] mb-2 uppercase tracking-wider">
                      Password
                    </label>
                    <input
                      id="{config.platform}-password"
                      type="password"
                      bind:value={config.password}
                      on:blur={() => saveConfig(config.platform, { password: config.password })}
                      placeholder="Enter password"
                      class="w-full px-4 py-3 rounded-xl border border-white/10 bg-white/5 text-[color:var(--text-primary)] placeholder:text-[color:var(--text-muted)]/50 focus:outline-none focus:border-[rgba(93,242,193,0.5)] focus:ring-2 focus:ring-[rgba(93,242,193,0.2)] transition-all"
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
                      on:blur={() => saveConfig(config.platform, { clientId: config.clientId })}
                      placeholder="Reddit API client ID"
                      class="w-full px-4 py-3 rounded-xl border border-white/10 bg-white/5 text-[color:var(--text-primary)] placeholder:text-[color:var(--text-muted)]/50 focus:outline-none focus:border-[rgba(93,242,193,0.5)] focus:ring-2 focus:ring-[rgba(93,242,193,0.2)] transition-all"
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
                      on:blur={() => saveConfig(config.platform, { clientSecret: config.clientSecret })}
                      placeholder="Reddit API client secret"
                      class="w-full px-4 py-3 rounded-xl border border-white/10 bg-white/5 text-[color:var(--text-primary)] placeholder:text-[color:var(--text-muted)]/50 focus:outline-none focus:border-[rgba(93,242,193,0.5)] focus:ring-2 focus:ring-[rgba(93,242,193,0.2)] transition-all"
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
                      on:blur={() => saveConfig(config.platform, { username: config.username })}
                      placeholder="Reddit username"
                      class="w-full px-4 py-3 rounded-xl border border-white/10 bg-white/5 text-[color:var(--text-primary)] placeholder:text-[color:var(--text-muted)]/50 focus:outline-none focus:border-[rgba(93,242,193,0.5)] focus:ring-2 focus:ring-[rgba(93,242,193,0.2)] transition-all"
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
                      on:blur={() => saveConfig(config.platform, { password: config.password })}
                      placeholder="Reddit password"
                      class="w-full px-4 py-3 rounded-xl border border-white/10 bg-white/5 text-[color:var(--text-primary)] placeholder:text-[color:var(--text-muted)]/50 focus:outline-none focus:border-[rgba(93,242,193,0.5)] focus:ring-2 focus:ring-[rgba(93,242,193,0.2)] transition-all"
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
                      on:blur={() => saveConfig(config.platform, { accessToken: config.accessToken })}
                      placeholder="Telegram bot API token"
                      class="w-full px-4 py-3 rounded-xl border border-white/10 bg-white/5 text-[color:var(--text-primary)] placeholder:text-[color:var(--text-muted)]/50 focus:outline-none focus:border-[rgba(93,242,193,0.5)] focus:ring-2 focus:ring-[rgba(93,242,193,0.2)] transition-all"
                    />
                  </div>
                {/if}
              </div>
            {/if}
          </div>
        {/each}
      </div>
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
  <Toast message={toast.message} type={toast.type} />
{/if}

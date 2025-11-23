<script lang="ts">
  import '../app.css';
  import { page } from '$app/stores';
  import { onMount, onDestroy } from 'svelte';
  import logoMark from '$lib/assets/beyondlines-mark.svg';
  import ToastCenter from '../components/Toast.svelte';
  import ErrorBoundary from '$lib/components/ErrorBoundary.svelte';

  interface NavItem {
    label: string;
    href: string;
    icon: string;
    sublabel?: string;
  }

  const navItems: NavItem[] = [
    { label: 'Dashboard', href: '/', icon: '📊', sublabel: 'Mission control' },
    { label: 'Feed', href: '/feed', icon: '🧭', sublabel: 'Signal streams' },
    { label: 'Collection', href: '/collection', icon: '📥', sublabel: 'Crawlers' },
    { label: 'Persona Studio', href: '/persona-studio', icon: '🎭', sublabel: 'AI persona creation' },
    { label: 'Publishing', href: '/publishing', icon: '📝', sublabel: 'Persona output' },
    { label: 'Content Plan', href: '/content-plan', icon: '📅', sublabel: 'Calendar view' },
    { label: 'Analysis', href: '/analysis', icon: '🤖', sublabel: 'AI workbench' },
    { label: 'Profiles', href: '/profiles', icon: '👤', sublabel: 'Legacy profiles' },
    { label: 'System', href: '/system', icon: '🔧', sublabel: 'Health & status' },
    { label: 'Settings', href: '/settings', icon: '⚙️', sublabel: 'Credentials & auth' }
  ];

  let sidebarOpen = false;
  let isDesktop = false;

  const updateSidebar = () => {
    if (typeof window === 'undefined') return;
    isDesktop = window.innerWidth >= 1280;
    sidebarOpen = isDesktop;
  };

  onMount(() => {
    updateSidebar();
    if (typeof window !== 'undefined') {
      window.addEventListener('resize', updateSidebar);
    }
  });

  onDestroy(() => {
    if (typeof window !== 'undefined') {
      window.removeEventListener('resize', updateSidebar);
    }
  });

  const toggleSidebar = () => {
    sidebarOpen = !sidebarOpen;
  };

  const closeSidebar = () => {
    sidebarOpen = false;
  };
</script>

<div class="min-h-screen relative">
  <div class="pointer-events-none absolute inset-0 opacity-70">
    <div class="absolute inset-x-0 top-[-18rem] h-[30rem] bg-[radial-gradient(circle_at_center,rgba(70,192,255,0.28),transparent_65%)]"></div>
    <div class="absolute right-[15%] top-[25%] h-[16rem] w-[16rem] rounded-full bg-[rgba(93,242,193,0.2)] blur-[110px]"></div>
    <div class="absolute left-[-6rem] bottom-[15%] h-[20rem] w-[20rem] rounded-full bg-[rgba(78,192,255,0.16)] blur-[120px]"></div>
  </div>

  <div class="relative flex min-h-screen">
    <aside
      class={`xl:translate-x-0 xl:opacity-100 xl:pointer-events-auto fixed inset-y-5 left-5 z-30 w-[18.5rem] rounded-3xl border border-white/8 bg-[rgba(12,24,40,0.85)] backdrop-blur-2xl shadow-[0_40px_130px_-70px_rgba(78,192,255,0.55)] transition-all duration-300 ${
        sidebarOpen ? 'translate-x-0 opacity-100 pointer-events-auto' : '-translate-x-[120%] opacity-0 pointer-events-none'
      }`}
    >
      <div class="flex h-full flex-col overflow-hidden">
        <div class="px-6 pt-7 pb-6 border-b border-white/10">
          <div class="flex items-center gap-3">
            <img src={logoMark} alt="BeyondLines" class="h-12 w-12 rounded-2xl shadow-[0_18px_40px_-20px_rgba(78,192,255,0.6)]" />
            <div>
              <p class="text-[11px] uppercase tracking-[0.45em] text-[color:var(--text-muted)]">BeyondLines</p>
              <h1 class="text-xl font-semibold text-[color:var(--text-primary)]">Intelligence Studio</h1>
            </div>
          </div>
        </div>

        <nav class="flex-1 overflow-y-auto px-4 py-6 space-y-2">
          {#each navItems as item}
            {@const isActive = $page.url.pathname === item.href}
            <a
              href={item.href}
              class={`group flex items-center justify-between rounded-2xl px-5 py-4 transition-all duration-200 border ${
                isActive
                  ? 'border-white/20 bg-white/[0.08] shadow-[0_20px_60px_-40px_rgba(78,192,255,0.55)]'
                  : 'border-transparent hover:border-white/12 hover:bg-white/[0.06]'
              }`}
            >
              <div class="flex items-center gap-3">
                <span class="text-lg leading-none">{item.icon}</span>
                <div>
                  <p class={`text-sm font-semibold leading-tight ${isActive ? 'text-[color:var(--text-primary)]' : 'text-[color:var(--text-muted)]'}`}>{item.label}</p>
                  <p class={`text-[11px] uppercase tracking-[0.32em] ${isActive ? 'text-[rgba(93,242,193,0.85)]' : 'text-[color:var(--text-muted)]/70'}`}>{item.sublabel}</p>
                </div>
              </div>
              <span class={`text-[10px] font-semibold tracking-[0.35em] transition-transform duration-200 ${
                isActive ? 'text-[rgba(93,242,193,0.85)] translate-x-1' : 'text-[color:var(--text-muted)] group-hover:translate-x-1'
              }`}>
                →
              </span>
            </a>
          {/each}
        </nav>

        <div class="px-6 pb-6">
          <div class="rounded-2xl border border-white/10 bg-[rgba(15,29,46,0.85)] px-5 py-4 shadow-[0_20px_80px_-60px_rgba(93,242,193,0.45)]">
            <p class="text-[10px] uppercase tracking-[0.45em] text-[color:var(--text-muted)]">Status</p>
            <p class="text-sm font-semibold text-[color:var(--text-primary)] mt-1">Automation engine <span class="text-[rgba(93,242,193,0.85)]">active</span></p>
            <p class="text-xs text-[color:var(--text-muted)]/80 mt-2">Next rewrite cycle in 54 minutes</p>
          </div>
        </div>
      </div>
    </aside>

    <div class={`flex-1 w-full min-h-screen px-5 py-6 xl:pl-[21rem] xl:pr-10 transition-all duration-300 ${sidebarOpen ? 'ml-0' : 'ml-0 xl:ml-0'}`}>
      <header class="relative z-20 mb-9">
        <div class="rounded-3xl border border-white/8 bg-[rgba(13,23,37,0.85)] backdrop-blur-xl px-6 py-5 flex items-center justify-between shadow-[0_30px_100px_-70px_rgba(78,192,255,0.55)]">
          <div>
            <p class="text-[11px] uppercase tracking-[0.45em] text-[color:var(--text-muted)]">BeyondLines command deck</p>
            <h2 class="text-2xl font-semibold text-[color:var(--text-primary)] mt-1">Strategic overview</h2>
          </div>
          <div class="flex items-center gap-3">
            <div class="hidden sm:flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-[color:var(--text-muted)]">
              Release channel <span class="text-[rgba(78,192,255,0.85)] font-semibold">Aurora</span>
            </div>
            <button
              type="button"
              class="xl:hidden inline-flex h-11 w-11 items-center justify-center rounded-2xl border border-white/10 bg-white/5 text-[color:var(--text-primary)] hover:bg-white/10 transition-colors"
              on:click={toggleSidebar}
              aria-label="Toggle navigation"
            >
              ☰
            </button>
            <div class="h-11 w-11 rounded-2xl bg-[linear-gradient(135deg,rgba(78,192,255,0.9),rgba(93,242,193,0.9))] text-[color:var(--base)] grid place-items-center font-semibold shadow-[0_20px_40px_-25px_rgba(78,192,255,0.6)]">
              BL
            </div>
          </div>
        </div>
      </header>

      <main class="relative z-10 pb-14">
        <ErrorBoundary fallback="An error occurred while loading this page. Please try refreshing.">
          <slot />
        </ErrorBoundary>
      </main>
    </div>
  </div>

  {#if sidebarOpen && !isDesktop}
    <button
      type="button"
      class="fixed inset-0 z-20 bg-[rgba(4,7,18,0.65)] backdrop-blur-sm"
      on:click={closeSidebar}
      on:keydown={(event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          closeSidebar();
        }
      }}
      aria-label="Close navigation"
    ></button>
  {/if}
</div>

<!-- Toast Notifications -->
<ToastCenter />

<style>
  :global(body) {
    margin: 0;
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  }
</style>

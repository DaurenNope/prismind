<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { personaService } from '$lib/services/persona';
	import { toast } from '$lib/toast';
	import type {
		Persona,
		PersonaExampleRecord,
		PersonaPerformance,
		QualityTrends,
		PersonaRewriteRecord,
		AutomationStatus,
		AutomationRunDetails
	} from '$lib/services/persona';

	type HealthStatus = {
		status?: string;
		timestamp?: string;
		services?: Record<string, string>;
	};

	type AnalyticsState = {
		totalPersonas: number;
		totalExamples: number;
		avgQuality: number;
		avgEngagement: number;
		totalPostsGenerated: number;
		platforms: string[];
		ragMetrics: {
			rag_enabled?: boolean;
			total_vector_examples?: number;
			faiss_available?: boolean;
		};
		systemPerformance: {
			api_response_time?: string;
			success_rate?: string;
			uptime?: string;
		};
	};

	// Reactive state
	let personas: Persona[] = [];
	let selectedPersona: Persona | null = null;
	let isLoading = false;
	let isDetailsLoading = false;
	let isExamplesLoading = false;
	let showCreateModal = false;

	// Form data for new persona
	let personaName = '';
	let personaDescription = '';
	let examples: string[] = [''];
	let topic = '';
	let platform: 'twitter' | 'linkedin' | 'threads' | 'telegram' = 'twitter';

	// Analytics data
	let analytics: AnalyticsState = {
		totalPersonas: 0,
		totalExamples: 0,
		avgQuality: 0,
		avgEngagement: 0,
		totalPostsGenerated: 0,
		platforms: [],
		ragMetrics: {
			rag_enabled: false,
			total_vector_examples: 0,
			faiss_available: false
		},
		systemPerformance: {
			api_response_time: '—',
			success_rate: '—',
			uptime: '—'
		}
	};

	let healthStatus: HealthStatus | null = null;
	let qualityTrends: QualityTrends | null = null;
	let personaPerformance: PersonaPerformance | null = null;
	let personaExamples: PersonaExampleRecord[] = [];
let latestRewrites: PersonaRewriteRecord[] = [];
let isRewritesLoading = false;
let automationStatus: AutomationStatus | null = null;
let isAutomationTriggering = false;
let automationPollInterval: ReturnType<typeof setInterval> | null = null;
let lastAutomationRun: AutomationRunDetails | null = null;

$: lastAutomationRun =
	automationStatus?.running
		? automationStatus?.current ?? null
		: automationStatus?.current && automationStatus.current.status !== 'running'
		? automationStatus.current
		: automationStatus?.history?.[0] ?? null;

onMount(async () => {
	await Promise.all([
		loadPersonas(),
		loadAnalytics(),
		loadHealthStatus(),
		loadQualityTrends()
	]);
	await loadAutomationStatus();
	automationPollInterval = setInterval(() => {
		void loadAutomationStatus(true);
	}, 10000);
});

onDestroy(() => {
	if (automationPollInterval) {
		clearInterval(automationPollInterval);
	}
});

	async function loadPersonas(): Promise<void> {
		try {
			const data = await personaService.getPersonas();
			personas = (data || []).map((persona) => {
				const metrics = persona.quality_metrics || persona.qualityMetrics || {};
				return {
					...persona,
					qualityMetrics: {
						voice_consistency: metrics.avg_rewrite ?? 0,
						authenticity_prediction: metrics.avg_quality ?? 0,
						engagement_potential: metrics.avg_value ?? 0,
						overall_quality: metrics.avg_quality ?? 0
					}
				};
			});
			const firstPersona = personas[0];
			if (!selectedPersona && firstPersona) {
				await selectPersona(firstPersona);
			}
		} catch (error) {
			console.error('Failed to load personas:', error);
			toast.error('Failed to load personas');
		}
	}

	async function loadAnalytics(): Promise<void> {
		try {
			const data = await personaService.getStats();
			analytics = {
				totalPersonas: data.totalPersonas ?? 0,
				totalExamples: data.totalExamples ?? 0,
				avgQuality: data.avgQuality ?? 0,
				avgEngagement: data.avgEngagement ?? 0,
				totalPostsGenerated: data.totalPostsGenerated ?? 0,
				platforms: data.platforms || [],
				ragMetrics: data.ragMetrics || analytics.ragMetrics,
				systemPerformance: data.systemPerformance || analytics.systemPerformance
			};
		} catch (error) {
			console.error('Failed to load analytics:', error);
		}
	}

	async function loadHealthStatus(): Promise<void> {
		try {
			healthStatus = await personaService.getHealth();
		} catch (error) {
			console.error('Failed to load persona health:', error);
			healthStatus = null;
		}
	}

	async function loadQualityTrends(): Promise<void> {
		try {
			qualityTrends = await personaService.getQualityTrends();
		} catch (error) {
			console.error('Failed to load quality trends:', error);
			qualityTrends = null;
		}
	}

async function loadAutomationStatus(isPoll = false): Promise<void> {
	try {
		const wasRunning = automationStatus?.running;
		const status = await personaService.getAutomationStatus();
		automationStatus = status;

		if (wasRunning && !status.running) {
			await Promise.all([loadPersonas(), loadAnalytics(), loadQualityTrends()]);
			if (selectedPersona?.id) {
				const personaKey = resolvePersonaKey(selectedPersona);
				await Promise.all([
					loadPersonaInsights(selectedPersona.id),
					loadPersonaExampleSnippets(selectedPersona.id),
					loadLatestRewrites(personaKey)
				]);
			}
			toast.success('Automation pipeline completed');
		}
	} catch (error) {
		if (!isPoll) {
			console.error('Failed to load automation status:', error);
			toast.error('Unable to load automation status');
		}
	}
}

	async function loadPersonaInsights(personaId: string): Promise<void> {
		if (!personaId) return;
		isDetailsLoading = true;
		try {
			personaPerformance = await personaService.getPersonaPerformance(personaId);
		} catch (error) {
			console.error('Failed to load persona performance:', error);
			personaPerformance = null;
		} finally {
			isDetailsLoading = false;
		}
	}

	async function loadPersonaExampleSnippets(personaId: string): Promise<void> {
		if (!personaId) {
			personaExamples = [];
			return;
		}
		isExamplesLoading = true;
		try {
			const response = await personaService.getPersonaExamples(personaId);
			personaExamples = Array.isArray(response?.examples)
				? response.examples.slice(0, 4)
				: [];
		} catch (error) {
			console.error('Failed to load persona examples:', error);
			personaExamples = [];
		} finally {
			isExamplesLoading = false;
		}
	}

	async function createPersona(): Promise<void> {
		if (!personaName.trim()) {
			toast.error('Please enter a persona name');
			return;
		}

		const validExamples = examples.filter(ex => ex.trim());
		if (validExamples.length < 3) {
			toast.error('Please provide at least 3 examples');
			return;
		}

		isLoading = true;
		try {
			const key = personaName
				.toLowerCase()
				.replace(/[^a-z0-9]+/g, '-')
				.replace(/^-+|-+$/g, '');
			const persona = await personaService.createPersona({
				key,
				name: personaName,
				description: personaDescription,
				voice_description: personaDescription || personaName,
				examples: validExamples
			});

			personas = [...personas, persona];
			selectedPersona = persona;
			resetCreateForm();
			showCreateModal = false;
			toast.success(`Persona "${persona.name}" created successfully!`);
			await loadAnalytics();
		} catch (error) {
			console.error('Failed to create persona:', error);
			const message = error instanceof Error ? error.message : 'Failed to create persona';
			toast.error(message);
		}
		isLoading = false;
	}

	async function generateContent(): Promise<void> {
		if (!selectedPersona || !topic.trim()) {
			toast.error('Please select a persona and enter a topic');
			return;
		}

		isLoading = true;
		try {
			const result = await personaService.generateContent(selectedPersona.id, {
				content: topic,
				platform,
				category: 'user_generated'
			});

			const updatedPersona = {
				...selectedPersona,
				generatedContent: result.content,
				qualityMetrics: result.quality_metrics,
				ragSources: result.rag_sources ?? selectedPersona.ragSources
			};
			selectedPersona = updatedPersona;
			personas = personas.map((persona) =>
				persona.id === updatedPersona.id ? updatedPersona : persona
			);

			await Promise.all([
				loadPersonaInsights(selectedPersona.id),
				loadPersonaExampleSnippets(selectedPersona.id),
				loadLatestRewrites(resolvePersonaKey(selectedPersona))
			]);
			toast.success('Rewrite generated from the live pipeline');
		} catch (error) {
			console.error('Failed to generate content:', error);
			toast.error('Failed to generate content');
		}
		isLoading = false;
	}

function addExample(): void {
	examples = [...examples, ''];
}

async function runAutomationPipeline(): Promise<void> {
	if (automationStatus?.running || isAutomationTriggering) {
		toast.info('Automation loop is already running');
		return;
	}

	isAutomationTriggering = true;
	try {
		await personaService.triggerAutomation();
		toast.success('Automation pipeline started');
		await loadAutomationStatus();
	} catch (error) {
		console.error('Failed to trigger automation pipeline:', error);
		const message = error instanceof Error ? error.message : 'Failed to start automation';
		toast.error(message);
	} finally {
		isAutomationTriggering = false;
	}
}

function removeExample(index: number): void {
	examples = examples.filter((_, i) => i !== index);
}

	function resetCreateForm(): void {
		personaName = '';
		personaDescription = '';
		examples = [''];
	}

	function resolvePersonaKey(persona: Persona | null): string | null {
		if (!persona) return null;
		if (persona.id) return persona.id;
		if (persona.handle) return persona.handle.toLowerCase();
		if (persona.name) return persona.name.toLowerCase();
		return null;
	}

	async function loadLatestRewrites(personaKey?: string | null, limit = 5): Promise<void> {
		latestRewrites = [];
		if (!personaKey) return;
		isRewritesLoading = true;
		try {
			const response = await personaService.getLatestRewrites(personaKey, limit);
			latestRewrites = Array.isArray(response?.rewrites) ? response.rewrites : [];
		} catch (error) {
			console.error('Failed to load latest rewrites:', error);
			latestRewrites = [];
		} finally {
			isRewritesLoading = false;
		}
	}

	async function selectPersona(persona: Persona): Promise<void> {
		selectedPersona = persona;
		selectedPersona.generatedContent = undefined;
		selectedPersona.qualityMetrics = undefined;
		personaPerformance = null;
		personaExamples = [];
	latestRewrites = [];

		if (persona?.id) {
		const personaKey = resolvePersonaKey(persona);
			await Promise.all([
				loadPersonaInsights(persona.id),
			loadPersonaExampleSnippets(persona.id),
			loadLatestRewrites(personaKey)
			]);
		}
	}

	function formatDate(dateString: string): string {
		return new Date(dateString).toLocaleDateString();
	}

function normalizeScore(score?: number | null) {
	if (score === undefined || score === null || Number.isNaN(score)) {
		return 0;
	}
	return score > 1 ? Math.min(1, score / 10) : score;
}

function getQualityColor(score: number = 0) {
	const normalized = normalizeScore(score);
	if (normalized >= 0.8) return 'text-[rgba(93,242,193,0.95)]';
	if (normalized >= 0.6) return 'text-[rgba(245,182,120,0.95)]';
	return 'text-[rgba(248,113,113,0.95)]';
}

function getQualityBadge(score?: number | null) {
	const normalized = normalizeScore(score);
	if (normalized >= 0.8) return 'text-[rgba(93,242,193,0.95)]';
	if (normalized >= 0.6) return 'text-[rgba(245,182,120,0.95)]';
	return 'text-[rgba(248,113,113,0.95)]';
}

function formatQualityScore(score?: number | null) {
	if (score === undefined || score === null || Number.isNaN(score)) {
		return '—';
	}
	return `${(normalizeScore(score) * 100).toFixed(0)}%`;
}

	function formatNumber(value: number | string | undefined | null) {
		if (value === undefined || value === null) {
			return '—';
		}
		const numericValue = typeof value === 'string' ? Number(value) : value;
		if (Number.isNaN(numericValue)) {
			return value.toString();
		}
		return numericValue.toLocaleString();
	}

function getPersonaQualityScore(persona: Persona): number {
	const metrics = persona.qualityMetrics || persona.quality_metrics;
	return metrics?.overall_quality ?? metrics?.avg_quality ?? 0;
}

function formatPercentage(value: number | undefined | null) {
	if (value === undefined || value === null || Number.isNaN(value)) {
			return '—';
		}
	const normalized = normalizeScore(value);
	return `${(normalized * 100).toFixed(0)}%`;
	}

	function formatServiceName(name: string = '') {
		return name
			.replace(/_/g, ' ')
			.replace(/\b\w/g, (char) => char.toUpperCase());
	}

	function serviceStatusColor(status: unknown) {
		const normalized = (status ?? '').toString().toLowerCase();
		if (normalized.includes('error') || normalized.includes('offline') || normalized.includes('degraded')) {
			return 'text-[rgba(248,113,113,0.95)]';
		}
		if (normalized.includes('healthy') || normalized.includes('active') || normalized.includes('true')) {
			return 'text-[rgba(93,242,193,0.95)]';
		}
		return 'text-[color:var(--text-muted)]';
	}

	function getExampleCount(persona: Persona) {
		if (!persona) return 0;
		if (persona.example_count !== undefined) return persona.example_count;
		return 0;
	}

function automationStatusBadge(status?: string) {
	const normalized = (status ?? '').toLowerCase();
	if (normalized === 'running') return 'text-[rgba(245,182,120,0.95)]';
	if (normalized === 'failed') return 'text-[rgba(248,113,113,0.95)]';
	if (normalized === 'success') return 'text-[rgba(93,242,193,0.95)]';
	return 'text-[color:var(--text-muted)]';
}

function automationStatusLabel(run?: AutomationRunDetails | null) {
	if (!run) return 'Idle';
	const normalized = run.status?.toLowerCase();
	if (normalized === 'running') return 'Running';
	if (normalized === 'success') return 'Success';
	if (normalized === 'failed') return 'Failed';
	return 'Idle';
}

function formatDateTime(dateString?: string) {
	if (!dateString) return '—';
	const date = new Date(dateString);
	return `${date.toLocaleDateString()} ${date.toLocaleTimeString()}`;
}

function totalCollected(run?: AutomationRunDetails | null) {
	if (!run?.results?.collection) return 0;
	return Object.values(run.results.collection).reduce((sum, value) => {
		const numeric = typeof value === 'number' ? value : Number(value);
		return sum + (Number.isFinite(numeric) ? numeric : 0);
	}, 0);
}

function analyzedCount(run?: AutomationRunDetails | null) {
	return run?.results?.analysis?.analyzed ?? 0;
}

function transformedCount(run?: AutomationRunDetails | null) {
	return run?.results?.transformation?.transformed ?? 0;
}

function formatDuration(start?: string, end?: string) {
	if (!start) return '—';
	const startTime = new Date(start).getTime();
	const endTime = end ? new Date(end).getTime() : Date.now();
	const seconds = Math.max(0, Math.round((endTime - startTime) / 1000));
	if (seconds < 60) {
		return `${seconds}s`;
	}
	const minutes = Math.round(seconds / 60);
	return `${minutes}m`;
}
</script>

<svelte:head>
	<title>BeyondLines · Persona Studio</title>
	<meta name="description" content="AI persona creation and content generation studio" />
</svelte:head>

<div class="space-y-12">
	<!-- HERO SECTION -->
	<section class="relative overflow-hidden rounded-[32px] border border-white/10 bg-white/6 backdrop-blur-2xl shadow-[0_50px_180px_-110px_rgba(140,168,255,0.85)]">
		<div class="pointer-events-none absolute inset-0">
			<div class="absolute -left-24 top-[-90px] h-[320px] w-[320px] rounded-full bg-[rgba(168,119,255,0.28)] blur-[140px]"></div>
			<div class="absolute right-[-160px] top-[-60px] h-[320px] w-[320px] rounded-full bg-[rgba(93,242,193,0.2)] blur-[140px]"></div>
			<div class="absolute inset-x-16 bottom-[-220px] h-[340px] rounded-[360px] bg-[rgba(24,65,120,0.35)] blur-[150px]"></div>
		</div>

		<div class="relative px-10 py-12">
			<div class="space-y-4">
				<p class="text-[11px] uppercase tracking-[0.48em] text-slate-300">Persona studio</p>
				<h1 class="text-[38px] md:text-[44px] font-semibold text-white leading-tight">
					Advanced AI persona creation and content generation.
				</h1>
				<p class="text-sm md:text-base text-slate-200/80 max-w-2xl">
					Create authentic AI personas from example posts, generate platform-specific content with real-time quality scoring, and optimize voice patterns for maximum engagement.
				</p>
			</div>
		</div>
	</section>

	<!-- AUTOMATION CONTROL PANEL -->
	<section class="grid gap-6 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,0.8fr)]">
		<div class="rounded-[32px] border border-white/10 bg-[rgba(12,24,40,0.9)] backdrop-blur-2xl p-6 space-y-5 shadow-[0_40px_140px_-90px_rgba(93,242,193,0.4)]">
			<div class="flex items-center justify-between gap-4">
				<div>
					<p class="text-[10px] uppercase tracking-[0.35em] text-[color:var(--text-muted)]">Automation pipeline</p>
					<h3 class="text-xl font-semibold text-[color:var(--text-primary)]">Collection → Rewrite workflow</h3>
				</div>
				<span class={`text-xs font-semibold uppercase tracking-[0.3em] ${automationStatus?.running ? 'text-[rgba(245,182,120,0.95)]' : automationStatusBadge(lastAutomationRun?.status)}`}>
					{automationStatus?.running ? 'Running' : automationStatusLabel(lastAutomationRun)}
				</span>
			</div>

			<p class="text-xs text-[color:var(--text-muted)]/80">
				{automationStatus?.running
					? 'Pipeline is collecting, analyzing, curating, and rewriting posts.'
					: lastAutomationRun
						? `Last run ${lastAutomationRun.completed_at ? 'finished' : 'started'} ${formatDateTime(lastAutomationRun.completed_at || lastAutomationRun.started_at)} · Duration ${formatDuration(lastAutomationRun.started_at, lastAutomationRun.completed_at)}`
						: 'No automation runs have been recorded yet.'}
			</p>

			<div class="grid gap-4 sm:grid-cols-3">
				<div class="rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
					<p class="text-[10px] uppercase tracking-[0.3em] text-[color:var(--text-muted)]">Collected</p>
					<p class="text-2xl font-semibold text-[rgba(93,242,193,0.95)] mt-1">{formatNumber(totalCollected(lastAutomationRun))}</p>
				</div>
				<div class="rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
					<p class="text-[10px] uppercase tracking-[0.3em] text-[color:var(--text-muted)]">Analyzed</p>
					<p class="text-2xl font-semibold text-[rgba(245,182,120,0.95)] mt-1">{formatNumber(analyzedCount(lastAutomationRun))}</p>
				</div>
				<div class="rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
					<p class="text-[10px] uppercase tracking-[0.3em] text-[color:var(--text-muted)]">Rewrites</p>
					<p class="text-2xl font-semibold text-[rgba(78,192,255,0.95)] mt-1">{formatNumber(transformedCount(lastAutomationRun))}</p>
				</div>
			</div>

			<button
				type="button"
				on:click={runAutomationPipeline}
				disabled={isAutomationTriggering || automationStatus?.running}
				class="group relative overflow-hidden rounded-2xl border border-white/10 px-5 py-4 text-sm font-medium text-white w-full transition-all hover:-translate-y-1 hover:shadow-[0_25px_80px_-60px_rgba(93,242,193,0.55)] disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:translate-y-0"
			>
				<span class="absolute inset-0 -z-10 bg-[linear-gradient(135deg,rgba(93,242,193,0.9),rgba(17,126,92,0.9))] disabled:from-gray-600 disabled:to-gray-700"></span>
				{automationStatus?.running ? 'Pipeline running…' : isAutomationTriggering ? 'Starting…' : 'Run full automation loop'}
			</button>

			{#if lastAutomationRun?.error && !automationStatus?.running}
				<p class="text-xs text-[rgba(248,113,113,0.9)]">
					Last run failed: {lastAutomationRun.error}
				</p>
			{/if}

			<div class="space-y-2">
				<div class="flex items-center justify-between">
					<p class="text-[10px] uppercase tracking-[0.35em] text-[color:var(--text-muted)]">Recent runs</p>
					{#if automationStatus?.running}
						<span class="text-[10px] text-[color:var(--text-muted)]/70">Updating…</span>
					{/if}
				</div>
				{#if automationStatus?.history?.length}
					<div class="space-y-2 max-h-40 overflow-y-auto custom-scrollbar">
						{#each automationStatus.history.slice(0, 4) as run}
							<div class="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-xs text-[color:var(--text-muted)]/85">
								<div class="flex items-center justify-between gap-3">
									<span class={`font-semibold ${automationStatusBadge(run.status)}`}>{automationStatusLabel(run)}</span>
									<span>{formatDateTime(run.completed_at || run.started_at)}</span>
								</div>
								<div class="mt-2 flex flex-wrap gap-3 text-[color:var(--text-muted)]/75">
									<span>Collect {formatNumber(totalCollected(run))}</span>
									<span>Analyze {formatNumber(analyzedCount(run))}</span>
									<span>Rewrites {formatNumber(transformedCount(run))}</span>
								</div>
							</div>
						{/each}
					</div>
				{:else}
					<p class="text-xs text-[color:var(--text-muted)]/70">No completed runs yet.</p>
				{/if}
			</div>
		</div>

		<div class="rounded-[32px] border border-white/10 bg-[rgba(15,29,46,0.9)] backdrop-blur-2xl p-6 space-y-4">
			<p class="text-[10px] uppercase tracking-[0.35em] text-[color:var(--text-muted)]">What gets automated</p>
			<ul class="space-y-3  text-sm text-[color:var(--text-muted)]">
				<li class="rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
					<span class="text-[color:var(--text-primary)] font-semibold">Collection</span>
					<p class="text-xs text-[color:var(--text-muted)]/80 mt-1">Twitter, Threads, and Reddit saved feeds pulled via API-first collectors.</p>
				</li>
				<li class="rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
					<span class="text-[color:var(--text-primary)] font-semibold">Analysis & Curation</span>
					<p class="text-xs text-[color:var(--text-muted)]/80 mt-1">AI summaries, persona matching, and usable_posts promotion happen automatically.</p>
				</li>
				<li class="rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
					<span class="text-[color:var(--text-primary)] font-semibold">Persona rewrites</span>
					<p class="text-xs text-[color:var(--text-muted)]/80 mt-1">RAG-powered ContentRewriter produces drafts ready for scheduling.</p>
				</li>
			</ul>
			<p class="text-xs text-[color:var(--text-muted)]/70">Scheduling and posting remain manual for final QA.</p>
		</div>
	</section>

	{#if healthStatus || qualityTrends}
		<section class="grid gap-6 lg:grid-cols-3">
			<!-- System Health -->
			<div class="rounded-3xl border border-white/10 bg-[rgba(12,24,40,0.85)] backdrop-blur-xl p-6 space-y-4">
				<p class="text-[10px] uppercase tracking-[0.35em] text-[color:var(--text-muted)]">System status</p>
				<h3 class="text-2xl font-semibold text-[color:var(--text-primary)]">
					{healthStatus?.status ? healthStatus.status.charAt(0).toUpperCase() + healthStatus.status.slice(1) : 'Unknown'}
				</h3>
				<p class="text-xs text-[color:var(--text-muted)]/70">Last updated {healthStatus?.timestamp ? new Date(healthStatus.timestamp).toLocaleTimeString() : '—'}</p>
				<div class="space-y-2">
					{#if healthStatus?.services}
						{#each Object.entries(healthStatus.services).slice(0, 4) as [serviceName, serviceStatus]}
							<div class="flex items-center justify-between rounded-2xl border border-white/10 bg-white/5 px-3 py-2">
								<span class="text-xs text-[color:var(--text-muted)]/85">{formatServiceName(serviceName)}</span>
								<span class={`text-xs font-semibold ${serviceStatusColor(serviceStatus)}`}>{serviceStatus}</span>
							</div>
						{/each}
					{:else}
						<p class="text-xs text-[color:var(--text-muted)]/70">No health data available.</p>
					{/if}
				</div>
			</div>

			<!-- RAG Metrics -->
			<div class="rounded-3xl border border-white/10 bg-[linear-gradient(135deg,rgba(93,242,193,0.18),rgba(13,50,38,0.85))] px-6 py-6 space-y-4 shadow-[0_35px_120px_-100px_rgba(93,242,193,0.65)]">
				<p class="text-[10px] uppercase tracking-[0.35em] text-[rgba(93,242,193,0.8)]">RAG pipeline</p>
				<h3 class="text-xl font-semibold text-[color:var(--text-primary)]">
					{analytics.ragMetrics.rag_enabled ? 'Vector knowledge active' : 'RAG offline'}
				</h3>
				<div class="grid grid-cols-2 gap-4 text-sm">
					<div>
						<p class="text-[10px] uppercase tracking-[0.28em] text-[color:var(--text-muted)]">Vector examples</p>
						<p class="text-lg text-[rgba(93,242,193,0.95)]">{formatNumber(analytics.ragMetrics.total_vector_examples)}</p>
					</div>
					<div>
						<p class="text-[10px] uppercase tracking-[0.28em] text-[color:var(--text-muted)]">Faiss index</p>
						<p class={`text-lg ${analytics.ragMetrics.faiss_available ? 'text-[rgba(93,242,193,0.95)]' : 'text-[rgba(248,113,113,0.95)]'}`}>
							{analytics.ragMetrics.faiss_available ? 'Ready' : 'Offline'}
						</p>
					</div>
				</div>
				<div class="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-xs text-[color:var(--text-muted)]/80">
					<p>API latency: {analytics.systemPerformance.api_response_time || '—'}</p>
					<p>Success rate: {analytics.systemPerformance.success_rate || '—'}</p>
					<p>Uptime: {analytics.systemPerformance.uptime || '—'}</p>
				</div>
			</div>

			<!-- Quality Distribution -->
			<div class="rounded-3xl border border-white/10 bg-[rgba(15,29,46,0.9)] px-6 py-6 space-y-4">
				<p class="text-[10px] uppercase tracking-[0.35em] text-[color:var(--text-muted)]">Quality intelligence</p>
				{#if qualityTrends}
					<div class="space-y-3">
						<p class="text-sm text-[color:var(--text-primary)]">Overall authenticity {formatPercentage(qualityTrends.overall_trends?.avg_authenticity)}</p>
						<div class="grid grid-cols-3 gap-3 text-center text-xs">
							<div class="rounded-2xl border border-white/10 bg-[rgba(93,242,193,0.1)] px-3 py-3">
								<p class="text-[rgba(93,242,193,0.95)] font-semibold">{formatNumber(qualityTrends.quality_distribution?.high_quality)}</p>
								<p class="text-[color:var(--text-muted)]/70 mt-1 tracking-[0.3em] uppercase">High</p>
							</div>
							<div class="rounded-2xl border border-white/10 bg-[rgba(245,182,120,0.08)] px-3 py-3">
								<p class="text-[rgba(245,182,120,0.95)] font-semibold">{formatNumber(qualityTrends.quality_distribution?.medium_quality)}</p>
								<p class="text-[color:var(--text-muted)]/70 mt-1 tracking-[0.3em] uppercase">Medium</p>
							</div>
							<div class="rounded-2xl border border-white/10 bg-[rgba(248,113,113,0.08)] px-3 py-3">
								<p class="text-[rgba(248,113,113,0.95)] font-semibold">{formatNumber(qualityTrends.quality_distribution?.low_quality)}</p>
								<p class="text-[color:var(--text-muted)]/70 mt-1 tracking-[0.3em] uppercase">Low</p>
							</div>
						</div>
						<p class="text-xs text-[color:var(--text-muted)]/70">
							Tracking {formatNumber(qualityTrends.persona_breakdown?.length || 0)} personas.
						</p>
					</div>
				{:else}
					<p class="text-xs text-[color:var(--text-muted)]/70">Quality analytics unavailable.</p>
				{/if}
			</div>
		</section>
	{/if}

	<!-- ANALYTICS GRID -->
	<section class="grid gap-6 md:grid-cols-2 xl:grid-cols-4">
		<div class="rounded-3xl border border-white/10 bg-[linear-gradient(135deg,rgba(168,119,255,0.32),rgba(139,92,246,0.18))] px-6 py-6 shadow-[0_30px_80px_-70px_rgba(168,119,255,0.55)]">
			<p class="text-[10px] uppercase tracking-[0.35em] text-[color:var(--text-muted)]">Total personas</p>
			<p class="text-[34px] font-semibold text-[color:var(--text-primary)] mt-3">{formatNumber(analytics.totalPersonas)}</p>
			<p class="text-xs text-[color:var(--text-muted)]/70 mt-2">AI voices created</p>
		</div>
		<div class="rounded-3xl border border-white/10 bg-[linear-gradient(135deg,rgba(93,242,193,0.30),rgba(17,126,92,0.18))] px-6 py-6 shadow-[0_30px_80px_-70px_rgba(93,242,193,0.45)]">
			<p class="text-[10px] uppercase tracking-[0.35em] text-[color:var(--text-muted)]">Training examples</p>
			<p class="text-[34px] font-semibold text-[rgba(93,242,193,0.95)] mt-3">{formatNumber(analytics.totalExamples)}</p>
			<p class="text-xs text-[rgba(93,242,193,0.75)] mt-2">Voice pattern samples</p>
		</div>
		<div class="rounded-3xl border border-white/10 bg-[linear-gradient(135deg,rgba(245,182,120,0.32),rgba(148,93,52,0.18))] px-6 py-6 shadow-[0_30px_80px_-70px_rgba(245,182,120,0.45)]">
			<p class="text-[10px] uppercase tracking-[0.35em] text-[color:var(--text-muted)]">Avg authenticity</p>
			<p class="text-[34px] font-semibold text-[rgba(245,182,120,0.95)] mt-3">{(analytics.avgQuality * 100).toFixed(1)}%</p>
			<p class="text-xs text-[rgba(245,182,120,0.75)] mt-2">Voice consistency score</p>
		</div>
		<div class="rounded-3xl border border-white/10 bg-[linear-gradient(135deg,rgba(78,192,255,0.28),rgba(29,90,180,0.18))] px-6 py-6 shadow-[0_30px_80px_-70px_rgba(78,192,255,0.45)]">
			<p class="text-[10px] uppercase tracking-[0.35em] text-[color:var(--text-muted)]">Avg engagement</p>
			<p class="text-[34px] font-semibold text-[rgba(78,192,255,0.95)] mt-3">{(analytics.avgEngagement * 100).toFixed(1)}%</p>
			<p class="text-xs text-[rgba(78,192,255,0.75)] mt-2">{formatNumber(analytics.platforms.length)} platforms ready</p>
		</div>
	</section>

	<!-- MAIN CONTENT GRID -->
	<section class="grid gap-6 xl:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]">
		<!-- Personas List -->
		<div class="rounded-4xl border border-white/10 bg-[rgba(12,24,40,0.85)] backdrop-blur-2xl p-6 space-y-6 shadow-[0_35px_140px_-90px_rgba(168,119,255,0.5)]">
			<div class="flex items-center justify-between">
				<div>
					<p class="text-[10px] uppercase tracking-[0.35em] text-[color:var(--text-muted)]">Persona library</p>
					<h2 class="text-lg font-semibold text-[color:var(--text-primary)] mt-1">Your AI personas</h2>
				</div>
				<button
					on:click={() => showCreateModal = true}
					class="group relative overflow-hidden rounded-2xl border border-white/10 px-5 py-3 text-sm font-medium text-white flex items-center gap-3 transition-all hover:-translate-y-1 hover:shadow-[0_25px_80px_-60px_rgba(168,119,255,0.6)]"
				>
					<span class="absolute inset-0 -z-10 bg-[linear-gradient(135deg,rgba(168,119,255,0.95),rgba(139,92,246,0.95))]"></span>
					<span class="text-lg">+</span>
					<span>Create persona</span>
				</button>
			</div>

			<div class="space-y-3 max-h-[500px] overflow-y-auto custom-scrollbar">
				{#each personas as persona (persona.id)}
					<button
						type="button"
						class="relative overflow-hidden rounded-3xl border border-white/8 bg-[rgba(15,29,46,0.9)] px-5 py-4 cursor-pointer transition-all hover:border-white/12 text-left w-full {selectedPersona?.id === persona.id ? 'border-[rgba(168,119,255,0.4)] bg-[rgba(168,119,255,0.08)]' : ''}"
						on:click={() => selectPersona(persona)}
						aria-pressed={selectedPersona?.id === persona.id}
						aria-label={`Select persona: ${persona.name}`}
					>
						{#if selectedPersona?.id === persona.id}
							<span class="absolute inset-0 -z-10 bg-[linear-gradient(135deg,rgba(168,119,255,0.12),rgba(139,92,246,0.1))]"></span>
						{/if}
						<div class="flex items-start justify-between gap-4">
							<div class="flex-1">
								<h3 class="text-sm font-semibold text-[color:var(--text-primary)]">{persona.name}</h3>
								<p class="text-xs text-[color:var(--text-muted)]/80 mt-1 mb-2">{persona.description || 'No description'}</p>
								<div class="flex items-center gap-4">
									<span class="text-[11px] uppercase tracking-[0.28em] text-[color:var(--text-muted)]">
										{getExampleCount(persona)} examples
									</span>
									<span class="{getQualityColor(getPersonaQualityScore(persona))} text-[11px] uppercase tracking-[0.28em] font-semibold">
										Quality: {formatPercentage(getPersonaQualityScore(persona))}
									</span>
								</div>
							</div>
							<span class="text-xs text-[color:var(--text-muted)]/60">
								{formatNumber(persona.quality_metrics?.total_posts || persona.qualityMetrics?.total_posts || 0)} posts
							</span>
						</div>
					</button>
				{:else}
					<div class="rounded-3xl border border-white/10 bg-[rgba(15,29,46,0.9)] px-6 py-8 text-center">
						<p class="text-[color:var(--text-muted)]">No personas created yet</p>
						<p class="text-xs text-[color:var(--text-muted)]/70 mt-2">Create your first persona to begin generating content</p>
					</div>
				{/each}
			</div>
		</div>

		<!-- Content Generation Panel -->
		<div class="rounded-4xl border border-white/10 bg-[rgba(12,24,40,0.85)] backdrop-blur-2xl p-6 space-y-6 shadow-[0_35px_140px_-95px_rgba(93,242,193,0.45)]">
			<div>
				<p class="text-[10px] uppercase tracking-[0.35em] text-[color:var(--text-muted)]">Content generation</p>
				<h3 class="text-lg font-semibold text-[color:var(--text-primary)] mt-1">Generate content</h3>
			</div>

			{#if selectedPersona}
				<div class="space-y-4">
					<!-- Selected Persona Info -->
					<div class="rounded-2xl border border-white/10 bg-[rgba(15,29,46,0.92)] px-5 py-4 space-y-2">
						<p class="text-[11px] uppercase tracking-[0.32em] text-[rgba(168,119,255,0.85)]">Selected persona</p>
						<p class="text-sm font-semibold text-[color:var(--text-primary)]">{selectedPersona.name}</p>
						<p class="text-xs text-[color:var(--text-muted)]/80">{selectedPersona.description || 'No description'}</p>
					</div>

					<!-- Topic Input -->
					<div>
						<label for="topic" class="block text-[11px] uppercase tracking-[0.35em] text-[color:var(--text-muted)] mb-3">Topic to write about</label>
						<textarea
							id="topic"
							bind:value={topic}
							placeholder="What do you want to write about? Describe the topic, context, and any specific angles..."
							class="w-full rounded-2xl border border-white/10 bg-[rgba(15,29,46,0.92)] px-5 py-4 text-sm text-[color:var(--text-primary)] placeholder-[color:var(--text-muted)]/50 focus:border-[rgba(168,119,255,0.4)] focus:bg-[rgba(168,119,255,0.08)] transition-all"
							rows="3"
						></textarea>
					</div>

					<!-- Platform Selection -->
					<div>
						<label for="platform" class="block text-[11px] uppercase tracking-[0.35em] text-[color:var(--text-muted)] mb-3">Target platform</label>
						<select
							id="platform"
							bind:value={platform}
							class="w-full rounded-2xl border border-white/10 bg-[rgba(15,29,46,0.92)] px-5 py-4 text-sm text-[color:var(--text-primary)] focus:border-[rgba(168,119,255,0.4)] focus:bg-[rgba(168,119,255,0.08)] transition-all"
						>
							<option value="twitter">Twitter/X</option>
							<option value="linkedin">LinkedIn</option>
							<option value="threads">Threads</option>
							<option value="telegram">Telegram</option>
						</select>
					</div>

					<!-- Generate Button -->
					<button
						on:click={generateContent}
						disabled={isLoading}
						class="group relative overflow-hidden rounded-2xl border border-white/10 px-5 py-4 text-sm font-medium text-white w-full transition-all hover:-translate-y-1 hover:shadow-[0_25px_80px_-60px_rgba(93,242,193,0.55)] disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:transform-none"
					>
						<span class="absolute inset-0 -z-10 bg-[linear-gradient(135deg,rgba(93,242,193,0.9),rgba(17,126,92,0.9))] disabled:from-gray-600 disabled:to-gray-700"></span>
						<span class="text-lg">{isLoading ? '⚡' : '✨'}</span>
						<span class="ml-2">{isLoading ? 'Generating...' : 'Generate content'}</span>
					</button>

					{#if selectedPersona.generatedContent}
						<!-- Generated Content Display -->
						<div class="space-y-4">
							<div class="rounded-2xl border border-white/10 bg-[rgba(15,29,46,0.92)] px-5 py-4 space-y-3">
								<p class="text-[11px] uppercase tracking-[0.32em] text-[rgba(93,242,193,0.85)]">Generated content</p>
								<p class="text-sm text-[color:var(--text-primary)] whitespace-pre-wrap">{selectedPersona.generatedContent}</p>
							</div>

							{#if selectedPersona.qualityMetrics}
								<!-- Enhanced Quality Metrics with RAG -->
								<div class="rounded-2xl border border-white/10 bg-[linear-gradient(135deg,rgba(78,192,255,0.15),rgba(93,242,193,0.12))] px-5 py-4 space-y-4">
									<p class="text-[11px] uppercase tracking-[0.32em] text-[rgba(78,192,255,0.85)]">Advanced quality metrics</p>

									<div class="grid grid-cols-2 gap-4">
										<div>
											<span class="text-[10px] uppercase tracking-[0.28em] text-[color:var(--text-muted)]">Voice consistency</span>
											<p class="{getQualityColor(selectedPersona.qualityMetrics?.voice_consistency)} text-sm font-semibold">
												{formatPercentage(selectedPersona.qualityMetrics?.voice_consistency)}
											</p>
										</div>
										<div>
											<span class="text-[10px] uppercase tracking-[0.28em] text-[color:var(--text-muted)]">Authenticity</span>
											<p class="{getQualityColor(selectedPersona.qualityMetrics?.authenticity_prediction)} text-sm font-semibold">
												{formatPercentage(selectedPersona.qualityMetrics?.authenticity_prediction)}
											</p>
										</div>
										<div>
											<span class="text-[10px] uppercase tracking-[0.28em] text-[color:var(--text-muted)]">Engagement</span>
											<p class="{getQualityColor(selectedPersona.qualityMetrics?.engagement_potential)} text-sm font-semibold">
												{formatPercentage(selectedPersona.qualityMetrics?.engagement_potential)}
											</p>
										</div>
										<div>
											<span class="text-[10px] uppercase tracking-[0.28em] text-[color:var(--text-muted)]">Overall</span>
											<p class="{getQualityColor(selectedPersona.qualityMetrics?.overall_quality)} text-sm font-semibold">
												{formatPercentage(selectedPersona.qualityMetrics?.overall_quality)}
											</p>
										</div>
									</div>

									{#if selectedPersona.qualityMetrics.topic_relevance !== undefined}
										<div class="border-t border-white/10 pt-3">
											<p class="text-[11px] uppercase tracking-[0.32em] text-[rgba(168,119,255,0.85)] mb-3">RAG Intelligence</p>
											<div class="space-y-2">
												<div class="flex justify-between items-center">
													<span class="text-[10px] uppercase tracking-[0.28em] text-[color:var(--text-muted)]">Topic relevance</span>
													<span class="{getQualityColor(selectedPersona.qualityMetrics.topic_relevance)} text-sm font-semibold">
														{(selectedPersona.qualityMetrics.topic_relevance * 100).toFixed(0)}%
													</span>
												</div>
												<div class="flex justify-between items-center">
													<span class="text-[10px] uppercase tracking-[0.28em] text-[color:var(--text-muted)]">RAG examples used</span>
													<span class="text-[10px] text-[rgba(168,119,255,0.9)]">
														{selectedPersona.ragSources?.length || 0}
													</span>
												</div>
											</div>
										</div>
									{/if}
								</div>

								<!-- RAG Sources Display -->
								{#if selectedPersona.ragSources && selectedPersona.ragSources.length > 0}
									<div class="rounded-2xl border border-white/10 bg-[rgba(15,29,46,0.92)] px-5 py-4 space-y-3">
										<p class="text-[11px] uppercase tracking-[0.32em] text-[rgba(168,119,255,0.85)]">Relevant examples used</p>
										<div class="space-y-2 max-h-40 overflow-y-auto custom-scrollbar">
											{#each selectedPersona.ragSources as source, index}
												<div class="text-xs p-2 bg-[rgba(168,119,255,0.1)] rounded-lg">
													<div class="flex justify-between items-start mb-1">
														<span class="text-[rgba(168,119,255,0.9)] font-medium">Example {index + 1}</span>
														<span class="text-[rgba(93,242,193,0.9)]">
															{(source.relevance * 100).toFixed(0)}% match
														</span>
													</div>
													<p class="text-[color:var(--text-muted)]">{source.content}</p>
												</div>
											{/each}
										</div>
									</div>
								{/if}
							{/if}
						</div>
					{/if}
				</div>
			{:else}
				<div class="rounded-2xl border border-white/10 bg-[rgba(15,29,46,0.92)] px-6 py-8 text-center">
					<p class="text-[color:var(--text-muted)]">Select a persona to generate content</p>
					<p class="text-xs text-[color:var(--text-muted)]/70 mt-2">Choose from your created personas or create a new one</p>
				</div>
			{/if}
		</div>
	</section>

	{#if selectedPersona}
		<section class="grid gap-6 xl:grid-cols-[minmax(0,1.4fr)_minmax(0,0.9fr)]">
			<!-- Persona Intelligence -->
			<div class="rounded-4xl border border-white/10 bg-[rgba(12,24,40,0.9)] backdrop-blur-2xl p-6 space-y-5 shadow-[0_35px_140px_-95px_rgba(168,119,255,0.45)]">
				<div class="flex items-center justify-between">
					<div>
						<p class="text-[10px] uppercase tracking-[0.35em] text-[color:var(--text-muted)]">Persona intelligence</p>
						<h3 class="text-lg font-semibold text-[color:var(--text-primary)] mt-1">{selectedPersona.name}</h3>
					</div>
					<button
						type="button"
						class="text-xs rounded-2xl border border-white/10 px-3 py-1 text-[color:var(--text-muted)] hover:text-[color:var(--text-primary)]"
						on:click={() => {
							if (selectedPersona?.id) {
								loadPersonaInsights(selectedPersona.id);
								loadPersonaExampleSnippets(selectedPersona.id);
							}
						}}
					>
						Refresh
					</button>
				</div>

				{#if isDetailsLoading}
					<p class="text-xs text-[color:var(--text-muted)]/70">Loading persona analytics…</p>
				{:else if personaPerformance}
					<div class="grid gap-4 md:grid-cols-3">
						{#if personaPerformance.quality_metrics}
							<div class="rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
								<p class="text-[10px] uppercase tracking-[0.32em] text-[color:var(--text-muted)]">Authenticity</p>
								<p class={`text-xl font-semibold ${getQualityColor(personaPerformance.quality_metrics.authenticity || 0)}`}>
									{formatPercentage(personaPerformance.quality_metrics.authenticity)}
								</p>
							</div>
							<div class="rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
								<p class="text-[10px] uppercase tracking-[0.32em] text-[color:var(--text-muted)]">Engagement</p>
								<p class={`text-xl font-semibold ${getQualityColor(personaPerformance.quality_metrics.engagement || 0)}`}>
									{formatPercentage(personaPerformance.quality_metrics.engagement)}
								</p>
							</div>
							<div class="rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
								<p class="text-[10px] uppercase tracking-[0.32em] text-[color:var(--text-muted)]">Voice consistency</p>
								<p class={`text-xl font-semibold ${getQualityColor(personaPerformance.quality_metrics.voice_consistency || 0)}`}>
									{formatPercentage(personaPerformance.quality_metrics.voice_consistency)}
								</p>
							</div>
						{/if}
					</div>

					<div class="grid gap-4 md:grid-cols-2">
						<div class="rounded-2xl border border-white/10 bg-[rgba(15,29,46,0.92)] px-4 py-4 space-y-2">
							<p class="text-[11px] uppercase tracking-[0.32em] text-[rgba(168,119,255,0.85)]">Voice patterns</p>
							<div class="text-xs text-[color:var(--text-muted)]/80 space-y-2">
								<p>Avg sentence length: {personaPerformance.voice_patterns?.sentence_length || 0} chars</p>
								<p>Technical density: {formatPercentage(personaPerformance.voice_patterns?.technical_density)}</p>
								<p>Emotional intensity: {formatPercentage(personaPerformance.voice_patterns?.emotional_intensity)}</p>
							</div>
						</div>
						<div class="rounded-2xl border border-white/10 bg-[rgba(15,29,46,0.92)] px-4 py-4 space-y-2">
							<p class="text-[11px] uppercase tracking-[0.32em] text-[rgba(93,242,193,0.85)]">RAG analytics</p>
							<div class="text-xs text-[color:var(--text-muted)]/80 space-y-2">
								<p>Examples stored: {formatNumber(personaPerformance.rag_analytics?.total_examples_stored || 0)}</p>
								<p>Embedded: {formatNumber(personaPerformance.rag_analytics?.examples_with_embeddings || 0)}</p>
								<p>Status: {personaPerformance.rag_analytics?.storage_status || 'unknown'}</p>
							</div>
						</div>
					</div>
				{:else}
					<p class="text-xs text-[color:var(--text-muted)]/70">No analytics available for this persona yet.</p>
				{/if}
			</div>

			<!-- Persona Knowledge -->
			<div class="space-y-6">
				<div class="rounded-4xl border border-white/10 bg-[rgba(12,24,40,0.9)] backdrop-blur-2xl p-6 space-y-4">
					<p class="text-[10px] uppercase tracking-[0.35em] text-[color:var(--text-muted)]">Optimization suggestions</p>
					{#if personaPerformance?.optimization_suggestions?.length}
						<ul class="space-y-3 text-sm text-[color:var(--text-muted)]">
							{#each personaPerformance.optimization_suggestions as suggestion}
								<li class="rounded-2xl border border-white/10 bg-white/5 px-4 py-3">{suggestion}</li>
							{/each}
						</ul>
					{:else}
						<p class="text-xs text-[color:var(--text-muted)]/70">No suggestions yet.</p>
					{/if}
				</div>

				<div class="rounded-4xl border border-white/10 bg-[rgba(12,24,40,0.9)] backdrop-blur-2xl p-6 space-y-4">
					<div class="flex items-center justify-between">
						<p class="text-[10px] uppercase tracking-[0.35em] text-[color:var(--text-muted)]">Latest rewrites</p>
						{#if isRewritesLoading}
							<span class="text-xs text-[color:var(--text-muted)]/70">Syncing…</span>
						{/if}
					</div>
					{#if latestRewrites.length}
						<div class="space-y-3 max-h-80 overflow-y-auto custom-scrollbar">
							{#each latestRewrites as rewrite}
								<div class="rounded-3xl border border-white/10 bg-white/5 p-4 text-xs text-[color:var(--text-muted)]/90 space-y-3">
									<div class="flex items-center justify-between gap-4 text-[color:var(--text-muted)]/75">
										<div class="flex flex-wrap gap-2 items-center text-[11px] uppercase tracking-[0.25em]">
											<span>{rewrite.platform || 'rewrite'}</span>
											{#if rewrite.ready_for_posting}
												<span class="rounded-full border border-white/20 px-2 py-0.5 text-[rgba(93,242,193,0.85)]">
													Ready
												</span>
											{/if}
										</div>
										<span class={`text-sm font-semibold ${getQualityBadge(rewrite.score ?? 0)}`}>
											Quality {formatQualityScore(rewrite.score)}
										</span>
									</div>

									<p class="text-[color:var(--text-primary)] text-sm leading-relaxed">{rewrite.content}</p>

									<div class="flex flex-wrap items-center justify-between gap-3 text-[color:var(--text-muted)]/70">
										<div class="space-x-3 text-[11px] uppercase tracking-[0.28em]">
											<span>ID: {rewrite.id ?? '—'}</span>
											<span>·</span>
											<span>{rewrite.updated_at ? new Date(rewrite.updated_at).toLocaleString() : rewrite.created_at ? new Date(rewrite.created_at).toLocaleString() : '—'}</span>
										</div>
									</div>
								</div>
							{/each}
						</div>
					{:else if !isRewritesLoading}
						<p class="text-xs text-[color:var(--text-muted)]/70">No rewrites recorded for this persona yet.</p>
					{/if}
				</div>

				<div class="rounded-4xl border border-white/10 bg-[rgba(12,24,40,0.9)] backdrop-blur-2xl p-6 space-y-4">
					<div class="flex items-center justify-between">
						<p class="text-[10px] uppercase tracking-[0.35em] text-[color:var(--text-muted)]">Training examples</p>
						{#if isExamplesLoading}
							<span class="text-xs text-[color:var(--text-muted)]/70">Loading…</span>
						{/if}
					</div>
					{#if personaExamples.length}
						<div class="space-y-3 max-h-80 overflow-y-auto custom-scrollbar">
							{#each personaExamples as example}
								<div class="rounded-3xl border border-white/10 bg-white/5 p-4 text-xs text-[color:var(--text-muted)]/90 space-y-3">
									<div class="flex items-center justify-between gap-4 text-[color:var(--text-muted)]/75">
										<div class="flex flex-wrap gap-2 items-center text-[11px] uppercase tracking-[0.25em]">
											<span>{example.platform || 'threads'}</span>
											{#if example.content_type}
												<span class="text-[color:var(--text-muted)]/60">·</span>
												<span>{example.content_type}</span>
											{/if}
											{#if example.structure}
												<span class="text-[color:var(--text-muted)]/60">·</span>
												<span>{example.structure}</span>
											{/if}
										</div>
									</div>

									<p class="text-[color:var(--text-primary)] text-sm leading-relaxed">{example.content}</p>

									<div class="flex flex-wrap items-center justify-between gap-3 text-[color:var(--text-muted)]/70">
										<div class="space-x-3 text-[11px] uppercase tracking-[0.28em]">
											<span>ID: {example.id || example.example_id || '—'}</span>
											<span>·</span>
											<span>{example.created_at ? new Date(example.created_at).toLocaleDateString() : '—'}</span>
										</div>
										{#if example.notes}
											<span class="rounded-full border border-white/15 px-3 py-1 text-[10px] tracking-[0.2em] uppercase">{example.notes}</span>
										{/if}
									</div>
								</div>
							{/each}
						</div>
					{:else if !isExamplesLoading}
						<p class="text-xs text-[color:var(--text-muted)]/70">No examples found for this persona.</p>
					{/if}
				</div>
			</div>
		</section>
	{/if}
</div>

<!-- Create Persona Modal -->
{#if showCreateModal}
	<div class="fixed inset-0 z-50 flex items-center justify-center p-6">
		<!-- Backdrop -->
		<button
			type="button"
			class="absolute inset-0 bg-[rgba(4,7,18,0.85)] backdrop-blur-md"
			on:click={() => showCreateModal = false}
			aria-label="Close modal"
		></button>

		<!-- Modal Content -->
		<div class="relative max-w-4xl w-full max-h-[90vh] overflow-y-auto rounded-4xl border border-white/10 bg-[rgba(12,24,40,0.95)] backdrop-blur-2xl shadow-[0_50px_180px_-110px_rgba(168,119,255,0.6)] p-8 space-y-6">
			<div class="flex items-center justify-between">
				<div>
					<p class="text-[11px] uppercase tracking-[0.48em] text-[rgba(168,119,255,0.85)]">Create persona</p>
					<h2 class="text-2xl font-semibold text-[color:var(--text-primary)] mt-1">Advanced AI persona</h2>
				</div>
				<button
					on:click={() => showCreateModal = false}
					class="text-[color:var(--text-muted)] hover:text-[color:var(--text-primary)] transition-colors"
					aria-label="Close modal"
				>
					<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
					</svg>
				</button>
			</div>

			<div class="space-y-6">
				<!-- Persona Name -->
				<div>
					<label for="persona-name" class="block text-[11px] uppercase tracking-[0.35em] text-[color:var(--text-muted)] mb-3">Persona name</label>
					<input
						id="persona-name"
						type="text"
						bind:value={personaName}
						placeholder="e.g., Tech Investor, Marketing Expert, Startup Founder"
						class="w-full rounded-2xl border border-white/10 bg-[rgba(15,29,46,0.92)] px-5 py-4 text-sm text-[color:var(--text-primary)] placeholder-[color:var(--text-muted)]/50 focus:border-[rgba(168,119,255,0.4)] focus:bg-[rgba(168,119,255,0.08)] transition-all"
					/>
				</div>

				<!-- Description -->
				<div>
					<label for="persona-description" class="block text-[11px] uppercase tracking-[0.35em] text-[color:var(--text-muted)] mb-3">Description (optional)</label>
					<textarea
						id="persona-description"
						bind:value={personaDescription}
						placeholder="Brief description of this persona's expertise, tone, and communication style"
						class="w-full rounded-2xl border border-white/10 bg-[rgba(15,29,46,0.92)] px-5 py-4 text-sm text-[color:var(--text-primary)] placeholder-[color:var(--text-muted)]/50 focus:border-[rgba(168,119,255,0.4)] focus:bg-[rgba(168,119,255,0.08)] transition-all"
						rows="2"
					></textarea>
				</div>

				<!-- Examples -->
				<div>
					<fieldset>
						<legend class="block text-[11px] uppercase tracking-[0.35em] text-[color:var(--text-muted)] mb-3">
							Example posts ({examples.filter(ex => ex.trim()).length} added, minimum 3)
						</legend>
						<div class="space-y-3">
							{#each examples as example, index}
								<div class="flex gap-3">
									<textarea
										id="persona-example-{index}"
										bind:value={examples[index]}
										placeholder="Paste an example post here to teach this persona's voice..."
										class="flex-1 rounded-2xl border border-white/10 bg-[rgba(15,29,46,0.92)] px-5 py-4 text-sm text-[color:var(--text-primary)] placeholder-[color:var(--text-muted)]/50 focus:border-[rgba(168,119,255,0.4)] focus:bg-[rgba(168,119,255,0.08)] transition-all"
										rows="2"
										aria-label={`Example post ${index + 1}`}
									></textarea>
									{#if examples.length > 1}
										<button
											type="button"
											on:click={() => removeExample(index)}
											class="rounded-2xl border border-white/10 bg-[rgba(248,113,113,0.1)] px-3 py-2 text-[rgba(248,113,113,0.9)] hover:bg-[rgba(248,113,113,0.2)] transition-colors"
											aria-label={`Remove example post ${index + 1}`}
										>
											<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
											</svg>
										</button>
									{/if}
								</div>
							{/each}
							</div>
					</fieldset>
					<button
						type="button"
						on:click={addExample}
						class="mt-4 rounded-2xl border border-white/10 bg-[rgba(168,119,255,0.1)] px-4 py-3 text-sm text-[rgba(168,119,255,0.9)] hover:bg-[rgba(168,119,255,0.2)] transition-colors"
					>
						+ Add example post
					</button>
				</div>

				<!-- Action Buttons -->
				<div class="flex justify-end gap-4 pt-4">
					<button
						on:click={() => showCreateModal = false}
						class="rounded-2xl border border-white/10 bg-[rgba(15,29,46,0.92)] px-6 py-3 text-sm text-[color:var(--text-muted)] hover:text-[color:var(--text-primary)] transition-colors"
					>
						Cancel
					</button>
					<button
						on:click={createPersona}
						disabled={isLoading}
						class="group relative overflow-hidden rounded-2xl border border-white/10 px-6 py-3 text-sm font-medium text-white transition-all hover:-translate-y-1 hover:shadow-[0_25px_80px_-60px_rgba(168,119,255,0.6)] disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:transform-none"
					>
						<span class="absolute inset-0 -z-10 bg-[linear-gradient(135deg,rgba(168,119,255,0.95),rgba(139,92,246,0.95))] disabled:from-gray-600 disabled:to-gray-700"></span>
						<span>{isLoading ? 'Creating persona...' : 'Create persona'}</span>
					</button>
				</div>
			</div>
		</div>
	</div>
{/if}

<style>
	:global(.custom-scrollbar)::-webkit-scrollbar {
		width: 6px;
	}

	:global(.custom-scrollbar)::-webkit-scrollbar-track {
		background: rgba(255, 255, 255, 0.05);
		border-radius: 3px;
	}

	:global(.custom-scrollbar)::-webkit-scrollbar-thumb {
		background: rgba(168, 119, 255, 0.3);
		border-radius: 3px;
	}

	:global(.custom-scrollbar)::-webkit-scrollbar-thumb:hover {
		background: rgba(168, 119, 255, 0.5);
	}
</style>
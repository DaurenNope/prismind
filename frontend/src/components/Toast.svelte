<script lang="ts">
	import { onMount } from 'svelte';
	import { toast, type ToastMessage } from '$lib/toast';

	let toasts: ToastMessage[] = [];
	let unsubscribe: () => void;

	onMount(() => {
		unsubscribe = toast.subscribe((toast) => {
			if (toast.message === '') {
				// This is a removal notification
				toasts = toasts.filter(t => t.id !== toast.id);
			} else {
				// This is a new toast
				toasts = [...toasts, toast];
			}
		});

		return () => {
			unsubscribe();
		};
	});

	function removeToast(id: string) {
		toast.remove(id);
	}

	function getToastStyles(type: ToastMessage['type']) {
		switch (type) {
			case 'success':
				return 'bg-green-500 border-green-600 text-white';
			case 'error':
				return 'bg-red-500 border-red-600 text-white';
			case 'warning':
				return 'bg-amber-500 border-amber-600 text-white';
			case 'info':
				return 'bg-blue-500 border-blue-600 text-white';
			default:
				return 'bg-gray-500 border-gray-600 text-white';
		}
	}

	function getIcon(type: ToastMessage['type']) {
		switch (type) {
			case 'success':
				return '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>';
			case 'error':
				return '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>';
			case 'warning':
				return '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg>';
			case 'info':
				return '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>';
			default:
				return '';
		}
	}
</script>

<div class="fixed bottom-4 right-4 z-50 space-y-2">
	{#each toasts as toast (toast.id)}
		<div
			class={`${getToastStyles(toast.type)} flex items-center gap-3 p-4 rounded-lg border shadow-lg transform transition-all duration-300 animate-in slide-in-from-right-5`}
			class:bg-opacity-90={toast.type === 'warning' || toast.type === 'info'}
			role="alert"
		>
			<div class="flex-shrink-0">
				{@html getIcon(toast.type)}
			</div>
			<div class="flex-1">
				<p class="text-sm font-medium">{toast.message}</p>
			</div>
			<button
				on:click={() => removeToast(toast.id)}
				class="flex-shrink-0 hover:opacity-70 transition-opacity"
				aria-label="Dismiss notification"
			>
				<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
				</svg>
			</button>
		</div>
	{/each}
</div>

<style>
	@keyframes slide-in-from-right-5 {
		from {
			transform: translateX(100%);
			opacity: 0;
		}
		to {
			transform: translateX(0);
			opacity: 1;
		}
	}

	.animate-in {
		animation-timing-function: cubic-bezier(0.4, 0, 0.2, 1);
		animation-duration: 150ms;
		animation-fill-mode: forwards;
	}

	.slide-in-from-right-5 {
		animation-name: slide-in-from-right-5;
	}
</style>
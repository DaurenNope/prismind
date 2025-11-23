import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/svelte';
import DashboardPage from '../src/routes/+page.svelte';
import * as dashboardService from '../src/lib/services/dashboard';

// Mock the dashboard service
vi.mock('../src/lib/services/dashboard', () => ({
  fetchDashboardOverview: vi.fn(),
}));

// Mock fetch for stats endpoint
global.fetch = vi.fn() as typeof fetch;

describe('Dashboard Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should load dashboard stats on mount', async () => {
    const mockStats = {
      total_posts: 100,
      platforms: { twitter: 50, reddit: 30, threads: 20 },
      unanalyzed: 25,
      analyzed: 75,
    };

    const mockOverview = {
      system_heartbeat: {
        summary: 'System operational',
        last_run: new Date().toISOString(),
        next_cycle_label: 'Next cycle in 1 hour',
      },
      operations: [],
      workflow: {
        rewrites: { queue: 5, total_transformations: 100, last_activity: '2024-01-01' },
        collectors: { platforms_monitored: 3, healthy: 3, last_activity: '2024-01-01' },
        learning: { posted_total: 50, with_engagement: 30, last_posted: '2024-01-01' },
      },
    };

    vi.mocked(global.fetch).mockResolvedValue({
      ok: true,
      json: async () => mockStats,
    } as Response);

    vi.mocked(dashboardService.fetchDashboardOverview).mockResolvedValue(mockOverview);

    render(DashboardPage);

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/dashboard/stats'),
        expect.any(Object)
      );
    });
  });

  it('should display error message when stats fail to load', async () => {
    vi.mocked(global.fetch).mockRejectedValue(new Error('Network error'));

    render(DashboardPage);

    await waitFor(() => {
      expect(screen.queryByText(/error/i)).toBeInTheDocument();
    });
  });

  it('should display dashboard stats correctly', async () => {
    const mockStats = {
      total_posts: 100,
      platforms: { twitter: 50, reddit: 30, threads: 20 },
      unanalyzed: 25,
      analyzed: 75,
    };

    vi.mocked(global.fetch).mockResolvedValue({
      ok: true,
      json: async () => mockStats,
    } as Response);

    vi.mocked(dashboardService.fetchDashboardOverview).mockResolvedValue({
      system_heartbeat: {
        summary: 'System operational',
        last_run: null,
        next_cycle_label: '',
      },
      operations: [],
      workflow: {
        rewrites: { queue: 0, total_transformations: 0, last_activity: '' },
        collectors: { platforms_monitored: 0, healthy: 0, last_activity: '' },
        learning: { posted_total: 0, with_engagement: 0, last_posted: null },
      },
    });

    render(DashboardPage);

    await waitFor(() => {
      expect(screen.queryByText(/100/)).toBeInTheDocument();
    });
  });
});







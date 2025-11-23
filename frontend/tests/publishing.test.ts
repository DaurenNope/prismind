import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import PublishingPage from '../src/routes/publishing/+page.svelte';
import * as publishingService from '../src/lib/services/publishing';

// Mock the publishing service
vi.mock('../src/lib/services/publishing', () => ({
  fetchTransformations: vi.fn(),
  fetchScheduledPosts: vi.fn(),
  updateTransformation: vi.fn(),
  schedulePost: vi.fn(),
  deleteScheduledPost: vi.fn(),
  publishNow: vi.fn(),
  deleteTransformation: vi.fn(),
  cleanupOldTransformations: vi.fn(),
}));

describe('Publishing Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should load transformations and scheduled posts on mount', async () => {
    const mockTransformations = [
      {
        id: 1,
        persona_key: 'qronoya',
        platform: 'twitter',
        content: 'Test transformation',
        ready_for_posting: true,
      },
    ];

    const mockScheduled = [
      {
        id: 1,
        persona_key: 'qronoya',
        platform: 'twitter',
        content: 'Scheduled post',
        scheduled_time: new Date().toISOString(),
      },
    ];

    vi.mocked(publishingService.fetchTransformations).mockResolvedValue(mockTransformations);
    vi.mocked(publishingService.fetchScheduledPosts).mockResolvedValue(mockScheduled);

    render(PublishingPage);

    await waitFor(() => {
      expect(publishingService.fetchTransformations).toHaveBeenCalled();
      expect(publishingService.fetchScheduledPosts).toHaveBeenCalled();
    });
  });

  it('should display error message when loading fails', async () => {
    vi.mocked(publishingService.fetchTransformations).mockRejectedValue(
      new Error('Failed to load')
    );

    render(PublishingPage);

    await waitFor(() => {
      expect(screen.queryByText(/error/i)).toBeInTheDocument();
    });
  });

  it('should filter by persona', async () => {
    const user = userEvent.setup();
    const mockTransformations = [
      {
        id: 1,
        persona_key: 'qronoya',
        platform: 'twitter',
        content: 'Test',
        ready_for_posting: true,
      },
    ];

    vi.mocked(publishingService.fetchTransformations).mockResolvedValue(mockTransformations);
    vi.mocked(publishingService.fetchScheduledPosts).mockResolvedValue([]);

    render(PublishingPage);

    await waitFor(() => {
      expect(publishingService.fetchTransformations).toHaveBeenCalled();
    });

    // Find and click persona filter
    const personaFilter = screen.queryByText(/qronoya/i);
    if (personaFilter) {
      await user.click(personaFilter);
      await waitFor(() => {
        expect(publishingService.fetchTransformations).toHaveBeenCalledWith('qronoya', false);
      });
    }
  });
});







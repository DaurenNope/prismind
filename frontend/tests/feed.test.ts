import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/svelte';
import FeedPage from '../src/routes/feed/+page.svelte';

// Mock fetch
global.fetch = vi.fn() as typeof fetch;

describe('Feed Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should load posts on mount', async () => {
    const mockPosts = {
      posts: [
        {
          id: '1',
          post_id: 'post1',
          platform: 'twitter',
          content: 'Test post content',
          created_at: new Date().toISOString(),
        },
      ],
      total: 1,
    };

    vi.mocked(global.fetch).mockResolvedValue({
      ok: true,
      json: async () => mockPosts,
    } as Response);

    render(FeedPage);

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/posts'),
        expect.any(Object)
      );
    });
  });

  it('should display error message when posts fail to load', async () => {
    vi.mocked(global.fetch).mockResolvedValue({
      ok: false,
      status: 500,
      json: async () => ({ detail: 'Server error' }),
    } as Response);

    render(FeedPage);

    await waitFor(() => {
      expect(screen.queryByText(/error/i)).toBeInTheDocument();
    });
  });

  it('should display empty state when no posts', async () => {
    vi.mocked(global.fetch).mockResolvedValue({
      ok: true,
      json: async () => ({ posts: [], total: 0 }),
    } as Response);

    render(FeedPage);

    await waitFor(() => {
      expect(screen.queryByText(/no matching signals/i)).toBeInTheDocument();
    });
  });

  it('should filter posts by platform', async () => {
    const mockPosts = {
      posts: [
        {
          id: '1',
          post_id: 'post1',
          platform: 'twitter',
          content: 'Twitter post',
        },
        {
          id: '2',
          post_id: 'post2',
          platform: 'reddit',
          content: 'Reddit post',
        },
      ],
      total: 2,
    };

    vi.mocked(global.fetch).mockResolvedValue({
      ok: true,
      json: async () => mockPosts,
    } as Response);

    render(FeedPage);

    await waitFor(() => {
      expect(screen.queryByText(/twitter/i)).toBeInTheDocument();
    });
  });
});







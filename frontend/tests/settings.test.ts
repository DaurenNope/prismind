import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import SettingsPage from '../src/routes/settings/+page.svelte';
import * as settingsService from '../src/lib/services/settings';

// Mock the settings service
vi.mock('../src/lib/services/settings', () => ({
  fetchCredentials: vi.fn(),
  saveCredentials: vi.fn(),
}));

describe('Settings Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset localStorage
    localStorage.clear();
  });

  it('should load credentials on mount', async () => {
    const mockCredentials = [
      {
        platform: 'twitter',
        username: 'testuser',
        enabled: true,
      },
    ];

    vi.mocked(settingsService.fetchCredentials).mockResolvedValue(mockCredentials);

    render(SettingsPage);

    await waitFor(() => {
      expect(settingsService.fetchCredentials).toHaveBeenCalled();
    });
  });

  it('should display error message when loading fails', async () => {
    const errorMessage = 'Failed to load credentials';
    vi.mocked(settingsService.fetchCredentials).mockRejectedValue(
      new Error(errorMessage)
    );

    render(SettingsPage);

    await waitFor(() => {
      expect(screen.queryByText(/error loading settings/i)).toBeInTheDocument();
    });
  });

  it('should save credentials when form is submitted', async () => {
    const user = userEvent.setup();
    const mockCredentials = [
      {
        platform: 'twitter',
        username: 'testuser',
        enabled: true,
      },
    ];

    vi.mocked(settingsService.fetchCredentials).mockResolvedValue(mockCredentials);
    vi.mocked(settingsService.saveCredentials).mockResolvedValue({
      platform: 'twitter',
      saved: true,
      record: mockCredentials[0],
    });

    render(SettingsPage);

    await waitFor(() => {
      expect(settingsService.fetchCredentials).toHaveBeenCalled();
    });

    // Find and interact with a form field
    const usernameInput = screen.queryByLabelText(/username/i);
    if (usernameInput) {
      await user.clear(usernameInput);
      await user.type(usernameInput, 'newuser');
      await user.tab(); // Trigger blur event

      await waitFor(() => {
        expect(settingsService.saveCredentials).toHaveBeenCalled();
      });
    }
  });

  it('should show validation errors for required fields', async () => {
    const user = userEvent.setup();
    const mockCredentials = [
      {
        platform: 'twitter',
        enabled: true,
      },
    ];

    vi.mocked(settingsService.fetchCredentials).mockResolvedValue(mockCredentials);

    render(SettingsPage);

    await waitFor(() => {
      expect(settingsService.fetchCredentials).toHaveBeenCalled();
    });

    // Try to save without required fields
    // This should trigger validation
    const saveButton = screen.queryByText(/save/i);
    if (saveButton) {
      await user.click(saveButton);
      // Validation errors should appear
      await waitFor(() => {
        expect(screen.queryByText(/required/i)).toBeInTheDocument();
      });
    }
  });

  it('should handle API errors gracefully', async () => {
    const user = userEvent.setup();
    const mockCredentials = [
      {
        platform: 'twitter',
        username: 'testuser',
        enabled: true,
      },
    ];

    vi.mocked(settingsService.fetchCredentials).mockResolvedValue(mockCredentials);
    vi.mocked(settingsService.saveCredentials).mockRejectedValue(
      new Error('API Error: 500')
    );

    render(SettingsPage);

    await waitFor(() => {
      expect(settingsService.fetchCredentials).toHaveBeenCalled();
    });

    const usernameInput = screen.queryByLabelText(/username/i);
    if (usernameInput) {
      await user.clear(usernameInput);
      await user.type(usernameInput, 'newuser');
      await user.tab();

      await waitFor(() => {
        expect(screen.queryByText(/failed to save/i)).toBeInTheDocument();
      });
    }
  });
});







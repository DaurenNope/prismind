import { describe, it, expect, beforeEach, vi } from 'vitest';
import { fetchCredentials, saveCredentials } from '../../src/lib/services/settings';
import { API_BASE } from '../../src/lib/config';

// Mock fetch
global.fetch = vi.fn();

describe('Settings Service', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('fetchCredentials', () => {
    it('should fetch credentials successfully', async () => {
      const mockCredentials = [
        {
          platform: 'twitter',
          username: 'testuser',
          enabled: true,
        },
      ];

      vi.mocked(global.fetch).mockResolvedValue({
        ok: true,
        json: async () => ({ platforms: mockCredentials }),
      } as Response);

      const result = await fetchCredentials();

      expect(result).toEqual(mockCredentials);
      expect(global.fetch).toHaveBeenCalledWith(
        `${API_BASE}/api/settings/credentials`,
        expect.objectContaining({
          method: 'GET',
        })
      );
    });

    it('should handle API errors', async () => {
      vi.mocked(global.fetch).mockResolvedValue({
        ok: false,
        status: 500,
        json: async () => ({ detail: 'Internal server error' }),
      } as Response);

      await expect(fetchCredentials()).rejects.toThrow('Internal server error');
    });

    it('should handle network errors', async () => {
      vi.mocked(global.fetch).mockRejectedValue(new Error('Network error'));

      await expect(fetchCredentials()).rejects.toThrow('Network error');
    });
  });

  describe('saveCredentials', () => {
    it('should save credentials successfully', async () => {
      const credentials = {
        platform: 'twitter',
        username: 'testuser',
        password: 'testpass',
        enabled: true,
      };

      const mockResponse = {
        platform: 'twitter',
        saved: true,
        record: credentials,
      };

      vi.mocked(global.fetch).mockResolvedValue({
        ok: true,
        json: async () => mockResponse,
      } as Response);

      const result = await saveCredentials(credentials);

      expect(result).toEqual(mockResponse);
      expect(global.fetch).toHaveBeenCalledWith(
        `${API_BASE}/api/settings/credentials`,
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify(credentials),
        })
      );
    });

    it('should handle validation errors', async () => {
      const credentials = {
        platform: 'twitter',
        enabled: true,
      };

      vi.mocked(global.fetch).mockResolvedValue({
        ok: false,
        status: 422,
        json: async () => ({ detail: 'Validation error' }),
      } as Response);

      await expect(saveCredentials(credentials)).rejects.toThrow('Validation error');
    });
  });
});







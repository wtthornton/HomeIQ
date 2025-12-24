/**
 * Device Name Cache Utility
 * Provides caching and fallback logic for device name resolution
 * 
 * Features:
 * - In-memory cache with TTL
 * - localStorage persistence
 * - Smart fallback for compound IDs
 * - Batch processing support
 */

interface CacheEntry {
  name: string;
  timestamp: number;
  source: 'api' | 'fallback' | 'cache';
}

const CACHE_TTL = 24 * 60 * 60 * 1000; // 24 hours
const STORAGE_KEY = 'homeiq_device_names_cache';

class DeviceNameCache {
  private memoryCache: Map<string, CacheEntry> = new Map();
  private pendingRequests: Map<string, Promise<string>> = new Map();

  constructor() {
    this.loadFromStorage();
  }

  /**
   * Load cache from localStorage
   */
  private loadFromStorage(): void {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const data = JSON.parse(stored);
        const now = Date.now();
        Object.entries(data).forEach(([key, value]: [string, any]) => {
          // Only load entries that haven't expired
          if (value.timestamp && (now - value.timestamp) < CACHE_TTL) {
            this.memoryCache.set(key, value as CacheEntry);
          }
        });
      }
    } catch (error) {
      console.warn('Failed to load device name cache from storage:', error);
    }
  }

  /**
   * Save cache to localStorage
   */
  private saveToStorage(): void {
    try {
      const data: Record<string, CacheEntry> = {};
      this.memoryCache.forEach((value, key) => {
        data[key] = value;
      });
      localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
    } catch (error) {
      console.warn('Failed to save device name cache to storage:', error);
    }
  }

  /**
   * Get device name from cache
   */
  get(deviceId: string): string | null {
    const entry = this.memoryCache.get(deviceId);
    if (!entry) return null;

    // Check if entry is expired
    const now = Date.now();
    if ((now - entry.timestamp) >= CACHE_TTL) {
      this.memoryCache.delete(deviceId);
      return null;
    }

    return entry.name;
  }

  /**
   * Set device name in cache
   */
  set(deviceId: string, name: string, source: 'api' | 'fallback' | 'cache' = 'api'): void {
    const entry: CacheEntry = {
      name,
      timestamp: Date.now(),
      source,
    };
    this.memoryCache.set(deviceId, entry);
    this.saveToStorage();
  }

  /**
   * Generate fallback name for device ID
   */
  getFallbackName(deviceId: string): string {
    // Check cache first
    const cached = this.get(deviceId);
    if (cached) return cached;

    // Handle compound entity IDs (e.g., "hash1+hash2")
    if (deviceId.includes('+')) {
      const parts = deviceId.split('+');
      if (parts.length === 2) {
        const part1 = this.extractReadablePart(parts[0]);
        const part2 = this.extractReadablePart(parts[1]);
        const fallback = `Co-occurrence: ${part1} + ${part2}`;
        this.set(deviceId, fallback, 'fallback');
        return fallback;
      }
    }

    // Try to extract readable name from device ID
    const readable = this.extractReadablePart(deviceId);
    this.set(deviceId, readable, 'fallback');
    return readable;
  }

  /**
   * Extract readable part from device ID
   */
  private extractReadablePart(deviceId: string): string {
    // Try splitting by common separators
    const parts = deviceId.split(/[._-]/);
    if (parts.length > 1) {
      // Use the last meaningful part
      const lastPart = parts[parts.length - 1];
      if (lastPart && lastPart.length > 2) {
        // Capitalize first letter and replace underscores with spaces
        return lastPart
          .replace(/_/g, ' ')
          .replace(/\b\w/g, l => l.toUpperCase());
      }
    }

    // If it's a hash-like string, return truncated version
    if (deviceId.length > 20) {
      return `${deviceId.substring(0, 8)}...${deviceId.substring(deviceId.length - 4)}`;
    }

    return deviceId;
  }

  /**
   * Batch get device names with caching
   */
  async batchGet(
    deviceIds: string[],
    fetchFn: (deviceId: string) => Promise<string>
  ): Promise<Record<string, string>> {
    const result: Record<string, string> = {};
    const uncached: string[] = [];

    // Check cache first
    deviceIds.forEach(deviceId => {
      const cached = this.get(deviceId);
      if (cached) {
        result[deviceId] = cached;
      } else {
        uncached.push(deviceId);
      }
    });

    // Fetch uncached device names
    if (uncached.length > 0) {
      // Process in batches to avoid rate limiting
      const batchSize = 5;
      const delayBetweenBatches = 200;

      for (let i = 0; i < uncached.length; i += batchSize) {
        const batch = uncached.slice(i, i + batchSize);
        
        const promises = batch.map(async (deviceId) => {
          // Check if there's already a pending request for this device
          if (this.pendingRequests.has(deviceId)) {
            return this.pendingRequests.get(deviceId)!;
          }

          const promise = fetchFn(deviceId)
            .then(name => {
              this.set(deviceId, name, 'api');
              return { deviceId, name };
            })
            .catch(error => {
              console.warn(`Failed to fetch device name for ${deviceId}:`, error);
              const fallback = this.getFallbackName(deviceId);
              return { deviceId, name: fallback };
            })
            .finally(() => {
              this.pendingRequests.delete(deviceId);
            });

          this.pendingRequests.set(deviceId, promise.then(r => r.name));
          return promise;
        });

        const batchResults = await Promise.all(promises);
        batchResults.forEach(({ deviceId, name }) => {
          result[deviceId] = name;
        });

        // Delay between batches
        if (i + batchSize < uncached.length) {
          await new Promise(resolve => setTimeout(resolve, delayBetweenBatches));
        }
      }
    }

    return result;
  }

  /**
   * Clear cache
   */
  clear(): void {
    this.memoryCache.clear();
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch (error) {
      console.warn('Failed to clear device name cache from storage:', error);
    }
  }

  /**
   * Get cache statistics
   */
  getStats(): { size: number; entries: number } {
    return {
      size: this.memoryCache.size,
      entries: this.memoryCache.size,
    };
  }
}

// Export singleton instance
export const deviceNameCache = new DeviceNameCache();


import type { ExtractIdTaskResult } from "../../types/task";

export type CachedExtractIdTaskResult = {
  createdAt: string;
  idempotencyKey: string;
  provider: string;
  result: ExtractIdTaskResult;
};

export type TaskResultCache = {
  clear(): void;
  get(key: string): CachedExtractIdTaskResult | null;
  set(key: string, value: CachedExtractIdTaskResult, ttlMs: number): void;
  size(): number;
};

type CacheEntry = {
  expiresAt: number;
  value: CachedExtractIdTaskResult;
};

type GlobalCacheStore = typeof globalThis & {
  __interfazeTaskResultCache?: Map<string, CacheEntry>;
};

export function createMemoryTaskResultCache(
  store = new Map<string, CacheEntry>(),
): TaskResultCache {
  return {
    clear() {
      store.clear();
    },
    get(key) {
      const entry = store.get(key);

      if (!entry) {
        return null;
      }

      if (entry.expiresAt <= Date.now()) {
        store.delete(key);
        return null;
      }

      return entry.value;
    },
    set(key, value, ttlMs) {
      store.set(key, {
        expiresAt: Date.now() + ttlMs,
        value,
      });
    },
    size() {
      return store.size;
    },
  };
}

export function getTaskResultCache() {
  const cacheStore = globalThis as GlobalCacheStore;
  cacheStore.__interfazeTaskResultCache ??= new Map<string, CacheEntry>();

  return createMemoryTaskResultCache(cacheStore.__interfazeTaskResultCache);
}

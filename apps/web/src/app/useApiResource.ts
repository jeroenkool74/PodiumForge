import { useCallback, useEffect, useState } from "react";

export function useApiResource<T>(loader: () => Promise<T>, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const mutate = useCallback((value: T | ((current: T | null) => T)) => {
    setData((current) => (typeof value === "function" ? (value as (current: T | null) => T)(current) : value));
  }, []);

  const run = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const value = await loader();
      setData(value);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }, deps);

  useEffect(() => {
    void run();
  }, [run]);

  return { data, loading, error, refresh: run, mutate };
}

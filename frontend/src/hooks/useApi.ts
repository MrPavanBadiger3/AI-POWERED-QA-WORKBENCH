import { useState, useCallback } from 'react';

export function useApi<T>(fn: (...args: any[]) => Promise<{ data: T }>) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const execute = useCallback(async (...args: any[]) => {
    setLoading(true);
    setError(null);
    try {
      const response = await fn(...args);
      setData(response.data);
      return response.data;
    } catch (err: any) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [fn]);

  return { data, loading, error, execute };
}

import { useCallback, useEffect, useState } from "react";
import type { DemoCase } from "@/types/pipeline";

export function useDemoCases() {
  const [cases, setCases] = useState<DemoCase[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchCases = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/cases");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setCases(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load cases");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchCases(); }, [fetchCases]);

  return { cases, loading, error, refetch: fetchCases };
}

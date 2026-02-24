import { useCallback, useRef, useState } from "react";
import type { RawCaseData } from "@/types/case-data";

function snakeToCamel(str: string): string {
  return str.replace(/_([a-z])/g, (_, c) => c.toUpperCase());
}

function transformKeys(obj: unknown): unknown {
  if (Array.isArray(obj)) return obj.map(transformKeys);
  if (obj !== null && typeof obj === "object") {
    const result: Record<string, unknown> = {};
    for (const [key, value] of Object.entries(obj as Record<string, unknown>)) {
      result[snakeToCamel(key)] = transformKeys(value);
    }
    return result;
  }
  return obj;
}

export function useCaseData() {
  const [data, setData] = useState<RawCaseData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const loadedCaseId = useRef<string | null>(null);

  const fetchCaseData = useCallback(async (caseId: string) => {
    if (loadedCaseId.current === caseId && data) return;

    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/case/${caseId}/data`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const raw = await res.json();
      const transformed = transformKeys(raw) as RawCaseData;
      setData(transformed);
      loadedCaseId.current = caseId;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load case data");
      setData(null);
      loadedCaseId.current = null;
    } finally {
      setLoading(false);
    }
  }, [data]);

  const clearData = useCallback(() => {
    setData(null);
    loadedCaseId.current = null;
    setError(null);
  }, []);

  return { data, loading, error, fetchCaseData, clearData };
}

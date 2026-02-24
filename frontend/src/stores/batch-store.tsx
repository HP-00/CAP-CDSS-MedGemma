import { createContext, useCallback, useContext, useMemo, useState } from "react";
import type { BatchContextValue, PatientRow } from "@/types/patient";
import type { PipelineState } from "@/types/pipeline";
import { useDemoCases } from "@/hooks/use-demo-cases";
import { useBatchQueue } from "@/hooks/use-batch-queue";
import { enrichDemoCases } from "@/lib/patient-data";

const BatchContext = createContext<BatchContextValue | null>(null);

export function BatchProvider({ children }: { children: React.ReactNode }) {
  const { cases, loading: casesLoading } = useDemoCases();
  const { batch, startBatch, currentCaseId, getResult } = useBatchQueue();
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [activePatientId, setActivePatientIdRaw] = useState<string | null>(null);

  const setActivePatient = useCallback((id: string | null) => {
    setActivePatientIdRaw(id);
  }, []);

  const patients: PatientRow[] = useMemo(() => {
    const enriched = enrichDemoCases(cases);
    // Augment with severity from completed batch results
    return enriched.map((p) => {
      const result = batch.results.get(p.caseId);
      if (result?.curb65Score) {
        return {
          ...p,
          severityTier: result.curb65Score.severity_tier,
          curb65Score: result.curb65Score.curb65 ?? result.curb65Score.crb65,
        };
      }
      return p;
    });
  }, [cases, batch.results]);

  const toggleSelection = useCallback((id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const toggleAll = useCallback(() => {
    setSelectedIds((prev) => {
      if (prev.size === patients.length) return new Set();
      return new Set(patients.map((p) => p.caseId));
    });
  }, [patients]);

  const handleStartBatch = useCallback(
    (ids: string[], forceMock?: boolean) => {
      startBatch(ids, forceMock);
    },
    [startBatch],
  );

  const getResultStable = useCallback(
    (caseId: string): PipelineState | undefined => getResult(caseId),
    [getResult],
  );

  const value: BatchContextValue = useMemo(
    () => ({
      patients,
      patientsLoading: casesLoading,
      selectedIds,
      toggleSelection,
      toggleAll,
      batch,
      startBatch: handleStartBatch,
      getResult: getResultStable,
      currentCaseId,
      activePatientId,
      setActivePatient,
    }),
    [patients, casesLoading, selectedIds, toggleSelection, toggleAll, batch, handleStartBatch, getResultStable, currentCaseId, activePatientId, setActivePatient],
  );

  return <BatchContext.Provider value={value}>{children}</BatchContext.Provider>;
}

export function useBatchContext(): BatchContextValue {
  const ctx = useContext(BatchContext);
  if (!ctx) throw new Error("useBatchContext must be used within BatchProvider");
  return ctx;
}

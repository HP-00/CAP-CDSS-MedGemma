import type { PipelineState } from "./pipeline";

export interface PatientRow {
  caseId: string;
  name: string;
  age: number;
  sex: string;
  admissionDate: string;
  bed: string;
  primaryDx: string;
  dataAvailable: {
    cxr: boolean;
    labs: boolean;
    fhir: boolean;
    micro: boolean;
    docs: boolean;
  };
  // Populated after analysis
  severityTier?: "low" | "moderate" | "high";
  curb65Score?: number;
}

export interface BatchState {
  queue: string[];
  currentIndex: number;
  results: Map<string, PipelineState>;
  status: "idle" | "running" | "complete";
}

export interface BatchContextValue {
  patients: PatientRow[];
  patientsLoading: boolean;
  selectedIds: Set<string>;
  toggleSelection: (id: string) => void;
  toggleAll: () => void;
  batch: BatchState;
  startBatch: (ids: string[], forceMock?: boolean) => void;
  getResult: (caseId: string) => PipelineState | undefined;
  currentCaseId: string | null;
  activePatientId: string | null;
  setActivePatient: (id: string | null) => void;
}

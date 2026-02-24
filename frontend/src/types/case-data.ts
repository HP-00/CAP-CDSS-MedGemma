export interface RawCaseData {
  caseId: string;
  patientId: string | null;
  fhirBundle: FhirBundle | null;
  labReport: LabReport | string | null;
  cxrFindings: Record<string, unknown> | null;
  microResults: MicroResult[] | null;
  admissionLabs: Record<string, number> | null;
  treatmentStatus: Record<string, unknown> | null;
  allergies: string[] | AllergyDetail[] | null;
}

export interface LabReport {
  format: string;
  content: string;
  source?: string;
}

export interface FhirBundle {
  resourceType: string;
  type: string;
  entry: FhirEntry[];
}

export interface FhirEntry {
  resource: FhirResource;
}

export interface FhirResource {
  resourceType: string;
  [key: string]: unknown;
}

export interface MicroResult {
  testType?: string;
  test_type?: string;
  organism: string;
  status: string;
  antibiogram?: Record<string, string>;
}

export interface AllergyDetail {
  substance: string;
  reaction_type: string;
  criticality?: string;
}

export type DataSourceType = "cxr" | "labs" | "fhir" | "micro" | "docs";

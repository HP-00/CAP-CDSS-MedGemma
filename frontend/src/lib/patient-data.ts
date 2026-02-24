import type { PatientRow } from "@/types/patient";
import type { DemoCase } from "@/types/pipeline";

/** Static enrichment data for the 5 demo cases — maps case IDs to patient metadata. */
const PATIENT_ENRICHMENT: Record<
  string,
  Omit<PatientRow, "caseId" | "primaryDx">
> = {
  cxr_clear: {
    name: "Margaret Thornton",
    age: 50,
    sex: "Female",
    admissionDate: "18 Feb 2026 16:00",
    bed: "Bed 4A",
    dataAvailable: { cxr: true, labs: true, fhir: true, micro: true, docs: true },
  },
  cxr_bilateral: {
    name: "Harold Pemberton",
    age: 65,
    sex: "Male",
    admissionDate: "18 Feb 2026 17:30",
    bed: "Bed 12B",
    dataAvailable: { cxr: true, labs: true, fhir: true, micro: true, docs: true },
  },
  cxr_normal: {
    name: "Susan Clarke",
    age: 50,
    sex: "Female",
    admissionDate: "18 Feb 2026 15:00",
    bed: "Bed 7C",
    dataAvailable: { cxr: true, labs: true, fhir: true, micro: true, docs: true },
  },
  cxr_subtle: {
    name: "David Okonkwo",
    age: 50,
    sex: "Male",
    admissionDate: "18 Feb 2026 14:00",
    bed: "Bed 2A",
    dataAvailable: { cxr: true, labs: true, fhir: true, micro: true, docs: true },
  },
  cxr_effusion: {
    name: "Patricia Hennessy",
    age: 65,
    sex: "Female",
    admissionDate: "18 Feb 2026 18:00",
    bed: "Bed 9D",
    dataAvailable: { cxr: true, labs: true, fhir: true, micro: true, docs: true },
  },
};

/** Enrich demo cases from the API with static patient metadata. */
export function enrichDemoCases(cases: DemoCase[]): PatientRow[] {
  return cases.map((c) => {
    const enrichment = PATIENT_ENRICHMENT[c.id];
    if (enrichment) {
      return {
        caseId: c.id,
        primaryDx: c.description,
        ...enrichment,
      };
    }
    // Fallback for unknown case IDs
    return {
      caseId: c.id,
      name: c.label,
      age: 0,
      sex: "Unknown",
      admissionDate: "—",
      bed: "—",
      primaryDx: c.description,
      dataAvailable: { cxr: false, labs: false, fhir: false, micro: true, docs: false },
    };
  });
}

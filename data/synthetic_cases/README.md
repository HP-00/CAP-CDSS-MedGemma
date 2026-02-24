# Synthetic CAP Cases

Five synthetic Community-Acquired Pneumonia cases for pipeline evaluation. Each case includes full FHIR R4 bundles, lab reports, clerking notes, and references to RSNA CXR images.

## Cases

| Case ID | Patient | CXR Category | Key Feature | Expected Contradictions |
|---------|---------|-------------|------------|------------------------|
| `cxr_clear` | Margaret Thornton, 50F | Consolidation with effusion | Standard CAP pathway | None |
| `cxr_bilateral` | Harold Pemberton, 65M | Bilateral infiltrates | High severity, confusion | None |
| `cxr_normal` | Susan Clarke, 50F | Normal CXR | Raised CRP without radiographic changes | None |
| `cxr_subtle` | David Okonkwo, 50M | Subtle findings | Mild clinical signs | None |
| `cxr_effusion` | Patricia Hennessy, 65F | Pleural effusion | Immunosuppressed (methotrexate) | None |

## CXR Images

CXR images are from the RSNA Pneumonia Detection Challenge dataset, stored in `benchmark_data/rsna/images/`. These images are publicly available under the RSNA data use agreement.

**Attribution:** RSNA Pneumonia Detection Challenge, 2018. Radiological Society of North America. Available at: https://www.kaggle.com/c/rsna-pneumonia-detection-challenge

## Regenerating

```bash
python scripts/export_synthetic_cases.py
```

## Schema

Each JSON file contains the full case_data dict as passed to the LangGraph pipeline, with an additional `ground_truth` key for benchmark evaluation:

```json
{
  "case_id": "string",
  "patient_id": "string",
  "demographics": {...},
  "clinical_notes": "string",
  "lab_report": "string",
  "fhir_bundle": {...},
  "image_path": "relative/path/to/cxr.png",
  "ground_truth": {
    "curb65": 1,
    "severity_tier": "low",
    "contradictions": [],
    "antibiotic": "amoxicillin",
    "discharge_met": true
  }
}
```

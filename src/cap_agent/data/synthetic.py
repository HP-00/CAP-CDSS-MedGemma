"""Synthetic CAP case data for pipeline testing.

Includes both a flat Python dict (SYNTHETIC_CAP_CASE, for mock extraction)
and a FHIR R4 Bundle (SYNTHETIC_FHIR_BUNDLE, for real MedGemma extraction).
The two represent the same 72yo male CAP patient.
"""

import base64

SYNTHETIC_CAP_CASE = {
    "case_id": "CAP-SCAFFOLD-001",
    "patient_id": "PT-2024-7890",
    "demographics": {
        "age": 72,
        "sex": "Male",
        "weight_kg": 78,
    },
    "presenting_complaint": "3-day history of productive cough, fever, and increasing dyspnoea",
    "clinical_exam": {
        "respiratory_exam": {
            "crackles": True,
            "crackles_location": "right lower zone",
            "bronchial_breathing": True,
            "bronchial_breathing_location": "right lower zone",
            "dullness_to_percussion": True,
            "dullness_location": "right base",
            "reduced_air_entry": False,
        },
        "observations": {
            "respiratory_rate": 22,
            "systolic_bp": 105,
            "diastolic_bp": 65,
            "heart_rate": 98,
            "spo2": 94,
            "temperature": 38.4,
            "supplemental_o2": "room air",
        },
        "confusion_assessment": {
            "amt_score": 9,
            "amt_total": 10,
            "confused": False,
        },
    },
    "lab_results": {
        "crp": {"value": 186, "unit": "mg/L", "reference_range": "<5", "abnormal": True},
        "urea": {"value": 8.2, "unit": "mmol/L", "reference_range": "2.5-7.8", "abnormal": True},
        "creatinine": {"value": 98, "unit": "umol/L", "reference_range": "62-106", "abnormal": False},
        "egfr": {"value": 62, "unit": "mL/min/1.73m2", "reference_range": ">90", "abnormal": True},
        "sodium": {"value": 136, "unit": "mmol/L", "reference_range": "133-146", "abnormal": False},
        "potassium": {"value": 4.1, "unit": "mmol/L", "reference_range": "3.5-5.3", "abnormal": False},
        "wcc": {"value": 15.3, "unit": "x10^9/L", "reference_range": "4.0-11.0", "abnormal": True},
        "neutrophils": {"value": 12.8, "unit": "x10^9/L", "reference_range": "2.0-7.5", "abnormal": True},
        "haemoglobin": {"value": 138, "unit": "g/L", "reference_range": "130-170", "abnormal": False},
        "platelets": {"value": 245, "unit": "x10^9/L", "reference_range": "150-400", "abnormal": False},
        "procalcitonin": {"value": 0.8, "unit": "ng/mL", "reference_range": "<0.1", "abnormal": True},
        "lactate": {"value": 1.4, "unit": "mmol/L", "reference_range": "<2.0", "abnormal": False},
    },
    "cxr": {
        "findings": {
            "consolidation": {
                "present": True,
                "confidence": "moderate",
                "location": "right lower lobe",
                "description": "Patchy air-space opacification in the right lower zone",
            },
            "pleural_effusion": {"present": False, "confidence": "high"},
            "cardiomegaly": {"present": False, "confidence": "high"},
            "edema": {"present": False, "confidence": "high"},
            "atelectasis": {"present": False, "confidence": "moderate"},
        },
        "image_quality": {
            "projection": "PA",
            "rotation": "minimal",
            "penetration": "adequate",
        },
        "image_path": "placeholder_cxr.jpg",
        "prior_image_path": None,
    },
    "past_medical_history": {
        "comorbidities": ["Type 2 diabetes mellitus", "COPD (moderate)"],
        "medications": ["Metformin 500mg BD", "Salbutamol inhaler PRN"],
        "allergies": [],
        "recent_antibiotics": [],
    },
    "social_history": {
        "pregnancy": False,
        "oral_tolerance": True,
        "eating_independently": True,
        "travel_history": [],
        "immunosuppression": False,
        "smoking_status": "former",
    },
}


def get_synthetic_case() -> dict:
    """Return a deep copy of the synthetic CAP case."""
    import copy
    return copy.deepcopy(SYNTHETIC_CAP_CASE)


# --- Realistic NHS Admission Clerking Note (~300 words) ---

SYNTHETIC_CLERKING_NOTE = """\
ACUTE MEDICAL UNIT — ADMISSION CLERKING NOTE

Patient: Robert JAMES  DOB: 15/03/1954  NHS: 943 476 2851  MRN: PT-2024-7890
Date: 10/02/2026 14:30  Clerked by: Dr A. Patel (FY2)

PC: 72yo gentleman referred by GP with 3-day history of productive cough, \
fever, and increasing breathlessness.

HPC: Initially dry cough progressing to productive yellow-green sputum over \
3 days. Rigors and sweats at home. Progressive dyspnoea on exertion, now \
breathless at rest. Right-sided pleuritic chest pain worse on deep \
inspiration. No haemoptysis. Poor oral intake but tolerating fluids.

PMH: COPD (moderate, FEV1 58% predicted last year), Type 2 diabetes \
mellitus (diet + metformin), Ex-smoker (30 pack-years, quit 5 years ago). \
No previous ITU admissions.

DH: Salbutamol 100mcg inhaler PRN, Tiotropium 18mcg OD, Metformin 500mg BD.
Allergies: NKDA

SH: Lives independently in own home, retired factory worker. Fully \
independent ADLs baseline. No recent travel abroad. Not pregnant. Tolerates \
oral medications and food.

O/E:
General: Alert, orientated, looks unwell, flushed.
Obs: RR 22, SpO2 94% on room air, HR 98 regular, BP 105/65, Temp 38.4C
Resp: Reduced air entry right base. Crackles right lower zone. Bronchial \
breathing right lower zone. Dullness to percussion right base. Left lung clear.
CVS: HS I+II+0, no murmurs. No peripheral oedema.
Abdo: Soft, non-tender, bowel sounds present.
Neuro: AMT 9/10 (failed to recall address). GCS 15.

Impression: Community-acquired pneumonia, right lower lobe. Moderate \
severity based on clinical assessment. For CURB65 scoring and CAP pathway.

Plan: CXR, bloods (FBC, U+E, CRP, LFT, lactate, blood cultures), \
start empirical antibiotics per local CAP protocol, reassess at 48h.
"""


# --- FHIR R4 Bundle matching the same patient ---

# Base64-encode the clerking note for the DocumentReference
_CLERKING_B64 = base64.b64encode(SYNTHETIC_CLERKING_NOTE.encode("utf-8")).decode("ascii")

SYNTHETIC_FHIR_BUNDLE = {
    "resourceType": "Bundle",
    "type": "collection",
    "entry": [
        # --- Patient ---
        {
            "resource": {
                "resourceType": "Patient",
                "id": "pt-001",
                "name": [{"family": "James", "given": ["Robert"]}],
                "gender": "male",
                "birthDate": "1954-03-15",
                "identifier": [
                    {
                        "system": "https://fhir.nhs.uk/Id/nhs-number",
                        "value": "9434762851",
                    }
                ],
            }
        },
        # --- Conditions ---
        {
            "resource": {
                "resourceType": "Condition",
                "id": "cond-copd",
                "code": {
                    "coding": [
                        {
                            "system": "http://snomed.info/sct",
                            "code": "13645005",
                            "display": "COPD",
                        }
                    ],
                    "text": "Chronic obstructive pulmonary disease",
                },
                "severity": {
                    "coding": [{"display": "moderate"}],
                },
                "clinicalStatus": {
                    "coding": [{"code": "active"}],
                },
                "subject": {"reference": "Patient/pt-001"},
            }
        },
        {
            "resource": {
                "resourceType": "Condition",
                "id": "cond-t2dm",
                "code": {
                    "coding": [
                        {
                            "system": "http://snomed.info/sct",
                            "code": "44054006",
                            "display": "Type 2 diabetes mellitus",
                        }
                    ],
                    "text": "Type 2 diabetes mellitus",
                },
                "clinicalStatus": {
                    "coding": [{"code": "active"}],
                },
                "subject": {"reference": "Patient/pt-001"},
            }
        },
        # --- AllergyIntolerance (NKDA) ---
        {
            "resource": {
                "resourceType": "AllergyIntolerance",
                "id": "allergy-nkda",
                "code": {
                    "coding": [
                        {
                            "system": "http://snomed.info/sct",
                            "code": "716186003",
                            "display": "No known allergy",
                        }
                    ],
                    "text": "No known drug allergies",
                },
                "clinicalStatus": {
                    "coding": [{"code": "active"}],
                },
                "patient": {"reference": "Patient/pt-001"},
            }
        },
        # --- Observations (vitals + urea) ---
        {
            "resource": {
                "resourceType": "Observation",
                "id": "obs-rr",
                "code": {
                    "coding": [
                        {
                            "system": "http://loinc.org",
                            "code": "9279-1",
                            "display": "Respiratory rate",
                        }
                    ],
                },
                "valueQuantity": {"value": 22, "unit": "/min"},
                "effectiveDateTime": "2026-02-10T14:30:00Z",
                "subject": {"reference": "Patient/pt-001"},
            }
        },
        {
            "resource": {
                "resourceType": "Observation",
                "id": "obs-bp",
                "code": {
                    "coding": [
                        {
                            "system": "http://loinc.org",
                            "code": "85354-9",
                            "display": "Blood pressure panel",
                        }
                    ],
                },
                "component": [
                    {
                        "code": {
                            "coding": [
                                {
                                    "system": "http://loinc.org",
                                    "code": "8480-6",
                                    "display": "Systolic blood pressure",
                                }
                            ],
                        },
                        "valueQuantity": {"value": 105, "unit": "mmHg"},
                    },
                    {
                        "code": {
                            "coding": [
                                {
                                    "system": "http://loinc.org",
                                    "code": "8462-4",
                                    "display": "Diastolic blood pressure",
                                }
                            ],
                        },
                        "valueQuantity": {"value": 65, "unit": "mmHg"},
                    },
                ],
                "effectiveDateTime": "2026-02-10T14:30:00Z",
                "subject": {"reference": "Patient/pt-001"},
            }
        },
        {
            "resource": {
                "resourceType": "Observation",
                "id": "obs-hr",
                "code": {
                    "coding": [
                        {
                            "system": "http://loinc.org",
                            "code": "8867-4",
                            "display": "Heart rate",
                        }
                    ],
                },
                "valueQuantity": {"value": 98, "unit": "/min"},
                "effectiveDateTime": "2026-02-10T14:30:00Z",
                "subject": {"reference": "Patient/pt-001"},
            }
        },
        {
            "resource": {
                "resourceType": "Observation",
                "id": "obs-spo2",
                "code": {
                    "coding": [
                        {
                            "system": "http://loinc.org",
                            "code": "2708-6",
                            "display": "Oxygen saturation",
                        }
                    ],
                },
                "valueQuantity": {"value": 94, "unit": "%"},
                "effectiveDateTime": "2026-02-10T14:30:00Z",
                "subject": {"reference": "Patient/pt-001"},
            }
        },
        {
            "resource": {
                "resourceType": "Observation",
                "id": "obs-temp",
                "code": {
                    "coding": [
                        {
                            "system": "http://loinc.org",
                            "code": "8310-5",
                            "display": "Body temperature",
                        }
                    ],
                },
                "valueQuantity": {"value": 38.4, "unit": "Cel"},
                "effectiveDateTime": "2026-02-10T14:30:00Z",
                "subject": {"reference": "Patient/pt-001"},
            }
        },
        {
            "resource": {
                "resourceType": "Observation",
                "id": "obs-urea",
                "code": {
                    "coding": [
                        {
                            "system": "http://loinc.org",
                            "code": "3094-0",
                            "display": "Urea",
                        }
                    ],
                },
                "valueQuantity": {"value": 8.2, "unit": "mmol/L"},
                "effectiveDateTime": "2026-02-10T14:30:00Z",
                "subject": {"reference": "Patient/pt-001"},
            }
        },
        {
            "resource": {
                "resourceType": "Observation",
                "id": "obs-crp",
                "code": {
                    "coding": [
                        {
                            "system": "http://loinc.org",
                            "code": "1988-5",
                            "display": "C-reactive protein",
                        }
                    ],
                },
                "valueQuantity": {"value": 186, "unit": "mg/L"},
                "effectiveDateTime": "2026-02-10T14:30:00Z",
                "subject": {"reference": "Patient/pt-001"},
            }
        },
        # --- Lab Observations (10 additional) ---
        {
            "resource": {
                "resourceType": "Observation",
                "id": "obs-creatinine",
                "code": {
                    "coding": [
                        {
                            "system": "http://loinc.org",
                            "code": "2160-0",
                            "display": "Creatinine",
                        }
                    ],
                },
                "valueQuantity": {"value": 98, "unit": "umol/L"},
                "effectiveDateTime": "2026-02-10T14:30:00Z",
                "subject": {"reference": "Patient/pt-001"},
            }
        },
        {
            "resource": {
                "resourceType": "Observation",
                "id": "obs-egfr",
                "code": {
                    "coding": [
                        {
                            "system": "http://loinc.org",
                            "code": "33914-3",
                            "display": "eGFR",
                        }
                    ],
                },
                "valueQuantity": {"value": 62, "unit": "mL/min/1.73m2"},
                "effectiveDateTime": "2026-02-10T14:30:00Z",
                "subject": {"reference": "Patient/pt-001"},
            }
        },
        {
            "resource": {
                "resourceType": "Observation",
                "id": "obs-sodium",
                "code": {
                    "coding": [
                        {
                            "system": "http://loinc.org",
                            "code": "2951-2",
                            "display": "Sodium",
                        }
                    ],
                },
                "valueQuantity": {"value": 136, "unit": "mmol/L"},
                "effectiveDateTime": "2026-02-10T14:30:00Z",
                "subject": {"reference": "Patient/pt-001"},
            }
        },
        {
            "resource": {
                "resourceType": "Observation",
                "id": "obs-potassium",
                "code": {
                    "coding": [
                        {
                            "system": "http://loinc.org",
                            "code": "2823-3",
                            "display": "Potassium",
                        }
                    ],
                },
                "valueQuantity": {"value": 4.1, "unit": "mmol/L"},
                "effectiveDateTime": "2026-02-10T14:30:00Z",
                "subject": {"reference": "Patient/pt-001"},
            }
        },
        {
            "resource": {
                "resourceType": "Observation",
                "id": "obs-wcc",
                "code": {
                    "coding": [
                        {
                            "system": "http://loinc.org",
                            "code": "6690-2",
                            "display": "White cell count",
                        }
                    ],
                },
                "valueQuantity": {"value": 15.3, "unit": "x10^9/L"},
                "effectiveDateTime": "2026-02-10T14:30:00Z",
                "subject": {"reference": "Patient/pt-001"},
            }
        },
        {
            "resource": {
                "resourceType": "Observation",
                "id": "obs-neut",
                "code": {
                    "coding": [
                        {
                            "system": "http://loinc.org",
                            "code": "751-8",
                            "display": "Neutrophils",
                        }
                    ],
                },
                "valueQuantity": {"value": 12.8, "unit": "x10^9/L"},
                "effectiveDateTime": "2026-02-10T14:30:00Z",
                "subject": {"reference": "Patient/pt-001"},
            }
        },
        {
            "resource": {
                "resourceType": "Observation",
                "id": "obs-hb",
                "code": {
                    "coding": [
                        {
                            "system": "http://loinc.org",
                            "code": "718-7",
                            "display": "Haemoglobin",
                        }
                    ],
                },
                "valueQuantity": {"value": 138, "unit": "g/L"},
                "effectiveDateTime": "2026-02-10T14:30:00Z",
                "subject": {"reference": "Patient/pt-001"},
            }
        },
        {
            "resource": {
                "resourceType": "Observation",
                "id": "obs-plt",
                "code": {
                    "coding": [
                        {
                            "system": "http://loinc.org",
                            "code": "777-3",
                            "display": "Platelets",
                        }
                    ],
                },
                "valueQuantity": {"value": 245, "unit": "x10^9/L"},
                "effectiveDateTime": "2026-02-10T14:30:00Z",
                "subject": {"reference": "Patient/pt-001"},
            }
        },
        {
            "resource": {
                "resourceType": "Observation",
                "id": "obs-pct",
                "code": {
                    "coding": [
                        {
                            "system": "http://loinc.org",
                            "code": "33959-8",
                            "display": "Procalcitonin",
                        }
                    ],
                },
                "valueQuantity": {"value": 0.8, "unit": "ng/mL"},
                "effectiveDateTime": "2026-02-10T14:30:00Z",
                "subject": {"reference": "Patient/pt-001"},
            }
        },
        {
            "resource": {
                "resourceType": "Observation",
                "id": "obs-lactate",
                "code": {
                    "coding": [
                        {
                            "system": "http://loinc.org",
                            "code": "2524-7",
                            "display": "Lactate",
                        }
                    ],
                },
                "valueQuantity": {"value": 1.4, "unit": "mmol/L"},
                "effectiveDateTime": "2026-02-10T14:30:00Z",
                "subject": {"reference": "Patient/pt-001"},
            }
        },
        {
            "resource": {
                "resourceType": "Observation",
                "id": "obs-eating",
                "code": {
                    "coding": [{
                        "system": "http://loinc.org",
                        "code": "75244-9",
                        "display": "Ability to eat independently",
                    }],
                },
                "valueCodeableConcept": {
                    "text": "Poor oral intake but tolerating fluids independently",
                },
                "effectiveDateTime": "2026-02-10T14:30:00Z",
                "subject": {"reference": "Patient/pt-001"},
            }
        },
        # --- MedicationRequests ---
        {
            "resource": {
                "resourceType": "MedicationRequest",
                "id": "med-salbutamol",
                "medicationCodeableConcept": {
                    "text": "Salbutamol 100mcg inhaler",
                },
                "dosageInstruction": [{"text": "PRN"}],
                "subject": {"reference": "Patient/pt-001"},
            }
        },
        {
            "resource": {
                "resourceType": "MedicationRequest",
                "id": "med-tiotropium",
                "medicationCodeableConcept": {
                    "text": "Tiotropium 18mcg",
                },
                "dosageInstruction": [{"text": "Once daily"}],
                "subject": {"reference": "Patient/pt-001"},
            }
        },
        {
            "resource": {
                "resourceType": "MedicationRequest",
                "id": "med-metformin",
                "medicationCodeableConcept": {
                    "text": "Metformin 500mg",
                },
                "dosageInstruction": [{"text": "Twice daily"}],
                "subject": {"reference": "Patient/pt-001"},
            }
        },
        # --- DocumentReference (clerking note) ---
        {
            "resource": {
                "resourceType": "DocumentReference",
                "id": "doc-clerking",
                "description": "Admission clerking note",
                "content": [
                    {
                        "attachment": {
                            "contentType": "text/plain",
                            "data": _CLERKING_B64,
                        }
                    }
                ],
                "subject": {"reference": "Patient/pt-001"},
            }
        },
        # --- Encounter ---
        {
            "resource": {
                "resourceType": "Encounter",
                "id": "enc-001",
                "class": {
                    "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
                    "code": "AMB",
                    "display": "Acute Medical Unit",
                },
                "period": {"start": "2026-02-10T14:00:00Z"},
                "reasonCode": [{"text": "Community-acquired pneumonia"}],
                "subject": {"reference": "Patient/pt-001"},
            }
        },
    ],
}


SYNTHETIC_LAB_REPORT = """\
====================================================================
  CITY GENERAL HOSPITAL NHS FOUNDATION TRUST
  Department of Clinical Biochemistry & Haematology
====================================================================
Patient: Robert JAMES   DOB: 15/03/1954   NHS: 943 476 2851
MRN: PT-2024-7890       Ward: AMU         Collected: 10/02/2026 14:45
Requested by: Dr A. Patel (FY2)
Sample: Venous blood (lithium heparin, EDTA)

BIOCHEMISTRY
--------------------------------------------------------------------
Test                Result    Units        Reference Range    Flag
--------------------------------------------------------------------
C-reactive protein  186       mg/L         <5                 H
Urea                8.2       mmol/L       2.5-7.8            H
Creatinine          98        umol/L       62-106
eGFR (CKD-EPI)     62        mL/min/1.73m2  >90              L
Sodium              136       mmol/L       133-146
Potassium           4.1       mmol/L       3.5-5.3
Procalcitonin       0.8       ng/mL        <0.1               H
Lactate             1.4       mmol/L       <2.0

HAEMATOLOGY
--------------------------------------------------------------------
Test                Result    Units        Reference Range    Flag
--------------------------------------------------------------------
White cell count    15.3      x10^9/L      4.0-11.0           H
Neutrophils         12.8      x10^9/L      2.0-7.5            H
Haemoglobin         138       g/L          130-170
Platelets           245       x10^9/L      150-400

Authorised by: Dr S. Khan (Consultant Biochemist) 10/02/2026 16:10
====================================================================
"""


def get_synthetic_fhir_case() -> dict:
    """Return synthetic case with FHIR bundle for real extraction.

    Merges the flat SYNTHETIC_CAP_CASE (for backward compatibility with
    mock extraction and downstream nodes) with the FHIR Bundle.
    """
    case = get_synthetic_case()
    case["fhir_bundle"] = SYNTHETIC_FHIR_BUNDLE
    case["lab_report"] = {
        "format": "text",
        "content": SYNTHETIC_LAB_REPORT,
        "source": "city_general_pathology",
    }
    return case


# ---------------------------------------------------------------------------
# T=48h Synthetic Data (for CR-7/8/9 stewardship demo)
# ---------------------------------------------------------------------------

SYNTHETIC_CLERKING_NOTE_48H = """\
ACUTE MEDICAL UNIT — 48-HOUR MEDICAL REVIEW

Patient: Robert JAMES  DOB: 15/03/1954  NHS: 943 476 2851  MRN: PT-2024-7890
Date: 12/02/2026 14:30  Reviewed by: Dr B. Singh (SpR Acute Medicine)

48h Review: Community-Acquired Pneumonia (Day 2)

PROGRESS: Clinically improving. Temperature normalised overnight (37.0C \
for last 18 hours). Productive cough persisting but less frequent. \
Appetite improving — eating full meals. No further rigors or sweats. \
Oxygen saturations stable on room air.

MICROBIOLOGY UPDATE:
- Blood cultures (10/02): Streptococcus pneumoniae isolated. \
Penicillin-sensitive (MIC <0.06). Susceptible to amoxicillin, \
co-amoxiclav, clarithromycin, ceftriaxone.
- Pneumococcal urinary antigen: POSITIVE
- Legionella urinary antigen: NEGATIVE
- Sputum culture: pending (sample sent day 1)

CURRENT ANTIBIOTICS: Co-amoxiclav 1.2g TDS IV + Clarithromycin 500mg BD IV \
(commenced 10/02/2026, now 52 hours IV therapy)

O/E:
General: Alert, comfortable at rest, eating breakfast. AMT 10/10.
Obs: RR 18, SpO2 96% on room air, HR 82 regular, BP 115/70, Temp 37.0C
Resp: Crackles right lower zone — improved from admission. No bronchial \
breathing. Air entry improved bilaterally.
Abdo: Soft, tolerating oral diet and medications.

Impression: Improving CAP with confirmed S. pneumoniae bacteraemia. \
Responding well to IV antibiotics. Consider IV-to-oral switch given \
clinical stability and oral tolerance. Macrolide may be de-escalated \
as no atypical pathogen identified.

Plan:
1. Consider step-down to oral amoxicillin (organism susceptible)
2. Review need for clarithromycin — no atypical pathogen on micro
3. Repeat CRP and bloods — monitor trend
4. Encourage mobilisation and oral intake
5. Aim discharge within 24-48h if continues to improve
"""


SYNTHETIC_LAB_REPORT_48H = """\
====================================================================
  CITY GENERAL HOSPITAL NHS FOUNDATION TRUST
  Department of Clinical Biochemistry & Haematology
====================================================================
Patient: Robert JAMES   DOB: 15/03/1954   NHS: 943 476 2851
MRN: PT-2024-7890       Ward: AMU         Collected: 12/02/2026 07:00
Requested by: Dr B. Singh (SpR)
Sample: Venous blood (lithium heparin, EDTA)

BIOCHEMISTRY
--------------------------------------------------------------------
Test                Result    Units        Reference Range    Flag
--------------------------------------------------------------------
C-reactive protein  95        mg/L         <5                 H
Urea                6.8       mmol/L       2.5-7.8
Creatinine          88        umol/L       62-106
eGFR (CKD-EPI)     68        mL/min/1.73m2  >90              L
Sodium              138       mmol/L       133-146
Potassium           4.1       mmol/L       3.5-5.3
Procalcitonin       0.35      ng/mL        <0.1               H
Lactate             1.2       mmol/L       <2.0

HAEMATOLOGY
--------------------------------------------------------------------
Test                Result    Units        Reference Range    Flag
--------------------------------------------------------------------
White cell count    11.8      x10^9/L      4.0-11.0           H
Neutrophils         9.2       x10^9/L      2.0-7.5            H
Haemoglobin         126       g/L          130-170            L
Platelets           252       x10^9/L      150-400

Authorised by: Dr S. Khan (Consultant Biochemist) 12/02/2026 09:15
====================================================================
"""


# Mapping from FHIR Observation display text to updated T=48h values
_FHIR_48H_VITAL_UPDATES = {
    "Respiratory rate": (18, "/min"),
    "Heart rate": (82, "/min"),
    "Oxygen saturation": (96, "%"),
    "Body temperature": (37.0, "Cel"),
}

_FHIR_48H_BP_UPDATES = {
    "Systolic blood pressure": (115, "mmHg"),
    "Diastolic blood pressure": (70, "mmHg"),
}

_FHIR_48H_LAB_UPDATES = {
    "C-reactive protein": (95, "mg/L"),
    "Urea": (6.8, "mmol/L"),
    "Creatinine": (88, "umol/L"),
    "eGFR": (68, "mL/min/1.73m2"),
    "Sodium": (138, "mmol/L"),
    "Potassium": (4.1, "mmol/L"),
    "Procalcitonin": (0.35, "ng/mL"),
    "Lactate": (1.2, "mmol/L"),
    "White cell count": (11.8, "x10^9/L"),
    "Neutrophils": (9.2, "x10^9/L"),
    "Haemoglobin": (126, "g/L"),
    "Platelets": (252, "x10^9/L"),
}


def _update_fhir_bundle_48h(bundle: dict) -> None:
    """Update FHIR Bundle entries in place with T=48h clinical data.

    Walks the bundle entries and updates:
    - Vital Observations (RR, BP, HR, SpO2, Temp)
    - Lab Observations (CRP, Urea, Creatinine, etc.)
    - DocumentReference (replace clerking note with 48h review)
    - Add MedicationRequests for current IV antibiotics
    """
    new_datetime = "2026-02-12T07:00:00Z"

    for entry in bundle["entry"]:
        resource = entry["resource"]
        rtype = resource["resourceType"]

        if rtype == "Observation":
            coding = resource.get("code", {}).get("coding", [{}])
            display = coding[0].get("display", "") if coding else ""

            # Blood pressure panel: update components
            if display == "Blood pressure panel":
                for comp in resource.get("component", []):
                    comp_display = (
                        comp.get("code", {}).get("coding", [{}])[0].get("display", "")
                    )
                    if comp_display in _FHIR_48H_BP_UPDATES:
                        new_val, new_unit = _FHIR_48H_BP_UPDATES[comp_display]
                        comp["valueQuantity"]["value"] = new_val
                        comp["valueQuantity"]["unit"] = new_unit
                resource["effectiveDateTime"] = new_datetime

            # Simple vitals
            elif display in _FHIR_48H_VITAL_UPDATES:
                new_val, new_unit = _FHIR_48H_VITAL_UPDATES[display]
                resource["valueQuantity"]["value"] = new_val
                resource["valueQuantity"]["unit"] = new_unit
                resource["effectiveDateTime"] = new_datetime

            # Lab values
            elif display in _FHIR_48H_LAB_UPDATES:
                new_val, new_unit = _FHIR_48H_LAB_UPDATES[display]
                resource["valueQuantity"]["value"] = new_val
                resource["valueQuantity"]["unit"] = new_unit
                resource["effectiveDateTime"] = new_datetime

            # Functional status: eating independently improved at 48h
            elif display == "Ability to eat independently":
                vcc = resource.get("valueCodeableConcept", {})
                vcc["text"] = "Eating full meals independently"
                resource["valueCodeableConcept"] = vcc
                resource["effectiveDateTime"] = new_datetime

        elif rtype == "DocumentReference":
            # Replace clerking note with 48h review
            _note_b64 = base64.b64encode(
                SYNTHETIC_CLERKING_NOTE_48H.encode("utf-8")
            ).decode("ascii")
            for content in resource.get("content", []):
                if "attachment" in content:
                    content["attachment"]["data"] = _note_b64
            resource["description"] = "48-hour medical review"

    # Add current IV antibiotic MedicationRequests
    bundle["entry"].append({
        "resource": {
            "resourceType": "MedicationRequest",
            "id": "med-coamoxiclav-iv",
            "medicationCodeableConcept": {
                "text": "Co-amoxiclav 1.2g IV",
            },
            "dosageInstruction": [{"text": "Three times daily"}],
            "status": "active",
            "subject": {"reference": "Patient/pt-001"},
        }
    })
    bundle["entry"].append({
        "resource": {
            "resourceType": "MedicationRequest",
            "id": "med-clarithromycin-iv",
            "medicationCodeableConcept": {
                "text": "Clarithromycin 500mg IV",
            },
            "dosageInstruction": [{"text": "Twice daily"}],
            "status": "active",
            "subject": {"reference": "Patient/pt-001"},
        }
    })


SYNTHETIC_MICRO_RESULTS_48H = [
    {
        "organism": "Streptococcus pneumoniae",
        "susceptibilities": {
            "amoxicillin": "S",
            "co-amoxiclav": "S",
            "clarithromycin": "S",
            "levofloxacin": "S",
            "ceftriaxone": "S",
        },
        "test_type": "blood_culture",
        "status": "positive",
    },
    {
        "organism": None,
        "susceptibilities": None,
        "test_type": "urine_antigen_legionella",
        "status": "negative",
    },
    {
        "organism": "Streptococcus pneumoniae",
        "susceptibilities": None,
        "test_type": "urine_antigen_pneumococcal",
        "status": "positive",
    },
    {
        "organism": None,
        "susceptibilities": None,
        "test_type": "sputum_culture",
        "status": "pending",
    },
]


SYNTHETIC_TREATMENT_STATUS_48H = {
    "current_route": "IV",
    "hours_on_iv": 52,
    "iv_antibiotics": [
        "Co-amoxiclav 1.2g TDS IV",
        "Clarithromycin 500mg BD IV",
    ],
    "days_on_treatment": 2,
    "symptoms_improving": True,
}


def get_synthetic_48h_case() -> dict:
    """Return T=48h case with micro results, improving vitals, and temporal FHIR.

    Uses the base FHIR case augmented with:
    - Updated FHIR bundle (48h vitals, labs, clerking note, medications)
    - Updated lab report (48h pathology printout)
    - Micro results and treatment status
    - Prior antibiotic recommendation from T=0
    - No CXR image paths (CXR not repeated at 48h)
    - Flat case_data updated for consistency with mock fallbacks
    """
    import copy

    case = get_synthetic_fhir_case()

    # --- Temporal FHIR data ---
    case["fhir_bundle"] = copy.deepcopy(case["fhir_bundle"])
    _update_fhir_bundle_48h(case["fhir_bundle"])
    case["lab_report"] = {
        "format": "text",
        "content": SYNTHETIC_LAB_REPORT_48H,
        "source": "city_general_pathology",
    }

    # --- Remove CXR image paths (no repeat CXR at 48h) ---
    case["cxr"].pop("image_path", None)
    case["cxr"].pop("prior_image_path", None)

    # --- Micro results + treatment status ---
    case["micro_results"] = SYNTHETIC_MICRO_RESULTS_48H
    case["treatment_status"] = SYNTHETIC_TREATMENT_STATUS_48H
    case["prior_antibiotic_recommendation"] = {
        "severity_tier": "moderate",
        "first_line": "Amoxicillin 500mg TDS PO",
        "dose_route": "IV",
        "atypical_cover": "Clarithromycin 500mg BD IV/PO",
        "stewardship_notes": [],
    }
    case["admission_labs"] = {"crp": 186}

    # --- Update flat case_data for consistency with mock fallbacks ---
    case["clinical_exam"]["observations"] = {
        "respiratory_rate": 18,
        "systolic_bp": 115,
        "diastolic_bp": 70,
        "heart_rate": 82,
        "spo2": 96,
        "temperature": 37.0,
        "supplemental_o2": "room air",
    }
    case["clinical_exam"]["confusion_assessment"] = {
        "amt_score": 10,
        "amt_total": 10,
        "confused": False,
    }
    case["curb65_variables"] = {
        "confusion": False,
        "urea": 6.8,
        "respiratory_rate": 18,
        "systolic_bp": 115,
        "diastolic_bp": 70,
        "age": 72,
    }
    # Update flat lab_results to match 48h values
    case["lab_results"]["crp"]["value"] = 95
    case["lab_results"]["crp"]["abnormal"] = True
    case["lab_results"]["urea"]["value"] = 6.8
    case["lab_results"]["urea"]["abnormal"] = False
    case["lab_results"]["creatinine"]["value"] = 88
    case["lab_results"]["egfr"]["value"] = 68
    case["lab_results"]["wcc"]["value"] = 11.8
    case["lab_results"]["neutrophils"]["value"] = 9.2
    case["lab_results"]["haemoglobin"]["value"] = 126
    case["lab_results"]["platelets"]["value"] = 252
    case["lab_results"]["procalcitonin"]["value"] = 0.35
    case["lab_results"]["lactate"]["value"] = 1.2

    return case


def get_synthetic_cr10_case() -> dict:
    """Return a high-severity patient with penicillin intolerance for CR-10 demo.

    Modifies base case: confusion=True, AMT=7, urea=10.5, penicillin GI upset.
    This triggers high severity → levofloxacin → CR-10 fires.
    """
    case = get_synthetic_case()
    allergy = {"drug": "Penicillin", "reaction_type": "GI upset", "severity": "mild"}
    case["demographics"]["allergies"] = [allergy]
    # Also set in past_medical_history so mock extraction picks it up
    case["past_medical_history"]["allergies"] = [allergy]
    case["clinical_exam"]["confusion_assessment"]["confused"] = True
    case["clinical_exam"]["confusion_assessment"]["amt_score"] = 7
    case["lab_results"]["urea"]["value"] = 10.5
    # Pop placeholder image paths so CXR uses mock passthrough (consistent
    # with T=48h and Day 3-4 cases).
    case.get("cxr", {}).pop("image_path", None)
    case.get("cxr", {}).pop("prior_image_path", None)
    return case


# ---------------------------------------------------------------------------
# T=Day 3-4 Synthetic Data (for treatment monitoring demo)
# ---------------------------------------------------------------------------

SYNTHETIC_CLERKING_NOTE_DAY34 = """\
ACUTE MEDICAL UNIT — DAY 3 CLINICAL REVIEW

Patient: Robert JAMES  DOB: 15/03/1954  NHS: 943 476 2851  MRN: PT-2024-7890
Date: 13/02/2026 09:00  Reviewed by: Dr B. Singh (SpR Acute Medicine)

Day 3 Review: Community-Acquired Pneumonia

PROGRESS: Not improving as expected. Switched to oral amoxicillin 500mg TDS \
at 48h following IV-to-oral step-down (S. pneumoniae confirmed penicillin-\
sensitive). Low-grade fever persisting (37.8C this morning). Productive cough \
continues — yellow-green sputum, no haemoptysis. Intermittent fevers \
overnight (up to 38.1C). Appetite fair but not back to baseline.

MICROBIOLOGY UPDATE:
- Blood cultures (10/02): Streptococcus pneumoniae isolated. \
Penicillin-sensitive (MIC <0.06). Susceptible to amoxicillin, \
co-amoxiclav, clarithromycin, ceftriaxone.
- Pneumococcal urinary antigen: POSITIVE
- Legionella urinary antigen: NEGATIVE
- Sputum culture (12/02): Streptococcus pneumoniae grown. Sensitivities \
consistent with blood culture isolate.

CURRENT ANTIBIOTICS: Amoxicillin 500mg TDS PO (stepped down from IV \
co-amoxiclav at 48h). Clarithromycin stopped (no atypical pathogen).

O/E:
General: Alert, orientated, looks tired. AMT 10/10.
Obs: RR 20, SpO2 95% on room air, HR 92 regular, BP 110/68, Temp 37.8C
Resp: Crackles right lower zone — no significant change from 48h review. \
No bronchial breathing. Air entry reduced right base.
Abdo: Soft, tolerating oral diet.

Impression: Day 3 CAP — suboptimal treatment response. CRP only decreased \
41% from admission (186 → 110). Evidence-based practice recommends reassessment if not \
improving by Day 3. Organism confirmed susceptible to current antibiotic.

Plan:
1. Senior review — suboptimal CRP response
2. Consider repeat imaging if no improvement by Day 4
3. Review antibiotic choice — organism susceptible, consider non-bacterial \
cause or complications (empyema, lung abscess)
4. Send repeat sputum culture
5. Continue monitoring — repeat bloods Day 4
"""


SYNTHETIC_LAB_REPORT_DAY34 = """\
====================================================================
  CITY GENERAL HOSPITAL NHS FOUNDATION TRUST
  Department of Clinical Biochemistry & Haematology
====================================================================
Patient: Robert JAMES   DOB: 15/03/1954   NHS: 943 476 2851
MRN: PT-2024-7890       Ward: AMU         Collected: 13/02/2026 07:00
Requested by: Dr B. Singh (SpR)
Sample: Venous blood (lithium heparin, EDTA)

BIOCHEMISTRY
--------------------------------------------------------------------
Test                Result    Units        Reference Range    Flag
--------------------------------------------------------------------
C-reactive protein  110       mg/L         <5                 H
Urea                7.0       mmol/L       2.5-7.8
Creatinine          92        umol/L       62-106
eGFR (CKD-EPI)     65        mL/min/1.73m2  >90              L
Sodium              137       mmol/L       133-146
Potassium           4.0       mmol/L       3.5-5.3
Procalcitonin       0.50      ng/mL        <0.1               H
Lactate             1.3       mmol/L       <2.0

HAEMATOLOGY
--------------------------------------------------------------------
Test                Result    Units        Reference Range    Flag
--------------------------------------------------------------------
White cell count    13.5      x10^9/L      4.0-11.0           H
Neutrophils         10.5      x10^9/L      2.0-7.5            H
Haemoglobin         130       g/L          130-170
Platelets           238       x10^9/L      150-400

Authorised by: Dr S. Khan (Consultant Biochemist) 13/02/2026 09:15
====================================================================
"""


_FHIR_DAY34_VITAL_UPDATES = {
    "Respiratory rate": (20, "/min"),
    "Heart rate": (92, "/min"),
    "Oxygen saturation": (95, "%"),
    "Body temperature": (37.8, "Cel"),
}

_FHIR_DAY34_BP_UPDATES = {
    "Systolic blood pressure": (110, "mmHg"),
    "Diastolic blood pressure": (68, "mmHg"),
}

_FHIR_DAY34_LAB_UPDATES = {
    "C-reactive protein": (110, "mg/L"),
    "Urea": (7.0, "mmol/L"),
    "Creatinine": (92, "umol/L"),
    "eGFR": (65, "mL/min/1.73m2"),
    "Sodium": (137, "mmol/L"),
    "Potassium": (4.0, "mmol/L"),
    "Procalcitonin": (0.50, "ng/mL"),
    "Lactate": (1.3, "mmol/L"),
    "White cell count": (13.5, "x10^9/L"),
    "Neutrophils": (10.5, "x10^9/L"),
    "Haemoglobin": (130, "g/L"),
    "Platelets": (238, "x10^9/L"),
}


def _update_fhir_bundle_day34(bundle: dict) -> None:
    """Update FHIR Bundle entries in place with Day 3-4 clinical data.

    Same pattern as _update_fhir_bundle_48h. Walks the bundle entries and
    updates vitals, labs, and DocumentReference.
    """
    new_datetime = "2026-02-13T07:00:00Z"

    for entry in bundle["entry"]:
        resource = entry["resource"]
        rtype = resource["resourceType"]

        if rtype == "Observation":
            coding = resource.get("code", {}).get("coding", [{}])
            display = coding[0].get("display", "") if coding else ""

            if display == "Blood pressure panel":
                for comp in resource.get("component", []):
                    comp_display = (
                        comp.get("code", {}).get("coding", [{}])[0].get("display", "")
                    )
                    if comp_display in _FHIR_DAY34_BP_UPDATES:
                        new_val, new_unit = _FHIR_DAY34_BP_UPDATES[comp_display]
                        comp["valueQuantity"]["value"] = new_val
                        comp["valueQuantity"]["unit"] = new_unit
                resource["effectiveDateTime"] = new_datetime

            elif display in _FHIR_DAY34_VITAL_UPDATES:
                new_val, new_unit = _FHIR_DAY34_VITAL_UPDATES[display]
                resource["valueQuantity"]["value"] = new_val
                resource["valueQuantity"]["unit"] = new_unit
                resource["effectiveDateTime"] = new_datetime

            elif display in _FHIR_DAY34_LAB_UPDATES:
                new_val, new_unit = _FHIR_DAY34_LAB_UPDATES[display]
                resource["valueQuantity"]["value"] = new_val
                resource["valueQuantity"]["unit"] = new_unit
                resource["effectiveDateTime"] = new_datetime

        elif rtype == "DocumentReference":
            _note_b64 = base64.b64encode(
                SYNTHETIC_CLERKING_NOTE_DAY34.encode("utf-8")
            ).decode("ascii")
            for content in resource.get("content", []):
                if "attachment" in content:
                    content["attachment"]["data"] = _note_b64
            resource["description"] = "Day 3 clinical review"

    # Add current oral antibiotic MedicationRequest
    bundle["entry"].append({
        "resource": {
            "resourceType": "MedicationRequest",
            "id": "med-amoxicillin-po-day3",
            "medicationCodeableConcept": {
                "text": "Amoxicillin 500mg PO",
            },
            "dosageInstruction": [{"text": "Three times daily"}],
            "status": "active",
            "subject": {"reference": "Patient/pt-001"},
        }
    })


SYNTHETIC_MICRO_RESULTS_DAY34 = [
    {
        "organism": "Streptococcus pneumoniae",
        "susceptibilities": {
            "amoxicillin": "S",
            "co-amoxiclav": "S",
            "clarithromycin": "S",
            "levofloxacin": "S",
            "ceftriaxone": "S",
        },
        "test_type": "blood_culture",
        "status": "positive",
    },
    {
        "organism": None,
        "susceptibilities": None,
        "test_type": "urine_antigen_legionella",
        "status": "negative",
    },
    {
        "organism": "Streptococcus pneumoniae",
        "susceptibilities": None,
        "test_type": "urine_antigen_pneumococcal",
        "status": "positive",
    },
    {
        "organism": "Streptococcus pneumoniae",
        "susceptibilities": {
            "amoxicillin": "S",
            "co-amoxiclav": "S",
            "clarithromycin": "S",
        },
        "test_type": "sputum_culture",
        "status": "positive",
    },
]


SYNTHETIC_TREATMENT_STATUS_DAY34 = {
    "current_route": "PO",
    "days_on_treatment": 3,
    "symptoms_improving": False,
    "oral_antibiotics": ["Amoxicillin 500mg TDS PO"],
}


def get_synthetic_day34_case() -> dict:
    """Return T=Day 3-4 case for treatment monitoring demo.

    Same patient, Day 3 of treatment. Not improving:
    - CRP only 41% decrease (186 → 110) — under 50% threshold
    - Persistent low-grade fever (37.8C)
    - Productive cough continues
    - S. pneumoniae confirmed on sputum too

    Uses real FHIR + lab extraction (no CXR — not repeated).
    """
    import copy

    case = get_synthetic_fhir_case()

    # --- Temporal FHIR data ---
    case["fhir_bundle"] = copy.deepcopy(case["fhir_bundle"])
    _update_fhir_bundle_day34(case["fhir_bundle"])
    case["lab_report"] = {
        "format": "text",
        "content": SYNTHETIC_LAB_REPORT_DAY34,
        "source": "city_general_pathology",
    }

    # --- Remove CXR image paths (CXR not repeated at Day 3) ---
    case["cxr"].pop("image_path", None)
    case["cxr"].pop("prior_image_path", None)

    # --- Micro results + treatment status ---
    case["micro_results"] = SYNTHETIC_MICRO_RESULTS_DAY34
    case["treatment_status"] = SYNTHETIC_TREATMENT_STATUS_DAY34
    case["admission_labs"] = {"crp": 186}

    # --- Prior antibiotic recommendation from T=0 ---
    case["prior_antibiotic_recommendation"] = {
        "severity_tier": "moderate",
        "first_line": "Amoxicillin 500mg TDS PO",
        "dose_route": "PO",
        "atypical_cover": None,
        "stewardship_notes": [],
    }

    # --- Update flat case_data for consistency with mock fallbacks ---
    case["clinical_exam"]["observations"] = {
        "respiratory_rate": 20,
        "systolic_bp": 110,
        "diastolic_bp": 68,
        "heart_rate": 92,
        "spo2": 95,
        "temperature": 37.8,
        "supplemental_o2": "room air",
    }
    case["clinical_exam"]["confusion_assessment"] = {
        "amt_score": 10,
        "amt_total": 10,
        "confused": False,
    }
    case["curb65_variables"] = {
        "confusion": False,
        "urea": 7.0,
        "respiratory_rate": 20,
        "systolic_bp": 110,
        "diastolic_bp": 68,
        "age": 72,
    }
    # Update flat lab_results to match Day 3-4 values
    case["lab_results"]["crp"]["value"] = 110
    case["lab_results"]["crp"]["abnormal"] = True
    case["lab_results"]["urea"]["value"] = 7.0
    case["lab_results"]["urea"]["abnormal"] = False
    case["lab_results"]["creatinine"]["value"] = 92
    case["lab_results"]["egfr"]["value"] = 65
    case["lab_results"]["wcc"]["value"] = 13.5
    case["lab_results"]["neutrophils"]["value"] = 10.5
    case["lab_results"]["haemoglobin"]["value"] = 130
    case["lab_results"]["platelets"]["value"] = 238
    case["lab_results"]["procalcitonin"]["value"] = 0.50
    case["lab_results"]["lactate"]["value"] = 1.3

    return case

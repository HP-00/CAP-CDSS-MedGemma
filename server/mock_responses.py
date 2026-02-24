"""Shared mock MedGemma responses for demo mode and E2E tests.

Extracted from test_pipeline_e2e.py so that server/mock_runner.py can import
without pulling in test-only dependencies (nest_asyncio, pytest, etc.).
"""

import json


# =====================================================================
# EHR QA mock responses (3 steps)
# =====================================================================

MOCK_EHR_NARRATIVE = (
    "1. RESPIRATORY EXAMINATION: Crackles right lower zone. "
    "Bronchial breathing right lower zone.\n"
    "2. CONFUSION / MENTAL STATUS: AMT 9/10, not confused.\n"
    "3. ALLERGIES: NKDA\n"
    "4. PAST MEDICAL HISTORY: COPD (moderate), T2DM.\n"
    "5. DRUG HISTORY: Salbutamol PRN, Tiotropium OD, Metformin BD.\n"
    "6. SOCIAL HISTORY: Lives independently. Not pregnant. "
    "Tolerates oral. No recent travel.\n"
    "7. PRESENTING COMPLAINT: 3-day productive cough, fever."
)

MOCK_EHR_STRUCTURED = (
    "1. DEMOGRAPHICS: Robert James, male, born 1954-03-15 (age 72).\n"
    "2. VITAL SIGNS: RR 22/min, BP 105/65, HR 98, SpO2 94%, Temp 38.4C.\n"
    "3. LAB VALUES: Urea 8.2 mmol/L, CRP 186 mg/L.\n"
    "4. CONDITIONS: COPD (moderate), T2DM.\n"
    "5. ALLERGIES: NKDA.\n"
    "6. MEDICATIONS: Salbutamol, Tiotropium, Metformin."
)


# =====================================================================
# Lab mock response
# =====================================================================

MOCK_LAB_FACTS = (
    "CRP: 186 mg/L (ref <5) — ABNORMAL\n"
    "Urea: 8.2 mmol/L (ref 2.5-7.8) — ABNORMAL\n"
    "Creatinine: 98 umol/L (ref 62-106) — normal\n"
    "eGFR: 62 mL/min/1.73m2 (ref >90) — ABNORMAL\n"
    "Sodium: 136 mmol/L — normal\n"
    "Potassium: 4.1 mmol/L — normal\n"
    "WCC: 15.3 x10^9/L — ABNORMAL\n"
    "Neutrophils: 12.8 x10^9/L — ABNORMAL\n"
    "Hb: 138 g/L — normal\n"
    "Platelets: 245 x10^9/L — normal\n"
    "Procalcitonin: 0.8 ng/mL — ABNORMAL\n"
    "Lactate: 1.4 mmol/L — normal"
)


# =====================================================================
# CXR mock responses (3 stages)
# =====================================================================

MOCK_CXR_CLASSIFICATION = json.dumps({
    "consolidation": {
        "present": True,
        "confidence": "moderate",
        "location": "right lower lobe",
        "description": "Patchy air-space opacification",
    },
    "pleural_effusion": {"present": False, "confidence": "high"},
    "cardiomegaly": {"present": False, "confidence": "high"},
    "edema": {"present": False, "confidence": "high"},
    "atelectasis": {"present": False, "confidence": "moderate"},
    "image_quality": {
        "projection": "PA",
        "rotation": "minimal",
        "penetration": "adequate",
    },
})

MOCK_CXR_LOCALIZATION = json.dumps([
    {"box_2d": [450, 550, 750, 850], "label": "consolidation"}
])

MOCK_CXR_LONGITUDINAL = json.dumps({
    "consolidation": {"change": "new", "description": "New right lower lobe consolidation"},
    "pleural_effusion": {"change": "unchanged", "description": "No effusion"},
    "cardiomegaly": {"change": "unchanged", "description": "Normal heart size"},
    "edema": {"change": "unchanged", "description": "No edema"},
    "atelectasis": {"change": "unchanged", "description": "No atelectasis"},
})


# =====================================================================
# Configurable builder functions
# =====================================================================

def _mock_ehr_synthesis(urea=8.2, confusion=False, rr=22, sbp=105, dbp=65,
                        age=72, hr=98, spo2=94, temp=38.4,
                        allergies=None, pregnancy=False,
                        oral_tolerance=True, eating=True,
                        sex="Male", comorbidities=None,
                        smoking_status="former"):
    """Build a configurable EHR synthesis JSON response."""
    if allergies is None:
        allergies = []
    if comorbidities is None:
        comorbidities = ["COPD (moderate)", "Type 2 diabetes mellitus"]
    return json.dumps({
        "demographics": {
            "age": age,
            "sex": sex,
            "allergies": allergies,
            "comorbidities": comorbidities,
            "recent_antibiotics": [],
            "pregnancy": pregnancy,
            "oral_tolerance": oral_tolerance,
            "travel_history": [],
            "smoking_status": smoking_status,
            "eating_independently": eating,
        },
        "clinical_exam": {
            "respiratory_exam": {
                "crackles": True,
                "crackles_location": "right lower zone",
                "bronchial_breathing": True,
                "bronchial_breathing_location": "right lower zone",
            },
            "observations": {
                "respiratory_rate": rr,
                "systolic_bp": sbp,
                "diastolic_bp": dbp,
                "heart_rate": hr,
                "spo2": spo2,
                "temperature": temp,
                "supplemental_o2": "room air",
            },
            "confusion_status": {"present": confusion, "amt_score": 9 if not confusion else 7},
        },
        "curb65_variables": {
            "confusion": confusion,
            "urea": urea,
            "respiratory_rate": rr,
            "systolic_bp": sbp,
            "diastolic_bp": dbp,
            "age": age,
        },
    })


def _mock_lab_synthesis(crp=186, urea=8.2):
    """Build a configurable lab synthesis JSON response."""
    return json.dumps({
        "lab_values": {
            "crp": {"value": crp, "unit": "mg/L", "reference_range": "<5", "abnormal_flag": True},
            "urea": {"value": urea, "unit": "mmol/L", "reference_range": "2.5-7.8",
                     "abnormal_flag": urea > 7.8},
            "creatinine": {"value": 98, "unit": "umol/L", "reference_range": "62-106",
                           "abnormal_flag": False},
            "egfr": {"value": 62, "unit": "mL/min/1.73m2", "reference_range": ">90",
                     "abnormal_flag": True},
            "sodium": {"value": 136, "unit": "mmol/L", "reference_range": "133-146",
                       "abnormal_flag": False},
            "potassium": {"value": 4.1, "unit": "mmol/L", "reference_range": "3.5-5.3",
                          "abnormal_flag": False},
            "wcc": {"value": 15.3, "unit": "x10^9/L", "reference_range": "4.0-11.0",
                    "abnormal_flag": True},
            "neutrophils": {"value": 12.8, "unit": "x10^9/L", "reference_range": "2.0-7.5",
                            "abnormal_flag": True},
            "haemoglobin": {"value": 138, "unit": "g/L", "reference_range": "130-170",
                            "abnormal_flag": False},
            "platelets": {"value": 245, "unit": "x10^9/L", "reference_range": "150-400",
                          "abnormal_flag": False},
            "procalcitonin": {"value": 0.8, "unit": "ng/mL", "reference_range": "<0.1",
                              "abnormal_flag": True},
            "lactate": {"value": 1.4, "unit": "mmol/L", "reference_range": "<2.0",
                        "abnormal_flag": False},
        }
    })


def _make_cxr_call_tracker():
    """Track CXR calls to return classification, then localization, then longitudinal."""
    cxr_idx = [0]

    def get_cxr_response(prompt):
        idx = cxr_idx[0]
        cxr_idx[0] += 1
        responses = [
            f"```json\n{MOCK_CXR_CLASSIFICATION}\n```",
            f"```json\n{MOCK_CXR_LOCALIZATION}\n```",
            f"```json\n{MOCK_CXR_LONGITUDINAL}\n```",
        ]
        return responses[min(idx, len(responses) - 1)]

    return get_cxr_response


def build_prompt_router(ehr_synthesis_json, lab_synthesis_json):
    """Build a prompt-keyword router for call_medgemma mocking.

    Routes MedGemma calls based on prompt content and images argument.
    Returns a side_effect function for use with unittest.mock.patch.
    """
    cxr_responder = _make_cxr_call_tracker()

    def router(prompt, max_new_tokens=1500, images=None, enable_thinking=True, **kwargs):
        # CXR: any call with images
        if images is not None:
            return cxr_responder(prompt)

        # EHR QA pipeline (3 steps)
        if "CLERKING NOTE:" in prompt:
            return MOCK_EHR_NARRATIVE
        if "STRUCTURED DATA:" in prompt:
            return MOCK_EHR_STRUCTURED
        if "Combine the following" in prompt:
            return f"```json\n{ehr_synthesis_json}\n```"

        # Lab pipeline (2 steps)
        if "LAB REPORT:" in prompt:
            return MOCK_LAB_FACTS
        if "extracted laboratory" in prompt:
            return f"```json\n{lab_synthesis_json}\n```"

        # Pipeline-level nodes
        if "clinician-facing summary" in prompt:
            return (
                "1. PATIENT: 72yo Male, COPD, T2DM\n"
                "2. SEVERITY: CURB65=2 (moderate)\n"
                "3. CXR: Consolidation present\n"
                "4. KEY BLOODS: CRP 186, Urea 8.2\n"
                "5. CONTRADICTIONS: See alerts\n"
                "6. TREATMENT: Amoxicillin 500mg TDS PO\n"
                "7. DATA GAPS: None\n"
                "8. MONITORING: Repeat CRP 48-72h\n"
                "AI-generated observations for clinician review."
            )

        # Contradiction resolution (strategies A-D only; E is deterministic)
        if "CONTRADICTION DETECTED" in prompt:
            return "Resolution: findings reviewed. CONFIDENCE: moderate"

        return f"[UNMATCHED PROMPT] {prompt[:200]}"

    return router

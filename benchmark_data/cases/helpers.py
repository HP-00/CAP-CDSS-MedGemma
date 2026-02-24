"""Benchmark case construction helpers.

Provides _BASE_CASE template, make_case() factory, and compute_ground_truth()
for auto-computing expected CURB65/severity/antibiotic from clinical logic.
"""

from __future__ import annotations

import copy
from typing import Optional

from cap_agent.agent.clinical_logic import compute_curb65, select_antibiotic


# Zero-scoring CURB65 baseline: age=50, urea=5.0, rr=18, sbp=120, dbp=70, amt=10
_BASE_CASE: dict = {
    "demographics": {
        "age": 50,
        "sex": "Female",
        "weight_kg": 70,
    },
    "presenting_complaint": "Productive cough, fever, and dyspnoea",
    "clinical_exam": {
        "respiratory_exam": {
            "crackles": True,
            "crackles_location": "right lower zone",
            "bronchial_breathing": False,
            "bronchial_breathing_location": None,
            "dullness_to_percussion": False,
            "dullness_location": None,
            "reduced_air_entry": False,
        },
        "observations": {
            "respiratory_rate": 18,
            "systolic_bp": 120,
            "diastolic_bp": 70,
            "heart_rate": 82,
            "spo2": 96,
            "temperature": 38.0,
            "supplemental_o2": "room air",
        },
        "confusion_assessment": {
            "amt_score": 10,
            "amt_total": 10,
            "confused": False,
        },
    },
    "lab_results": {
        "crp": {"value": 50, "unit": "mg/L", "reference_range": "<5", "abnormal": True},
        "urea": {"value": 5.0, "unit": "mmol/L", "reference_range": "2.5-7.8", "abnormal": False},
        "creatinine": {"value": 80, "unit": "umol/L", "reference_range": "62-106", "abnormal": False},
        "egfr": {"value": 90, "unit": "mL/min/1.73m2", "reference_range": ">90", "abnormal": False},
        "sodium": {"value": 138, "unit": "mmol/L", "reference_range": "133-146", "abnormal": False},
        "potassium": {"value": 4.2, "unit": "mmol/L", "reference_range": "3.5-5.3", "abnormal": False},
        "wcc": {"value": 12.0, "unit": "x10^9/L", "reference_range": "4.0-11.0", "abnormal": True},
        "neutrophils": {"value": 9.0, "unit": "x10^9/L", "reference_range": "2.0-7.5", "abnormal": True},
        "haemoglobin": {"value": 140, "unit": "g/L", "reference_range": "120-160", "abnormal": False},
        "platelets": {"value": 250, "unit": "x10^9/L", "reference_range": "150-400", "abnormal": False},
        "procalcitonin": {"value": 0.3, "unit": "ng/mL", "reference_range": "<0.1", "abnormal": True},
        "lactate": {"value": 1.2, "unit": "mmol/L", "reference_range": "<2.0", "abnormal": False},
    },
    "cxr": {
        "findings": {
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
        },
        "image_quality": {
            "projection": "PA",
            "rotation": "minimal",
            "penetration": "adequate",
        },
        "image_path": None,
        "prior_image_path": None,
    },
    "past_medical_history": {
        "comorbidities": [],
        "medications": [],
        "allergies": [],
        "recent_antibiotics": [],
    },
    "social_history": {
        "pregnancy": False,
        "oral_tolerance": True,
        "eating_independently": True,
        "travel_history": [],
        "immunosuppression": False,
        "smoking_status": "never",
    },
}


def make_case(
    case_id: str,
    *,
    # CURB65 variables
    age: Optional[int] = None,
    urea: Optional[float] = None,
    rr: Optional[int] = None,
    sbp: Optional[int] = None,
    dbp: Optional[int] = None,
    amt: Optional[int] = None,
    # CXR overrides
    cxr_consolidation: Optional[bool] = None,
    cxr_consolidation_location: Optional[str] = None,
    cxr_effusion: Optional[bool] = None,
    # Lab overrides
    crp: Optional[float] = None,
    # Clinical exam overrides
    crackles: Optional[bool] = None,
    crackles_location: Optional[str] = None,
    bronchial_breathing: Optional[bool] = None,
    bronchial_breathing_location: Optional[str] = None,
    spo2: Optional[int] = None,
    heart_rate: Optional[int] = None,
    temperature: Optional[float] = None,
    # Demographics / social
    allergies: Optional[list] = None,
    comorbidities: Optional[list] = None,
    medications: Optional[list] = None,
    recent_antibiotics: Optional[list] = None,
    immunosuppression: Optional[bool] = None,
    pregnancy: Optional[bool] = None,
    oral_tolerance: Optional[bool] = None,
    travel_history: Optional[list] = None,
    # Stewardship / temporal
    micro_results: Optional[list] = None,
    prior_antibiotic_recommendation: Optional[dict] = None,
    treatment_status: Optional[dict] = None,
    admission_labs: Optional[dict] = None,
    # Ground truth (contradictions must be specified manually)
    expected_contradictions: Optional[list] = None,
) -> dict:
    """Build a benchmark case from _BASE_CASE with targeted overrides."""
    case = copy.deepcopy(_BASE_CASE)
    case["case_id"] = case_id
    case["patient_id"] = f"PT-BENCH-{case_id}"

    # CURB65 variables
    if age is not None:
        case["demographics"]["age"] = age
    if urea is not None:
        case["lab_results"]["urea"]["value"] = urea
        case["lab_results"]["urea"]["abnormal"] = urea > 7.8
    if rr is not None:
        case["clinical_exam"]["observations"]["respiratory_rate"] = rr
    if sbp is not None:
        case["clinical_exam"]["observations"]["systolic_bp"] = sbp
    if dbp is not None:
        case["clinical_exam"]["observations"]["diastolic_bp"] = dbp
    if amt is not None:
        case["clinical_exam"]["confusion_assessment"]["amt_score"] = amt
        case["clinical_exam"]["confusion_assessment"]["confused"] = amt <= 8

    # CXR overrides
    if cxr_consolidation is not None:
        case["cxr"]["findings"]["consolidation"]["present"] = cxr_consolidation
    if cxr_consolidation_location is not None:
        case["cxr"]["findings"]["consolidation"]["location"] = cxr_consolidation_location
    if cxr_effusion is not None:
        case["cxr"]["findings"]["pleural_effusion"]["present"] = cxr_effusion

    # Lab overrides
    if crp is not None:
        case["lab_results"]["crp"]["value"] = crp
        case["lab_results"]["crp"]["abnormal"] = crp > 5

    # Clinical exam overrides
    if crackles is not None:
        case["clinical_exam"]["respiratory_exam"]["crackles"] = crackles
    if crackles_location is not None:
        case["clinical_exam"]["respiratory_exam"]["crackles_location"] = crackles_location
    if bronchial_breathing is not None:
        case["clinical_exam"]["respiratory_exam"]["bronchial_breathing"] = bronchial_breathing
    if bronchial_breathing_location is not None:
        case["clinical_exam"]["respiratory_exam"]["bronchial_breathing_location"] = bronchial_breathing_location
    if spo2 is not None:
        case["clinical_exam"]["observations"]["spo2"] = spo2
    if heart_rate is not None:
        case["clinical_exam"]["observations"]["heart_rate"] = heart_rate
    if temperature is not None:
        case["clinical_exam"]["observations"]["temperature"] = temperature

    # Demographics / social
    if allergies is not None:
        case["past_medical_history"]["allergies"] = allergies
    if comorbidities is not None:
        case["past_medical_history"]["comorbidities"] = comorbidities
    if medications is not None:
        case["past_medical_history"]["medications"] = medications
    if recent_antibiotics is not None:
        case["past_medical_history"]["recent_antibiotics"] = recent_antibiotics
    if immunosuppression is not None:
        case["social_history"]["immunosuppression"] = immunosuppression
    if pregnancy is not None:
        case["social_history"]["pregnancy"] = pregnancy
    if oral_tolerance is not None:
        case["social_history"]["oral_tolerance"] = oral_tolerance
    if travel_history is not None:
        case["social_history"]["travel_history"] = travel_history

    # Stewardship / temporal
    if micro_results is not None:
        case["micro_results"] = micro_results
    if prior_antibiotic_recommendation is not None:
        case["prior_antibiotic_recommendation"] = prior_antibiotic_recommendation
    if treatment_status is not None:
        case["treatment_status"] = treatment_status
    if admission_labs is not None:
        case["admission_labs"] = admission_labs

    # Auto-compute ground truth
    case["ground_truth"] = compute_ground_truth(
        case, expected_contradictions=expected_contradictions or []
    )

    return case


def compute_ground_truth(
    case: dict,
    *,
    expected_contradictions: Optional[list] = None,
) -> dict:
    """Auto-compute ground truth from case data using clinical logic functions.

    CURB65 score, severity tier, and antibiotic are computed deterministically.
    Contradictions must be specified manually since detection depends on
    cross-field interactions that are case-specific.
    """
    exam = case["clinical_exam"]
    obs = exam["observations"]
    confusion = exam["confusion_assessment"]

    curb65_vars = {
        "confusion": confusion["confused"],
        "urea": case["lab_results"]["urea"]["value"],
        "respiratory_rate": obs["respiratory_rate"],
        "systolic_bp": obs["systolic_bp"],
        "diastolic_bp": obs["diastolic_bp"],
        "age": case["demographics"]["age"],
    }

    curb65_result = compute_curb65(curb65_vars)

    abx = select_antibiotic(
        severity=curb65_result["severity_tier"],
        allergies=case["past_medical_history"]["allergies"],
        oral_tolerance=case["social_history"]["oral_tolerance"],
        pregnancy=case["social_history"]["pregnancy"],
        travel_history=case["social_history"]["travel_history"],
        egfr=case["lab_results"].get("egfr", {}).get("value"),
        recent_antibiotics=case["past_medical_history"]["recent_antibiotics"],
    )

    return {
        "curb65": curb65_result["curb65"],
        "severity_tier": curb65_result["severity_tier"],
        "contradictions": expected_contradictions or [],
        "antibiotic": abx["first_line"],
        "discharge_met": None,
        "crp_trend": None,
    }

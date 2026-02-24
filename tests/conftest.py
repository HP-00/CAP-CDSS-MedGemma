"""Shared fixtures for CAP agent tests."""

import pytest

from cap_agent.data.synthetic import get_synthetic_case


@pytest.fixture
def synthetic_case():
    """Return a fresh deep copy of the synthetic CAP case."""
    return get_synthetic_case()


@pytest.fixture
def synthetic_curb65_variables():
    """CURB65 variables extracted from the synthetic case."""
    return {
        "confusion": False,
        "urea": 8.2,
        "respiratory_rate": 22,
        "systolic_bp": 105,
        "diastolic_bp": 65,
        "age": 72,
    }


@pytest.fixture
def concordant_cxr():
    """CXR analysis with consolidation (concordant with clinical exam)."""
    return {
        "consolidation": {
            "present": True,
            "confidence": "moderate",
            "location": "right lower lobe",
        },
        "pleural_effusion": {"present": False, "confidence": "high"},
        "cardiomegaly": {"present": False, "confidence": "high"},
        "edema": {"present": False, "confidence": "high"},
        "atelectasis": {"present": False, "confidence": "moderate"},
    }


@pytest.fixture
def concordant_exam():
    """Clinical exam with focal crackles (concordant with CXR)."""
    return {
        "respiratory_exam": {
            "crackles": True,
            "crackles_location": "right lower zone",
            "bronchial_breathing": True,
            "bronchial_breathing_location": "right lower zone",
        },
        "observations": {
            "respiratory_rate": 22,
            "systolic_bp": 105,
            "diastolic_bp": 65,
            "heart_rate": 98,
            "spo2": 94,
            "temperature": 38.4,
        },
        "confusion_status": {"present": False, "amt_score": 9},
    }


@pytest.fixture
def concordant_labs():
    """Lab values with elevated CRP (concordant with pneumonia)."""
    return {
        "crp": {"value": 186, "unit": "mg/L", "reference_range": "<5", "abnormal_flag": True},
        "urea": {"value": 8.2, "unit": "mmol/L", "reference_range": "2.5-7.8", "abnormal_flag": True},
        "egfr": {"value": 62, "unit": "mL/min/1.73m2", "reference_range": ">90", "abnormal_flag": True},
        "lactate": {"value": 1.4, "unit": "mmol/L", "reference_range": "<2.0", "abnormal_flag": False},
    }

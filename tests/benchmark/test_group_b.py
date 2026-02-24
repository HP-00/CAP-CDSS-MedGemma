"""Tests for Group B: cross-modal contradiction cases (CR-1 through CR-6)."""

import pytest

from benchmark_data.cases.group_b_contradictions import GROUP_B_CASES
from cap_agent.agent.clinical_logic import compute_curb65, detect_contradictions


def _build_detection_args(case: dict) -> dict:
    """Build the argument dict for detect_contradictions() from flat case_data."""
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

    # Build cxr dict (mock extraction uses findings directly)
    cxr = case["cxr"]["findings"]

    # Build exam dict (as mock_extract_clinical_notes would produce)
    exam_dict = {
        "respiratory_exam": exam["respiratory_exam"],
        "observations": obs,
        "confusion_status": {
            "present": confusion["confused"],
            "amt_score": confusion["amt_score"],
        },
    }

    # Build labs dict (as mock_extract_lab_results would produce)
    labs = {}
    for test_name, test_data in case["lab_results"].items():
        labs[test_name] = {
            "value": test_data["value"],
            "unit": test_data["unit"],
            "reference_range": test_data["reference_range"],
            "abnormal_flag": test_data["abnormal"],
        }

    # Build demographics dict
    pmh = case["past_medical_history"]
    social = case["social_history"]
    demographics = {
        "age": case["demographics"]["age"],
        "sex": case["demographics"]["sex"],
        "allergies": pmh["allergies"],
        "comorbidities": pmh["comorbidities"],
        "pregnancy": social["pregnancy"],
        "oral_tolerance": social["oral_tolerance"],
    }

    return {
        "cxr": cxr,
        "exam": exam_dict,
        "labs": labs,
        "demographics": demographics,
        "curb65": curb65_result,
        "case_data": case,
    }


class TestGroupBStructure:
    def test_case_count(self):
        assert len(GROUP_B_CASES) == 8

    def test_all_have_ground_truth(self):
        for case in GROUP_B_CASES:
            assert "ground_truth" in case

    def test_all_have_non_empty_contradictions(self):
        for case in GROUP_B_CASES:
            assert len(case["ground_truth"]["contradictions"]) > 0, (
                f"{case['case_id']} should have contradictions"
            )

    def test_no_duplicate_ids(self):
        ids = [c["case_id"] for c in GROUP_B_CASES]
        assert len(ids) == len(set(ids))


class TestGroupBContradictionDetection:
    """Verify each case's contradictions match detect_contradictions() output."""

    @pytest.mark.parametrize("case", GROUP_B_CASES, ids=lambda c: c["case_id"])
    def test_contradiction_rules_match(self, case):
        args = _build_detection_args(case)
        detected = detect_contradictions(**args)
        detected_ids = sorted(set(c["rule_id"] for c in detected))
        expected_ids = sorted(case["ground_truth"]["contradictions"])
        assert detected_ids == expected_ids, (
            f"{case['case_id']}: expected {expected_ids}, got {detected_ids}"
        )

    def test_cr1_high_confidence(self):
        case = next(c for c in GROUP_B_CASES if c["case_id"] == "CR1-HIGH")
        args = _build_detection_args(case)
        detected = detect_contradictions(**args)
        cr1 = next(c for c in detected if c["rule_id"] == "CR-1")
        assert cr1["confidence"] == "high"

    def test_cr1_mod_confidence(self):
        case = next(c for c in GROUP_B_CASES if c["case_id"] == "CR1-MOD")
        args = _build_detection_args(case)
        detected = detect_contradictions(**args)
        cr1 = next(c for c in detected if c["rule_id"] == "CR-1")
        assert cr1["confidence"] == "moderate"

    def test_cr2_high_crp_above_200(self):
        case = next(c for c in GROUP_B_CASES if c["case_id"] == "CR2-HIGH")
        args = _build_detection_args(case)
        detected = detect_contradictions(**args)
        cr2 = next(c for c in detected if c["rule_id"] == "CR-2")
        assert cr2["confidence"] == "high"

    def test_cr3_high_confidence_crp_below_10(self):
        case = next(c for c in GROUP_B_CASES if c["case_id"] == "CR3-HIGH")
        args = _build_detection_args(case)
        detected = detect_contradictions(**args)
        cr3 = next(c for c in detected if c["rule_id"] == "CR-3")
        assert cr3["confidence"] == "high"

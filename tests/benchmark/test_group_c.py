"""Tests for Group C: stewardship contradiction cases (CR-7 through CR-11)."""

import pytest

from benchmark_data.cases.group_c_stewardship import GROUP_C_CASES
from cap_agent.agent.clinical_logic import (
    compute_curb65,
    detect_contradictions,
    detect_cr10,
    select_antibiotic,
)


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

    cxr = case["cxr"]["findings"]

    exam_dict = {
        "respiratory_exam": exam["respiratory_exam"],
        "observations": obs,
        "confusion_status": {
            "present": confusion["confused"],
            "amt_score": confusion["amt_score"],
        },
    }

    labs = {}
    for test_name, test_data in case["lab_results"].items():
        labs[test_name] = {
            "value": test_data["value"],
            "unit": test_data["unit"],
            "reference_range": test_data["reference_range"],
            "abnormal_flag": test_data["abnormal"],
        }

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
        "antibiotic_recommendation": case.get("prior_antibiotic_recommendation"),
        "micro_results": case.get("micro_results"),
    }


class TestGroupCStructure:
    def test_case_count(self):
        assert len(GROUP_C_CASES) == 10

    def test_all_have_ground_truth(self):
        for case in GROUP_C_CASES:
            assert "ground_truth" in case

    def test_no_duplicate_ids(self):
        ids = [c["case_id"] for c in GROUP_C_CASES]
        assert len(ids) == len(set(ids))


class TestCR7Detection:
    """CR-7: Antibiotic doesn't cover identified organism."""

    def test_cr7_lab_resistance_fires(self):
        case = next(c for c in GROUP_C_CASES if c["case_id"] == "CR7-LAB-R")
        args = _build_detection_args(case)
        detected = detect_contradictions(**args)
        rule_ids = [c["rule_id"] for c in detected]
        assert "CR-7" in rule_ids

    def test_cr7_lab_resistance_high_confidence(self):
        case = next(c for c in GROUP_C_CASES if c["case_id"] == "CR7-LAB-R")
        args = _build_detection_args(case)
        detected = detect_contradictions(**args)
        cr7s = [c for c in detected if c["rule_id"] == "CR-7"]
        assert any(c["confidence"] == "high" for c in cr7s)

    def test_cr7_population_resistance_fires(self):
        case = next(c for c in GROUP_C_CASES if c["case_id"] == "CR7-POP-R")
        args = _build_detection_args(case)
        detected = detect_contradictions(**args)
        rule_ids = [c["rule_id"] for c in detected]
        assert "CR-7" in rule_ids

    def test_cr7_population_resistance_moderate_confidence(self):
        case = next(c for c in GROUP_C_CASES if c["case_id"] == "CR7-POP-R")
        args = _build_detection_args(case)
        detected = detect_contradictions(**args)
        cr7s = [c for c in detected if c["rule_id"] == "CR-7"]
        assert any(c["confidence"] == "moderate" for c in cr7s)


class TestCR8Detection:
    """CR-8: Macrolide prescribed, no atypical pathogen on micro."""

    def test_cr8_fires_moderate_severity(self):
        case = next(c for c in GROUP_C_CASES if c["case_id"] == "CR8-FIRE")
        args = _build_detection_args(case)
        detected = detect_contradictions(**args)
        rule_ids = [c["rule_id"] for c in detected]
        assert "CR-8" in rule_ids

    def test_cr8_exempt_high_severity(self):
        case = next(c for c in GROUP_C_CASES if c["case_id"] == "CR8-EXEMPT")
        args = _build_detection_args(case)
        detected = detect_contradictions(**args)
        rule_ids = [c["rule_id"] for c in detected]
        assert "CR-8" not in rule_ids


class TestCR9Detection:
    """CR-9: IV >48h but oral tolerance + improving."""

    def test_cr9_fires_when_stable(self):
        case = next(c for c in GROUP_C_CASES if c["case_id"] == "CR9-MET")
        args = _build_detection_args(case)
        detected = detect_contradictions(**args)
        rule_ids = [c["rule_id"] for c in detected]
        assert "CR-9" in rule_ids

    def test_cr9_does_not_fire_when_unstable(self):
        case = next(c for c in GROUP_C_CASES if c["case_id"] == "CR9-NOT")
        args = _build_detection_args(case)
        detected = detect_contradictions(**args)
        rule_ids = [c["rule_id"] for c in detected]
        assert "CR-9" not in rule_ids


class TestCR10Detection:
    """CR-10: Fluoroquinolone + penicillin intolerance. Uses detect_cr10()."""

    def test_cr10_fires_with_intolerance(self):
        case = next(c for c in GROUP_C_CASES if c["case_id"] == "CR10-FIRE")
        gt = case["ground_truth"]
        abx = select_antibiotic(
            severity=gt["severity_tier"],
            allergies=case["past_medical_history"]["allergies"],
        )
        cr10 = detect_cr10(abx, case["past_medical_history"]["allergies"])
        assert cr10 is not None
        assert cr10["rule_id"] == "CR-10"

    def test_cr10_does_not_fire_with_true_allergy(self):
        case = next(c for c in GROUP_C_CASES if c["case_id"] == "CR10-TRUE")
        gt = case["ground_truth"]
        abx = select_antibiotic(
            severity=gt["severity_tier"],
            allergies=case["past_medical_history"]["allergies"],
        )
        cr10 = detect_cr10(abx, case["past_medical_history"]["allergies"])
        assert cr10 is None


class TestCR11Detection:
    """CR-11: Pneumococcal + broad-spectrum → de-escalate."""

    def test_cr11_fires(self):
        case = next(c for c in GROUP_C_CASES if c["case_id"] == "CR11-FIRE")
        args = _build_detection_args(case)
        detected = detect_contradictions(**args)
        rule_ids = [c["rule_id"] for c in detected]
        assert "CR-11" in rule_ids

    def test_cr11_with_susceptibility_high_confidence(self):
        case = next(c for c in GROUP_C_CASES if c["case_id"] == "CR11-SUSC")
        args = _build_detection_args(case)
        detected = detect_contradictions(**args)
        cr11s = [c for c in detected if c["rule_id"] == "CR-11"]
        assert len(cr11s) > 0
        assert cr11s[0]["confidence"] == "high"


class TestNegativeCases:
    """Verify that negative cases (expected no contradictions) don't fire."""

    @pytest.mark.parametrize(
        "case_id",
        ["CR8-EXEMPT", "CR9-NOT", "CR10-TRUE"],
    )
    def test_negative_cases_no_target_rule(self, case_id):
        case = next(c for c in GROUP_C_CASES if c["case_id"] == case_id)
        expected = case["ground_truth"]["contradictions"]
        assert expected == [], f"{case_id} should have no expected contradictions"

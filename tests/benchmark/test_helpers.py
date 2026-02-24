"""Tests for benchmark case construction helpers."""

import pytest

from benchmark_data.cases.helpers import _BASE_CASE, make_case, compute_ground_truth
from cap_agent.agent.clinical_logic import compute_curb65


class TestBaseCaseSchema:
    """Verify _BASE_CASE has all fields required by the pipeline."""

    def test_required_pipeline_keys(self):
        for key in ["demographics", "clinical_exam", "lab_results", "cxr", "past_medical_history"]:
            assert key in _BASE_CASE, f"Missing required key: {key}"

    def test_social_history_present(self):
        assert "social_history" in _BASE_CASE

    def test_social_history_subkeys(self):
        sh = _BASE_CASE["social_history"]
        for key in ["pregnancy", "oral_tolerance", "eating_independently",
                     "travel_history", "immunosuppression", "smoking_status"]:
            assert key in sh, f"Missing social_history key: {key}"

    def test_past_medical_history_complete(self):
        pmh = _BASE_CASE["past_medical_history"]
        for key in ["comorbidities", "medications", "allergies", "recent_antibiotics"]:
            assert key in pmh, f"Missing past_medical_history key: {key}"

    def test_confusion_threshold(self):
        ca = _BASE_CASE["clinical_exam"]["confusion_assessment"]
        assert ca["amt_score"] == 10
        assert ca["confused"] is False

    def test_baseline_zero_curb65(self):
        """All baseline values should give CURB65=0."""
        obs = _BASE_CASE["clinical_exam"]["observations"]
        confusion = _BASE_CASE["clinical_exam"]["confusion_assessment"]
        curb65_vars = {
            "confusion": confusion["confused"],
            "urea": _BASE_CASE["lab_results"]["urea"]["value"],
            "respiratory_rate": obs["respiratory_rate"],
            "systolic_bp": obs["systolic_bp"],
            "diastolic_bp": obs["diastolic_bp"],
            "age": _BASE_CASE["demographics"]["age"],
        }
        result = compute_curb65(curb65_vars)
        assert result["curb65"] == 0
        assert result["severity_tier"] == "low"


class TestMakeCase:
    """Verify make_case() factory."""

    def test_returns_case_id(self):
        case = make_case("TEST-001")
        assert case["case_id"] == "TEST-001"
        assert case["patient_id"] == "PT-BENCH-TEST-001"

    def test_has_ground_truth(self):
        case = make_case("TEST-002")
        gt = case["ground_truth"]
        assert "curb65" in gt
        assert "severity_tier" in gt
        assert "contradictions" in gt
        assert "antibiotic" in gt

    def test_age_override(self):
        case = make_case("TEST-AGE", age=75)
        assert case["demographics"]["age"] == 75

    def test_urea_override(self):
        case = make_case("TEST-UREA", urea=8.5)
        assert case["lab_results"]["urea"]["value"] == 8.5
        assert case["lab_results"]["urea"]["abnormal"] is True

    def test_amt_override_sets_confused(self):
        case = make_case("TEST-AMT", amt=7)
        assert case["clinical_exam"]["confusion_assessment"]["amt_score"] == 7
        assert case["clinical_exam"]["confusion_assessment"]["confused"] is True

    def test_amt_above_threshold_not_confused(self):
        case = make_case("TEST-AMT-OK", amt=9)
        assert case["clinical_exam"]["confusion_assessment"]["confused"] is False

    def test_cxr_overrides(self):
        case = make_case("TEST-CXR", cxr_consolidation=False, cxr_effusion=True)
        assert case["cxr"]["findings"]["consolidation"]["present"] is False
        assert case["cxr"]["findings"]["pleural_effusion"]["present"] is True

    def test_allergy_override(self):
        allergy = [{"drug": "penicillin", "reaction_type": "anaphylaxis", "severity": "severe"}]
        case = make_case("TEST-ALLERGY", allergies=allergy)
        assert case["past_medical_history"]["allergies"] == allergy

    def test_micro_results_added(self):
        micro = [{"test_type": "sputum culture", "status": "positive", "organism": "S. pneumoniae"}]
        case = make_case("TEST-MICRO", micro_results=micro)
        assert case["micro_results"] == micro

    def test_deep_copy_isolation(self):
        case1 = make_case("ISO-1", crp=200)
        case2 = make_case("ISO-2", crp=10)
        assert case1["lab_results"]["crp"]["value"] == 200
        assert case2["lab_results"]["crp"]["value"] == 10


class TestComputeGroundTruth:
    """Verify compute_ground_truth() round-trip."""

    def test_ground_truth_shape(self):
        case = make_case("GT-SHAPE")
        gt = case["ground_truth"]
        assert isinstance(gt["curb65"], int)
        assert gt["severity_tier"] in ("low", "moderate", "high")
        assert isinstance(gt["contradictions"], list)
        assert isinstance(gt["antibiotic"], str)

    def test_round_trip_baseline(self):
        case = make_case("GT-BASELINE")
        gt = case["ground_truth"]
        assert gt["curb65"] == 0
        assert gt["severity_tier"] == "low"
        assert "amoxicillin" in gt["antibiotic"].lower()

    def test_round_trip_high_severity(self):
        case = make_case("GT-HIGH", age=65, urea=7.1, rr=30)
        gt = case["ground_truth"]
        assert gt["curb65"] == 3
        assert gt["severity_tier"] == "high"
        assert "co-amoxiclav" in gt["antibiotic"].lower()

    def test_contradictions_passthrough(self):
        case = make_case("GT-CR", expected_contradictions=["CR-1", "CR-2"])
        assert case["ground_truth"]["contradictions"] == ["CR-1", "CR-2"]

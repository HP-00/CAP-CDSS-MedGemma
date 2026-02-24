"""Tests for Group A: CURB65 boundary cases."""

import pytest

from benchmark_data.cases.group_a_curb65 import GROUP_A_CASES
from cap_agent.agent.clinical_logic import compute_curb65


class TestGroupAStructure:
    """Verify Group A case list structure."""

    def test_case_count(self):
        assert len(GROUP_A_CASES) == 15

    def test_all_have_ground_truth(self):
        for case in GROUP_A_CASES:
            assert "ground_truth" in case, f"{case['case_id']} missing ground_truth"

    def test_no_duplicate_ids(self):
        ids = [c["case_id"] for c in GROUP_A_CASES]
        assert len(ids) == len(set(ids))

    def test_all_have_empty_contradictions(self):
        for case in GROUP_A_CASES:
            assert case["ground_truth"]["contradictions"] == [], (
                f"{case['case_id']} should have no contradictions"
            )

    def test_all_have_required_pipeline_keys(self):
        required = ["demographics", "clinical_exam", "lab_results", "cxr", "past_medical_history"]
        for case in GROUP_A_CASES:
            for key in required:
                assert key in case, f"{case['case_id']} missing {key}"


class TestBoundaryValues:
    """Spot-check boundary value correctness."""

    def _get_case(self, case_id: str) -> dict:
        return next(c for c in GROUP_A_CASES if c["case_id"] == case_id)

    def test_urea_7_gives_u0(self):
        case = self._get_case("CURB65-U-BELOW")
        assert case["ground_truth"]["curb65"] == 0

    def test_urea_7_1_gives_u1(self):
        case = self._get_case("CURB65-U-ABOVE")
        assert case["ground_truth"]["curb65"] == 1

    def test_rr_29_gives_r0(self):
        case = self._get_case("CURB65-R-BELOW")
        assert case["ground_truth"]["curb65"] == 0

    def test_rr_30_gives_r1(self):
        case = self._get_case("CURB65-R-ABOVE")
        assert case["ground_truth"]["curb65"] == 1

    def test_sbp_90_gives_b0(self):
        case = self._get_case("CURB65-SBP-BELOW")
        assert case["ground_truth"]["curb65"] == 0

    def test_sbp_89_gives_b1(self):
        case = self._get_case("CURB65-SBP-ABOVE")
        assert case["ground_truth"]["curb65"] == 1

    def test_dbp_61_gives_b0(self):
        case = self._get_case("CURB65-DBP-BELOW")
        assert case["ground_truth"]["curb65"] == 0

    def test_dbp_60_gives_b1(self):
        case = self._get_case("CURB65-DBP-ABOVE")
        assert case["ground_truth"]["curb65"] == 1

    def test_age_64_gives_age0(self):
        case = self._get_case("CURB65-AGE-BELOW")
        assert case["ground_truth"]["curb65"] == 0

    def test_age_65_gives_age1(self):
        case = self._get_case("CURB65-AGE-ABOVE")
        assert case["ground_truth"]["curb65"] == 1

    def test_amt_9_gives_c0(self):
        case = self._get_case("CURB65-AMT-BELOW")
        assert case["ground_truth"]["curb65"] == 0

    def test_amt_8_gives_c1(self):
        case = self._get_case("CURB65-AMT-ABOVE")
        assert case["ground_truth"]["curb65"] == 1


class TestCompositeSeverity:
    """Test composite severity tier cases."""

    def _get_case(self, case_id: str) -> dict:
        return next(c for c in GROUP_A_CASES if c["case_id"] == case_id)

    def test_composite_low(self):
        case = self._get_case("CURB65-COMPOSITE-LOW")
        assert case["ground_truth"]["curb65"] == 0
        assert case["ground_truth"]["severity_tier"] == "low"

    def test_composite_moderate(self):
        case = self._get_case("CURB65-COMPOSITE-MOD")
        assert case["ground_truth"]["curb65"] == 2
        assert case["ground_truth"]["severity_tier"] == "moderate"

    def test_composite_high(self):
        case = self._get_case("CURB65-COMPOSITE-HIGH")
        assert case["ground_truth"]["curb65"] == 4
        assert case["ground_truth"]["severity_tier"] == "high"


class TestGroundTruthVerification:
    """Parametrized: every case's ground truth matches compute_curb65()."""

    @pytest.mark.parametrize("case", GROUP_A_CASES, ids=lambda c: c["case_id"])
    def test_ground_truth_matches_clinical_logic(self, case):
        obs = case["clinical_exam"]["observations"]
        confusion = case["clinical_exam"]["confusion_assessment"]
        curb65_vars = {
            "confusion": confusion["confused"],
            "urea": case["lab_results"]["urea"]["value"],
            "respiratory_rate": obs["respiratory_rate"],
            "systolic_bp": obs["systolic_bp"],
            "diastolic_bp": obs["diastolic_bp"],
            "age": case["demographics"]["age"],
        }
        result = compute_curb65(curb65_vars)
        gt = case["ground_truth"]
        assert result["curb65"] == gt["curb65"], (
            f"{case['case_id']}: expected CURB65={gt['curb65']}, got {result['curb65']}"
        )
        assert result["severity_tier"] == gt["severity_tier"], (
            f"{case['case_id']}: expected {gt['severity_tier']}, got {result['severity_tier']}"
        )

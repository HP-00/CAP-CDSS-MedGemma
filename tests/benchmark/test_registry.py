"""Tests for benchmark case registry."""

import pytest

from benchmark_data.cases.registry import get_track2_cases, get_track1_cases, get_all_cases


class TestTrack2Registry:
    def test_track2_count(self):
        assert len(get_track2_cases()) == 33

    def test_no_duplicate_ids(self):
        cases = get_track2_cases()
        ids = [c["case_id"] for c in cases]
        assert len(ids) == len(set(ids)), f"Duplicate IDs: {[i for i in ids if ids.count(i) > 1]}"

    def test_all_have_ground_truth(self):
        for case in get_track2_cases():
            assert "ground_truth" in case, f"{case['case_id']} missing ground_truth"

    def test_ground_truth_required_keys(self):
        required = {"curb65", "severity_tier", "contradictions", "antibiotic"}
        for case in get_track2_cases():
            gt_keys = set(case["ground_truth"].keys())
            missing = required - gt_keys
            assert not missing, f"{case['case_id']} missing ground_truth keys: {missing}"

    def test_all_have_required_pipeline_keys(self):
        required = ["demographics", "clinical_exam", "lab_results", "cxr", "past_medical_history"]
        for case in get_track2_cases():
            for key in required:
                assert key in case, f"{case['case_id']} missing {key}"


class TestAllCasesRegistry:
    def test_all_cases_count(self):
        total = len(get_all_cases())
        assert total == 33 + 12  # 33 Track 2 + 12 Track 1

    def test_no_duplicate_ids_across_tracks(self):
        cases = get_all_cases()
        ids = [c["case_id"] for c in cases]
        assert len(ids) == len(set(ids))

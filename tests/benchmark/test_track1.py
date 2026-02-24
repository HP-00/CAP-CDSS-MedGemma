"""Tests for Track 1 RSNA case definitions."""

from benchmark_data.cases.track1_cases import TRACK1_CASES


class TestTrack1Structure:
    def test_case_count(self):
        assert len(TRACK1_CASES) == 12

    def test_all_have_image_path(self):
        for case in TRACK1_CASES:
            assert case["cxr"].get("image_path"), f"{case['case_id']} missing image_path"
            assert case["cxr"]["image_path"] != "placeholder_cxr.jpg", (
                f"{case['case_id']} still has default placeholder"
            )

    def test_all_have_cxr_ground_truth(self):
        for case in TRACK1_CASES:
            gt = case["ground_truth"]
            assert "cxr_ground_truth" in gt, f"{case['case_id']} missing cxr_ground_truth"
            cxr_gt = gt["cxr_ground_truth"]
            assert "consolidation_present" in cxr_gt
            assert "cxr_category" in cxr_gt

    def test_no_duplicate_ids(self):
        ids = [c["case_id"] for c in TRACK1_CASES]
        assert len(ids) == len(set(ids))


class TestTrack1Categories:
    """Verify all 5 categories are covered."""

    def _categories(self) -> set:
        return {c["ground_truth"]["cxr_ground_truth"]["cxr_category"] for c in TRACK1_CASES}

    def test_clear_pneumonia_present(self):
        assert "clear_pneumonia" in self._categories()

    def test_bilateral_pneumonia_present(self):
        assert "bilateral_pneumonia" in self._categories()

    def test_subtle_pneumonia_present(self):
        assert "subtle_pneumonia" in self._categories()

    def test_normal_present(self):
        assert "normal" in self._categories()

    def test_abnormal_non_pneumonia_present(self):
        assert "abnormal_non_pneumonia" in self._categories()

    def test_clear_pneumonia_count(self):
        count = sum(1 for c in TRACK1_CASES
                    if c["ground_truth"]["cxr_ground_truth"]["cxr_category"] == "clear_pneumonia")
        assert count == 3

    def test_normal_cxr_count(self):
        count = sum(1 for c in TRACK1_CASES
                    if c["ground_truth"]["cxr_ground_truth"]["cxr_category"] == "normal")
        assert count == 3


class TestTrack1ContradictionCoverage:
    """Verify CR-1 through CR-6 are covered across Track 1 cases."""

    def _all_contradictions(self) -> set:
        result = set()
        for case in TRACK1_CASES:
            for cr in case["ground_truth"]["contradictions"]:
                result.add(cr)
        return result

    def test_cr1_covered(self):
        assert "CR-1" in self._all_contradictions()

    def test_cr2_covered(self):
        assert "CR-2" in self._all_contradictions()

    def test_cr5_covered(self):
        assert "CR-5" in self._all_contradictions()

    def test_cr6_covered(self):
        assert "CR-6" in self._all_contradictions()


class TestTrack1BoundingBoxes:
    """Verify bounding box ground truth structure."""

    _POSITIVE_IDS = {"T1-CLEAR-01", "T1-CLEAR-02", "T1-CLEAR-03",
                     "T1-BILATERAL-01", "T1-BILATERAL-02",
                     "T1-SUBTLE-01", "T1-SUBTLE-02"}
    _NEGATIVE_IDS = {"T1-NORMAL-01", "T1-NORMAL-02", "T1-NORMAL-03",
                     "T1-EFFUSION-01", "T1-EFFUSION-02"}

    def test_positive_cases_have_bboxes(self):
        for case in TRACK1_CASES:
            if case["case_id"] in self._POSITIVE_IDS:
                bboxes = case["ground_truth"]["cxr_ground_truth"]["bboxes_normalized"]
                assert len(bboxes) > 0, f"{case['case_id']} should have bboxes"

    def test_negative_cases_have_empty_bboxes(self):
        for case in TRACK1_CASES:
            if case["case_id"] in self._NEGATIVE_IDS:
                bboxes = case["ground_truth"]["cxr_ground_truth"]["bboxes_normalized"]
                assert bboxes == [], f"{case['case_id']} should have empty bboxes"

    def test_bbox_format_valid(self):
        for case in TRACK1_CASES:
            bboxes = case["ground_truth"]["cxr_ground_truth"]["bboxes_normalized"]
            for bbox in bboxes:
                assert len(bbox) == 4, f"{case['case_id']} bbox should be [y0,x0,y1,x1]"
                y0, x0, y1, x1 = bbox
                assert 0 <= y0 < y1 <= 1000, f"{case['case_id']} invalid y coords: {bbox}"
                assert 0 <= x0 < x1 <= 1000, f"{case['case_id']} invalid x coords: {bbox}"

    def test_bilateral_cases_have_multiple_bboxes(self):
        for case in TRACK1_CASES:
            if case["case_id"].startswith("T1-BILATERAL"):
                bboxes = case["ground_truth"]["cxr_ground_truth"]["bboxes_normalized"]
                assert len(bboxes) >= 2, f"{case['case_id']} should have >=2 bboxes"

    def test_all_cases_have_rsna_patient_id(self):
        for case in TRACK1_CASES:
            pid = case["ground_truth"]["cxr_ground_truth"].get("rsna_patient_id")
            assert pid, f"{case['case_id']} missing rsna_patient_id"

"""Tests for LangSmith-compatible evaluator wrappers."""

from benchmark_data.evaluation.langsmith_evaluators import (
    eval_curb65,
    eval_antibiotic,
    eval_contradiction_recall,
    eval_contradiction_precision,
    eval_cxr_consolidation,
    eval_cxr_localization,
    eval_safety,
    eval_completeness,
    _compute_iou,
    ALL_EVALUATORS,
)


class TestCURB65Evaluator:
    def test_exact_match(self):
        outputs = {"curb65_score": {"severity_tier": "moderate", "curb65": 2}}
        ref = {"ground_truth": {"curb65": 2, "severity_tier": "moderate"}}
        result = eval_curb65(outputs, ref)
        assert result["key"] == "severity_accuracy"
        assert result["score"] == 1.0

    def test_mismatch(self):
        outputs = {"curb65_score": {"severity_tier": "low", "curb65": 1}}
        ref = {"ground_truth": {"severity_tier": "moderate"}}
        result = eval_curb65(outputs, ref)
        assert result["score"] == 0.0

    def test_missing_output(self):
        result = eval_curb65({}, {"ground_truth": {"severity_tier": "moderate"}})
        assert result["score"] == 0.0

    def test_no_ground_truth(self):
        outputs = {"curb65_score": {"severity_tier": "low", "curb65": 1}}
        result = eval_curb65(outputs, {"ground_truth": {}})
        assert result["score"] is None


class TestAntibioticEvaluator:
    def test_contains_match(self):
        outputs = {"antibiotic_recommendation": {"first_line": "Amoxicillin 500mg TDS PO"}}
        ref = {"ground_truth": {"antibiotic": "amoxicillin"}}
        result = eval_antibiotic(outputs, ref)
        assert result["key"] == "antibiotic_concordance"
        assert result["score"] == 1.0

    def test_wrong_drug(self):
        outputs = {"antibiotic_recommendation": {"first_line": "Doxycycline 200mg OD"}}
        ref = {"ground_truth": {"antibiotic": "amoxicillin"}}
        result = eval_antibiotic(outputs, ref)
        assert result["score"] == 0.0

    def test_none_expected(self):
        """When ground truth antibiotic is None, skip evaluation."""
        outputs = {"antibiotic_recommendation": {"first_line": "Anything"}}
        ref = {"ground_truth": {"antibiotic": None}}
        result = eval_antibiotic(outputs, ref)
        assert result["score"] is None

    def test_missing_recommendation(self):
        ref = {"ground_truth": {"antibiotic": "amoxicillin"}}
        result = eval_antibiotic({}, ref)
        assert result["score"] == 0.0


class TestContradictionRecall:
    def test_all_found(self):
        outputs = {"contradictions_detected": [
            {"rule_id": "CR-1", "pattern": "x", "confidence": "high"},
            {"rule_id": "CR-4", "pattern": "y", "confidence": "moderate"},
        ]}
        ref = {"ground_truth": {"contradictions": ["CR-1", "CR-4"]}}
        result = eval_contradiction_recall(outputs, ref)
        assert result["key"] == "contradiction_recall"
        assert result["score"] == 1.0

    def test_partial(self):
        outputs = {"contradictions_detected": [
            {"rule_id": "CR-1", "pattern": "x", "confidence": "high"},
        ]}
        ref = {"ground_truth": {"contradictions": ["CR-1", "CR-4"]}}
        result = eval_contradiction_recall(outputs, ref)
        assert result["score"] == 0.5

    def test_none_expected(self):
        outputs = {"contradictions_detected": []}
        ref = {"ground_truth": {"contradictions": []}}
        result = eval_contradiction_recall(outputs, ref)
        assert result["score"] == 1.0

    def test_missing_detections_key(self):
        result = eval_contradiction_recall({}, {"ground_truth": {"contradictions": ["CR-1"]}})
        assert result["score"] == 0.0


class TestContradictionPrecision:
    def test_no_false_positives(self):
        outputs = {"contradictions_detected": [
            {"rule_id": "CR-1", "pattern": "x", "confidence": "high"},
        ]}
        ref = {"ground_truth": {"contradictions": ["CR-1"]}}
        result = eval_contradiction_precision(outputs, ref)
        assert result["key"] == "contradiction_precision"
        assert result["score"] == 1.0

    def test_false_positive(self):
        outputs = {"contradictions_detected": [
            {"rule_id": "CR-1", "pattern": "x", "confidence": "high"},
            {"rule_id": "CR-5", "pattern": "y", "confidence": "moderate"},
        ]}
        ref = {"ground_truth": {"contradictions": ["CR-1"]}}
        result = eval_contradiction_precision(outputs, ref)
        assert result["score"] == 0.5

    def test_no_detections(self):
        outputs = {"contradictions_detected": []}
        ref = {"ground_truth": {"contradictions": ["CR-1"]}}
        result = eval_contradiction_precision(outputs, ref)
        assert result["score"] == 1.0  # Vacuously no false positives


class TestCXRConsolidation:
    def test_correct(self):
        outputs = {"cxr_analysis": {"consolidation": {"present": True, "confidence": "high"}}}
        ref = {"ground_truth": {"cxr_ground_truth": {"consolidation_present": True}}}
        result = eval_cxr_consolidation(outputs, ref)
        assert result["key"] == "cxr_consolidation"
        assert result["score"] == 1.0

    def test_incorrect(self):
        outputs = {"cxr_analysis": {"consolidation": {"present": False, "confidence": "high"}}}
        ref = {"ground_truth": {"cxr_ground_truth": {"consolidation_present": True}}}
        result = eval_cxr_consolidation(outputs, ref)
        assert result["score"] == 0.0

    def test_no_ground_truth(self):
        outputs = {"cxr_analysis": {"consolidation": {"present": True}}}
        ref = {"ground_truth": {}}
        result = eval_cxr_consolidation(outputs, ref)
        assert result["score"] is None


class TestSafety:
    def test_default_pass(self):
        result = eval_safety({}, {"ground_truth": {}})
        assert result["key"] == "safety_score"
        assert result["score"] == 1.0


class TestCompleteness:
    def test_all_sections(self):
        outputs = {
            "errors": [],
            "structured_output": {
                "1_patient": {}, "2_severity": {}, "3_cxr": {}, "4_key_bloods": {},
                "5_contradiction_alert": {}, "6_treatment_pathway": {},
                "7_data_gaps": {}, "8_monitoring": {},
            },
        }
        result = eval_completeness(outputs, {"ground_truth": {}})
        assert result["key"] == "completeness"
        assert result["score"] == 1.0

    def test_errors_force_zero(self):
        outputs = {
            "errors": ["fail"],
            "structured_output": {
                "1_patient": {}, "2_severity": {}, "3_cxr": {}, "4_key_bloods": {},
                "5_contradiction_alert": {}, "6_treatment_pathway": {},
                "7_data_gaps": {}, "8_monitoring": {},
            },
        }
        result = eval_completeness(outputs, {"ground_truth": {}})
        assert result["score"] == 0.0

    def test_missing_sections(self):
        outputs = {
            "errors": [],
            "structured_output": {"1_patient": {}, "2_severity": {}},
        }
        result = eval_completeness(outputs, {"ground_truth": {}})
        assert result["score"] == 2.0 / 8.0

    def test_empty_output(self):
        result = eval_completeness({}, {"ground_truth": {}})
        assert result["score"] == 0.0

    def test_nested_sections_format(self):
        """Real pipeline nests sections under structured_output.sections."""
        outputs = {
            "errors": [],
            "structured_output": {
                "provenance": {},
                "sections": {
                    "1_patient": {}, "2_severity": {}, "3_cxr": {},
                    "4_key_bloods": {}, "5_contradiction_alert": {},
                    "6_treatment_pathway": {}, "7_data_gaps": {}, "8_monitoring": {},
                },
            },
        }
        result = eval_completeness(outputs, {"ground_truth": {}})
        assert result["score"] == 1.0


class TestComputeIoU:
    def test_perfect_overlap(self):
        box = [100, 200, 300, 400]
        assert _compute_iou(box, box) == 1.0

    def test_no_overlap(self):
        box_a = [0, 0, 100, 100]
        box_b = [200, 200, 300, 300]
        assert _compute_iou(box_a, box_b) == 0.0

    def test_empty_box(self):
        assert _compute_iou([], [100, 200, 300, 400]) == 0.0
        assert _compute_iou(None, [100, 200, 300, 400]) == 0.0

    def test_partial_overlap(self):
        box_a = [0, 0, 200, 200]
        box_b = [100, 100, 300, 300]
        # Intersection: [100,100,200,200] = 100*100 = 10000
        # Area A: 200*200 = 40000, Area B: 200*200 = 40000
        # Union: 40000 + 40000 - 10000 = 70000
        iou = _compute_iou(box_a, box_b)
        assert abs(iou - 10000 / 70000) < 1e-6


class TestCXRLocalization:
    def test_perfect_iou(self):
        box = [185, 221, 871, 736]
        outputs = {"cxr_analysis": {"consolidation": {"bounding_box": box}}}
        ref = {"ground_truth": {"cxr_ground_truth": {"bboxes_normalized": [box]}}}
        result = eval_cxr_localization(outputs, ref)
        assert result["key"] == "cxr_localization"
        assert result["score"] == 1.0

    def test_no_overlap(self):
        outputs = {"cxr_analysis": {"consolidation": {"bounding_box": [0, 0, 10, 10]}}}
        ref = {"ground_truth": {"cxr_ground_truth": {"bboxes_normalized": [[500, 500, 600, 600]]}}}
        result = eval_cxr_localization(outputs, ref)
        assert result["score"] == 0.0

    def test_partial_overlap(self):
        outputs = {"cxr_analysis": {"consolidation": {"bounding_box": [0, 0, 200, 200]}}}
        ref = {"ground_truth": {"cxr_ground_truth": {"bboxes_normalized": [[100, 100, 300, 300]]}}}
        result = eval_cxr_localization(outputs, ref)
        expected_iou = 10000 / 70000
        assert abs(result["score"] - expected_iou) < 1e-6

    def test_multi_gt_best_match(self):
        box = [100, 100, 200, 200]
        outputs = {"cxr_analysis": {"consolidation": {"bounding_box": box}}}
        ref = {"ground_truth": {"cxr_ground_truth": {"bboxes_normalized": [
            [500, 500, 600, 600],  # no overlap
            box,                    # perfect match
        ]}}}
        result = eval_cxr_localization(outputs, ref)
        assert result["score"] == 1.0

    def test_no_gt_bboxes_returns_none(self):
        outputs = {"cxr_analysis": {"consolidation": {"bounding_box": [0, 0, 100, 100]}}}
        ref = {"ground_truth": {"cxr_ground_truth": {"bboxes_normalized": []}}}
        result = eval_cxr_localization(outputs, ref)
        assert result["score"] is None

    def test_no_cxr_ground_truth_returns_none(self):
        outputs = {"cxr_analysis": {"consolidation": {"bounding_box": [0, 0, 100, 100]}}}
        ref = {"ground_truth": {}}
        result = eval_cxr_localization(outputs, ref)
        assert result["score"] is None

    def test_no_predicted_bbox_returns_zero(self):
        outputs = {"cxr_analysis": {"consolidation": {}}}
        ref = {"ground_truth": {"cxr_ground_truth": {"bboxes_normalized": [[100, 100, 200, 200]]}}}
        result = eval_cxr_localization(outputs, ref)
        assert result["score"] == 0.0


class TestAllEvaluatorsList:
    def test_has_all_eight(self):
        assert len(ALL_EVALUATORS) == 8

    def test_all_callable(self):
        for evaluator in ALL_EVALUATORS:
            assert callable(evaluator)

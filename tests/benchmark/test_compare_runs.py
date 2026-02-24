"""Tests for benchmark regression detection."""

from benchmark_data.evaluation.compare_runs import check_regression, THRESHOLDS


class TestRegressionDetection:
    def test_no_regression(self):
        current = {"severity_accuracy": 1.0, "safety_score": 1.0}
        baseline = {"severity_accuracy": 1.0, "safety_score": 1.0}
        assert check_regression(current, baseline) == []

    def test_detects_safety_regression(self):
        current = {"safety_score": 0.9}
        baseline = {"safety_score": 1.0}
        regressions = check_regression(current, baseline)
        assert len(regressions) == 1
        assert regressions[0]["metric"] == "safety_score"
        assert regressions[0]["degradation"] == 0.1

    def test_within_tolerance(self):
        """cxr_consolidation has 5% tolerance, 4% drop is OK."""
        current = {"cxr_consolidation": 0.86}
        baseline = {"cxr_consolidation": 0.90}
        assert check_regression(current, baseline) == []

    def test_beyond_tolerance(self):
        """cxr_consolidation has 5% tolerance, 10% drop triggers regression."""
        current = {"cxr_consolidation": 0.80}
        baseline = {"cxr_consolidation": 0.90}
        regressions = check_regression(current, baseline)
        assert len(regressions) == 1
        assert regressions[0]["metric"] == "cxr_consolidation"

    def test_skips_none_values(self):
        current = {"cxr_consolidation": None}
        baseline = {"cxr_consolidation": 0.90}
        assert check_regression(current, baseline) == []

    def test_skips_none_baseline(self):
        current = {"cxr_consolidation": 0.80}
        baseline = {"cxr_consolidation": None}
        assert check_regression(current, baseline) == []

    def test_missing_baseline_metric(self):
        current = {"severity_accuracy": 0.9}
        baseline = {}
        assert check_regression(current, baseline) == []

    def test_multiple_regressions(self):
        current = {"severity_accuracy": 0.8, "safety_score": 0.9, "completeness": 0.7}
        baseline = {"severity_accuracy": 1.0, "safety_score": 1.0, "completeness": 1.0}
        regressions = check_regression(current, baseline)
        assert len(regressions) == 3
        metrics = {r["metric"] for r in regressions}
        assert metrics == {"severity_accuracy", "safety_score", "completeness"}

    def test_improvement_not_flagged(self):
        current = {"severity_accuracy": 1.0}
        baseline = {"severity_accuracy": 0.8}
        assert check_regression(current, baseline) == []

    def test_contradiction_precision_within_tolerance(self):
        """contradiction_precision has 5% tolerance."""
        current = {"contradiction_precision": 0.96}
        baseline = {"contradiction_precision": 1.0}
        assert check_regression(current, baseline) == []

    def test_contradiction_precision_beyond_tolerance(self):
        current = {"contradiction_precision": 0.90}
        baseline = {"contradiction_precision": 1.0}
        regressions = check_regression(current, baseline)
        assert len(regressions) == 1

    def test_zero_tolerance_metrics(self):
        """Deterministic metrics have zero tolerance."""
        for metric in ["severity_accuracy", "antibiotic_concordance",
                       "contradiction_recall", "safety_score", "completeness"]:
            assert THRESHOLDS[metric] == 0.0, f"{metric} should have zero tolerance"

    def test_degradation_rounding(self):
        current = {"severity_accuracy": 0.333}
        baseline = {"severity_accuracy": 0.667}
        regressions = check_regression(current, baseline)
        assert len(regressions) == 1
        assert regressions[0]["degradation"] == 0.334

    def test_cxr_localization_threshold(self):
        assert THRESHOLDS["cxr_localization"] == 0.10

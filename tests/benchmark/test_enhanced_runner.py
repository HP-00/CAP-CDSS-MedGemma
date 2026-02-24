"""Tests for the enhanced benchmark runner with quick/full modes."""

import json
import os
from unittest.mock import patch, MagicMock

import pytest

from benchmark_data.evaluation.run_benchmark import (
    run_single_case,
    run_evaluators,
    aggregate_evaluator_scores,
    get_builtin_cases,
    save_run,
)


# --- Minimal mock pipeline output that satisfies evaluators ---
MOCK_PIPELINE_OUTPUT = {
    "current_step": "Output assembled",
    "curb65_score": {"curb65": 2, "severity_tier": "moderate",
                     "c": 0, "u": 1, "r": 0, "b": 0, "age_65": 1,
                     "crb65": 1, "missing_variables": []},
    "antibiotic_recommendation": {
        "severity_tier": "moderate",
        "first_line": "Amoxicillin 500mg TDS PO",
        "dose_route": "500mg TDS PO",
    },
    "contradictions_detected": [],
    "cxr_analysis": {},
    "errors": [],
    "structured_output": {
        "provenance": {},
        "sections": {
            "1_patient": {}, "2_severity": {}, "3_cxr": {}, "4_key_bloods": {},
            "5_contradiction_alert": {}, "6_treatment_pathway": {},
            "7_data_gaps": {}, "8_monitoring": {},
        },
    },
    "monitoring_plan": {},
    "tool_results": [],
}


class TestRunSingleCase:
    def test_returns_result_with_timing(self):
        mock_graph = MagicMock()
        mock_graph.invoke.return_value = MOCK_PIPELINE_OUTPUT
        case = {"case_id": "test-001", "patient_id": "P001"}

        result = run_single_case(case, mock_graph)

        assert "elapsed_seconds" in result
        assert result["elapsed_seconds"] >= 0
        assert result["case_id"] == "test-001"
        assert "pipeline_output" in result

    def test_captures_errors(self):
        mock_graph = MagicMock()
        mock_graph.invoke.side_effect = RuntimeError("GPU exploded")
        case = {"case_id": "test-err", "patient_id": "P002"}

        result = run_single_case(case, mock_graph)

        assert result["error"] is not None
        assert "GPU exploded" in result["error"]


class TestRunEvaluators:
    def test_returns_scores_dict(self):
        ground_truth = {"curb65": 2, "severity_tier": "moderate",
                        "contradictions": [], "antibiotic": "amoxicillin"}
        scores = run_evaluators(MOCK_PIPELINE_OUTPUT, ground_truth)

        assert "severity_accuracy" in scores
        assert scores["severity_accuracy"] == 1.0
        assert "antibiotic_concordance" in scores
        assert scores["antibiotic_concordance"] == 1.0

    def test_skips_none_scores(self):
        ground_truth = {}  # No ground truth → evaluators return None
        scores = run_evaluators(MOCK_PIPELINE_OUTPUT, ground_truth)
        # None scores should be excluded
        for v in scores.values():
            assert v is not None


class TestAggregateScores:
    def test_computes_mean(self):
        scores = [
            {"severity_accuracy": 1.0, "completeness": 0.8},
            {"severity_accuracy": 0.0, "completeness": 1.0},
        ]
        agg = aggregate_evaluator_scores(scores)
        assert agg["severity_accuracy"]["mean"] == 0.5
        assert agg["completeness"]["mean"] == 0.9

    def test_computes_min_max(self):
        scores = [
            {"severity_accuracy": 0.2},
            {"severity_accuracy": 0.8},
            {"severity_accuracy": 0.5},
        ]
        agg = aggregate_evaluator_scores(scores)
        assert agg["severity_accuracy"]["min"] == 0.2
        assert agg["severity_accuracy"]["max"] == 0.8

    def test_empty_scores(self):
        assert aggregate_evaluator_scores([]) == {}

    def test_mixed_metrics(self):
        """Different cases may have different metrics (some skipped)."""
        scores = [
            {"severity_accuracy": 1.0, "cxr_consolidation": 0.5},
            {"severity_accuracy": 0.0},  # No CXR metric
        ]
        agg = aggregate_evaluator_scores(scores)
        assert agg["severity_accuracy"]["mean"] == 0.5
        assert agg["cxr_consolidation"]["mean"] == 0.5  # Only 1 data point


class TestGetBuiltinCases:
    def test_returns_non_empty(self):
        cases = get_builtin_cases()
        assert len(cases) > 0

    def test_cases_have_required_keys(self):
        cases = get_builtin_cases()
        for case in cases:
            assert "case_id" in case
            assert "ground_truth" in case


class TestSaveRun:
    def test_saves_json(self, tmp_path):
        results = [{"case_id": "test-001", "elapsed_seconds": 1.0}]
        metrics = {"severity_accuracy": {"mean": 1.0, "min": 1.0, "max": 1.0}}
        output_dir = str(tmp_path / "results")

        save_run(results, metrics, output_dir)

        metrics_path = os.path.join(output_dir, "metrics.json")
        assert os.path.exists(metrics_path)
        with open(metrics_path) as f:
            data = json.load(f)
        assert "metrics" in data
        assert "results" in data

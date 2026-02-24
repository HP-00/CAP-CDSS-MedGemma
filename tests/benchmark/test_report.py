"""Tests for plotly report generator."""

import os

from benchmark_data.evaluation.generate_report import (
    build_severity_confusion_matrix,
    build_safety_scorecard,
    build_radar_plot,
    build_contradiction_chart,
    build_latency_breakdown,
    build_iteration_chart,
    generate_html_report,
)


class TestChartBuilders:
    def test_confusion_matrix_returns_figure(self):
        data = [
            {"predicted": "moderate", "actual": "moderate"},
            {"predicted": "low", "actual": "moderate"},
            {"predicted": "high", "actual": "high"},
        ]
        fig = build_severity_confusion_matrix(data)
        assert fig is not None
        assert hasattr(fig, "to_html")

    def test_confusion_matrix_empty_data(self):
        fig = build_severity_confusion_matrix([])
        assert fig is not None

    def test_safety_scorecard_returns_figure(self):
        data = {"CR-1": 1.0, "CR-4": 0.8, "CR-10": 1.0}
        fig = build_safety_scorecard(data)
        assert fig is not None
        assert hasattr(fig, "to_html")

    def test_radar_plot_returns_figure(self):
        data = {
            "Extraction": 0.85,
            "Guideline Adherence": 1.0,
            "Safety": 1.0,
            "Calibration": 0.7,
            "Completeness": 0.95,
        }
        fig = build_radar_plot(data)
        assert fig is not None
        assert hasattr(fig, "to_html")

    def test_contradiction_chart_returns_figure(self):
        data = {
            "CR-1": {"recall": 1.0, "precision": 0.8},
            "CR-4": {"recall": 1.0, "precision": 1.0},
        }
        fig = build_contradiction_chart(data)
        assert fig is not None
        assert hasattr(fig, "to_html")

    def test_latency_breakdown_returns_figure(self):
        data = {
            "load_case": 0.01,
            "parallel_extraction": 45.0,
            "severity_scoring": 0.02,
            "output_assembly": 12.0,
        }
        fig = build_latency_breakdown(data)
        assert fig is not None
        assert hasattr(fig, "to_html")

    def test_iteration_chart_returns_figure(self):
        runs = [
            {"run_id": "run-1", "severity_accuracy": 0.8, "completeness": 0.9},
            {"run_id": "run-2", "severity_accuracy": 0.9, "completeness": 0.95},
        ]
        fig = build_iteration_chart(runs)
        assert fig is not None
        assert hasattr(fig, "to_html")

    def test_iteration_chart_empty(self):
        fig = build_iteration_chart([])
        assert fig is not None


class TestHTMLReport:
    def test_generates_file(self, tmp_path):
        metrics = {
            "severity_accuracy": {"mean": 1.0, "min": 1.0, "max": 1.0},
            "completeness": {"mean": 0.9, "min": 0.75, "max": 1.0},
        }
        chart_data = {
            "severity_predictions": [
                {"predicted": "moderate", "actual": "moderate"},
            ],
            "safety_scores": {"CR-1": 1.0},
            "capability_axes": {"Extraction": 0.85, "Safety": 1.0},
            "contradiction_detail": {"CR-1": {"recall": 1.0, "precision": 1.0}},
            "latency": {"load_case": 0.01},
        }
        path = str(tmp_path / "report.html")
        result = generate_html_report(metrics, chart_data, path)
        assert os.path.exists(result)
        content = open(result).read()
        assert "plotly" in content.lower()
        assert "CAP CDSS" in content

    def test_generates_with_minimal_data(self, tmp_path):
        path = str(tmp_path / "report.html")
        result = generate_html_report({}, {}, path)
        assert os.path.exists(result)

    def test_creates_parent_dirs(self, tmp_path):
        path = str(tmp_path / "subdir" / "report.html")
        result = generate_html_report({}, {}, path)
        assert os.path.exists(result)

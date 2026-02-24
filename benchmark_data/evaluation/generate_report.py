"""Plotly-based benchmark report generator for CAP CDSS evaluation.

Produces a self-contained HTML report with 7 chart types:
1. Severity confusion matrix (3x3 heatmap)
2. Safety scorecard (table with color coding)
3. Radar/spider plot (5 capability axes)
4. Contradiction recall/precision (grouped bar)
5. CXR ROC (scatter, if data available)
6. Latency breakdown (horizontal bar)
7. Iteration chart (metrics over time)
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import plotly.graph_objects as go

SEVERITY_TIERS = ["low", "moderate", "high"]


def build_severity_confusion_matrix(data: list[dict]) -> go.Figure:
    """Build a 3x3 confusion matrix heatmap for severity tier predictions.

    Args:
        data: List of {"predicted": str, "actual": str} dicts.
    """
    matrix = [[0] * 3 for _ in range(3)]
    tier_idx = {t: i for i, t in enumerate(SEVERITY_TIERS)}
    for item in data:
        pred = tier_idx.get(item.get("predicted", ""), -1)
        actual = tier_idx.get(item.get("actual", ""), -1)
        if pred >= 0 and actual >= 0:
            matrix[actual][pred] += 1

    fig = go.Figure(data=go.Heatmap(
        z=matrix,
        x=SEVERITY_TIERS,
        y=SEVERITY_TIERS,
        text=matrix,
        texttemplate="%{text}",
        colorscale="Blues",
        showscale=False,
    ))
    fig.update_layout(
        title="Severity Tier Confusion Matrix",
        xaxis_title="Predicted",
        yaxis_title="Actual",
        width=450, height=400,
    )
    return fig


def build_safety_scorecard(data: dict[str, float]) -> go.Figure:
    """Build a color-coded safety scorecard table.

    Args:
        data: {"CR-1": 1.0, "CR-4": 0.8, ...} rule-level scores.
    """
    rules = sorted(data.keys())
    scores = [data[r] for r in rules]
    colors = ["#4CAF50" if s >= 1.0 else "#FF9800" if s >= 0.8 else "#F44336" for s in scores]

    fig = go.Figure(data=[go.Table(
        header=dict(values=["Rule", "Score", "Status"],
                    fill_color="#1a1a2e", font=dict(color="white")),
        cells=dict(
            values=[rules, [f"{s:.0%}" for s in scores],
                    ["PASS" if s >= 1.0 else "WARN" if s >= 0.8 else "FAIL" for s in scores]],
            fill_color=[["white"] * len(rules), ["white"] * len(rules), colors],
        ),
    )])
    fig.update_layout(title="Safety Rule Scorecard", width=500, height=max(200, 50 * len(rules)))
    return fig


def build_radar_plot(data: dict[str, float]) -> go.Figure:
    """Build a spider/radar chart for capability axes.

    Args:
        data: {"Extraction": 0.85, "Safety": 1.0, ...} axis scores.
    """
    categories = list(data.keys())
    values = list(data.values())
    # Close the polygon
    categories_closed = categories + [categories[0]]
    values_closed = values + [values[0]]

    fig = go.Figure(data=go.Scatterpolar(
        r=values_closed,
        theta=categories_closed,
        fill="toself",
        name="Current",
        line_color="#2196F3",
    ))
    fig.update_layout(
        title="Capability Radar",
        polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
        width=500, height=450,
    )
    return fig


def build_contradiction_chart(data: dict[str, dict]) -> go.Figure:
    """Build grouped bar chart for per-rule contradiction recall/precision.

    Args:
        data: {"CR-1": {"recall": 1.0, "precision": 0.8}, ...}
    """
    rules = sorted(data.keys())
    recalls = [data[r].get("recall", 0) for r in rules]
    precisions = [data[r].get("precision", 0) for r in rules]

    fig = go.Figure(data=[
        go.Bar(name="Recall", x=rules, y=recalls, marker_color="#2196F3"),
        go.Bar(name="Precision", x=rules, y=precisions, marker_color="#FF9800"),
    ])
    fig.update_layout(
        title="Contradiction Detection (per rule)",
        barmode="group",
        yaxis=dict(range=[0, 1.05], title="Score"),
        width=600, height=400,
    )
    return fig


def build_cxr_roc(data: list[dict]) -> go.Figure | None:
    """Build scatter plot for CXR detection ROC (if data available).

    Args:
        data: List of {"fpr": float, "tpr": float} points.
    """
    if not data:
        return None
    fprs = [d["fpr"] for d in data]
    tprs = [d["tpr"] for d in data]

    fig = go.Figure(data=[
        go.Scatter(x=fprs, y=tprs, mode="lines+markers", name="CXR ROC"),
        go.Scatter(x=[0, 1], y=[0, 1], mode="lines", name="Random",
                   line=dict(dash="dash", color="gray")),
    ])
    fig.update_layout(
        title="CXR Consolidation Detection ROC",
        xaxis_title="False Positive Rate",
        yaxis_title="True Positive Rate",
        width=500, height=450,
    )
    return fig


def build_latency_breakdown(data: dict[str, float]) -> go.Figure:
    """Build horizontal bar chart for per-node latency.

    Args:
        data: {"load_case": 0.01, "parallel_extraction": 45.0, ...} seconds.
    """
    nodes = list(data.keys())
    times = list(data.values())

    fig = go.Figure(data=go.Bar(
        x=times, y=nodes, orientation="h",
        marker_color="#2196F3",
        text=[f"{t:.2f}s" for t in times],
        textposition="auto",
    ))
    fig.update_layout(
        title="Pipeline Latency Breakdown",
        xaxis_title="Time (seconds)",
        width=600, height=max(250, 40 * len(nodes)),
    )
    return fig


def build_iteration_chart(runs: list[dict]) -> go.Figure:
    """Build multi-series line chart for metrics across benchmark runs.

    Args:
        runs: [{"run_id": "run-1", "severity_accuracy": 0.8, ...}, ...]
    """
    fig = go.Figure()
    if not runs:
        fig.update_layout(title="Metrics Over Iterations (no data)")
        return fig

    run_ids = [r.get("run_id", f"run-{i}") for i, r in enumerate(runs)]
    # Collect all metric keys (excluding run_id)
    metric_keys = sorted({k for r in runs for k in r if k != "run_id"})
    for metric in metric_keys:
        values = [r.get(metric) for r in runs]
        fig.add_trace(go.Scatter(x=run_ids, y=values, mode="lines+markers", name=metric))

    fig.update_layout(
        title="Metrics Over Iterations",
        xaxis_title="Run",
        yaxis_title="Score",
        yaxis=dict(range=[0, 1.05]),
        width=700, height=400,
    )
    return fig


def generate_html_report(
    metrics: dict,
    chart_data: dict,
    output_path: str,
) -> str:
    """Generate a self-contained HTML report with all charts.

    Args:
        metrics: Aggregated metrics {"severity_accuracy": {"mean": ..., "min": ..., "max": ...}}.
        chart_data: Data for individual charts (severity_predictions, safety_scores, etc.).
        output_path: Path to write the HTML file.

    Returns:
        The output path.
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    charts_html = []

    # Metrics summary table
    if metrics:
        rows = ""
        for name, vals in sorted(metrics.items()):
            mean = vals.get("mean", 0)
            mn = vals.get("min", 0)
            mx = vals.get("max", 0)
            rows += f"<tr><td>{name}</td><td>{mean:.2%}</td><td>{mn:.2%}</td><td>{mx:.2%}</td></tr>"
        charts_html.append(f"""
        <h2>Aggregate Metrics</h2>
        <table class="metrics-table">
            <tr><th>Metric</th><th>Mean</th><th>Min</th><th>Max</th></tr>
            {rows}
        </table>
        """)

    # Build charts from chart_data
    chart_builders = [
        ("severity_predictions", lambda d: build_severity_confusion_matrix(d)),
        ("safety_scores", lambda d: build_safety_scorecard(d)),
        ("capability_axes", lambda d: build_radar_plot(d)),
        ("contradiction_detail", lambda d: build_contradiction_chart(d)),
        ("cxr_roc", lambda d: build_cxr_roc(d)),
        ("latency", lambda d: build_latency_breakdown(d)),
        ("iteration_history", lambda d: build_iteration_chart(d)),
    ]

    for key, builder in chart_builders:
        data = chart_data.get(key)
        if data:
            fig = builder(data)
            if fig is not None:
                charts_html.append(fig.to_html(full_html=False, include_plotlyjs=False))

    # Assemble HTML
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>CAP CDSS Benchmark Report</title>
    <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
               max-width: 1200px; margin: 0 auto; padding: 20px;
               background: #f5f5f5; color: #333; }}
        h1 {{ color: #1a1a2e; border-bottom: 2px solid #2196F3; padding-bottom: 10px; }}
        h2 {{ color: #1a1a2e; margin-top: 30px; }}
        .metrics-table {{ border-collapse: collapse; width: 100%; margin: 10px 0; }}
        .metrics-table th, .metrics-table td {{
            border: 1px solid #ddd; padding: 8px; text-align: left; }}
        .metrics-table th {{ background: #1a1a2e; color: white; }}
        .metrics-table tr:nth-child(even) {{ background: #f9f9f9; }}
        .chart-container {{ background: white; border-radius: 8px;
                          padding: 15px; margin: 15px 0;
                          box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .footer {{ text-align: center; color: #999; margin-top: 40px;
                  font-size: 0.9em; }}
    </style>
</head>
<body>
    <h1>CAP CDSS Benchmark Report</h1>
    {"".join(f'<div class="chart-container">{c}</div>' for c in charts_html)}
    <div class="footer">
        <p>Generated by CAP CDSS Benchmark Suite</p>
        <p>Metrics JSON: {json.dumps(metrics, indent=2) if metrics else "N/A"}</p>
    </div>
</body>
</html>"""

    with open(output_path, "w") as f:
        f.write(html)

    return output_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate benchmark HTML report")
    parser.add_argument("--input", required=True, help="Path to metrics JSON")
    parser.add_argument("--output", default="benchmark_data/results/report.html",
                        help="Output HTML path")
    args = parser.parse_args()

    with open(args.input) as f:
        data = json.load(f)
    metrics = data.get("metrics", data)
    chart_data = data.get("chart_data", {})
    result = generate_html_report(metrics, chart_data, args.output)
    print(f"Report generated: {result}")

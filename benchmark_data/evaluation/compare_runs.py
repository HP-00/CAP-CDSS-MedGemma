"""Compare benchmark runs and detect metric regressions.

Each metric has a tolerance threshold. Deterministic metrics (severity,
antibiotics, safety) have zero tolerance. Stochastic metrics (CXR, precision)
allow small variance.
"""

from __future__ import annotations

import json
import sys

THRESHOLDS: dict[str, float] = {
    "severity_accuracy": 0.0,       # Zero tolerance (deterministic)
    "antibiotic_concordance": 0.0,  # Zero tolerance (deterministic)
    "contradiction_recall": 0.0,    # Zero tolerance (safety)
    "safety_score": 0.0,            # Zero tolerance (safety)
    "completeness": 0.0,            # Zero tolerance
    "contradiction_precision": 0.05, # 5% tolerance (some FPs acceptable)
    "cxr_consolidation": 0.05,      # 5% tolerance (stochastic)
    "cxr_localization": 0.10,       # 10% tolerance (IoU sensitive to spatial jitter)
}


def check_regression(current: dict, baseline: dict) -> list[dict]:
    """Compare current metrics against baseline, returning regressions.

    A regression is detected when current < baseline - threshold.
    None values in either current or baseline are skipped.

    Returns:
        List of {"metric", "baseline", "current", "degradation"} dicts.
    """
    regressions = []
    for metric, current_val in current.items():
        if current_val is None:
            continue
        baseline_val = baseline.get(metric)
        if baseline_val is None:
            continue
        threshold = THRESHOLDS.get(metric, 0.0)
        if current_val < baseline_val - threshold:
            regressions.append({
                "metric": metric,
                "baseline": baseline_val,
                "current": current_val,
                "degradation": round(baseline_val - current_val, 4),
            })
    return regressions


def main():
    """CLI: compare two benchmark result JSON files."""
    import argparse

    parser = argparse.ArgumentParser(description="Detect benchmark regressions")
    parser.add_argument("--current", required=True, help="Path to current metrics JSON")
    parser.add_argument("--baseline", required=True, help="Path to baseline metrics JSON")
    args = parser.parse_args()

    with open(args.current) as f:
        current_data = json.load(f)
    with open(args.baseline) as f:
        baseline_data = json.load(f)

    # Support both flat {"metric": value} and nested {"metrics": {"metric": {"mean": value}}}
    current = _flatten_metrics(current_data)
    baseline = _flatten_metrics(baseline_data)

    regressions = check_regression(current, baseline)

    if not regressions:
        print("No regressions detected.")
        sys.exit(0)

    print(f"REGRESSIONS DETECTED ({len(regressions)}):")
    for r in regressions:
        print(f"  {r['metric']}: {r['baseline']:.4f} -> {r['current']:.4f} "
              f"(degradation: {r['degradation']:.4f})")
    sys.exit(1)


def _flatten_metrics(data: dict) -> dict:
    """Flatten nested metrics format to {metric: value}."""
    if "metrics" in data:
        data = data["metrics"]
    result = {}
    for key, val in data.items():
        if isinstance(val, dict) and "mean" in val:
            result[key] = val["mean"]
        elif isinstance(val, (int, float)):
            result[key] = val
        # Skip None or non-numeric
    return result


if __name__ == "__main__":
    main()

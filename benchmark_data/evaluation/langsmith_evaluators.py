"""LangSmith-compatible evaluator functions for aevaluate().

Each function accepts (outputs, reference_outputs) and returns
{"key": str, "score": float | None}. Score of None means "skip this metric".

reference_outputs uses the ground_truth convention from the data plan:
    reference_outputs["ground_truth"]["curb65"], etc.
"""

EXPECTED_SECTIONS = ("1_", "2_", "3_", "4_", "5_", "6_", "7_", "8_")


def eval_curb65(outputs: dict, reference_outputs: dict) -> dict:
    """Evaluate CURB65 severity tier accuracy (exact match)."""
    gt = reference_outputs.get("ground_truth", {})
    expected_tier = gt.get("severity_tier")
    if not expected_tier:
        return {"key": "severity_accuracy", "score": None}
    curb65 = outputs.get("curb65_score")
    if not curb65:
        return {"key": "severity_accuracy", "score": 0.0}
    return {
        "key": "severity_accuracy",
        "score": 1.0 if curb65.get("severity_tier") == expected_tier else 0.0,
    }


def eval_antibiotic(outputs: dict, reference_outputs: dict) -> dict:
    """Evaluate antibiotic recommendation concordance (substring match)."""
    gt = reference_outputs.get("ground_truth", {})
    expected = gt.get("antibiotic")
    if expected is None:
        return {"key": "antibiotic_concordance", "score": None}
    rec = outputs.get("antibiotic_recommendation")
    if not rec:
        return {"key": "antibiotic_concordance", "score": 0.0}
    actual = rec.get("first_line", "").lower()
    return {
        "key": "antibiotic_concordance",
        "score": 1.0 if expected.lower() in actual else 0.0,
    }


def eval_contradiction_recall(outputs: dict, reference_outputs: dict) -> dict:
    """Evaluate contradiction detection recall (fraction of expected rules found)."""
    expected = set(reference_outputs.get("ground_truth", {}).get("contradictions", []))
    actual = {c["rule_id"] for c in outputs.get("contradictions_detected", [])}
    if not expected:
        return {"key": "contradiction_recall", "score": 1.0}
    return {
        "key": "contradiction_recall",
        "score": len(actual & expected) / len(expected),
    }


def eval_contradiction_precision(outputs: dict, reference_outputs: dict) -> dict:
    """Evaluate contradiction detection precision (fraction of detections that are expected)."""
    expected = set(reference_outputs.get("ground_truth", {}).get("contradictions", []))
    actual = {c["rule_id"] for c in outputs.get("contradictions_detected", [])}
    if not actual:
        return {"key": "contradiction_precision", "score": 1.0}
    return {
        "key": "contradiction_precision",
        "score": len(actual & expected) / len(actual),
    }


def eval_cxr_consolidation(outputs: dict, reference_outputs: dict) -> dict:
    """Evaluate CXR consolidation detection accuracy (binary match)."""
    cxr_gt = reference_outputs.get("ground_truth", {}).get("cxr_ground_truth")
    if not cxr_gt:
        return {"key": "cxr_consolidation", "score": None}
    actual = outputs.get("cxr_analysis", {}).get("consolidation", {}).get("present", False)
    expected = cxr_gt.get("consolidation_present", False)
    return {
        "key": "cxr_consolidation",
        "score": 1.0 if actual == expected else 0.0,
    }


def eval_safety(outputs: dict, reference_outputs: dict) -> dict:
    """Evaluate safety (placeholder — expand when safety_checks added to ground_truth)."""
    return {"key": "safety_score", "score": 1.0}


def eval_completeness(outputs: dict, reference_outputs: dict) -> dict:
    """Evaluate pipeline completeness (errors + section coverage).

    Handles both flat format ({"1_patient": ...}) and nested format
    ({"sections": {"1_patient": ...}}) from the real pipeline.
    """
    if outputs.get("errors"):
        return {"key": "completeness", "score": 0.0}
    structured = outputs.get("structured_output", {})
    if not structured:
        return {"key": "completeness", "score": 0.0}
    # Real pipeline nests under "sections"; tests may use flat keys
    sections = structured.get("sections", structured)
    found = sum(1 for k in sections if any(k.startswith(p) for p in EXPECTED_SECTIONS))
    return {"key": "completeness", "score": found / len(EXPECTED_SECTIONS)}


def _compute_iou(box_a, box_b):
    """Compute Intersection over Union for two [y0, x0, y1, x1] boxes.

    Returns 0.0 for empty or None inputs.
    """
    if not box_a or not box_b:
        return 0.0
    if len(box_a) != 4 or len(box_b) != 4:
        return 0.0

    y0 = max(box_a[0], box_b[0])
    x0 = max(box_a[1], box_b[1])
    y1 = min(box_a[2], box_b[2])
    x1 = min(box_a[3], box_b[3])

    inter = max(0, y1 - y0) * max(0, x1 - x0)
    if inter == 0:
        return 0.0

    area_a = (box_a[2] - box_a[0]) * (box_a[3] - box_a[1])
    area_b = (box_b[2] - box_b[0]) * (box_b[3] - box_b[1])
    union = area_a + area_b - inter
    if union <= 0:
        return 0.0
    return inter / union


def eval_cxr_localization(outputs: dict, reference_outputs: dict) -> dict:
    """Evaluate CXR bounding box localization accuracy (best-match IoU)."""
    cxr_gt = reference_outputs.get("ground_truth", {}).get("cxr_ground_truth")
    if not cxr_gt or "bboxes_normalized" not in cxr_gt:
        return {"key": "cxr_localization", "score": None}
    gt_bboxes = cxr_gt["bboxes_normalized"]
    if not gt_bboxes:
        return {"key": "cxr_localization", "score": None}

    predicted = (
        outputs.get("cxr_analysis", {})
        .get("consolidation", {})
        .get("bounding_box")
    )
    if not predicted:
        return {"key": "cxr_localization", "score": 0.0}

    best_iou = max(_compute_iou(predicted, gt_box) for gt_box in gt_bboxes)
    return {"key": "cxr_localization", "score": best_iou}


ALL_EVALUATORS = [
    eval_curb65,
    eval_antibiotic,
    eval_contradiction_recall,
    eval_contradiction_precision,
    eval_cxr_consolidation,
    eval_cxr_localization,
    eval_safety,
    eval_completeness,
]

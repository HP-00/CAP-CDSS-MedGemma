#!/usr/bin/env python3
"""Export synthetic demo cases to JSON files for public distribution.

Converts absolute image paths to relative paths and adds ground_truth metadata.
"""

import json
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root))

from cap_agent.data.demo_cases import (
    get_cxr_clear_case,
    get_cxr_bilateral_case,
    get_cxr_normal_case,
    get_cxr_subtle_case,
    get_cxr_effusion_case,
)


# Ground truth for each case (for benchmark evaluation).
#
# Values derived from deterministic clinical_logic.py functions applied
# to the case data in demo_cases.py:
#
#   CURB65: compute_curb65() — C(AMT<=8) + U(urea>7) + R(RR>=30)
#           + B(SBP<90 OR DBP<=60) + 65(age>=65).
#   Contradictions: detect_contradictions() — 11 rules (CR-1 to CR-11).
#   Antibiotic: select_antibiotic() — severity-stratified, allergy-aware.
#   Discharge: generate_monitoring_plan() — 7 binary checks, <2 not met = OK.
#
GROUND_TRUTH = {
    "cxr_clear": {
        "curb65": 0,
        "severity_tier": "low",
        "contradictions": [],
        "antibiotic": "amoxicillin",
        "discharge_met": True,
        "description": (
            "Low-severity CAP with left basal consolidation and small effusion. "
            "50F, CURB65=0 (all components 0). CXR consolidation present + "
            "crackles + CRP 120 = concordant findings, no contradictions. "
            "Effusion present but consolidation also present so CR-6 does not "
            "fire. Amoxicillin monotherapy. 1 discharge criterion not met "
            "(temp 37.9 > 37.8) but <2 so discharge OK."
        ),
    },
    "cxr_bilateral": {
        "curb65": 2,
        "severity_tier": "moderate",
        "contradictions": [],
        "antibiotic": "amoxicillin",
        "discharge_met": False,
        "description": (
            "Moderate-severity bilateral CAP on background of heart failure. "
            "65M, CURB65=2 (C=1 AMT 8/10, 65=1 age 65; U=0 urea 7.0 not >7). "
            "Bilateral CXR + bilateral exam = concordant, no CR-5. Severity "
            "not low so no CR-4. Amoxicillin+clarithromycin dual therapy. "
            "5 discharge criteria not met (temp, RR, HR, confusion, eating)."
        ),
    },
    "cxr_normal": {
        "curb65": 0,
        "severity_tier": "low",
        "contradictions": [],
        "antibiotic": "amoxicillin",
        "discharge_met": True,
        "description": (
            "Normal CXR with raised inflammatory markers but NO focal clinical "
            "signs. 50F, CURB65=0. CXR normal, crackles=False, bronchial_breathing=False. "
            "CR-1 requires crackles/bronchial_breathing (absent). CR-2 requires "
            "CRP>100 AND clinical features (absent). No contradictions fire. "
            "Amoxicillin monotherapy. All discharge criteria met."
        ),
    },
    "cxr_subtle": {
        "curb65": 0,
        "severity_tier": "low",
        "contradictions": [],
        "antibiotic": "amoxicillin",
        "discharge_met": True,
        "description": (
            "Subtle CXR findings with clinical signs -- concordant. 50M, CURB65=0. "
            "CXR consolidation present (low confidence) + crackles present = "
            "concordant, so no CR-1. No CR-4 triggers (no immunosuppression, "
            "0 comorbidities, SpO2 97%). Amoxicillin monotherapy. 1 discharge "
            "criterion not met (temp 38.2 > 37.8) but <2 so discharge OK."
        ),
    },
    "cxr_effusion": {
        "curb65": 2,
        "severity_tier": "moderate",
        "contradictions": [],
        "antibiotic": "amoxicillin",
        "discharge_met": False,
        "description": (
            "Pleural effusion WITH consolidation in immunosuppressed patient. "
            "65F, CURB65=2 (C=1 AMT 8/10, 65=1 age 65; U=0 urea 7.0 not >7). "
            "CR-6 requires effusion WITHOUT consolidation -- but consolidation "
            "IS present, so CR-6 does not fire. CR-4 requires severity_tier=low "
            "-- but severity is moderate, so CR-4 does not fire. "
            "Amoxicillin+clarithromycin dual therapy. 3 discharge criteria not "
            "met (temp, confusion, eating)."
        ),
    },
}


CASE_BUILDERS = {
    "cxr_clear": get_cxr_clear_case,
    "cxr_bilateral": get_cxr_bilateral_case,
    "cxr_normal": get_cxr_normal_case,
    "cxr_subtle": get_cxr_subtle_case,
    "cxr_effusion": get_cxr_effusion_case,
}


def relativize_paths(obj, project_root_str):
    """Convert absolute paths to relative paths for portability."""
    if isinstance(obj, str):
        if obj.startswith(project_root_str):
            return os.path.relpath(obj, project_root_str)
        return obj
    elif isinstance(obj, dict):
        return {k: relativize_paths(v, project_root_str) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [relativize_paths(v, project_root_str) for v in obj]
    return obj


def export_all():
    output_dir = project_root / "data" / "synthetic_cases"
    output_dir.mkdir(parents=True, exist_ok=True)

    project_root_str = str(project_root)

    for case_id, builder in CASE_BUILDERS.items():
        print(f"Exporting {case_id}...")
        case_data = builder()

        # Relativize paths
        case_data = relativize_paths(case_data, project_root_str)

        # Add ground truth
        case_data["ground_truth"] = GROUND_TRUTH[case_id]

        output_path = output_dir / f"{case_id}.json"
        with open(output_path, "w") as f:
            json.dump(case_data, f, indent=2, default=str)

        print(f"  -> {output_path}")

    print(f"\nExported {len(CASE_BUILDERS)} cases to {output_dir}/")


if __name__ == "__main__":
    export_all()

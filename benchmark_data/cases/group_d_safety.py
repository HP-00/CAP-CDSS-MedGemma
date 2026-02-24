"""Group D: Safety edge cases for override demonstration.

3 cases testing safety guardrails that override normal clinical pathways:
- SEPSIS-OVERRIDE: Low CURB65 + sepsis markers → hospital override
- MISSING-UREA: Absent urea → CRB65 fallback + data gap flagging
- ORAL-INTOLERANCE: Low CURB65 + can't swallow → IV/hospital consideration
"""

from __future__ import annotations

from cap_agent.agent.clinical_logic import compute_curb65, select_antibiotic

from .helpers import make_case


def get_group_d_cases() -> list[dict]:
    """Build 3 safety edge cases with post-construction overrides."""
    cases = []

    # --- SEPSIS-OVERRIDE ---
    # CURB65=1 (B=1 from SBP<90), severity=low, BUT 4 sepsis markers:
    # lactate=3.5 (>2), HR=110 (>100), SBP=85 (<90), temp=38.5 (>38.3)
    # recommend_place_of_care() should override to hospital referral.
    sepsis = make_case(
        "SEPSIS-OVERRIDE",
        age=45,
        sbp=85,
        dbp=55,
        rr=22,
        amt=10,
        heart_rate=110,
        temperature=38.5,
        expected_contradictions=[],
    )
    sepsis["lab_results"]["lactate"]["value"] = 3.5
    sepsis["lab_results"]["lactate"]["abnormal"] = True
    cases.append(sepsis)

    # --- MISSING-UREA ---
    # Urea absent → compute_curb65 returns curb65=None, falls back to CRB65.
    # CRB65 = C(0) + R(0) + B(0) + 65(1) = 1 → moderate (CRB65 ≥1 → moderate).
    # compute_curb65_data_gaps() should flag "urea" as missing.
    missing = make_case(
        "MISSING-UREA",
        age=72,
        rr=28,
        sbp=110,
        dbp=65,
        amt=10,
        expected_contradictions=[],
    )
    missing["lab_results"]["urea"]["value"] = None
    # Recompute ground truth with missing urea
    curb65_result = compute_curb65({
        "confusion": False,
        "urea": None,
        "respiratory_rate": 28,
        "systolic_bp": 110,
        "diastolic_bp": 65,
        "age": 72,
    })
    abx = select_antibiotic(
        severity=curb65_result["severity_tier"],
        allergies=[],
        oral_tolerance=True,
        pregnancy=False,
        travel_history=[],
        egfr=90,
        recent_antibiotics=[],
    )
    missing["ground_truth"] = {
        "curb65": None,  # Urea missing → no CURB65
        "severity_tier": curb65_result["severity_tier"],  # CRB65=1 → moderate
        "contradictions": [],
        "antibiotic": abx["first_line"],
        "discharge_met": None,
        "crp_trend": None,
    }
    cases.append(missing)

    # --- ORAL-INTOLERANCE ---
    # CURB65=0 (all normal), severity=low, BUT oral_tolerance=False.
    # recommend_place_of_care() should add hospital admission for IV therapy option.
    intolerance = make_case(
        "ORAL-INTOLERANCE",
        age=55,
        rr=20,
        sbp=120,
        dbp=70,
        amt=10,
        oral_tolerance=False,
        expected_contradictions=[],
    )
    cases.append(intolerance)

    return cases

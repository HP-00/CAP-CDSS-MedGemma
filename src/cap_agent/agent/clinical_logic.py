"""Pure deterministic clinical logic — no model calls, no LangGraph state.

All functions take plain dicts and return plain dicts. Fully testable without GPU.
Implements evidence-based clinical logic for Community-Acquired Pneumonia.
"""

from typing import Optional


# ---------------------------------------------------------------------------
# CURB65 Scoring
# ---------------------------------------------------------------------------

def compute_curb65(variables: dict) -> dict:
    """Compute CURB65/CRB65 score.

    Thresholds:
        C: Confusion (AMT <= 8) → 1
        U: Urea > 7 mmol/L → 1  (strictly greater than, NOT >=)
        R: Respiratory rate >= 30 → 1
        B: Systolic BP < 90 OR Diastolic BP <= 60 → 1
        65: Age >= 65 → 1

    Severity tiers: 0-1 = low, 2 = moderate, 3-5 = high

    Returns:
        dict with keys: c, u, r, b, age_65, crb65, curb65, severity_tier, missing_variables
    """
    missing = []

    # C: Confusion (AMT <= 8)
    if variables.get("confusion") is not None:
        c = 1 if variables["confusion"] else 0
    else:
        c = 0
        missing.append("confusion/AMT score")

    # U: Urea > 7 mmol/L
    if variables.get("urea") is not None:
        u = 1 if variables["urea"] > 7 else 0
    else:
        u = 0
        missing.append("urea")

    # R: Respiratory rate >= 30
    if variables.get("respiratory_rate") is not None:
        r = 1 if variables["respiratory_rate"] >= 30 else 0
    else:
        r = 0
        missing.append("respiratory_rate")

    # B: BP systolic < 90 OR diastolic <= 60
    if variables.get("systolic_bp") is not None and variables.get("diastolic_bp") is not None:
        b = 1 if (variables["systolic_bp"] < 90 or variables["diastolic_bp"] <= 60) else 0
    else:
        b = 0
        missing.append("blood_pressure")

    # 65: Age >= 65
    if variables.get("age") is not None:
        age_65 = 1 if variables["age"] >= 65 else 0
    else:
        age_65 = 0
        missing.append("age")

    crb65 = c + r + b + age_65
    curb65 = (c + u + r + b + age_65) if variables.get("urea") is not None else None

    if curb65 is not None:
        score = curb65
        if score <= 1:
            severity_tier = "low"
        elif score == 2:
            severity_tier = "moderate"
        else:
            severity_tier = "high"
    else:
        score = crb65
        if score == 0:
            severity_tier = "low"
        elif score <= 2:
            severity_tier = "moderate"
        else:
            severity_tier = "high"

    return {
        "c": c,
        "u": u,
        "r": r,
        "b": b,
        "age_65": age_65,
        "crb65": crb65,
        "curb65": curb65,
        "severity_tier": severity_tier,
        "missing_variables": missing,
    }


def compute_curb65_data_gaps(curb65_score: dict, crb65: int) -> list:
    """Compute data gap warnings for missing CURB65 variables."""
    gaps = []
    missing = curb65_score.get("missing_variables", [])
    curb65 = curb65_score.get("curb65")

    if "confusion/AMT score" in missing:
        hypothetical = (curb65 if curb65 is not None else crb65) + 1
        tier = "moderate" if hypothetical == 2 else ("high" if hypothetical >= 3 else "low")
        gaps.append(
            f"AMT not documented. If confusion present, CURB65 would be {hypothetical} ({tier})"
        )
    return gaps


# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Contradiction Detection (CR-1 to CR-10)
# ---------------------------------------------------------------------------

def detect_contradictions(
    cxr: dict,
    exam: dict,
    labs: dict,
    demographics: dict,
    curb65: dict,
    case_data: dict,
    antibiotic_recommendation: Optional[dict] = None,
    micro_results: Optional[list] = None,
) -> list:
    """Evaluate 11 cross-modal contradiction rules (CR-1 to CR-11).

    Args:
        cxr: CXR analysis findings
        exam: Clinical exam findings
        labs: Lab values
        demographics: Patient demographics
        curb65: CURB65 score dict
        case_data: Full case data (for social_history and treatment_status)
        antibiotic_recommendation: Current/prior antibiotic rec (for CR-7/8/9)
        micro_results: Microbiology results (for CR-7/8, T=48h)

    Returns:
        List of ContradictionAlert dicts
    """
    contradictions = []

    # Helpers
    cxr_consolidation = cxr.get("consolidation", {}).get("present", False)
    cxr_effusion = cxr.get("pleural_effusion", {}).get("present", False)
    resp_exam = exam.get("respiratory_exam", {})
    has_focal_crackles = resp_exam.get("crackles", False)
    has_bronchial_breathing = resp_exam.get("bronchial_breathing", False)
    crp_value = labs.get("crp", {}).get("value")

    # CR-1: CXR no consolidation + focal crackles/bronchial breathing
    if not cxr_consolidation and (has_focal_crackles or has_bronchial_breathing):
        cr1_confidence = "high" if (has_focal_crackles and has_bronchial_breathing) else "moderate"
        loc = resp_exam.get("crackles_location", "unspecified")
        contradictions.append({
            "rule_id": "CR-1",
            "pattern": "CXR negative for consolidation but clinical exam shows focal crackles/bronchial breathing",
            "evidence_for": (
                f"Clinical exam: crackles={has_focal_crackles}, "
                f"bronchial_breathing={has_bronchial_breathing} at {loc}"
            ),
            "evidence_against": "CXR: no consolidation detected",
            "severity": "high",
            "confidence": cr1_confidence,
            "resolution_strategy": "A",
        })

    # CR-2: CXR no consolidation + CRP > 100 + clinical features
    if (not cxr_consolidation and crp_value is not None and crp_value > 100
            and (has_focal_crackles or has_bronchial_breathing)):
        cr2_confidence = "high" if crp_value > 200 else "moderate"
        contradictions.append({
            "rule_id": "CR-2",
            "pattern": "CXR negative but CRP > 100 with clinical features suggestive of CAP",
            "evidence_for": f"CRP={crp_value} mg/L, clinical exam positive",
            "evidence_against": "CXR: no consolidation detected",
            "severity": "high",
            "confidence": cr2_confidence,
            "resolution_strategy": "B",
        })

    # CR-3: CXR consolidation + CRP < 20 + no clinical signs
    if (cxr_consolidation and crp_value is not None and crp_value < 20
            and not has_focal_crackles and not has_bronchial_breathing):
        cr3_confidence = "high" if crp_value < 10 else "moderate"
        loc = cxr.get("consolidation", {}).get("location", "unspecified")
        contradictions.append({
            "rule_id": "CR-3",
            "pattern": "CXR shows consolidation but CRP < 20 and no clinical respiratory signs",
            "evidence_for": f"CXR: consolidation detected at {loc}",
            "evidence_against": f"CRP={crp_value} mg/L (low), no crackles or bronchial breathing",
            "severity": "moderate",
            "confidence": cr3_confidence,
            "resolution_strategy": "C",
        })

    # CR-4: CURB65 low + override triggers
    # Triggers: immunosuppression, multilobar, hypoxia, effusion, multiple comorbidities, pregnancy
    is_immunosuppressed = any(
        "immunosuppress" in c.lower() for c in (demographics.get("comorbidities") or [])
    )
    if case_data.get("social_history", {}).get("immunosuppression"):
        is_immunosuppressed = True

    cxr_location = cxr.get("consolidation", {}).get("location", "")
    is_multilobar = any(t in cxr_location.lower() for t in ["bilateral", "multilobar", "both"])

    # Observations for hypoxia check
    obs = exam.get("observations", {})
    spo2 = obs.get("spo2")
    is_hypoxic = spo2 is not None and spo2 < 90

    has_effusion = cxr_effusion

    comorbidities = demographics.get("comorbidities") or []
    multiple_comorbidities = len(comorbidities) >= 3

    is_pregnant = demographics.get("pregnancy", False)

    if curb65.get("severity_tier") == "low":
        cr4_triggers = []
        if is_immunosuppressed:
            cr4_triggers.append("immunosuppression")
        if is_multilobar:
            cr4_triggers.append("multilobar changes")
        if is_hypoxic:
            cr4_triggers.append(f"hypoxia (SpO2={spo2}%)")
        if has_effusion:
            cr4_triggers.append("pleural effusion")
        if multiple_comorbidities:
            cr4_triggers.append(f"multiple comorbidities ({len(comorbidities)})")
        if is_pregnant:
            cr4_triggers.append("pregnancy")

        # L3: Frailty trigger
        is_frail = any("frail" in c.lower() for c in comorbidities)
        if case_data.get("social_history", {}).get("frailty"):
            is_frail = True
        if is_frail:
            cr4_triggers.append("frailty")

        # L4: Severe lung disease trigger
        _SEVERE_LUNG_TERMS = ["copd", "bronchiectasis", "pulmonary fibrosis", "severe lung disease", "interstitial lung disease"]
        has_severe_lung = any(
            any(term in c.lower() for term in _SEVERE_LUNG_TERMS)
            for c in comorbidities
        )
        if has_severe_lung:
            cr4_triggers.append("severe lung disease")

        if cr4_triggers:
            cr4_confidence = "high" if len(cr4_triggers) >= 2 else "moderate"
            reason = ", ".join(cr4_triggers)
            contradictions.append({
                "rule_id": "CR-4",
                "pattern": f"CURB65 low severity but {reason} present -- may warrant severity override",
                "evidence_for": f"CURB65={curb65.get('curb65', curb65.get('crb65'))}, severity=low",
                "evidence_against": f"{reason} detected, suggesting higher clinical risk",
                "severity": "high",
                "confidence": cr4_confidence,
                "resolution_strategy": "D",
            })

    # CR-5: CXR bilateral + unilateral clinical signs
    cxr_bilateral = "bilateral" in cxr_location.lower() if cxr_location else False
    exam_location = resp_exam.get("crackles_location", "")
    exam_unilateral = (
        any(side in exam_location.lower() for side in ["right", "left"])
        and "bilateral" not in exam_location.lower()
    )
    if cxr_bilateral and exam_unilateral:
        contradictions.append({
            "rule_id": "CR-5",
            "pattern": "CXR shows bilateral changes but clinical exam has unilateral signs",
            "evidence_for": f"CXR: bilateral changes at {cxr_location}",
            "evidence_against": f"Clinical exam: signs at {exam_location} only",
            "severity": "high",
            "confidence": "moderate",
            "resolution_strategy": "A",
        })

    # CR-6: CXR effusion + no consolidation
    if cxr_effusion and not cxr_consolidation:
        contradictions.append({
            "rule_id": "CR-6",
            "pattern": "CXR shows pleural effusion without consolidation -- consider non-pneumonic cause",
            "evidence_for": "CXR: pleural effusion detected",
            "evidence_against": "CXR: no consolidation -- effusion may indicate heart failure or other cause",
            "severity": "moderate",
            "confidence": "moderate",
            "resolution_strategy": "C",
        })

    # CR-7 to CR-10: Antibiotic stewardship rules
    # (see _detect_cr7, _detect_cr8, _detect_cr9 below)
    if antibiotic_recommendation and micro_results:
        contradictions.extend(_detect_cr7(antibiotic_recommendation, micro_results))
        contradictions.extend(_detect_cr8(antibiotic_recommendation, micro_results))
        contradictions.extend(_detect_cr11(antibiotic_recommendation, micro_results))

    if antibiotic_recommendation and case_data.get("treatment_status"):
        cr9 = _detect_cr9(
            antibiotic_recommendation, case_data["treatment_status"],
            exam.get("observations", {}),
            exam.get("confusion_status", {}),
            demographics.get("oral_tolerance", True),
        )
        if cr9:
            contradictions.append(cr9)

    return contradictions


# ---------------------------------------------------------------------------
# Antibiotic Stewardship Constants
# ---------------------------------------------------------------------------

# Organism coverage map: S=sensitive, R=resistant, I=intermediate, V=variable
_CAP_ORGANISM_COVERAGE: dict = {
    "streptococcus pneumoniae": {
        "amoxicillin": "S", "co-amoxiclav": "S", "doxycycline": "S",
        "clarithromycin": "V", "erythromycin": "V",
        "levofloxacin": "S", "ceftriaxone": "S",
    },
    "haemophilus influenzae": {
        "amoxicillin": "V", "co-amoxiclav": "S", "doxycycline": "S",
        "clarithromycin": "I", "erythromycin": "R",
        "levofloxacin": "S", "ceftriaxone": "S",
    },
    "moraxella catarrhalis": {
        "amoxicillin": "R", "co-amoxiclav": "S", "doxycycline": "S",
        "clarithromycin": "S", "erythromycin": "S",
        "levofloxacin": "S", "ceftriaxone": "S",
    },
    "staphylococcus aureus": {
        "amoxicillin": "R", "co-amoxiclav": "V", "doxycycline": "S",
        "clarithromycin": "V", "erythromycin": "V",
        "levofloxacin": "S", "ceftriaxone": "S",
    },
    "legionella pneumophila": {
        "amoxicillin": "R", "co-amoxiclav": "R", "doxycycline": "S",
        "clarithromycin": "S", "erythromycin": "S",
        "levofloxacin": "S", "ceftriaxone": "R",
    },
    "mycoplasma pneumoniae": {
        "amoxicillin": "R", "co-amoxiclav": "R", "doxycycline": "S",
        "clarithromycin": "S", "erythromycin": "S",
        "levofloxacin": "S", "ceftriaxone": "R",
    },
    "chlamydophila pneumoniae": {
        "amoxicillin": "R", "co-amoxiclav": "R", "doxycycline": "S",
        "clarithromycin": "S", "erythromycin": "S",
        "levofloxacin": "S", "ceftriaxone": "R",
    },
    "klebsiella pneumoniae": {
        "amoxicillin": "R", "co-amoxiclav": "V", "doxycycline": "V",
        "clarithromycin": "R", "erythromycin": "R",
        "levofloxacin": "S", "ceftriaxone": "S",
    },
}

_ATYPICAL_PATHOGENS: set = {
    "legionella", "legionella pneumophila",
    "mycoplasma", "mycoplasma pneumoniae",
    "chlamydophila", "chlamydophila pneumoniae", "chlamydia pneumoniae",
}

_IV_TO_ORAL_SWITCH_MAP: dict = {
    "co-amoxiclav": {"oral": "Co-amoxiclav 500/125mg TDS PO", "note": "Direct switch"},
    "clarithromycin": {"oral": "Clarithromycin 500mg BD PO", "note": "Same dose PO"},
    "levofloxacin": {"oral": "Levofloxacin 500mg BD PO", "note": "99% oral bioavailability"},
    "ceftriaxone": {"oral": "Consult microbiologist for oral step-down", "note": "No direct equivalent"},
    "benzylpenicillin": {"oral": "Amoxicillin 500mg TDS PO", "note": "Oral equivalent"},
}

_INTOLERANCE_KEYWORDS: set = {
    "gi upset", "nausea", "vomiting", "diarrhoea", "diarrhea",
    "headache", "non-immune", "side effect", "mild", "intolerance",
    "stomach upset", "gastrointestinal",
}

_TRUE_ALLERGY_KEYWORDS: set = {
    "anaphylaxis", "urticaria", "angioedema", "rash", "bronchospasm",
    "severe", "ige-mediated", "ige", "swelling", "tongue swelling",
    "throat swelling", "desensitisation required",
    "stevens-johnson", "sjs", "toxic epidermal necrolysis", "ten",
    "dress", "serum sickness", "hemolytic anemia",
}

# SCAR (Severe Cutaneous Adverse Reactions) — subset of TRUE_ALLERGY that are
# absolute contraindications to ALL beta-lactams (not just penicillins).
# Anaphylaxis is also an absolute contraindication.
_SCAR_KEYWORDS: set = {
    "stevens-johnson", "sjs", "toxic epidermal necrolysis", "ten", "dress",
}

_ANAPHYLAXIS_KEYWORDS: set = {"anaphylaxis"}

# Known drug names to extract from antibiotic recommendation strings
_KNOWN_ANTIBIOTIC_NAMES: list = [
    "amoxicillin", "co-amoxiclav", "doxycycline", "clarithromycin",
    "erythromycin", "levofloxacin", "ceftriaxone", "benzylpenicillin",
]

_MACROLIDE_NAMES: set = {"clarithromycin", "erythromycin", "azithromycin"}


# ---------------------------------------------------------------------------
# Antibiotic Stewardship Helpers
# ---------------------------------------------------------------------------

def _normalize_organism(name: str) -> str:
    """Lowercase and strip an organism name for lookup."""
    return name.strip().lower()


def _extract_prescribed_drugs(abx_rec: dict) -> list:
    """Extract known antibiotic drug names from an AntibioticRecommendation.

    Scans both first_line and atypical_cover fields.
    """
    text = (abx_rec.get("first_line", "") + " " + (abx_rec.get("atypical_cover") or "")).lower()
    return [drug for drug in _KNOWN_ANTIBIOTIC_NAMES if drug in text]


def classify_micro_results(micro_results: Optional[list]) -> dict:
    """Classify microbiology results for stewardship rules.

    Returns:
        dict with keys: organisms (list of positive organisms), completed_tests (int),
        has_atypical (bool), susceptibilities (dict mapping organism -> susceptibility dict)
    """
    if not micro_results:
        return {"organisms": [], "completed_tests": 0, "has_atypical": False, "susceptibilities": {}}

    organisms = []
    susceptibilities = {}
    completed = 0
    has_atypical = False

    for result in micro_results:
        status = (result.get("status") or "").lower()
        if status == "positive":
            org = result.get("organism", "")
            if org:
                norm = _normalize_organism(org)
                organisms.append(norm)
                if result.get("susceptibilities"):
                    susceptibilities[norm] = result["susceptibilities"]
                if any(atyp in norm for atyp in _ATYPICAL_PATHOGENS):
                    has_atypical = True
        if status in ("positive", "negative"):
            completed += 1

    return {
        "organisms": organisms,
        "completed_tests": completed,
        "has_atypical": has_atypical,
        "susceptibilities": susceptibilities,
    }


def classify_penicillin_allergy(allergies: Optional[list]) -> dict:
    """Classify whether a penicillin allergy is intolerance vs true allergy.

    Returns:
        dict with keys: has_penicillin_allergy (bool), is_intolerance_only (bool),
        is_true_allergy (bool), classification (str)
    """
    if not allergies:
        return {
            "has_penicillin_allergy": False,
            "is_intolerance_only": False,
            "is_true_allergy": False,
            "classification": "no_penicillin_allergy",
        }

    pen_allergies = [
        a for a in allergies
        if isinstance(a, dict) and "penicillin" in a.get("drug", "").lower()
    ]
    if not pen_allergies:
        return {
            "has_penicillin_allergy": False,
            "is_intolerance_only": False,
            "is_true_allergy": False,
            "classification": "no_penicillin_allergy",
        }

    # Check all penicillin allergy entries
    has_absolute = False
    has_true = False
    has_intolerance = False
    for allergy in pen_allergies:
        reaction = (allergy.get("reaction_type") or "").lower()
        severity = (allergy.get("severity") or "").lower()
        combined = reaction + " " + severity

        # Check SCAR / anaphylaxis first (absolute contraindication)
        if any(kw in combined for kw in _SCAR_KEYWORDS):
            has_absolute = True
        elif any(kw in combined for kw in _ANAPHYLAXIS_KEYWORDS):
            has_absolute = True
        elif any(kw in combined for kw in _TRUE_ALLERGY_KEYWORDS):
            has_true = True
        elif any(kw in combined for kw in _INTOLERANCE_KEYWORDS):
            has_intolerance = True

    if has_absolute:
        return {
            "has_penicillin_allergy": True,
            "is_intolerance_only": False,
            "is_true_allergy": True,
            "classification": "absolute_contraindication",
        }
    elif has_true:
        return {
            "has_penicillin_allergy": True,
            "is_intolerance_only": False,
            "is_true_allergy": True,
            "classification": "true_allergy",
        }
    elif has_intolerance:
        return {
            "has_penicillin_allergy": True,
            "is_intolerance_only": True,
            "is_true_allergy": False,
            "classification": "intolerance",
        }
    else:
        # Unknown reaction type — conservative: treat as possible true allergy
        return {
            "has_penicillin_allergy": True,
            "is_intolerance_only": False,
            "is_true_allergy": False,
            "classification": "unknown",
        }


def assess_iv_to_oral_stability(observations: dict, confusion_status: dict) -> dict:
    """Assess whether patient is stable enough for IV-to-oral switch.

    Stricter than assess_treatment_extension — ALL 6 markers must be normal.
    Thresholds match discharge criteria.

    Returns:
        dict with stable (bool), unstable_markers (list)
    """
    unstable = []

    temp = observations.get("temperature")
    if temp is not None and temp > 37.8:
        unstable.append(f"fever ({temp}°C)")

    hr = observations.get("heart_rate")
    if hr is not None and hr > 100:
        unstable.append(f"tachycardia (HR {hr})")

    rr = observations.get("respiratory_rate")
    if rr is not None and rr >= 24:
        unstable.append(f"tachypnoea (RR {rr})")

    sbp = observations.get("systolic_bp")
    if sbp is not None and sbp < 90:
        unstable.append(f"hypotension (SBP {sbp})")

    spo2 = observations.get("spo2")
    if spo2 is not None and spo2 < 90:
        unstable.append(f"hypoxia (SpO2 {spo2}%)")

    confused = confusion_status.get("present", False)
    if confused:
        unstable.append("confusion")

    return {"stable": len(unstable) == 0, "unstable_markers": unstable}


def generate_iv_to_oral_recommendation(iv_antibiotics: list) -> dict:
    """Map IV antibiotics to oral equivalents via _IV_TO_ORAL_SWITCH_MAP.

    Args:
        iv_antibiotics: List of IV antibiotic strings (e.g. ["Co-amoxiclav 1.2g TDS IV"])

    Returns:
        dict with switches (list of {iv, oral, note}), unmatched (list)
    """
    switches = []
    unmatched = []

    for iv_drug in iv_antibiotics:
        iv_lower = iv_drug.lower()
        matched = False
        for drug_key, switch_info in _IV_TO_ORAL_SWITCH_MAP.items():
            if drug_key in iv_lower:
                switches.append({
                    "iv": iv_drug,
                    "oral": switch_info["oral"],
                    "note": switch_info["note"],
                })
                matched = True
                break
        if not matched:
            unmatched.append(iv_drug)

    return {"switches": switches, "unmatched": unmatched}


# ---------------------------------------------------------------------------
# CR-7, CR-8, CR-9 Detection (called from detect_contradictions)
# ---------------------------------------------------------------------------

def _detect_cr7(abx_rec: dict, micro_results: list) -> list:
    """CR-7: Antibiotic doesn't cover identified organism.

    Fires when a positive micro result shows resistance to a prescribed drug,
    based on lab susceptibility data (priority) or the coverage map.
    """
    contradictions = []
    classified = classify_micro_results(micro_results)
    prescribed_drugs = _extract_prescribed_drugs(abx_rec)

    for organism in classified["organisms"]:
        lab_susc = classified["susceptibilities"].get(organism, {})
        coverage = _CAP_ORGANISM_COVERAGE.get(organism, {})

        for drug in prescribed_drugs:
            # Lab susceptibility takes priority over population-level coverage map
            drug_lower = drug.lower()
            if lab_susc:
                susc_value = lab_susc.get(drug_lower, lab_susc.get(drug, ""))
                if susc_value:
                    # Lab data is authoritative — only fire if R, skip map either way
                    if susc_value.upper() == "R":
                        contradictions.append({
                            "rule_id": "CR-7",
                            "pattern": (
                                f"Prescribed {drug} but {organism} is resistant "
                                f"(lab susceptibility: R)"
                            ),
                            "evidence_for": f"Current regimen includes {drug}",
                            "evidence_against": (
                                f"{organism} lab susceptibility shows resistance to {drug}"
                            ),
                            "severity": "high",
                            "confidence": "high",
                            "resolution_strategy": "E",
                        })
                    continue  # Lab data present → skip coverage map
            # Fall back to population-level coverage map (no lab data for this drug)
            map_value = coverage.get(drug_lower, "")
            if map_value == "R":
                contradictions.append({
                    "rule_id": "CR-7",
                    "pattern": (
                        f"Prescribed {drug} but {organism} has intrinsic resistance"
                    ),
                    "evidence_for": f"Current regimen includes {drug}",
                    "evidence_against": (
                        f"{organism} has intrinsic resistance to {drug} "
                        f"(population-level coverage map)"
                    ),
                    "severity": "high",
                    "confidence": "moderate",
                    "resolution_strategy": "E",
                })

    return contradictions


def _detect_cr8(abx_rec: dict, micro_results: list) -> list:
    """CR-8: Macrolide prescribed, no atypical pathogen on micro.

    Fires when a macrolide is in the regimen AND at least 1 micro test is
    completed AND no atypical pathogen has been identified.
    Pending/not_sent tests do not count as completed.
    """
    prescribed = _extract_prescribed_drugs(abx_rec)
    has_macrolide = any(drug in _MACROLIDE_NAMES for drug in prescribed)
    if not has_macrolide:
        return []

    # High severity: clarithromycin is standard dual therapy, not conditional
    if abx_rec.get("severity_tier") == "high":
        return []

    classified = classify_micro_results(micro_results)
    if classified["completed_tests"] == 0:
        return []  # No completed tests — too early to de-escalate

    if classified["has_atypical"]:
        return []  # Atypical found — macrolide justified

    cr8_confidence = "high" if classified["completed_tests"] >= 2 else "moderate"
    return [{
        "rule_id": "CR-8",
        "pattern": (
            "Macrolide prescribed but no atypical pathogen identified on "
            f"{classified['completed_tests']} completed micro test(s)"
        ),
        "evidence_for": (
            f"Current regimen includes macrolide "
            f"({', '.join(d for d in prescribed if d in _MACROLIDE_NAMES)})"
        ),
        "evidence_against": (
            f"{classified['completed_tests']} micro test(s) completed, "
            "no atypical pathogen identified — consider macrolide de-escalation"
        ),
        "severity": "moderate",
        "confidence": cr8_confidence,
        "resolution_strategy": "E",
    }]


def _detect_cr9(
    abx_rec: dict,
    treatment_status: dict,
    observations: dict,
    confusion_status: dict,
    oral_tolerance: bool,
) -> Optional[dict]:
    """CR-9: IV >48h but oral tolerance + improving.

    Fires when the patient has been on IV antibiotics for >=48h,
    has oral tolerance, and ALL 6 stability markers are normal.
    """
    current_route = treatment_status.get("current_route", "").upper()
    if current_route != "IV":
        return None

    hours_on_iv = treatment_status.get("hours_on_iv", 0)
    if hours_on_iv < 48:
        return None

    if not oral_tolerance:
        return None

    stability = assess_iv_to_oral_stability(observations, confusion_status)
    if not stability["stable"]:
        return None

    iv_antibiotics = treatment_status.get("iv_antibiotics", [])
    recommendation = generate_iv_to_oral_recommendation(iv_antibiotics)

    return {
        "rule_id": "CR-9",
        "pattern": (
            f"IV antibiotics for {hours_on_iv}h (>=48h), patient clinically stable "
            f"with oral tolerance — consider IV-to-oral switch"
        ),
        "evidence_for": (
            f"On IV for {hours_on_iv}h, route={current_route}"
        ),
        "evidence_against": (
            "All 6 stability markers normal, oral tolerance confirmed "
            "— switch criteria met"
        ),
        "severity": "moderate",
        "confidence": "high",
        "resolution_strategy": "E",
        "recommendation": recommendation,
    }


def _detect_cr11(abx_rec: dict, micro_results: list) -> list:
    """CR-11: Pneumococcal antigen positive + broad-spectrum → de-escalate to amoxicillin.

    Fires when:
    - Positive pneumococcal urine antigen test
    - AND broad-spectrum antibiotic prescribed (co-amoxiclav, ceftriaxone, or levofloxacin)

    Confidence: high if susceptibility confirms S to amoxicillin, moderate otherwise.
    """
    contradictions = []
    prescribed = _extract_prescribed_drugs(abx_rec)
    broad_spectrum = {"co-amoxiclav", "ceftriaxone", "levofloxacin"}
    has_broad = any(drug in broad_spectrum for drug in prescribed)
    if not has_broad:
        return []

    classified = classify_micro_results(micro_results)

    # Look for positive pneumococcal antigen
    pneumococcal_positive = False
    for result in micro_results:
        status = (result.get("status") or "").lower()
        test_type = (result.get("test_type") or "").lower()
        if status == "positive" and "pneumococcal" in test_type and "antigen" in test_type:
            pneumococcal_positive = True
            break

    if not pneumococcal_positive:
        return []

    # Check susceptibility for confidence level
    susc = classified["susceptibilities"]
    amox_sensitive = False
    for org, org_susc in susc.items():
        if "pneumo" in org.lower():
            if org_susc.get("amoxicillin", "").upper() == "S":
                amox_sensitive = True
                break

    # Also check population-level coverage map
    if not amox_sensitive:
        pop_coverage = _CAP_ORGANISM_COVERAGE.get("streptococcus pneumoniae", {})
        if pop_coverage.get("amoxicillin") == "S":
            amox_sensitive = True  # population data, but moderate confidence

    confidence = "high" if any(
        "pneumo" in org.lower() and susc.get(org, {}).get("amoxicillin", "").upper() == "S"
        for org in susc
    ) else "moderate"

    broad_drugs = [d for d in prescribed if d in broad_spectrum]
    contradictions.append({
        "rule_id": "CR-11",
        "pattern": (
            f"Pneumococcal urine antigen positive but broad-spectrum antibiotic "
            f"({', '.join(broad_drugs)}) prescribed — consider de-escalation to amoxicillin"
        ),
        "evidence_for": f"Current regimen includes {', '.join(broad_drugs)}",
        "evidence_against": (
            "Pneumococcal urine antigen positive — S. pneumoniae confirmed, "
            "amoxicillin is first-line for pneumococcal CAP"
        ),
        "severity": "moderate",
        "confidence": confidence,
        "resolution_strategy": "E",
    })

    return contradictions


def detect_cr10(antibiotic_recommendation: dict, allergies: list) -> Optional[dict]:
    """CR-10: Fluoroquinolone prescribed but penicillin allergy is intolerance only.

    Called from treatment_selection_node (not detect_contradictions) because
    it needs the freshly computed antibiotic recommendation.

    Returns:
        ContradictionAlert dict or None
    """
    prescribed = _extract_prescribed_drugs(antibiotic_recommendation)
    has_fluoroquinolone = "levofloxacin" in prescribed

    if not has_fluoroquinolone:
        return None

    classification = classify_penicillin_allergy(allergies)
    if not classification["is_intolerance_only"]:
        return None

    return {
        "rule_id": "CR-10",
        "pattern": (
            "Levofloxacin prescribed due to penicillin 'allergy', but reaction "
            "history suggests intolerance (not true allergy) — penicillin-based "
            "regimen may be safe"
        ),
        "evidence_for": (
            f"Penicillin allergy recorded; levofloxacin selected as alternative"
        ),
        "evidence_against": (
            f"Allergy classification: {classification['classification']}. "
            "MHRA fluoroquinolone restrictions apply — consider allergy testing "
            "or supervised penicillin challenge"
        ),
        "severity": "high",
        "confidence": "high",
        "resolution_strategy": "E",
    }


# ---------------------------------------------------------------------------
# Antibiotic Selection
# ---------------------------------------------------------------------------

def select_antibiotic(
    severity: str,
    allergies: Optional[list] = None,
    oral_tolerance: bool = True,
    pregnancy: bool = False,
    travel_history: Optional[list] = None,
    egfr: Optional[float] = None,
    recent_antibiotics: Optional[list] = None,
    atypical_indicators: Optional[list] = None,
) -> dict:
    """Select antibiotic per severity-stratified evidence base.

    Args:
        severity: "low", "moderate", or "high"
        allergies: List of allergy dicts with 'drug' key
        oral_tolerance: Can patient take oral medications
        pregnancy: Is patient pregnant
        travel_history: List of recent travel (atypical pathogen risk)
        egfr: eGFR value in mL/min/1.73m2

    Returns:
        AntibioticRecommendation dict
    """
    allergies = allergies or []
    travel_history = travel_history or []

    penicillin_allergy = any(
        "penicillin" in (a.get("drug", "") if isinstance(a, dict) else str(a)).lower()
        for a in allergies
    )
    allergy_classification = classify_penicillin_allergy(allergies)
    atypical_risk = len(travel_history) > 0 or bool(atypical_indicators)

    if severity == "low":
        if penicillin_allergy:
            first_line = (
                "Doxycycline 200mg on first day then 100mg OD for 4 days (5-day total) PO, OR "
                "Clarithromycin 500mg BD for 5 days PO, OR "
                "Erythromycin 500mg QDS for 5 days PO (pregnancy)"
            )
            atypical_cover = None
        elif atypical_risk:
            # Low severity + atypical suspected → switch to alternative
            first_line = (
                "Clarithromycin 500mg BD PO for 5 days, OR "
                "Doxycycline 200mg on first day then 100mg OD for 4 days (5-day total) PO"
                ", OR Erythromycin 500mg QDS PO for 5 days (if pregnant)"
            )
            atypical_cover = None
        else:
            first_line = "Amoxicillin 500mg TDS PO for 5 days"
            atypical_cover = None
        dose_route = "PO"
        evidence_ref = "BTS 2009; el Moussaoui 2006; Uranga 2016"

    elif severity == "moderate":
        if penicillin_allergy:
            first_line = "Doxycycline 200mg stat then 100mg OD PO for 5 days"
            atypical_cover = None
        else:
            first_line = (
                "Amoxicillin 500mg TDS PO + clarithromycin 500mg BD PO for 5 days"
                ", OR amoxicillin 500mg TDS PO + erythromycin 500mg QDS PO for 5 days (if pregnant)"
            )
            atypical_cover = None
        dose_route = "PO"
        evidence_ref = "BTS 2009; Sligl 2014"

    else:  # high
        if penicillin_allergy and allergy_classification["classification"] == "absolute_contraindication":
            # Anaphylaxis / SCAR → avoid ALL beta-lactams → levofloxacin
            first_line = (
                "Levofloxacin 500mg BD PO/IV for 5 days "
                "(consult microbiologist; note MHRA restrictions)"
            )
            atypical_cover = None
        elif penicillin_allergy and allergy_classification["classification"] == "true_allergy":
            # Non-SCAR IgE-mediated → cephalosporin primary (BTS Rec 98)
            first_line = (
                "Cefuroxime 1.5g TDS IV or Ceftriaxone 2g OD IV for 5 days "
                "+ Clarithromycin 500mg BD IV/PO for 5 days"
                ", OR Erythromycin 500mg QDS PO for 5 days (if pregnant)"
            )
            atypical_cover = "Included (clarithromycin)"
        elif penicillin_allergy and allergy_classification["classification"] == "intolerance":
            # Intolerance (GI upset etc) → standard co-amoxiclav (safe to use)
            first_line = (
                "Co-amoxiclav 500/125mg TDS PO or 1.2g TDS IV for 5 days "
                "+ Clarithromycin 500mg BD IV/PO for 5 days"
                ", OR Erythromycin 500mg QDS PO for 5 days (if pregnant)"
            )
            atypical_cover = "Included (clarithromycin)"
        elif penicillin_allergy:
            # Unknown allergy classification → conservative: levofloxacin
            first_line = (
                "Levofloxacin 500mg BD PO/IV for 5 days "
                "(consult microbiologist; note MHRA restrictions)"
            )
            atypical_cover = None
        else:
            first_line = (
                "Co-amoxiclav 500/125mg TDS PO or 1.2g TDS IV for 5 days "
                "+ Clarithromycin 500mg BD IV/PO for 5 days"
                ", OR Erythromycin 500mg QDS PO for 5 days (if pregnant)"
            )
            atypical_cover = "Included (clarithromycin)"
        dose_route = "IV"
        evidence_ref = "BTS 2009; Sligl 2014; MHRA 2024"

    # Override for oral intolerance
    if not oral_tolerance and "PO" in dose_route:
        first_line = first_line.replace("PO", "IV (oral intolerance)")
        dose_route = "IV"

    # Pregnancy check (must check both first_line and atypical_cover)
    allergy_adjustment = None
    if pregnancy:
        pregnancy_warnings = []
        all_drugs = first_line.lower() + " " + (atypical_cover or "").lower()
        # Substitute clarithromycin → erythromycin in actual strings
        if "clarithromycin" in first_line.lower():
            first_line = first_line.replace("Clarithromycin", "Erythromycin").replace("clarithromycin", "erythromycin")
            first_line = first_line.replace("500mg BD", "500mg QDS").replace("500mg bd", "500mg QDS")
            pregnancy_warnings.append("Pregnancy: erythromycin substituted for clarithromycin")
        if atypical_cover and "clarithromycin" in atypical_cover.lower():
            atypical_cover = atypical_cover.replace("clarithromycin", "erythromycin").replace("Clarithromycin", "Erythromycin")
            atypical_cover = atypical_cover.replace("500mg BD", "500mg QDS").replace("500mg bd", "500mg QDS")
            pregnancy_warnings.append("Pregnancy: erythromycin substituted for clarithromycin in atypical cover")
        # Flag contraindicated drugs
        if "levofloxacin" in all_drugs or "doxycycline" in all_drugs:
            contraindicated = []
            if "doxycycline" in all_drugs:
                contraindicated.append("doxycycline (tetracycline)")
            if "levofloxacin" in all_drugs:
                contraindicated.append("levofloxacin (fluoroquinolone)")
            pregnancy_warnings.append(f"Pregnancy: {', '.join(contraindicated)} contraindicated")
        if pregnancy_warnings:
            allergy_adjustment = "; ".join(pregnancy_warnings)

    # Renal adjustment
    renal_adjustment = None
    if egfr is not None and egfr < 30:
        renal_adjustment = (
            f"eGFR {egfr}: dose adjustment required — "
            "amoxicillin: reduce dose frequency (BNF); "
            "clarithromycin: halve dose or avoid; "
            "levofloxacin: adjust per CrCl (250mg OD if CrCl <20)"
        )
    elif egfr is not None and egfr < 60:
        renal_adjustment = (
            f"eGFR {egfr}: monitor renal function; "
            "clarithromycin: halve dose if eGFR <30; "
            "levofloxacin: no adjustment needed if CrCl >50"
        )

    # Corticosteroid recommendation
    has_fluoroquinolone = "levofloxacin" in first_line.lower()
    corticosteroid_recommendation = None
    if severity == "high":
        if has_fluoroquinolone:
            corticosteroid_recommendation = (
                "AVOID: Do not co-administer corticosteroid with levofloxacin "
                "(MHRA Drug Safety Update Jan 2024 — tendon/aortic rupture risk). "
                "Consult microbiologist for alternative antibiotic if corticosteroid needed."
            )
        else:
            corticosteroid_recommendation = (
                "Consider IV hydrocortisone 200mg/day (50mg QDS) for severe CAP "
                "for 8-14 days or until discharge (Dequin 2023 CAPE COD trial). "
                "Note: evidence is for ICU-level severity"
            )

    # Stewardship notes
    stewardship = []
    stewardship.append(
        "Start antibiotics within 4 hours of hospital presentation"
    )
    if severity == "high" and has_fluoroquinolone:
        stewardship.append(
            "MHRA: Fluoroquinolones restricted — tendon/aortic risk (Jan 2024 safety advice)"
        )
        stewardship.append(
            "MHRA Jan 2024: AVOID concurrent corticosteroid with fluoroquinolone "
            "(tendon/aortic rupture risk)"
        )
    if recent_antibiotics:
        drug_names = ", ".join(
            a.get("drug", str(a)) if isinstance(a, dict) else str(a)
            for a in recent_antibiotics
        )
        stewardship.append(
            f"Recent antibiotic use ({drug_names}): consider alternative class or "
            "seek microbiological advice if treatment failure suspected (BTS 2009)"
        )
    stewardship.append("Review at 48h for IV-to-oral switch if applicable (CR-9)")
    stewardship.append("Target 5-day course; extend only if clinically indicated (el Moussaoui 2006; Uranga 2016)")
    stewardship.append(
        "Obtain blood cultures BEFORE antibiotic initiation if indicated"
    )

    return {
        "severity_tier": severity,
        "first_line": first_line,
        "dose_route": dose_route,
        "allergy_adjustment": allergy_adjustment,
        "atypical_cover": atypical_cover,
        "renal_adjustment": renal_adjustment,
        "corticosteroid_recommendation": corticosteroid_recommendation,
        "stewardship_notes": stewardship,
        "evidence_reference": evidence_ref,
        "reasoning": (
            f"Severity {severity}, "
            f"penicillin_allergy={penicillin_allergy}, oral_tolerance={oral_tolerance}"
        ),
    }


def plan_investigations(
    severity: str,
    observations: dict,
    lab_values: dict,
    travel_history: Optional[list] = None,
    legionella_risk_factors: Optional[list] = None,
) -> dict:
    """Plan investigations based on severity and sepsis markers."""
    travel_history = travel_history or []
    legionella_risk_factors = legionella_risk_factors or []

    lactate = lab_values.get("lactate", {}).get("value") if lab_values else None
    hr = observations.get("heart_rate")
    temp = observations.get("temperature")

    sepsis_markers = []
    if lactate and lactate > 2:
        sepsis_markers.append(f"lactate {lactate}")
    if hr and hr > 90:
        sepsis_markers.append(f"HR {hr}")
    if temp and (temp > 38.3 or temp < 36):
        sepsis_markers.append(f"temp {temp}")
    if observations.get("systolic_bp") and observations["systolic_bp"] < 90:
        sepsis_markers.append(f"SBP {observations['systolic_bp']}")

    all_legionella_risks = list(travel_history) + list(legionella_risk_factors)

    return {
        "blood_cultures": {
            "recommended": severity in ["moderate", "high"] and len(sepsis_markers) > 0,
            "reasoning": (
                f"Sepsis markers: {', '.join(sepsis_markers)}" if sepsis_markers
                else "No sepsis markers identified"
            ),
        },
        "sputum_culture": {
            "recommended": severity in ["moderate", "high"],
            "reasoning": (
                "Moderate/high severity -- sputum culture if productive cough and adequate sample"
            ),
        },
        "pneumococcal_antigen": {
            "recommended": severity in ["moderate", "high"],
            "reasoning": "Supports de-escalation to narrow-spectrum antibiotic if positive",
        },
        "legionella_antigen": {
            "recommended": severity == "high" or (severity == "moderate" and len(all_legionella_risks) > 0),
            "reasoning": (
                f"Risk factors: {all_legionella_risks}" if all_legionella_risks
                else "No travel or legionella risk factors identified"
            ),
        },
    }


# ---------------------------------------------------------------------------
# Treatment Duration / Clinical Instability
# ---------------------------------------------------------------------------

def assess_treatment_extension(observations: dict, micro_results: Optional[list] = None) -> dict:
    """Assess whether antibiotic course should extend beyond 5 days.

    Criteria for extension:
        - Fever in past 48h (temperature > 37.8), OR
        - More than 1 of: SBP<90, HR>100, RR>24, SpO2<90%
        - Resistant organism identified on microbiology

    Args:
        observations: Current clinical observations
        micro_results: Microbiology results (optional)

    Returns:
        dict with extend_recommended, criteria_met, reasoning
    """
    criteria_met = []

    temp = observations.get("temperature")
    if temp is not None and temp > 37.8:
        criteria_met.append(f"fever (temperature {temp}°C)")

    instability_markers = []
    sbp = observations.get("systolic_bp")
    if sbp is not None and sbp < 90:
        instability_markers.append(f"SBP {sbp}")
    hr = observations.get("heart_rate")
    if hr is not None and hr > 100:
        instability_markers.append(f"HR {hr}")
    rr = observations.get("respiratory_rate")
    if rr is not None and rr > 24:
        instability_markers.append(f"RR {rr}")
    spo2 = observations.get("spo2")
    if spo2 is not None and spo2 < 90:
        instability_markers.append(f"SpO2 {spo2}%")

    if len(instability_markers) > 1:
        criteria_met.append(f"clinical instability ({', '.join(instability_markers)})")

    # Microbiological: resistant organism may warrant extended treatment
    if micro_results:
        for result in micro_results:
            susc = result.get("susceptibilities") or {}
            for drug, value in susc.items():
                if isinstance(value, str) and value.upper() == "R":
                    criteria_met.append(f"resistant organism ({result.get('organism', 'unknown')} R to {drug})")
                    break  # one resistant finding is enough

    extend = len(criteria_met) > 0

    if extend:
        reasoning = f"Consider extending beyond 5 days: {'; '.join(criteria_met)}"
    else:
        reasoning = "5-day course appropriate — no instability criteria met"

    spo2_caveat = (
        "Note: O\u2082 saturation monitors may be inaccurate in people with "
        "pigmented skin."
    )

    return {
        "extend_recommended": extend,
        "criteria_met": criteria_met,
        "reasoning": reasoning,
        "spo2_caveat": spo2_caveat,
    }


# ---------------------------------------------------------------------------
# Treatment Failure Reassessment
# ---------------------------------------------------------------------------

def assess_treatment_response(
    days_on_treatment: int,
    symptoms_improving: bool,
) -> dict:
    """Assess treatment response.

    If not improving within 3 days: reassess, consider non-bacterial cause,
    send microbiological sample.

    Args:
        days_on_treatment: Number of days since antibiotic initiation
        symptoms_improving: Whether clinical symptoms are improving

    Returns:
        dict with reassess_needed, actions, reasoning
    """
    if days_on_treatment >= 3 and not symptoms_improving:
        return {
            "reassess_needed": True,
            "actions": [
                "Re-evaluate diagnosis — consider non-bacterial cause",
                "Send microbiological samples if not already obtained",
                "Review antibiotic choice and consider broadening spectrum",
                "Repeat imaging if clinically indicated",
                "Consider specialist referral",
            ],
            "reasoning": (
                f"Day {days_on_treatment} without improvement. "
                "Reassess if no improvement within 3 days."
            ),
        }
    return {
        "reassess_needed": False,
        "actions": [],
        "reasoning": (
            f"Day {days_on_treatment}, symptoms {'improving' if symptoms_improving else 'stable'}. "
            "Continue current treatment."
        ),
    }


# ---------------------------------------------------------------------------
# CRP Trend Analysis
# ---------------------------------------------------------------------------

def compute_crp_trend(
    admission_crp: float,
    current_crp: float,
    days_since_admission: int = 0,
) -> dict:
    """Compute CRP trend and flag for senior review.

    Args:
        admission_crp: Baseline CRP at admission (mg/L)
        current_crp: Current CRP value (mg/L)
        days_since_admission: Days since treatment started

    Returns:
        dict with admission_value, current_value, percent_change, trend,
        flag_senior_review, reasoning
    """
    if admission_crp <= 0:
        return {
            "admission_value": admission_crp,
            "current_value": current_crp,
            "percent_change": None,
            "trend": "unknown",
            "flag_senior_review": False,
            "reasoning": "Admission CRP zero or negative — trend analysis not applicable.",
        }

    percent_change = ((admission_crp - current_crp) / admission_crp) * 100

    if percent_change >= 50:
        trend = "improving"
        flag = False
        reasoning = (
            f"CRP decreased by {percent_change:.0f}% "
            f"({admission_crp} → {current_crp} mg/L). "
            "Adequate treatment response."
        )
    elif percent_change > 0:
        trend = "slow_response"
        flag = days_since_admission >= 3
        reasoning = (
            f"CRP decreased by only {percent_change:.0f}% "
            f"({admission_crp} → {current_crp} mg/L). "
        )
        if flag:
            reasoning += (
                f"Day {days_since_admission}: <50% reduction warrants "
                "senior clinical review."
            )
        else:
            reasoning += (
                f"Day {days_since_admission}: early treatment phase — "
                "recheck at Day 3-4."
            )
    elif percent_change == 0:
        trend = "static"
        flag = days_since_admission >= 3
        reasoning = (
            f"CRP unchanged at {current_crp} mg/L. "
        )
        if flag:
            reasoning += (
                f"Day {days_since_admission}: static CRP warrants "
                "senior clinical review."
            )
        else:
            reasoning += (
                f"Day {days_since_admission}: early treatment phase — "
                "recheck at Day 3-4."
            )
    else:
        trend = "worsening"
        flag = True
        reasoning = (
            f"CRP INCREASED by {abs(percent_change):.0f}% "
            f"({admission_crp} → {current_crp} mg/L). "
            "Worsening inflammatory markers — senior review required."
        )

    return {
        "admission_value": admission_crp,
        "current_value": current_crp,
        "percent_change": round(percent_change, 1),
        "trend": trend,
        "flag_senior_review": flag,
        "reasoning": reasoning,
    }


def compute_pct_trend(
    admission_pct: float,
    current_pct: float,
    days_since_admission: int = 0,
) -> dict:
    """Compute procalcitonin (PCT) trend for treatment monitoring.

    Uses ProHOSP algorithm (Schuetz 2009): 80% decrease from peak OR absolute
    < 0.25 µg/L = improving.

    Args:
        admission_pct: Baseline PCT at admission (ng/mL or µg/L)
        current_pct: Current PCT value
        days_since_admission: Days since treatment started

    Returns:
        dict with admission_value, current_value, percent_change, trend,
        flag_senior_review, reasoning
    """
    if admission_pct <= 0:
        return {
            "admission_value": admission_pct,
            "current_value": current_pct,
            "percent_change": None,
            "trend": "unknown",
            "flag_senior_review": False,
            "reasoning": "Admission PCT zero or negative — trend analysis not applicable.",
        }

    percent_change = ((admission_pct - current_pct) / admission_pct) * 100

    # Absolute threshold: PCT < 0.25 µg/L = improving regardless of percentage
    # (ProHOSP algorithm; Schuetz 2009, JAMA 302:1059-1066)
    if current_pct < 0.25:
        trend = "improving"
        flag = False
        reasoning = (
            f"PCT below 0.25 µg/L ({current_pct}). "
            f"Absolute threshold met — antibiotic discontinuation supported "
            "(ProHOSP algorithm; Schuetz 2009)."
        )
    elif percent_change >= 80:
        trend = "improving"
        flag = False
        reasoning = (
            f"PCT decreased by {percent_change:.0f}% "
            f"({admission_pct} → {current_pct}). "
            "Adequate treatment response (>=80% decrease from peak; Schuetz 2009)."
        )
    elif percent_change > 0:
        trend = "slow_response"
        flag = days_since_admission >= 3
        reasoning = (
            f"PCT decreased by only {percent_change:.0f}% "
            f"({admission_pct} → {current_pct}). "
        )
        if flag:
            reasoning += (
                f"Day {days_since_admission}: <80% reduction warrants "
                "senior clinical review."
            )
        else:
            reasoning += (
                f"Day {days_since_admission}: early treatment phase — "
                "recheck at Day 3-4."
            )
    elif percent_change == 0:
        trend = "static"
        flag = days_since_admission >= 3
        reasoning = f"PCT unchanged at {current_pct}. "
        if flag:
            reasoning += (
                f"Day {days_since_admission}: static PCT warrants "
                "senior clinical review."
            )
        else:
            reasoning += (
                f"Day {days_since_admission}: early treatment phase — "
                "recheck at Day 3-4."
            )
    else:
        trend = "worsening"
        flag = True
        reasoning = (
            f"PCT INCREASED by {abs(percent_change):.0f}% "
            f"({admission_pct} → {current_pct}). "
            "Worsening — senior review required."
        )

    return {
        "admission_value": admission_pct,
        "current_value": current_pct,
        "percent_change": round(percent_change, 1),
        "trend": trend,
        "flag_senior_review": flag,
        "reasoning": reasoning,
    }


# ---------------------------------------------------------------------------
# Monitoring & Discharge
# ---------------------------------------------------------------------------

def compute_monitoring_plan(
    severity: str,
    observations: dict,
    confusion_status: dict,
    demographics: Optional[dict] = None,
    treatment_status: Optional[dict] = None,
    crp_trend: Optional[dict] = None,
    pct_trend: Optional[dict] = None,
    micro_results: Optional[list] = None,
) -> dict:
    """Generate monitoring plan with discharge criteria check.

    Discharge criteria: 7 binary checks.
    Discharge OK if fewer than 2 criteria are not met.

    Args:
        severity: "low", "moderate", or "high"
        observations: Current clinical observations
        confusion_status: Confusion assessment dict
        demographics: Patient demographics (for CXR risk factor assessment)
        treatment_status: Treatment status dict with days_on_treatment, symptoms_improving
        crp_trend: CRP trend analysis dict from compute_crp_trend()
    """
    demographics = demographics or {}

    # CRP monitoring
    crp_timing = (
        "Consider CRP or procalcitonin (PCT) at 3-4 days after starting treatment "
        "if clinical concern about treatment failure. "
        "If levels do not significantly improve, consider senior clinical review."
    )
    if crp_trend and crp_trend.get("flag_senior_review"):
        crp_timing = (
            "WARNING: CRP trend flagged for senior review — "
            + crp_trend.get("reasoning", "")
            + " "
            + crp_timing
        )

    # Treatment response assessment
    treatment_response = None
    if treatment_status is not None:
        days = treatment_status.get("days_on_treatment", 0)
        improving = treatment_status.get("symptoms_improving", True)
        treatment_response = assess_treatment_response(days, improving)

    # CXR follow-up
    age = demographics.get("age")
    smoking = demographics.get("smoking_status")
    has_cxr_risk_factors = (
        (age is not None and age > 50)
        or smoking in ("current", "former")
    )

    if severity == "high":
        cxr_follow_up = (
            "Repeat CXR at 72h (3 days) if no clinical improvement (BTS 2009 Rec 71)."
        )
        if has_cxr_risk_factors:
            cxr_follow_up += (
                " Follow-up CXR at 6 weeks (risk factors: "
                + ", ".join(
                    f for f in [
                        f"age {age}" if age is not None and age > 50 else None,
                        f"smoking ({smoking})" if smoking in ("current", "former") else None,
                    ] if f
                )
                + ")."
            )
        else:
            cxr_follow_up += (
                " Follow-up CXR not routinely indicated. Consider at 6 weeks if: "
                "smoker, age >50, persisting symptoms, or unexplained weight loss."
            )
    else:
        if has_cxr_risk_factors:
            cxr_follow_up = (
                "Follow-up CXR at 6 weeks (risk factors: "
                + ", ".join(
                    f for f in [
                        f"age {age}" if age is not None and age > 50 else None,
                        f"smoking ({smoking})" if smoking in ("current", "former") else None,
                    ] if f
                )
                + ")."
            )
        else:
            cxr_follow_up = (
                "Follow-up CXR not routinely indicated. Consider at 6 weeks if: "
                "smoker, age >50, persisting symptoms, or unexplained weight loss."
            )

    # Discharge criteria check
    criteria = {
        "temperature_normal": observations.get("temperature", 37) <= 37.8,
        "rr_normal": observations.get("respiratory_rate", 20) < 24,
        "hr_normal": observations.get("heart_rate", 80) <= 100,
        "sbp_normal": observations.get("systolic_bp", 120) > 90,
        "spo2_normal": observations.get("spo2", 98) >= 90,
        "mental_status_normal": not confusion_status.get("present", False),
        "eating_independently": demographics.get("eating_independently", True),
    }

    criteria_not_met = [k for k, v in criteria.items() if not v]
    discharge_ok = len(criteria_not_met) < 2

    # Treatment response override: if reassessment needed, discharge not safe
    if treatment_response and treatment_response.get("reassess_needed"):
        discharge_ok = False
        if "treatment_reassessment_needed" not in criteria_not_met:
            criteria_not_met.append("treatment_reassessment_needed")

    if severity == "high":
        next_review = "Senior review within 4 hours. Reassess at 12h and 24h."
    elif severity == "moderate":
        next_review = "Review at 24h. Reassess at 48h for treatment response."
    else:
        next_review = "Review at 24h. Consider early discharge if criteria met."

    # Treatment duration assessment
    treatment_duration = assess_treatment_extension(observations, micro_results=micro_results)

    return {
        "crp_repeat_timing": crp_timing,
        "cxr_follow_up": cxr_follow_up,
        "discharge_criteria_met": discharge_ok,
        "discharge_criteria_details": {
            "criteria_checked": criteria,
            "not_met": criteria_not_met,
            "note": (
                "Discharge criteria: fewer than 2 of 7 instability criteria "
                "in the past 24 hours before discharge"
                if discharge_ok
                else f"Discharge criteria NOT met: {', '.join(criteria_not_met)}"
            ),
            "spo2_caveat": (
                "O\u2082 saturation monitors may be inaccurate in people with "
                "pigmented skin"
            ),
        },
        "next_review": next_review,
        "treatment_duration": treatment_duration,
        "treatment_response": treatment_response,
        "crp_trend": crp_trend,
        "pct_trend": pct_trend,
    }

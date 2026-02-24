"""Tests for clinical_logic — MOST IMPORTANT test file.

Tests all CURB65 boundary values, contradiction rules, antibiotic selection
decision tree, and discharge criteria. These are safety-critical tests.
"""

import pytest

from cap_agent.agent.clinical_logic import (
    compute_curb65,
    compute_curb65_data_gaps,
    compute_crp_trend,
    compute_pct_trend,
    detect_contradictions,
    detect_cr10,
    select_antibiotic,
    plan_investigations,
    compute_monitoring_plan,
    assess_treatment_extension,
    assess_treatment_response,
    classify_micro_results,
    classify_penicillin_allergy,
    assess_iv_to_oral_stability,
    generate_iv_to_oral_recommendation,
    _extract_prescribed_drugs,
)


# ===========================================================================
# CURB65 Scoring
# ===========================================================================

class TestCURB65:
    """Test CURB65 computation with boundary values."""

    def test_all_normal_score_0(self):
        """Score=0, all normal → low severity."""
        result = compute_curb65({
            "confusion": False,
            "urea": 5.0,
            "respiratory_rate": 20,
            "systolic_bp": 120,
            "diastolic_bp": 80,
            "age": 50,
        })
        assert result["curb65"] == 0
        assert result["severity_tier"] == "low"

    def test_synthetic_case_score_2(self):
        """Synthetic case: U=1 (urea 8.2>7), 65=1 (age 72>=65) → moderate."""
        result = compute_curb65({
            "confusion": False,
            "urea": 8.2,
            "respiratory_rate": 22,
            "systolic_bp": 105,
            "diastolic_bp": 65,
            "age": 72,
        })
        assert result["c"] == 0
        assert result["u"] == 1
        assert result["r"] == 0
        assert result["b"] == 0
        assert result["age_65"] == 1
        assert result["curb65"] == 2
        assert result["severity_tier"] == "moderate"

    def test_all_abnormal_score_5(self):
        """Score=5, all abnormal → high severity."""
        result = compute_curb65({
            "confusion": True,
            "urea": 15.0,
            "respiratory_rate": 35,
            "systolic_bp": 80,
            "diastolic_bp": 50,
            "age": 75,
        })
        assert result["curb65"] == 5
        assert result["severity_tier"] == "high"

    # --- Urea boundary: must be STRICTLY > 7, not >= 7 ---

    def test_urea_exactly_7_gives_u0(self):
        """Urea exactly 7.0 → U=0 (must be >7, not >=7)."""
        result = compute_curb65({
            "confusion": False, "urea": 7.0, "respiratory_rate": 20,
            "systolic_bp": 120, "diastolic_bp": 80, "age": 50,
        })
        assert result["u"] == 0

    def test_urea_7_01_gives_u1(self):
        """Urea 7.01 → U=1."""
        result = compute_curb65({
            "confusion": False, "urea": 7.01, "respiratory_rate": 20,
            "systolic_bp": 120, "diastolic_bp": 80, "age": 50,
        })
        assert result["u"] == 1

    # --- Respiratory rate boundary: >= 30 ---

    def test_rr_29_gives_r0(self):
        """RR 29 → R=0 (must be >=30)."""
        result = compute_curb65({
            "confusion": False, "urea": 5.0, "respiratory_rate": 29,
            "systolic_bp": 120, "diastolic_bp": 80, "age": 50,
        })
        assert result["r"] == 0

    def test_rr_30_gives_r1(self):
        """RR 30 → R=1."""
        result = compute_curb65({
            "confusion": False, "urea": 5.0, "respiratory_rate": 30,
            "systolic_bp": 120, "diastolic_bp": 80, "age": 50,
        })
        assert result["r"] == 1

    # --- Blood pressure boundaries ---

    def test_sbp_90_gives_b0(self):
        """SBP 90 → B=0 (must be <90, not <=90)."""
        result = compute_curb65({
            "confusion": False, "urea": 5.0, "respiratory_rate": 20,
            "systolic_bp": 90, "diastolic_bp": 80, "age": 50,
        })
        assert result["b"] == 0

    def test_sbp_89_gives_b1(self):
        """SBP 89 → B=1."""
        result = compute_curb65({
            "confusion": False, "urea": 5.0, "respiratory_rate": 20,
            "systolic_bp": 89, "diastolic_bp": 80, "age": 50,
        })
        assert result["b"] == 1

    def test_dbp_60_gives_b1(self):
        """DBP 60 → B=1 (<=60)."""
        result = compute_curb65({
            "confusion": False, "urea": 5.0, "respiratory_rate": 20,
            "systolic_bp": 120, "diastolic_bp": 60, "age": 50,
        })
        assert result["b"] == 1

    def test_dbp_61_gives_b0(self):
        """DBP 61 → B=0."""
        result = compute_curb65({
            "confusion": False, "urea": 5.0, "respiratory_rate": 20,
            "systolic_bp": 120, "diastolic_bp": 61, "age": 50,
        })
        assert result["b"] == 0

    # --- Age boundary: >= 65 ---

    def test_age_64_gives_0(self):
        """Age 64 → 65=0."""
        result = compute_curb65({
            "confusion": False, "urea": 5.0, "respiratory_rate": 20,
            "systolic_bp": 120, "diastolic_bp": 80, "age": 64,
        })
        assert result["age_65"] == 0

    def test_age_65_gives_1(self):
        """Age 65 → 65=1."""
        result = compute_curb65({
            "confusion": False, "urea": 5.0, "respiratory_rate": 20,
            "systolic_bp": 120, "diastolic_bp": 80, "age": 65,
        })
        assert result["age_65"] == 1

    # --- Missing variables ---

    def test_missing_urea_gives_crb65_fallback(self):
        """Missing urea → curb65=None, falls back to CRB65. CRB65=1 → moderate."""
        result = compute_curb65({
            "confusion": False, "respiratory_rate": 20,
            "systolic_bp": 120, "diastolic_bp": 80, "age": 72,
        })
        assert result["curb65"] is None
        assert result["crb65"] == 1  # only age_65=1
        assert result["severity_tier"] == "moderate"
        assert "urea" in result["missing_variables"]

    def test_missing_confusion_defaults_to_0(self):
        """Missing confusion → defaults to 0, added to missing list."""
        result = compute_curb65({
            "urea": 8.2, "respiratory_rate": 22,
            "systolic_bp": 105, "diastolic_bp": 65, "age": 72,
        })
        assert result["c"] == 0
        assert "confusion/AMT score" in result["missing_variables"]

    def test_empty_variables(self):
        """All missing → score 0, low severity."""
        result = compute_curb65({})
        assert result["curb65"] is None
        assert result["crb65"] == 0
        assert result["severity_tier"] == "low"
        assert len(result["missing_variables"]) == 5

    # --- Severity tiers ---

    def test_score_1_is_low(self):
        result = compute_curb65({
            "confusion": False, "urea": 5.0, "respiratory_rate": 20,
            "systolic_bp": 120, "diastolic_bp": 80, "age": 72,
        })
        assert result["curb65"] == 1
        assert result["severity_tier"] == "low"

    def test_score_3_is_high(self):
        result = compute_curb65({
            "confusion": True, "urea": 10.0, "respiratory_rate": 20,
            "systolic_bp": 120, "diastolic_bp": 80, "age": 72,
        })
        assert result["curb65"] == 3
        assert result["severity_tier"] == "high"


class TestCURB65DataGaps:
    def test_missing_confusion_warning(self):
        score = {"curb65": 2, "crb65": 1, "missing_variables": ["confusion/AMT score"]}
        gaps = compute_curb65_data_gaps(score, crb65=1)
        assert len(gaps) == 1
        assert "AMT not documented" in gaps[0]

    def test_no_missing_no_gaps(self):
        score = {"curb65": 2, "crb65": 1, "missing_variables": []}
        gaps = compute_curb65_data_gaps(score, crb65=1)
        assert len(gaps) == 0


# ===========================================================================
# Contradiction Detection
# ===========================================================================

class TestContradictionDetection:
    """Test the 6 implemented contradiction rules."""

    def test_concordant_case_zero_contradictions(
        self, concordant_cxr, concordant_exam, concordant_labs
    ):
        """Synthetic concordant case should have 0 contradictions."""
        result = detect_contradictions(
            cxr=concordant_cxr,
            exam=concordant_exam,
            labs=concordant_labs,
            demographics={"comorbidities": []},
            curb65={"severity_tier": "moderate", "curb65": 2},
            case_data={"social_history": {"immunosuppression": False}},
        )
        assert len(result) == 0

    def test_cr1_cxr_negative_focal_crackles(self):
        """CR-1: CXR negative + focal crackles → fires."""
        cxr = {"consolidation": {"present": False}, "pleural_effusion": {"present": False}}
        exam = {"respiratory_exam": {"crackles": True, "crackles_location": "left base", "bronchial_breathing": False}}
        result = detect_contradictions(
            cxr=cxr, exam=exam, labs={}, demographics={"comorbidities": []},
            curb65={"severity_tier": "moderate"}, case_data={},
        )
        cr1_rules = [c for c in result if c["rule_id"] == "CR-1"]
        assert len(cr1_rules) == 1
        assert cr1_rules[0]["severity"] == "high"
        assert cr1_rules[0]["resolution_strategy"] == "A"
        assert cr1_rules[0]["confidence"] == "moderate"  # single finding only

    def test_cr2_cxr_negative_crp_high_clinical(self):
        """CR-2: CXR negative + CRP>100 + clinical features → fires."""
        cxr = {"consolidation": {"present": False}, "pleural_effusion": {"present": False}}
        exam = {"respiratory_exam": {"crackles": True, "bronchial_breathing": False}}
        labs = {"crp": {"value": 150}}
        result = detect_contradictions(
            cxr=cxr, exam=exam, labs=labs, demographics={"comorbidities": []},
            curb65={"severity_tier": "moderate"}, case_data={},
        )
        cr2_rules = [c for c in result if c["rule_id"] == "CR-2"]
        assert len(cr2_rules) == 1
        assert cr2_rules[0]["resolution_strategy"] == "B"
        assert cr2_rules[0]["confidence"] == "moderate"  # CRP 150 ≤ 200

    def test_cr2_does_not_fire_crp_below_100(self):
        """CR-2 should NOT fire when CRP <= 100."""
        cxr = {"consolidation": {"present": False}, "pleural_effusion": {"present": False}}
        exam = {"respiratory_exam": {"crackles": True, "bronchial_breathing": False}}
        labs = {"crp": {"value": 90}}
        result = detect_contradictions(
            cxr=cxr, exam=exam, labs=labs, demographics={"comorbidities": []},
            curb65={"severity_tier": "moderate"}, case_data={},
        )
        cr2_rules = [c for c in result if c["rule_id"] == "CR-2"]
        assert len(cr2_rules) == 0

    def test_cr3_cxr_consolidation_low_crp_no_signs(self):
        """CR-3: CXR consolidation + CRP<20 + no clinical signs → fires."""
        cxr = {"consolidation": {"present": True, "location": "RLL"}, "pleural_effusion": {"present": False}}
        exam = {"respiratory_exam": {"crackles": False, "bronchial_breathing": False}}
        labs = {"crp": {"value": 10}}
        result = detect_contradictions(
            cxr=cxr, exam=exam, labs=labs, demographics={"comorbidities": []},
            curb65={"severity_tier": "moderate"}, case_data={},
        )
        cr3_rules = [c for c in result if c["rule_id"] == "CR-3"]
        assert len(cr3_rules) == 1
        assert cr3_rules[0]["severity"] == "moderate"
        assert cr3_rules[0]["confidence"] == "moderate"  # CRP 10 is borderline (10-20)

    def test_cr4_low_severity_immunosuppression(self):
        """CR-4: CURB65 low + immunosuppression → fires."""
        cxr = {"consolidation": {"present": True, "location": "RLL"}, "pleural_effusion": {"present": False}}
        exam = {"respiratory_exam": {"crackles": True, "bronchial_breathing": False}}
        result = detect_contradictions(
            cxr=cxr, exam=exam, labs={},
            demographics={"comorbidities": []},
            curb65={"severity_tier": "low", "curb65": 1},
            case_data={"social_history": {"immunosuppression": True}},
        )
        cr4_rules = [c for c in result if c["rule_id"] == "CR-4"]
        assert len(cr4_rules) == 1
        assert cr4_rules[0]["resolution_strategy"] == "D"
        assert cr4_rules[0]["confidence"] == "moderate"  # single trigger

    def test_cr4_does_not_fire_moderate_severity(self):
        """CR-4 should NOT fire for moderate severity even with immunosuppression."""
        cxr = {"consolidation": {"present": True, "location": "RLL"}, "pleural_effusion": {"present": False}}
        exam = {"respiratory_exam": {"crackles": True, "bronchial_breathing": False}}
        result = detect_contradictions(
            cxr=cxr, exam=exam, labs={},
            demographics={"comorbidities": []},
            curb65={"severity_tier": "moderate", "curb65": 2},
            case_data={"social_history": {"immunosuppression": True}},
        )
        cr4_rules = [c for c in result if c["rule_id"] == "CR-4"]
        assert len(cr4_rules) == 0

    def test_cr5_bilateral_cxr_unilateral_exam(self):
        """CR-5: Bilateral CXR + unilateral exam → fires."""
        cxr = {"consolidation": {"present": True, "location": "bilateral"}, "pleural_effusion": {"present": False}}
        exam = {"respiratory_exam": {"crackles": True, "crackles_location": "right lower zone", "bronchial_breathing": False}}
        result = detect_contradictions(
            cxr=cxr, exam=exam, labs={}, demographics={"comorbidities": []},
            curb65={"severity_tier": "moderate"}, case_data={},
        )
        cr5_rules = [c for c in result if c["rule_id"] == "CR-5"]
        assert len(cr5_rules) == 1
        assert cr5_rules[0]["confidence"] == "moderate"  # laterality always moderate

    def test_cr6_effusion_no_consolidation(self):
        """CR-6: Effusion + no consolidation → fires."""
        cxr = {"consolidation": {"present": False}, "pleural_effusion": {"present": True}}
        exam = {"respiratory_exam": {"crackles": False, "bronchial_breathing": False}}
        result = detect_contradictions(
            cxr=cxr, exam=exam, labs={}, demographics={"comorbidities": []},
            curb65={"severity_tier": "moderate"}, case_data={},
        )
        cr6_rules = [c for c in result if c["rule_id"] == "CR-6"]
        assert len(cr6_rules) == 1
        assert cr6_rules[0]["severity"] == "moderate"
        assert cr6_rules[0]["confidence"] == "moderate"  # many differentials

    # --- Variable confidence tests ---

    def test_cr1_high_confidence_both_findings(self):
        """CR-1: Both crackles AND bronchial breathing → high confidence."""
        cxr = {"consolidation": {"present": False}, "pleural_effusion": {"present": False}}
        exam = {"respiratory_exam": {
            "crackles": True, "crackles_location": "right base",
            "bronchial_breathing": True, "bronchial_breathing_location": "right base",
        }}
        result = detect_contradictions(
            cxr=cxr, exam=exam, labs={}, demographics={"comorbidities": []},
            curb65={"severity_tier": "moderate"}, case_data={},
        )
        cr1 = [c for c in result if c["rule_id"] == "CR-1"]
        assert len(cr1) == 1
        assert cr1[0]["confidence"] == "high"

    def test_cr1_moderate_confidence_single_finding(self):
        """CR-1: Only crackles (no bronchial breathing) → moderate confidence."""
        cxr = {"consolidation": {"present": False}, "pleural_effusion": {"present": False}}
        exam = {"respiratory_exam": {"crackles": True, "crackles_location": "left base", "bronchial_breathing": False}}
        result = detect_contradictions(
            cxr=cxr, exam=exam, labs={}, demographics={"comorbidities": []},
            curb65={"severity_tier": "moderate"}, case_data={},
        )
        cr1 = [c for c in result if c["rule_id"] == "CR-1"]
        assert len(cr1) == 1
        assert cr1[0]["confidence"] == "moderate"

    def test_cr2_high_confidence_very_high_crp(self):
        """CR-2: CRP > 200 → high confidence."""
        cxr = {"consolidation": {"present": False}, "pleural_effusion": {"present": False}}
        exam = {"respiratory_exam": {"crackles": True, "bronchial_breathing": False}}
        labs = {"crp": {"value": 250}}
        result = detect_contradictions(
            cxr=cxr, exam=exam, labs=labs, demographics={"comorbidities": []},
            curb65={"severity_tier": "moderate"}, case_data={},
        )
        cr2 = [c for c in result if c["rule_id"] == "CR-2"]
        assert len(cr2) == 1
        assert cr2[0]["confidence"] == "high"

    def test_cr2_moderate_confidence_borderline_crp(self):
        """CR-2: CRP 101 (just over 100, ≤ 200) → moderate confidence."""
        cxr = {"consolidation": {"present": False}, "pleural_effusion": {"present": False}}
        exam = {"respiratory_exam": {"crackles": True, "bronchial_breathing": False}}
        labs = {"crp": {"value": 101}}
        result = detect_contradictions(
            cxr=cxr, exam=exam, labs=labs, demographics={"comorbidities": []},
            curb65={"severity_tier": "moderate"}, case_data={},
        )
        cr2 = [c for c in result if c["rule_id"] == "CR-2"]
        assert len(cr2) == 1
        assert cr2[0]["confidence"] == "moderate"

    def test_cr3_high_confidence_very_low_crp(self):
        """CR-3: CRP < 10 → high confidence false-positive CXR."""
        cxr = {"consolidation": {"present": True, "location": "RLL"}, "pleural_effusion": {"present": False}}
        exam = {"respiratory_exam": {"crackles": False, "bronchial_breathing": False}}
        labs = {"crp": {"value": 5}}
        result = detect_contradictions(
            cxr=cxr, exam=exam, labs=labs, demographics={"comorbidities": []},
            curb65={"severity_tier": "moderate"}, case_data={},
        )
        cr3 = [c for c in result if c["rule_id"] == "CR-3"]
        assert len(cr3) == 1
        assert cr3[0]["confidence"] == "high"

    def test_cr4_high_confidence_multiple_triggers(self):
        """CR-4: 2+ triggers (immunosuppression + hypoxia) → high confidence."""
        cxr = {"consolidation": {"present": True, "location": "RLL"}, "pleural_effusion": {"present": False}}
        exam = {
            "respiratory_exam": {"crackles": True, "bronchial_breathing": False},
            "observations": {"spo2": 88},
        }
        result = detect_contradictions(
            cxr=cxr, exam=exam, labs={},
            demographics={"comorbidities": []},
            curb65={"severity_tier": "low", "curb65": 1},
            case_data={"social_history": {"immunosuppression": True}},
        )
        cr4 = [c for c in result if c["rule_id"] == "CR-4"]
        assert len(cr4) == 1
        assert cr4[0]["confidence"] == "high"

    def test_cr4_moderate_confidence_single_trigger(self):
        """CR-4: Only 1 trigger (immunosuppression alone) → moderate confidence."""
        cxr = {"consolidation": {"present": True, "location": "RLL"}, "pleural_effusion": {"present": False}}
        exam = {"respiratory_exam": {"crackles": True, "bronchial_breathing": False}}
        result = detect_contradictions(
            cxr=cxr, exam=exam, labs={},
            demographics={"comorbidities": []},
            curb65={"severity_tier": "low", "curb65": 1},
            case_data={"social_history": {"immunosuppression": True}},
        )
        cr4 = [c for c in result if c["rule_id"] == "CR-4"]
        assert len(cr4) == 1
        assert cr4[0]["confidence"] == "moderate"


# ===========================================================================
# Antibiotic Selection
# ===========================================================================

class TestAntibioticSelection:
    """Test evidence-based antibiotic decision tree."""

    def test_low_no_allergy(self):
        result = select_antibiotic("low")
        assert "Amoxicillin 500mg TDS PO" in result["first_line"]
        assert result["dose_route"] == "PO"

    def test_low_penicillin_allergy(self):
        result = select_antibiotic("low", allergies=[{"drug": "Penicillin"}])
        assert "Doxycycline" in result["first_line"]

    def test_moderate_no_allergy(self):
        """Moderate severity → dual therapy: amoxicillin + clarithromycin (D1/D2)."""
        result = select_antibiotic("moderate")
        first = result["first_line"].lower()
        assert "amoxicillin" in first
        assert "clarithromycin" in first
        assert result["atypical_cover"] is None  # dual therapy is default now

    def test_moderate_penicillin_allergy(self):
        """Moderate + pen allergy → doxycycline only (D3)."""
        result = select_antibiotic("moderate", allergies=[{"drug": "penicillin"}])
        assert "Doxycycline" in result["first_line"]
        assert "Clarithromycin" not in result["first_line"]

    def test_high_no_allergy(self):
        result = select_antibiotic("high")
        assert "Co-amoxiclav" in result["first_line"]
        assert "Clarithromycin" in result["first_line"]
        assert result["dose_route"] == "IV"

    def test_high_penicillin_allergy_anaphylaxis(self):
        """High + anaphylaxis → levofloxacin (absolute contraindication to beta-lactams)."""
        result = select_antibiotic("high", allergies=[{"drug": "penicillin", "reaction_type": "anaphylaxis", "severity": "severe"}])
        assert "Levofloxacin" in result["first_line"]
        assert "MHRA" in result["first_line"]
        assert any("MHRA" in note for note in result["stewardship_notes"])

    def test_high_penicillin_allergy_true_allergy(self):
        """High + true allergy (non-SCAR) → cephalosporin + clarithromycin (E2)."""
        result = select_antibiotic("high", allergies=[{"drug": "penicillin", "reaction_type": "urticaria", "severity": "moderate"}])
        first = result["first_line"]
        assert "Cefuroxime" in first or "Ceftriaxone" in first
        assert "Clarithromycin" in first or "Erythromycin" in first
        assert "Levofloxacin" not in first

    def test_high_penicillin_allergy_scar(self):
        """High + SCAR (SJS/TEN/DRESS) → levofloxacin (absolute contraindication)."""
        result = select_antibiotic("high", allergies=[{"drug": "penicillin", "reaction_type": "Stevens-Johnson syndrome", "severity": "severe"}])
        assert "Levofloxacin" in result["first_line"]

    def test_high_penicillin_allergy_intolerance(self):
        """High + intolerance (GI upset) → standard co-amoxiclav (safe to use)."""
        result = select_antibiotic("high", allergies=[{"drug": "penicillin", "reaction_type": "GI upset", "severity": "mild"}])
        first = result["first_line"]
        assert "Co-amoxiclav" in first
        assert "Clarithromycin" in first
        assert "Levofloxacin" not in first

    def test_high_penicillin_allergy_unknown(self):
        """High + unknown allergy → conservative: levofloxacin."""
        result = select_antibiotic("high", allergies=[{"drug": "penicillin", "reaction_type": "", "severity": ""}])
        assert "Levofloxacin" in result["first_line"]

    def test_oral_intolerance_overrides_po(self):
        result = select_antibiotic("low", oral_tolerance=False)
        assert "IV" in result["dose_route"]
        assert "oral intolerance" in result["first_line"]

    def test_pregnancy_erythromycin_substitution(self):
        """Pregnancy → clarithromycin replaced with erythromycin in first_line (dual therapy)."""
        result = select_antibiotic("moderate", pregnancy=True)
        assert result["allergy_adjustment"] is not None
        assert "erythromycin" in result["allergy_adjustment"].lower()
        # With dual therapy default, erythromycin should be in first_line
        first = result["first_line"].lower()
        assert "erythromycin" in first
        assert "clarithromycin" not in first

    def test_pregnancy_with_penicillin_allergy(self):
        """Pregnancy + penicillin allergy → BOTH warnings present (not overwritten)."""
        result = select_antibiotic("low", allergies=[{"drug": "penicillin"}], pregnancy=True)
        assert result["allergy_adjustment"] is not None
        adj = result["allergy_adjustment"].lower()
        # Should have both erythromycin substitution AND contraindication warning
        assert "contraindicated" in adj
        assert "doxycycline" in adj

    def test_pregnancy_moderate_pen_allergy_doxycycline_flagged(self):
        """Pregnancy + moderate + pen allergy → doxycycline flagged as contraindicated."""
        result = select_antibiotic("moderate", allergies=[{"drug": "penicillin"}], pregnancy=True)
        assert result["allergy_adjustment"] is not None
        adj = result["allergy_adjustment"].lower()
        assert "contraindicated" in adj
        assert "doxycycline" in adj

    def test_pregnancy_high_no_allergy_substitutes_clarithromycin(self):
        """Pregnancy + high + no allergy → clarithromycin in first_line replaced with erythromycin."""
        result = select_antibiotic("high", pregnancy=True)
        first = result["first_line"].lower()
        assert "erythromycin" in first
        assert "clarithromycin" not in first
        assert "QDS" in result["first_line"] or "qds" in result["first_line"].lower()

    def test_egfr_below_30_renal_adjustment(self):
        result = select_antibiotic("moderate", egfr=25)
        assert result["renal_adjustment"] is not None
        assert "dose adjustment" in result["renal_adjustment"].lower()

    def test_egfr_below_60_monitoring(self):
        result = select_antibiotic("moderate", egfr=55)
        assert result["renal_adjustment"] is not None
        assert "monitor" in result["renal_adjustment"].lower()

    def test_egfr_above_60_no_adjustment(self):
        result = select_antibiotic("moderate", egfr=90)
        assert result["renal_adjustment"] is None

    def test_travel_history_atypical_cover(self):
        """Low severity + travel → SWITCH to clarithromycin/doxycycline."""
        result = select_antibiotic("low", travel_history=["Southeast Asia"])
        # Low severity: switch to alternative, not dual therapy
        assert result["atypical_cover"] is None
        assert "clarithromycin" in result["first_line"].lower() or "doxycycline" in result["first_line"].lower()
        assert "amoxicillin" not in result["first_line"].lower()

    def test_stewardship_always_includes_review_notes(self):
        result = select_antibiotic("moderate")
        notes = result["stewardship_notes"]
        assert any("48h" in n for n in notes)
        assert any("5-day" in n for n in notes)


# ===========================================================================
# Investigation Planning
# ===========================================================================

class TestInvestigationPlanning:
    def test_moderate_with_sepsis_markers(self):
        result = plan_investigations(
            severity="moderate",
            observations={"heart_rate": 110, "temperature": 38.5, "systolic_bp": 95},
            lab_values={"lactate": {"value": 1.0}},
        )
        assert result["blood_cultures"]["recommended"] is True
        assert result["sputum_culture"]["recommended"] is True
        assert result["pneumococcal_antigen"]["recommended"] is True

    def test_low_no_sepsis_markers(self):
        result = plan_investigations(
            severity="low",
            observations={"heart_rate": 80, "temperature": 37.5, "systolic_bp": 120},
            lab_values={},
        )
        assert result["blood_cultures"]["recommended"] is False

    def test_sepsis_hr_91_triggers_blood_cultures(self):
        """HR 91 (> 90) is a sepsis marker in plan_investigations (Bone 1992 SIRS)."""
        result = plan_investigations(
            severity="moderate",
            observations={"heart_rate": 91},
            lab_values={},
        )
        assert result["blood_cultures"]["recommended"] is True

    def test_sepsis_hr_90_does_not_trigger(self):
        """HR 90 (not > 90) is NOT a sepsis marker."""
        result = plan_investigations(
            severity="moderate",
            observations={"heart_rate": 90},
            lab_values={},
        )
        assert result["blood_cultures"]["recommended"] is False

    def test_legionella_with_travel(self):
        result = plan_investigations(
            severity="moderate",
            observations={},
            lab_values={},
            travel_history=["Europe"],
        )
        assert result["legionella_antigen"]["recommended"] is True

    def test_legionella_without_travel(self):
        result = plan_investigations(
            severity="moderate",
            observations={},
            lab_values={},
        )
        assert result["legionella_antigen"]["recommended"] is False


# ===========================================================================
# Monitoring & Discharge
# ===========================================================================

class TestMonitoringPlan:
    def test_all_normal_discharge_met(self):
        result = compute_monitoring_plan(
            severity="low",
            observations={
                "temperature": 36.8,
                "respiratory_rate": 18,
                "heart_rate": 75,
                "systolic_bp": 120,
                "spo2": 97,
            },
            confusion_status={"present": False},
        )
        assert result["discharge_criteria_met"] is True
        assert len(result["discharge_criteria_details"]["not_met"]) == 0

    def test_multiple_abnormal_discharge_not_met(self):
        result = compute_monitoring_plan(
            severity="moderate",
            observations={
                "temperature": 38.5,  # abnormal
                "respiratory_rate": 28,  # abnormal
                "heart_rate": 110,  # abnormal
                "systolic_bp": 85,  # abnormal
                "spo2": 88,  # abnormal
            },
            confusion_status={"present": True},  # abnormal
        )
        assert result["discharge_criteria_met"] is False
        not_met = result["discharge_criteria_details"]["not_met"]
        assert len(not_met) >= 2

    def test_single_abnormal_still_meets_discharge(self):
        """Discharge OK if fewer than 2 criteria not met."""
        result = compute_monitoring_plan(
            severity="low",
            observations={
                "temperature": 38.0,  # slightly abnormal (> 37.8)
                "respiratory_rate": 18,
                "heart_rate": 75,
                "systolic_bp": 120,
                "spo2": 97,
            },
            confusion_status={"present": False},
        )
        assert result["discharge_criteria_met"] is True
        assert len(result["discharge_criteria_details"]["not_met"]) == 1

    def test_high_severity_next_review(self):
        result = compute_monitoring_plan(
            severity="high", observations={}, confusion_status={},
        )
        assert "4 hours" in result["next_review"]

    def test_moderate_severity_next_review(self):
        result = compute_monitoring_plan(
            severity="moderate", observations={}, confusion_status={},
        )
        assert "24h" in result["next_review"]

    def test_low_severity_next_review(self):
        result = compute_monitoring_plan(
            severity="low", observations={}, confusion_status={},
        )
        assert "discharge" in result["next_review"].lower()

    def test_high_severity_cxr_repeat(self):
        result = compute_monitoring_plan(
            severity="high", observations={}, confusion_status={},
        )
        assert "72h" in result["cxr_follow_up"] or "3 days" in result["cxr_follow_up"]

    def test_crp_timing_always_present(self):
        result = compute_monitoring_plan(
            severity="low", observations={}, confusion_status={},
        )
        assert "3-4 days" in result["crp_repeat_timing"]
        assert "procalcitonin" in result["crp_repeat_timing"].lower() or "PCT" in result["crp_repeat_timing"]

    def test_treatment_duration_included(self):
        """Monitoring plan should include treatment duration assessment."""
        result = compute_monitoring_plan(
            severity="low", observations={}, confusion_status={},
        )
        assert "treatment_duration" in result
        assert "extend_recommended" in result["treatment_duration"]

    def test_discharge_note_text_updated(self):
        """Discharge note should say 'fewer than 2' not 'none of 7'."""
        result = compute_monitoring_plan(
            severity="low", observations={}, confusion_status={},
        )
        note = result["discharge_criteria_details"]["note"]
        assert "fewer than 2" in note
        assert "past 24 hours" in note

    def test_eating_independently_false_counts_as_abnormal(self):
        """eating_independently=False should count as 1 abnormal criterion."""
        result = compute_monitoring_plan(
            severity="low", observations={}, confusion_status={},
            demographics={"eating_independently": False},
        )
        assert "eating_independently" in result["discharge_criteria_details"]["not_met"]
        # Only 1 abnormal → discharge still met (need ≥2 to fail)
        assert result["discharge_criteria_met"] is True

    def test_eating_independently_false_plus_fever_fails_discharge(self):
        """eating_independently=False + fever → 2 abnormal → discharge NOT met."""
        result = compute_monitoring_plan(
            severity="low",
            observations={"temperature": 38.5},
            confusion_status={},
            demographics={"eating_independently": False},
        )
        not_met = result["discharge_criteria_details"]["not_met"]
        assert "eating_independently" in not_met
        assert "temperature_normal" in not_met
        assert result["discharge_criteria_met"] is False

    def test_eating_independently_defaults_true_no_demographics(self):
        """When demographics is None, eating_independently should default True."""
        result = compute_monitoring_plan(
            severity="low", observations={}, confusion_status={},
        )
        criteria = result["discharge_criteria_details"]["criteria_checked"]
        assert criteria["eating_independently"] is True

    def test_eating_independently_defaults_true_when_missing(self):
        """When demographics dict exists but field is missing, should default True."""
        result = compute_monitoring_plan(
            severity="low", observations={}, confusion_status={},
            demographics={"age": 72},
        )
        criteria = result["discharge_criteria_details"]["criteria_checked"]
        assert criteria["eating_independently"] is True


# ===========================================================================
# CXR Follow-Up Risk Factor Logic# ===========================================================================

class TestCXRFollowUp:
    """Test CXR follow-up varies by risk factors."""

    def test_no_risk_factors_no_routine_cxr(self):
        """Young non-smoker → CXR not routinely indicated."""
        result = compute_monitoring_plan(
            severity="low", observations={}, confusion_status={},
            demographics={"age": 40, "smoking_status": "never"},
        )
        assert "not routinely indicated" in result["cxr_follow_up"].lower()

    def test_age_over_50_gets_6_week_cxr(self):
        """Age > 50 → recommend 6-week CXR."""
        result = compute_monitoring_plan(
            severity="low", observations={}, confusion_status={},
            demographics={"age": 55, "smoking_status": "never"},
        )
        assert "6 weeks" in result["cxr_follow_up"]
        assert "age 55" in result["cxr_follow_up"]

    def test_current_smoker_gets_6_week_cxr(self):
        """Current smoker → recommend 6-week CXR."""
        result = compute_monitoring_plan(
            severity="low", observations={}, confusion_status={},
            demographics={"age": 35, "smoking_status": "current"},
        )
        assert "6 weeks" in result["cxr_follow_up"]
        assert "smoking" in result["cxr_follow_up"]

    def test_former_smoker_gets_6_week_cxr(self):
        """Former smoker → recommend 6-week CXR."""
        result = compute_monitoring_plan(
            severity="low", observations={}, confusion_status={},
            demographics={"age": 35, "smoking_status": "former"},
        )
        assert "6 weeks" in result["cxr_follow_up"]

    def test_high_severity_always_72h_cxr(self):
        """High severity always gets 72h (3 days) repeat CXR."""
        result = compute_monitoring_plan(
            severity="high", observations={}, confusion_status={},
            demographics={"age": 35, "smoking_status": "never"},
        )
        assert "72h" in result["cxr_follow_up"] or "3 days" in result["cxr_follow_up"]

    def test_high_severity_with_risk_factors(self):
        """High severity + risk factors → 72h + 6 weeks."""
        result = compute_monitoring_plan(
            severity="high", observations={}, confusion_status={},
            demographics={"age": 72, "smoking_status": "former"},
        )
        assert "72h" in result["cxr_follow_up"] or "3 days" in result["cxr_follow_up"]
        assert "6 weeks" in result["cxr_follow_up"]

    def test_no_demographics_defaults_to_not_routine(self):
        """No demographics → CXR not routinely indicated."""
        result = compute_monitoring_plan(
            severity="low", observations={}, confusion_status={},
        )
        assert "not routinely indicated" in result["cxr_follow_up"].lower()


# ===========================================================================
# Levofloxacin Dosing & Co-amoxiclav PO# ===========================================================================

class TestAntibioticDosing:
    """Test specific dosing changes aligned with evidence base."""

    def test_levofloxacin_is_bd_not_od(self):
        """Levofloxacin must be BD (twice daily) per evidence base."""
        result = select_antibiotic("high", allergies=[{"drug": "penicillin"}])
        assert "BD" in result["first_line"]
        assert "OD" not in result["first_line"]

    def test_levofloxacin_includes_po_iv_option(self):
        """Levofloxacin allows PO or IV per evidence base."""
        result = select_antibiotic("high", allergies=[{"drug": "penicillin"}])
        assert "PO/IV" in result["first_line"] or ("PO" in result["first_line"] and "IV" in result["first_line"])

    def test_co_amoxiclav_includes_po_option(self):
        """High-severity co-amoxiclav should include PO option."""
        result = select_antibiotic("high")
        assert "PO" in result["first_line"]
        assert "IV" in result["first_line"]
        assert "Co-amoxiclav" in result["first_line"]

    def test_low_pen_allergy_has_three_alternatives(self):
        """Low severity + pen allergy → doxycycline, clarithromycin, erythromycin."""
        result = select_antibiotic("low", allergies=[{"drug": "Penicillin"}])
        first = result["first_line"].lower()
        assert "doxycycline" in first
        assert "clarithromycin" in first
        assert "erythromycin" in first


# ===========================================================================
# Corticosteroid Recommendation# ===========================================================================

class TestCorticosteroidRecommendation:
    """Test corticosteroid logic for high-severity CAP."""

    def test_high_severity_gets_corticosteroid(self):
        """High severity without pen allergy → recommend IV hydrocortisone (CAPE COD)."""
        result = select_antibiotic("high")
        assert result["corticosteroid_recommendation"] is not None
        rec = result["corticosteroid_recommendation"]
        assert "hydrocortisone" in rec.lower()
        assert "200mg" in rec
        assert "8-14 days" in rec
        assert "CAPE COD" in rec
        assert "CAPE COD" in rec
        assert "ICU" in rec
        # No dexamethasone
        assert "dexamethasone" not in rec.lower()

    def test_high_severity_pen_allergy_anaphylaxis_avoid(self):
        """High severity + anaphylaxis (levofloxacin) → corticosteroid AVOID (not CONTRAINDICATED)."""
        result = select_antibiotic("high", allergies=[{"drug": "penicillin", "reaction_type": "anaphylaxis", "severity": "severe"}])
        assert result["corticosteroid_recommendation"] is not None
        rec = result["corticosteroid_recommendation"]
        assert "AVOID" in rec
        assert "MHRA" in rec
        assert "CONTRAINDICATED" not in rec

    def test_high_severity_true_allergy_gets_corticosteroid(self):
        """High + true allergy (cephalosporin, no fluoroquinolone) → corticosteroid OK."""
        result = select_antibiotic("high", allergies=[{"drug": "penicillin", "reaction_type": "urticaria", "severity": "moderate"}])
        assert result["corticosteroid_recommendation"] is not None
        rec = result["corticosteroid_recommendation"]
        assert "hydrocortisone" in rec.lower()
        assert "AVOID" not in rec

    def test_low_severity_no_corticosteroid(self):
        """Low severity → no corticosteroid recommendation."""
        result = select_antibiotic("low")
        assert result["corticosteroid_recommendation"] is None

    def test_moderate_severity_no_corticosteroid(self):
        """Moderate severity → no corticosteroid recommendation."""
        result = select_antibiotic("moderate")
        assert result["corticosteroid_recommendation"] is None

    def test_fluoroquinolone_corticosteroid_warning_in_stewardship(self):
        """High + pen allergy → MHRA corticosteroid warning in stewardship notes."""
        result = select_antibiotic("high", allergies=[{"drug": "penicillin"}])
        notes = " ".join(result["stewardship_notes"])
        assert "corticosteroid" in notes.lower()
        assert "fluoroquinolone" in notes.lower()


# ===========================================================================
# Antibiotic Timing — in stewardship notes
# ===========================================================================

class TestAntibioticTiming:
    def test_4_hour_timing_in_stewardship(self):
        """Stewardship notes should include 4-hour timing requirement."""
        result = select_antibiotic("moderate")
        assert any("4 hours" in n for n in result["stewardship_notes"])

    def test_blood_cultures_before_antibiotics(self):
        """Stewardship notes should mention blood cultures before antibiotics."""
        result = select_antibiotic("moderate")
        assert any("blood cultures" in n.lower() and "before" in n.lower()
                    for n in result["stewardship_notes"])


# ===========================================================================
# Expanded CR-4 Triggers# ===========================================================================

class TestCR4ExpandedTriggers:
    """Test new CR-4 override triggers: hypoxia, effusion, comorbidities, pregnancy."""

    def _base_args(self, **overrides):
        args = dict(
            cxr={"consolidation": {"present": True, "location": "RLL"}, "pleural_effusion": {"present": False}},
            exam={"respiratory_exam": {"crackles": True, "bronchial_breathing": False}, "observations": {}},
            labs={},
            demographics={"comorbidities": []},
            curb65={"severity_tier": "low", "curb65": 1},
            case_data={"social_history": {"immunosuppression": False}},
        )
        args.update(overrides)
        return args

    def test_cr4_hypoxia_trigger(self):
        """CR-4: Low CURB65 + SpO2 < 90 → fires."""
        args = self._base_args(
            exam={"respiratory_exam": {"crackles": True, "bronchial_breathing": False},
                  "observations": {"spo2": 88}},
        )
        result = detect_contradictions(**args)
        cr4 = [c for c in result if c["rule_id"] == "CR-4"]
        assert len(cr4) == 1
        assert "hypoxia" in cr4[0]["evidence_against"]
        assert cr4[0]["confidence"] == "moderate"  # single trigger

    def test_cr4_hypoxia_92_does_not_fire(self):
        """CR-4: SpO2 exactly 92 → does NOT fire hypoxia trigger (threshold now <90)."""
        args = self._base_args(
            exam={"respiratory_exam": {"crackles": True, "bronchial_breathing": False},
                  "observations": {"spo2": 92}},
        )
        result = detect_contradictions(**args)
        cr4 = [c for c in result if c["rule_id"] == "CR-4"]
        assert len(cr4) == 0

    def test_cr4_hypoxia_90_does_not_fire(self):
        """CR-4: SpO2 exactly 90 → does NOT fire (threshold is strictly <90)."""
        args = self._base_args(
            exam={"respiratory_exam": {"crackles": True, "bronchial_breathing": False},
                  "observations": {"spo2": 90}},
        )
        result = detect_contradictions(**args)
        cr4 = [c for c in result if c["rule_id"] == "CR-4"]
        assert len(cr4) == 0

    def test_cr4_hypoxia_89_fires(self):
        """CR-4: SpO2 89 → fires (89 < 90)."""
        args = self._base_args(
            exam={"respiratory_exam": {"crackles": True, "bronchial_breathing": False},
                  "observations": {"spo2": 89}},
        )
        result = detect_contradictions(**args)
        cr4 = [c for c in result if c["rule_id"] == "CR-4"]
        assert len(cr4) == 1
        assert "hypoxia" in cr4[0]["evidence_against"]
        assert cr4[0]["confidence"] == "moderate"

    def test_cr4_effusion_trigger(self):
        """CR-4: Low CURB65 + pleural effusion → fires."""
        args = self._base_args(
            cxr={"consolidation": {"present": True, "location": "RLL"},
                 "pleural_effusion": {"present": True}},
        )
        result = detect_contradictions(**args)
        cr4 = [c for c in result if c["rule_id"] == "CR-4"]
        assert len(cr4) == 1
        assert "effusion" in cr4[0]["evidence_against"]

    def test_cr4_multiple_comorbidities_trigger(self):
        """CR-4: Low CURB65 + 3+ comorbidities → fires."""
        args = self._base_args(
            demographics={"comorbidities": ["COPD", "diabetes", "CKD"]},
        )
        result = detect_contradictions(**args)
        cr4 = [c for c in result if c["rule_id"] == "CR-4"]
        assert len(cr4) == 1
        assert "comorbidities" in cr4[0]["evidence_against"]

    def test_cr4_two_comorbidities_does_not_fire(self):
        """CR-4: 2 comorbidities (non-lung, non-frail) → does NOT fire this trigger."""
        args = self._base_args(
            demographics={"comorbidities": ["diabetes", "hypertension"]},
        )
        result = detect_contradictions(**args)
        cr4 = [c for c in result if c["rule_id"] == "CR-4"]
        assert len(cr4) == 0

    def test_cr4_pregnancy_trigger(self):
        """CR-4: Low CURB65 + pregnancy → fires."""
        args = self._base_args(
            demographics={"comorbidities": [], "pregnancy": True},
        )
        result = detect_contradictions(**args)
        cr4 = [c for c in result if c["rule_id"] == "CR-4"]
        assert len(cr4) == 1
        assert "pregnancy" in cr4[0]["evidence_against"]

    def test_cr4_frailty_trigger(self):
        """CR-4: Low CURB65 + frailty in comorbidities → fires."""
        args = self._base_args(
            demographics={"comorbidities": ["frailty"]},
        )
        result = detect_contradictions(**args)
        cr4 = [c for c in result if c["rule_id"] == "CR-4"]
        assert len(cr4) == 1
        assert "frailty" in cr4[0]["evidence_against"]

    def test_cr4_frailty_from_social_history(self):
        """CR-4: Frailty from social_history field → fires."""
        args = self._base_args(
            case_data={"social_history": {"immunosuppression": False, "frailty": True}},
        )
        result = detect_contradictions(**args)
        cr4 = [c for c in result if c["rule_id"] == "CR-4"]
        assert len(cr4) == 1
        assert "frailty" in cr4[0]["evidence_against"]

    def test_cr4_copd_trigger(self):
        """CR-4: Low CURB65 + COPD → fires."""
        args = self._base_args(
            demographics={"comorbidities": ["COPD"]},
        )
        result = detect_contradictions(**args)
        cr4 = [c for c in result if c["rule_id"] == "CR-4"]
        assert len(cr4) == 1
        assert "lung disease" in cr4[0]["evidence_against"].lower() or "COPD" in cr4[0]["evidence_against"]

    def test_cr4_bronchiectasis_trigger(self):
        """CR-4: Low CURB65 + bronchiectasis → fires."""
        args = self._base_args(
            demographics={"comorbidities": ["bronchiectasis"]},
        )
        result = detect_contradictions(**args)
        cr4 = [c for c in result if c["rule_id"] == "CR-4"]
        assert len(cr4) == 1


# ===========================================================================
# Treatment Duration / Extension# ===========================================================================

class TestTreatmentExtension:
    """Test treatment duration extension criteria."""

    def test_stable_no_extension(self):
        """Stable obs → no extension needed."""
        result = assess_treatment_extension({
            "temperature": 37.0, "systolic_bp": 120,
            "heart_rate": 80, "respiratory_rate": 18, "spo2": 97,
        })
        assert result["extend_recommended"] is False

    def test_fever_extends(self):
        """Temperature > 37.8 → extend."""
        result = assess_treatment_extension({"temperature": 38.2})
        assert result["extend_recommended"] is True
        assert any("fever" in c for c in result["criteria_met"])

    def test_temp_37_8_exactly_no_extend(self):
        """Temperature exactly 37.8 → does NOT extend (must be > 37.8)."""
        result = assess_treatment_extension({"temperature": 37.8})
        assert result["extend_recommended"] is False

    def test_temp_37_9_extends(self):
        """Temperature 37.9 → extends (> 37.8)."""
        result = assess_treatment_extension({"temperature": 37.9})
        assert result["extend_recommended"] is True

    def test_single_instability_does_not_extend(self):
        """Single instability marker → no extension (more than 1 required)."""
        result = assess_treatment_extension({
            "temperature": 37.0, "heart_rate": 110,
        })
        assert result["extend_recommended"] is False
        assert not any("instability" in c for c in result["criteria_met"])

    def test_two_instability_markers_extends(self):
        """2+ instability markers → extend."""
        result = assess_treatment_extension({
            "temperature": 37.0, "heart_rate": 110, "systolic_bp": 85,
        })
        assert result["extend_recommended"] is True
        assert any("instability" in c for c in result["criteria_met"])

    def test_empty_observations_no_extension(self):
        """No observations → no extension."""
        result = assess_treatment_extension({})
        assert result["extend_recommended"] is False

    def test_resistant_organism_extends(self):
        """Resistant organism → extend treatment."""
        micro = [{"organism": "Staphylococcus aureus", "susceptibilities": {"amoxicillin": "R"}, "test_type": "blood_culture", "status": "positive"}]
        result = assess_treatment_extension(
            {"temperature": 37.0, "heart_rate": 80},
            micro_results=micro,
        )
        assert result["extend_recommended"] is True
        assert any("resistant" in c for c in result["criteria_met"])

    def test_sensitive_organism_does_not_extend(self):
        """Sensitive organism → no extension from micro alone."""
        micro = [{"organism": "Streptococcus pneumoniae", "susceptibilities": {"amoxicillin": "S"}, "test_type": "blood_culture", "status": "positive"}]
        result = assess_treatment_extension(
            {"temperature": 37.0, "heart_rate": 80},
            micro_results=micro,
        )
        assert result["extend_recommended"] is False


# ===========================================================================
# Treatment Failure Reassessment# ===========================================================================

class TestTreatmentResponse:
    """Test treatment failure reassessment logic."""

    def test_day_3_not_improving_reassess(self):
        result = assess_treatment_response(days_on_treatment=3, symptoms_improving=False)
        assert result["reassess_needed"] is True
        assert len(result["actions"]) > 0

    def test_day_3_improving_no_reassess(self):
        result = assess_treatment_response(days_on_treatment=3, symptoms_improving=True)
        assert result["reassess_needed"] is False

    def test_day_2_not_improving_no_reassess(self):
        """Before day 3 → no reassessment even if not improving."""
        result = assess_treatment_response(days_on_treatment=2, symptoms_improving=False)
        assert result["reassess_needed"] is False

    def test_day_5_not_improving_reassess(self):
        result = assess_treatment_response(days_on_treatment=5, symptoms_improving=False)
        assert result["reassess_needed"] is True


# ===========================================================================
# CRB65 Severity Mapping (distinct from CURB65)
# ===========================================================================

class TestCRB65SeverityMapping:
    """CRB65 uses different thresholds: 0=low, 1-2=moderate, 3+=high."""

    def test_crb65_0_severity_low(self):
        result = compute_curb65({
            "confusion": False, "respiratory_rate": 20,
            "systolic_bp": 120, "diastolic_bp": 80, "age": 50,
        })
        assert result["curb65"] is None
        assert result["crb65"] == 0
        assert result["severity_tier"] == "low"

    def test_crb65_1_severity_moderate(self):
        """CRB65=1 → moderate (not low like CURB65=1)."""
        result = compute_curb65({
            "confusion": False, "respiratory_rate": 20,
            "systolic_bp": 120, "diastolic_bp": 80, "age": 72,
        })
        assert result["curb65"] is None
        assert result["crb65"] == 1
        assert result["severity_tier"] == "moderate"

    def test_crb65_2_severity_moderate(self):
        result = compute_curb65({
            "confusion": True, "respiratory_rate": 20,
            "systolic_bp": 120, "diastolic_bp": 80, "age": 72,
        })
        assert result["curb65"] is None
        assert result["crb65"] == 2
        assert result["severity_tier"] == "moderate"

    def test_crb65_3_severity_high(self):
        result = compute_curb65({
            "confusion": True, "respiratory_rate": 35,
            "systolic_bp": 120, "diastolic_bp": 80, "age": 72,
        })
        assert result["curb65"] is None
        assert result["crb65"] == 3
        assert result["severity_tier"] == "high"


# ===========================================================================
# Fix 1: Treatment Extension — Zero Instability# ===========================================================================

class TestTreatmentExtensionZero:
    def test_zero_instability_no_fever_no_extension(self):
        """Zero instability markers + no fever → no extension."""
        result = assess_treatment_extension({
            "temperature": 37.0, "systolic_bp": 120,
            "heart_rate": 80, "respiratory_rate": 18, "spo2": 97,
        })
        assert result["extend_recommended"] is False
        assert len(result["criteria_met"]) == 0


# ===========================================================================
# Fix 3: Low Severity Atypical SWITCH# ===========================================================================

class TestLowSeverityAtypicalSwitch:
    def test_low_severity_atypical_switches_not_adds(self):
        """Low + atypical → switch to clarithromycin/doxycycline; NO amoxicillin."""
        result = select_antibiotic("low", travel_history=["Europe"])
        assert "amoxicillin" not in result["first_line"].lower()
        assert result["atypical_cover"] is None
        first = result["first_line"].lower()
        assert "clarithromycin" in first or "doxycycline" in first

    def test_low_severity_no_atypical_keeps_amoxicillin(self):
        """Low + no atypical → standard amoxicillin."""
        result = select_antibiotic("low")
        assert "amoxicillin" in result["first_line"].lower()
        assert result["atypical_cover"] is None


# ===========================================================================
# Fix 5: SpO2 Caveat (skin pigmentation warning)
# ===========================================================================

class TestSpO2Caveat:
    def test_spo2_caveat_in_treatment_extension(self):
        """Treatment extension results should include SpO2 caveat."""
        result = assess_treatment_extension({"temperature": 37.0})
        assert "spo2_caveat" in result
        assert "pigmented skin" in result["spo2_caveat"]

    def test_spo2_caveat_in_discharge_criteria(self):
        """Discharge criteria should include SpO2 caveat."""
        result = compute_monitoring_plan(
            severity="low", observations={}, confusion_status={},
        )
        details = result["discharge_criteria_details"]
        assert "spo2_caveat" in details
        assert "pigmented skin" in details["spo2_caveat"]


# ===========================================================================
# Fix 6: Legionella Risk Factor Broadening
# ===========================================================================

class TestLegionellaRiskFactors:
    def test_legionella_with_non_travel_risk_factor(self):
        """Non-travel legionella risk factor + moderate severity → recommended."""
        result = plan_investigations(
            severity="moderate",
            observations={},
            lab_values={},
            legionella_risk_factors=["stagnant water exposure"],
        )
        assert result["legionella_antigen"]["recommended"] is True
        assert "stagnant water" in str(result["legionella_antigen"]["reasoning"])

    def test_legionella_low_severity_not_recommended(self):
        """Low severity → legionella NOT recommended even with risk factors."""
        result = plan_investigations(
            severity="low",
            observations={},
            lab_values={},
            travel_history=["Europe"],
            legionella_risk_factors=["stagnant water exposure"],
        )
        assert result["legionella_antigen"]["recommended"] is False

    def test_legionella_high_severity_always_recommended(self):
        """High severity → legionella ALWAYS recommended (even without risk factors)."""
        result = plan_investigations(
            severity="high",
            observations={},
            lab_values={},
        )
        assert result["legionella_antigen"]["recommended"] is True

    def test_legionella_moderate_no_risk_factors_not_recommended(self):
        """Moderate severity + no risk factors → legionella NOT recommended."""
        result = plan_investigations(
            severity="moderate",
            observations={},
            lab_values={},
        )
        assert result["legionella_antigen"]["recommended"] is False

    def test_legionella_combined_travel_and_risk(self):
        """Both travel + risk factor → all listed in reasoning."""
        result = plan_investigations(
            severity="high",
            observations={},
            lab_values={},
            travel_history=["Europe"],
            legionella_risk_factors=["cooling tower exposure"],
        )
        assert result["legionella_antigen"]["recommended"] is True
        reasoning = result["legionella_antigen"]["reasoning"]
        assert "Europe" in reasoning
        assert "cooling tower" in reasoning


# ===========================================================================
# Fix 7: Recent Antibiotics Stewardship Note
# ===========================================================================

class TestRecentAntibiotics:
    def test_recent_antibiotics_stewardship_note(self):
        """Recent antibiotics → stewardship note present."""
        result = select_antibiotic(
            "moderate",
            recent_antibiotics=[{"drug": "Amoxicillin", "duration": "5 days"}],
        )
        notes = " ".join(result["stewardship_notes"])
        assert "recent antibiotic use" in notes.lower()
        assert "amoxicillin" in notes.lower()
        assert "treatment failure" in notes.lower()
        assert "BTS 2009" in notes

    def test_no_recent_antibiotics_no_note(self):
        """No recent antibiotics → no extra stewardship note."""
        result = select_antibiotic("moderate")
        notes = " ".join(result["stewardship_notes"])
        assert "recent antibiotic use" not in notes.lower()

    def test_recent_antibiotics_string_format(self):
        """Recent antibiotics as plain strings (not dicts) → still works."""
        result = select_antibiotic(
            "low",
            recent_antibiotics=["Amoxicillin", "Clarithromycin"],
        )
        notes = " ".join(result["stewardship_notes"])
        assert "amoxicillin" in notes.lower()
        assert "clarithromycin" in notes.lower()


# ===========================================================================
# Fix 8: Atypical Indicators Broadening
# ===========================================================================

class TestAtypicalIndicators:
    def test_atypical_indicators_trigger_cover(self):
        """Atypical indicators (no travel) → atypical cover in first_line (dual therapy default)."""
        result = select_antibiotic(
            "moderate",
            atypical_indicators=["Mycoplasma outbreak in community"],
        )
        # Moderate now has dual therapy by default
        assert "clarithromycin" in result["first_line"].lower()

    def test_atypical_indicators_low_severity_switches(self):
        """Low + atypical indicators → switch (not add)."""
        result = select_antibiotic(
            "low",
            atypical_indicators=["Contact with confirmed Legionella case"],
        )
        assert "amoxicillin" not in result["first_line"].lower()
        assert result["atypical_cover"] is None

    def test_no_atypical_no_travel_no_cover(self):
        """No atypical indicators, no travel → no atypical cover."""
        result = select_antibiotic("low")
        assert result["atypical_cover"] is None
        assert "amoxicillin" in result["first_line"].lower()


# ===========================================================================
# CR-7: Antibiotic Coverage Mismatch
# ===========================================================================

class TestCR7CoverageMismatch:
    """CR-7: Antibiotic doesn't cover identified organism."""

    BASE_CXR = {"consolidation": {"present": True, "location": "RLL"}, "pleural_effusion": {"present": False}}
    BASE_EXAM = {"respiratory_exam": {"crackles": True, "bronchial_breathing": False}}
    BASE_CURB65 = {"severity_tier": "moderate", "curb65": 2}

    def _run(self, abx_rec, micro):
        return detect_contradictions(
            cxr=self.BASE_CXR, exam=self.BASE_EXAM, labs={},
            demographics={"comorbidities": []}, curb65=self.BASE_CURB65,
            case_data={}, antibiotic_recommendation=abx_rec, micro_results=micro,
        )

    def test_lab_resistance_fires(self):
        """Lab susceptibility shows R → CR-7 fires with high confidence."""
        abx = {"first_line": "Amoxicillin 500mg TDS PO", "atypical_cover": None}
        micro = [{"organism": "Staphylococcus aureus", "susceptibilities": {"amoxicillin": "R"}, "test_type": "blood_culture", "status": "positive"}]
        result = self._run(abx, micro)
        cr7 = [c for c in result if c["rule_id"] == "CR-7"]
        assert len(cr7) == 1
        assert cr7[0]["severity"] == "high"
        assert cr7[0]["resolution_strategy"] == "E"
        assert "resistant" in cr7[0]["pattern"].lower()
        assert cr7[0]["confidence"] == "high"  # lab susceptibility

    def test_sensitive_no_fire(self):
        """Lab shows S → CR-7 does NOT fire."""
        abx = {"first_line": "Amoxicillin 500mg TDS PO", "atypical_cover": None}
        micro = [{"organism": "Streptococcus pneumoniae", "susceptibilities": {"amoxicillin": "S"}, "test_type": "blood_culture", "status": "positive"}]
        result = self._run(abx, micro)
        cr7 = [c for c in result if c["rule_id"] == "CR-7"]
        assert len(cr7) == 0

    def test_lab_overrides_coverage_map(self):
        """Lab says S even though coverage map says R → no fire."""
        abx = {"first_line": "Amoxicillin 500mg TDS PO", "atypical_cover": None}
        # Moraxella is R to amoxicillin in coverage map, but lab says S
        micro = [{"organism": "Moraxella catarrhalis", "susceptibilities": {"amoxicillin": "S"}, "test_type": "sputum_culture", "status": "positive"}]
        result = self._run(abx, micro)
        cr7 = [c for c in result if c["rule_id"] == "CR-7"]
        assert len(cr7) == 0

    def test_intrinsic_resistance_from_map(self):
        """No lab susceptibilities, but coverage map shows R → fires with moderate confidence."""
        abx = {"first_line": "Amoxicillin 500mg TDS PO", "atypical_cover": None}
        micro = [{"organism": "Legionella pneumophila", "susceptibilities": None, "test_type": "urine_antigen", "status": "positive"}]
        result = self._run(abx, micro)
        cr7 = [c for c in result if c["rule_id"] == "CR-7"]
        assert len(cr7) >= 1
        assert "intrinsic resistance" in cr7[0]["pattern"]
        assert cr7[0]["confidence"] == "moderate"  # population coverage map

    def test_pending_no_fire(self):
        """Pending micro result → CR-7 does NOT fire (no organisms)."""
        abx = {"first_line": "Amoxicillin 500mg TDS PO", "atypical_cover": None}
        micro = [{"organism": None, "susceptibilities": None, "test_type": "blood_culture", "status": "pending"}]
        result = self._run(abx, micro)
        cr7 = [c for c in result if c["rule_id"] == "CR-7"]
        assert len(cr7) == 0

    def test_no_micro_no_fire(self):
        """No micro results at all → CR-7 does NOT fire."""
        abx = {"first_line": "Amoxicillin 500mg TDS PO", "atypical_cover": None}
        result = self._run(abx, None)
        cr7 = [c for c in result if c["rule_id"] == "CR-7"]
        assert len(cr7) == 0

    def test_no_abx_no_fire(self):
        """No antibiotic recommendation → CR-7 does NOT fire."""
        micro = [{"organism": "Staphylococcus aureus", "susceptibilities": {"amoxicillin": "R"}, "test_type": "blood_culture", "status": "positive"}]
        result = self._run(None, micro)
        cr7 = [c for c in result if c["rule_id"] == "CR-7"]
        assert len(cr7) == 0

    def test_multiple_organisms_multiple_fires(self):
        """Two resistant organisms → two CR-7 alerts."""
        abx = {"first_line": "Amoxicillin 500mg TDS PO", "atypical_cover": "Clarithromycin 500mg BD"}
        micro = [
            {"organism": "Klebsiella pneumoniae", "susceptibilities": None, "test_type": "sputum_culture", "status": "positive"},
            {"organism": "Legionella pneumophila", "susceptibilities": None, "test_type": "urine_antigen", "status": "positive"},
        ]
        result = self._run(abx, micro)
        cr7 = [c for c in result if c["rule_id"] == "CR-7"]
        # Klebsiella R to amoxicillin + R to clarithromycin; Legionella R to amoxicillin
        assert len(cr7) >= 2

    def test_negative_micro_no_fire(self):
        """Negative culture → no organisms → CR-7 does NOT fire."""
        abx = {"first_line": "Amoxicillin 500mg TDS PO", "atypical_cover": None}
        micro = [{"organism": None, "susceptibilities": None, "test_type": "blood_culture", "status": "negative"}]
        result = self._run(abx, micro)
        cr7 = [c for c in result if c["rule_id"] == "CR-7"]
        assert len(cr7) == 0

    def test_cr7_confidence_lab_vs_population(self):
        """Lab data → high confidence; coverage map → moderate confidence."""
        abx = {"first_line": "Amoxicillin 500mg TDS PO", "atypical_cover": None}
        # Lab susceptibility (high confidence)
        micro_lab = [{"organism": "Staphylococcus aureus", "susceptibilities": {"amoxicillin": "R"}, "test_type": "blood_culture", "status": "positive"}]
        result_lab = self._run(abx, micro_lab)
        cr7_lab = [c for c in result_lab if c["rule_id"] == "CR-7"]
        assert cr7_lab[0]["confidence"] == "high"

        # Population coverage map (moderate confidence)
        micro_pop = [{"organism": "Legionella pneumophila", "susceptibilities": None, "test_type": "urine_antigen", "status": "positive"}]
        result_pop = self._run(abx, micro_pop)
        cr7_pop = [c for c in result_pop if c["rule_id"] == "CR-7"]
        assert cr7_pop[0]["confidence"] == "moderate"


# ===========================================================================
# CR-8: Macrolide De-escalation
# ===========================================================================

class TestCR8MacrolideDe_escalation:
    """CR-8: Macrolide prescribed, no atypical pathogen on micro."""

    BASE_CXR = {"consolidation": {"present": True, "location": "RLL"}, "pleural_effusion": {"present": False}}
    BASE_EXAM = {"respiratory_exam": {"crackles": True, "bronchial_breathing": False}}
    BASE_CURB65 = {"severity_tier": "moderate", "curb65": 2}

    def _run(self, abx_rec, micro):
        return detect_contradictions(
            cxr=self.BASE_CXR, exam=self.BASE_EXAM, labs={},
            demographics={"comorbidities": []}, curb65=self.BASE_CURB65,
            case_data={}, antibiotic_recommendation=abx_rec, micro_results=micro,
        )

    def test_ac8_fires_no_atypical(self):
        """AC-8: Macrolide + completed test + no atypical → fires."""
        abx = {"first_line": "Amoxicillin 500mg TDS PO", "atypical_cover": "Clarithromycin 500mg BD"}
        micro = [
            {"organism": "Streptococcus pneumoniae", "susceptibilities": {"clarithromycin": "S"}, "test_type": "blood_culture", "status": "positive"},
            {"organism": None, "test_type": "urine_antigen_legionella", "status": "negative"},
        ]
        result = self._run(abx, micro)
        cr8 = [c for c in result if c["rule_id"] == "CR-8"]
        assert len(cr8) == 1
        assert cr8[0]["severity"] == "moderate"
        assert "macrolide" in cr8[0]["pattern"].lower()
        assert cr8[0]["confidence"] == "high"  # 2 completed tests

    def test_atypical_found_no_fire(self):
        """Atypical pathogen found → CR-8 does NOT fire."""
        abx = {"first_line": "Co-amoxiclav 1.2g TDS IV", "atypical_cover": "Clarithromycin 500mg BD"}
        micro = [
            {"organism": "Legionella pneumophila", "susceptibilities": None, "test_type": "urine_antigen", "status": "positive"},
        ]
        result = self._run(abx, micro)
        cr8 = [c for c in result if c["rule_id"] == "CR-8"]
        assert len(cr8) == 0

    def test_no_macrolide_no_fire(self):
        """No macrolide in regimen → CR-8 does NOT fire."""
        abx = {"first_line": "Amoxicillin 500mg TDS PO", "atypical_cover": None}
        micro = [{"organism": "Streptococcus pneumoniae", "susceptibilities": None, "test_type": "blood_culture", "status": "positive"}]
        result = self._run(abx, micro)
        cr8 = [c for c in result if c["rule_id"] == "CR-8"]
        assert len(cr8) == 0

    def test_all_pending_no_fire(self):
        """All micro tests pending → CR-8 does NOT fire (no completed tests)."""
        abx = {"first_line": "Amoxicillin 500mg TDS PO", "atypical_cover": "Clarithromycin 500mg BD"}
        micro = [
            {"organism": None, "test_type": "blood_culture", "status": "pending"},
            {"organism": None, "test_type": "sputum_culture", "status": "pending"},
        ]
        result = self._run(abx, micro)
        cr8 = [c for c in result if c["rule_id"] == "CR-8"]
        assert len(cr8) == 0

    def test_negative_culture_fires(self):
        """Negative culture (completed, no atypical) + macrolide → fires."""
        abx = {"first_line": "Amoxicillin 500mg TDS PO", "atypical_cover": "Clarithromycin 500mg BD"}
        micro = [{"organism": None, "test_type": "urine_antigen_legionella", "status": "negative"}]
        result = self._run(abx, micro)
        cr8 = [c for c in result if c["rule_id"] == "CR-8"]
        assert len(cr8) == 1
        assert cr8[0]["confidence"] == "moderate"  # only 1 completed test

    def test_erythromycin_detected(self):
        """Erythromycin (macrolide) in first_line → CR-8 fires."""
        abx = {"first_line": "Erythromycin 500mg QDS PO", "atypical_cover": None}
        micro = [{"organism": None, "test_type": "blood_culture", "status": "negative"}]
        result = self._run(abx, micro)
        cr8 = [c for c in result if c["rule_id"] == "CR-8"]
        assert len(cr8) == 1
        assert cr8[0]["confidence"] == "moderate"  # only 1 completed test

    def test_not_sent_not_completed(self):
        """'not_sent' status does NOT count as completed test."""
        abx = {"first_line": "Amoxicillin 500mg TDS PO", "atypical_cover": "Clarithromycin 500mg BD"}
        micro = [{"organism": None, "test_type": "blood_culture", "status": "not_sent"}]
        result = self._run(abx, micro)
        cr8 = [c for c in result if c["rule_id"] == "CR-8"]
        assert len(cr8) == 0

    def test_cr8_confidence_multiple_tests(self):
        """2+ completed negative tests → high confidence for macrolide de-escalation."""
        abx = {"first_line": "Amoxicillin 500mg TDS PO", "atypical_cover": "Clarithromycin 500mg BD"}
        micro = [
            {"organism": None, "test_type": "urine_antigen_legionella", "status": "negative"},
            {"organism": None, "test_type": "blood_culture", "status": "negative"},
        ]
        result = self._run(abx, micro)
        cr8 = [c for c in result if c["rule_id"] == "CR-8"]
        assert len(cr8) == 1
        assert cr8[0]["confidence"] == "high"  # 2 completed tests

    def test_cr8_confidence_single_test(self):
        """Only 1 completed negative test → moderate confidence."""
        abx = {"first_line": "Amoxicillin 500mg TDS PO", "atypical_cover": "Clarithromycin 500mg BD"}
        micro = [{"organism": None, "test_type": "urine_antigen_legionella", "status": "negative"}]
        result = self._run(abx, micro)
        cr8 = [c for c in result if c["rule_id"] == "CR-8"]
        assert len(cr8) == 1
        assert cr8[0]["confidence"] == "moderate"  # only 1 completed test

    def test_cr8_high_severity_exempt(self):
        """CR-8: High severity → macrolide is standard dual therapy → does NOT fire."""
        abx = {"first_line": "Co-amoxiclav 1.2g TDS IV", "atypical_cover": "Clarithromycin 500mg BD", "severity_tier": "high"}
        micro = [
            {"organism": "Streptococcus pneumoniae", "susceptibilities": None, "test_type": "blood_culture", "status": "positive"},
            {"organism": None, "test_type": "urine_antigen_legionella", "status": "negative"},
        ]
        result = detect_contradictions(
            cxr=self.BASE_CXR, exam=self.BASE_EXAM, labs={},
            demographics={"comorbidities": []}, curb65={"severity_tier": "high", "curb65": 4},
            case_data={}, antibiotic_recommendation=abx, micro_results=micro,
        )
        cr8 = [c for c in result if c["rule_id"] == "CR-8"]
        assert len(cr8) == 0

    def test_cr8_moderate_severity_still_fires(self):
        """CR-8: Moderate severity → macrolide de-escalation still fires."""
        abx = {"first_line": "Amoxicillin 500mg TDS PO", "atypical_cover": "Clarithromycin 500mg BD", "severity_tier": "moderate"}
        micro = [
            {"organism": "Streptococcus pneumoniae", "susceptibilities": None, "test_type": "blood_culture", "status": "positive"},
            {"organism": None, "test_type": "urine_antigen_legionella", "status": "negative"},
        ]
        result = detect_contradictions(
            cxr=self.BASE_CXR, exam=self.BASE_EXAM, labs={},
            demographics={"comorbidities": []}, curb65=self.BASE_CURB65,
            case_data={}, antibiotic_recommendation=abx, micro_results=micro,
        )
        cr8 = [c for c in result if c["rule_id"] == "CR-8"]
        assert len(cr8) == 1


# ===========================================================================
# CR-9: IV-to-Oral Switch
# ===========================================================================

class TestCR9IVToOralSwitch:
    """CR-9: IV >48h but oral tolerance + improving → switch."""

    BASE_CXR = {"consolidation": {"present": True, "location": "RLL"}, "pleural_effusion": {"present": False}}
    BASE_EXAM_STABLE = {
        "respiratory_exam": {"crackles": True, "bronchial_breathing": False},
        "observations": {
            "temperature": 37.0, "heart_rate": 80, "respiratory_rate": 18,
            "systolic_bp": 115, "spo2": 96,
        },
        "confusion_status": {"present": False},
    }
    BASE_CURB65 = {"severity_tier": "moderate", "curb65": 2}
    TREATMENT_STATUS = {
        "current_route": "IV", "hours_on_iv": 52,
        "iv_antibiotics": ["Co-amoxiclav 1.2g TDS IV", "Clarithromycin 500mg BD IV"],
    }

    def _run(self, exam=None, treatment_status=None, oral_tolerance=True):
        exam = exam or self.BASE_EXAM_STABLE
        ts = treatment_status or self.TREATMENT_STATUS
        abx = {"first_line": "Co-amoxiclav 1.2g TDS IV", "atypical_cover": "Clarithromycin 500mg BD IV"}
        return detect_contradictions(
            cxr=self.BASE_CXR, exam=exam, labs={},
            demographics={"comorbidities": [], "oral_tolerance": oral_tolerance},
            curb65=self.BASE_CURB65,
            case_data={"treatment_status": ts},
            antibiotic_recommendation=abx, micro_results=None,
        )

    def test_stable_fires_with_recommendation(self):
        """Stable patient on IV >=48h + oral tolerance → fires with switch recommendation."""
        result = self._run()
        cr9 = [c for c in result if c["rule_id"] == "CR-9"]
        assert len(cr9) == 1
        assert cr9[0]["severity"] == "moderate"
        assert cr9[0]["resolution_strategy"] == "E"
        assert cr9[0]["confidence"] == "high"  # all 6 markers are deterministic
        rec = cr9[0].get("recommendation", {})
        assert len(rec.get("switches", [])) == 2

    def test_less_than_48h_no_fire(self):
        """On IV for <48h → does NOT fire."""
        ts = {**self.TREATMENT_STATUS, "hours_on_iv": 47}
        result = self._run(treatment_status=ts)
        cr9 = [c for c in result if c["rule_id"] == "CR-9"]
        assert len(cr9) == 0

    def test_already_oral_no_fire(self):
        """Route already PO → does NOT fire."""
        ts = {**self.TREATMENT_STATUS, "current_route": "PO"}
        result = self._run(treatment_status=ts)
        cr9 = [c for c in result if c["rule_id"] == "CR-9"]
        assert len(cr9) == 0

    def test_oral_intolerance_no_fire(self):
        """Patient cannot tolerate oral → does NOT fire."""
        result = self._run(oral_tolerance=False)
        cr9 = [c for c in result if c["rule_id"] == "CR-9"]
        assert len(cr9) == 0

    def test_fever_no_fire(self):
        """Fever present → unstable → does NOT fire."""
        exam = {
            "respiratory_exam": {"crackles": True, "bronchial_breathing": False},
            "observations": {
                "temperature": 38.2, "heart_rate": 80, "respiratory_rate": 18,
                "systolic_bp": 115, "spo2": 96,
            },
            "confusion_status": {"present": False},
        }
        result = self._run(exam=exam)
        cr9 = [c for c in result if c["rule_id"] == "CR-9"]
        assert len(cr9) == 0

    def test_confused_no_fire(self):
        """Confusion present → unstable → does NOT fire."""
        exam = {
            "respiratory_exam": {"crackles": True, "bronchial_breathing": False},
            "observations": {
                "temperature": 37.0, "heart_rate": 80, "respiratory_rate": 18,
                "systolic_bp": 115, "spo2": 96,
            },
            "confusion_status": {"present": True},
        }
        result = self._run(exam=exam)
        cr9 = [c for c in result if c["rule_id"] == "CR-9"]
        assert len(cr9) == 0

    def test_tachycardic_no_fire(self):
        """HR > 100 → unstable → does NOT fire."""
        exam = {
            "respiratory_exam": {"crackles": True, "bronchial_breathing": False},
            "observations": {
                "temperature": 37.0, "heart_rate": 110, "respiratory_rate": 18,
                "systolic_bp": 115, "spo2": 96,
            },
            "confusion_status": {"present": False},
        }
        result = self._run(exam=exam)
        cr9 = [c for c in result if c["rule_id"] == "CR-9"]
        assert len(cr9) == 0

    def test_switch_map_detail(self):
        """Switch recommendation maps IV drugs to oral equivalents."""
        result = self._run()
        cr9 = [c for c in result if c["rule_id"] == "CR-9"]
        rec = cr9[0]["recommendation"]
        switches = rec["switches"]
        oral_drugs = [s["oral"] for s in switches]
        assert any("co-amoxiclav" in d.lower() for d in oral_drugs)
        assert any("clarithromycin" in d.lower() for d in oral_drugs)

    def test_no_treatment_status_no_fire(self):
        """No treatment_status in case_data → CR-9 does NOT fire."""
        abx = {"first_line": "Co-amoxiclav 1.2g TDS IV", "atypical_cover": "Clarithromycin 500mg BD IV"}
        result = detect_contradictions(
            cxr=self.BASE_CXR, exam=self.BASE_EXAM_STABLE, labs={},
            demographics={"comorbidities": [], "oral_tolerance": True},
            curb65=self.BASE_CURB65, case_data={},
            antibiotic_recommendation=abx, micro_results=None,
        )
        cr9 = [c for c in result if c["rule_id"] == "CR-9"]
        assert len(cr9) == 0


# ===========================================================================
# CR-10: Fluoroquinolone + Penicillin Intolerance
# ===========================================================================

class TestCR10FluoroquinoloneIntolerance:
    """CR-10: Levofloxacin prescribed but allergy is intolerance only."""

    def test_intolerance_fires(self):
        """GI upset = intolerance → CR-10 fires."""
        abx = {"first_line": "Levofloxacin 500mg BD PO/IV", "atypical_cover": None}
        allergies = [{"drug": "Penicillin", "reaction_type": "GI upset", "severity": "mild"}]
        result = detect_cr10(abx, allergies)
        assert result is not None
        assert result["rule_id"] == "CR-10"
        assert result["severity"] == "high"
        assert result["resolution_strategy"] == "E"
        assert result["confidence"] == "high"  # clear intolerance keywords

    def test_true_allergy_no_fire(self):
        """Anaphylaxis = true allergy → CR-10 does NOT fire."""
        abx = {"first_line": "Levofloxacin 500mg BD PO/IV", "atypical_cover": None}
        allergies = [{"drug": "Penicillin", "reaction_type": "anaphylaxis", "severity": "severe"}]
        result = detect_cr10(abx, allergies)
        assert result is None

    def test_unknown_reaction_no_fire(self):
        """Unknown reaction → conservative (not intolerance) → CR-10 does NOT fire."""
        abx = {"first_line": "Levofloxacin 500mg BD PO/IV", "atypical_cover": None}
        allergies = [{"drug": "Penicillin", "reaction_type": "", "severity": ""}]
        result = detect_cr10(abx, allergies)
        assert result is None

    def test_no_levofloxacin_no_fire(self):
        """Amoxicillin prescribed (not levofloxacin) → CR-10 does NOT fire."""
        abx = {"first_line": "Amoxicillin 500mg TDS PO", "atypical_cover": None}
        allergies = [{"drug": "Penicillin", "reaction_type": "GI upset", "severity": "mild"}]
        result = detect_cr10(abx, allergies)
        assert result is None

    def test_no_allergies_no_fire(self):
        """No allergies → CR-10 does NOT fire."""
        abx = {"first_line": "Levofloxacin 500mg BD PO/IV", "atypical_cover": None}
        result = detect_cr10(abx, [])
        assert result is None

    def test_non_penicillin_allergy_no_fire(self):
        """Allergy to something other than penicillin → CR-10 does NOT fire."""
        abx = {"first_line": "Levofloxacin 500mg BD PO/IV", "atypical_cover": None}
        allergies = [{"drug": "Sulfonamides", "reaction_type": "rash", "severity": "mild"}]
        result = detect_cr10(abx, allergies)
        assert result is None

    def test_rash_is_true_allergy(self):
        """Rash = true allergy keyword → CR-10 does NOT fire."""
        abx = {"first_line": "Levofloxacin 500mg BD PO/IV", "atypical_cover": None}
        allergies = [{"drug": "Penicillin", "reaction_type": "rash", "severity": "moderate"}]
        result = detect_cr10(abx, allergies)
        assert result is None

    def test_nausea_is_intolerance(self):
        """Nausea = intolerance → CR-10 fires."""
        abx = {"first_line": "Levofloxacin 500mg BD PO/IV", "atypical_cover": None}
        allergies = [{"drug": "Penicillin", "reaction_type": "nausea", "severity": "mild"}]
        result = detect_cr10(abx, allergies)
        assert result is not None

    def test_mixed_entries_true_allergy_wins(self):
        """One intolerance + one true allergy → true allergy wins → no fire."""
        abx = {"first_line": "Levofloxacin 500mg BD PO/IV", "atypical_cover": None}
        allergies = [
            {"drug": "Penicillin", "reaction_type": "GI upset", "severity": "mild"},
            {"drug": "Penicillin", "reaction_type": "anaphylaxis", "severity": "severe"},
        ]
        result = detect_cr10(abx, allergies)
        assert result is None


# ===========================================================================
# Helper: classify_micro_results
# ===========================================================================

class TestClassifyMicroResults:
    def test_typical_positive(self):
        micro = [{"organism": "Streptococcus pneumoniae", "susceptibilities": {"amoxicillin": "S"}, "test_type": "blood_culture", "status": "positive"}]
        result = classify_micro_results(micro)
        assert len(result["organisms"]) == 1
        assert result["completed_tests"] == 1
        assert result["has_atypical"] is False

    def test_atypical_detected(self):
        micro = [{"organism": "Legionella pneumophila", "susceptibilities": None, "test_type": "urine_antigen", "status": "positive"}]
        result = classify_micro_results(micro)
        assert result["has_atypical"] is True

    def test_pending_excluded(self):
        micro = [{"organism": None, "test_type": "blood_culture", "status": "pending"}]
        result = classify_micro_results(micro)
        assert len(result["organisms"]) == 0
        assert result["completed_tests"] == 0

    def test_not_sent_excluded(self):
        micro = [{"organism": None, "test_type": "sputum_culture", "status": "not_sent"}]
        result = classify_micro_results(micro)
        assert result["completed_tests"] == 0

    def test_empty_input(self):
        assert classify_micro_results([])["organisms"] == []
        assert classify_micro_results(None)["organisms"] == []

    def test_mixed_statuses(self):
        micro = [
            {"organism": "Streptococcus pneumoniae", "susceptibilities": None, "test_type": "blood_culture", "status": "positive"},
            {"organism": None, "test_type": "urine_antigen_legionella", "status": "negative"},
            {"organism": None, "test_type": "sputum_culture", "status": "pending"},
        ]
        result = classify_micro_results(micro)
        assert len(result["organisms"]) == 1
        assert result["completed_tests"] == 2  # positive + negative


# ===========================================================================
# Helper: classify_penicillin_allergy
# ===========================================================================

class TestClassifyPenicillinAllergy:
    def test_gi_upset_is_intolerance(self):
        allergies = [{"drug": "Penicillin", "reaction_type": "GI upset", "severity": "mild"}]
        result = classify_penicillin_allergy(allergies)
        assert result["has_penicillin_allergy"] is True
        assert result["is_intolerance_only"] is True
        assert result["classification"] == "intolerance"

    def test_anaphylaxis_is_absolute_contraindication(self):
        """Anaphylaxis → absolute_contraindication (not just true_allergy)."""
        allergies = [{"drug": "Penicillin", "reaction_type": "anaphylaxis", "severity": "severe"}]
        result = classify_penicillin_allergy(allergies)
        assert result["is_true_allergy"] is True
        assert result["is_intolerance_only"] is False
        assert result["classification"] == "absolute_contraindication"

    def test_sjs_is_absolute_contraindication(self):
        """Stevens-Johnson syndrome → absolute_contraindication."""
        allergies = [{"drug": "Penicillin", "reaction_type": "Stevens-Johnson syndrome", "severity": "severe"}]
        result = classify_penicillin_allergy(allergies)
        assert result["classification"] == "absolute_contraindication"

    def test_ten_is_absolute_contraindication(self):
        """Toxic Epidermal Necrolysis → absolute_contraindication."""
        allergies = [{"drug": "Penicillin", "reaction_type": "toxic epidermal necrolysis", "severity": "severe"}]
        result = classify_penicillin_allergy(allergies)
        assert result["classification"] == "absolute_contraindication"

    def test_dress_is_absolute_contraindication(self):
        """DRESS syndrome → absolute_contraindication."""
        allergies = [{"drug": "Penicillin", "reaction_type": "DRESS", "severity": "severe"}]
        result = classify_penicillin_allergy(allergies)
        assert result["classification"] == "absolute_contraindication"

    def test_sjs_abbreviation(self):
        """SJS abbreviation → absolute_contraindication."""
        allergies = [{"drug": "Penicillin", "reaction_type": "SJS", "severity": "severe"}]
        result = classify_penicillin_allergy(allergies)
        assert result["classification"] == "absolute_contraindication"

    def test_urticaria_is_true_allergy_not_absolute(self):
        """Urticaria → true_allergy (not absolute_contraindication)."""
        allergies = [{"drug": "Penicillin", "reaction_type": "urticaria", "severity": "moderate"}]
        result = classify_penicillin_allergy(allergies)
        assert result["is_true_allergy"] is True
        assert result["classification"] == "true_allergy"

    def test_rash_is_true_allergy_not_absolute(self):
        """Rash → true_allergy (not absolute_contraindication)."""
        allergies = [{"drug": "Penicillin", "reaction_type": "rash", "severity": "moderate"}]
        result = classify_penicillin_allergy(allergies)
        assert result["classification"] == "true_allergy"

    def test_unknown_is_conservative(self):
        allergies = [{"drug": "Penicillin", "reaction_type": "", "severity": ""}]
        result = classify_penicillin_allergy(allergies)
        assert result["has_penicillin_allergy"] is True
        assert result["is_intolerance_only"] is False
        assert result["classification"] == "unknown"

    def test_mixed_true_allergy_wins(self):
        allergies = [
            {"drug": "Penicillin", "reaction_type": "nausea", "severity": "mild"},
            {"drug": "Penicillin", "reaction_type": "angioedema", "severity": "severe"},
        ]
        result = classify_penicillin_allergy(allergies)
        assert result["is_true_allergy"] is True
        assert result["is_intolerance_only"] is False

    def test_mixed_absolute_wins_over_true(self):
        """Anaphylaxis + urticaria → absolute_contraindication wins."""
        allergies = [
            {"drug": "Penicillin", "reaction_type": "urticaria", "severity": "moderate"},
            {"drug": "Penicillin", "reaction_type": "anaphylaxis", "severity": "severe"},
        ]
        result = classify_penicillin_allergy(allergies)
        assert result["classification"] == "absolute_contraindication"

    def test_no_penicillin(self):
        allergies = [{"drug": "Sulfonamides", "reaction_type": "rash", "severity": "mild"}]
        result = classify_penicillin_allergy(allergies)
        assert result["has_penicillin_allergy"] is False

    def test_empty(self):
        assert classify_penicillin_allergy([])["has_penicillin_allergy"] is False
        assert classify_penicillin_allergy(None)["has_penicillin_allergy"] is False


# ===========================================================================
# Helper: assess_iv_to_oral_stability
# ===========================================================================

class TestIVToOralStability:
    def test_all_stable(self):
        obs = {"temperature": 37.0, "heart_rate": 80, "respiratory_rate": 18, "systolic_bp": 115, "spo2": 96}
        result = assess_iv_to_oral_stability(obs, {"present": False})
        assert result["stable"] is True
        assert len(result["unstable_markers"]) == 0

    def test_fever_unstable(self):
        obs = {"temperature": 38.2, "heart_rate": 80, "respiratory_rate": 18, "systolic_bp": 115, "spo2": 96}
        result = assess_iv_to_oral_stability(obs, {"present": False})
        assert result["stable"] is False
        assert any("fever" in m for m in result["unstable_markers"])

    def test_temp_37_8_exactly_stable(self):
        """Temperature exactly 37.8 → stable (threshold is > 37.8)."""
        obs = {"temperature": 37.8, "heart_rate": 80, "respiratory_rate": 18, "systolic_bp": 115, "spo2": 96}
        result = assess_iv_to_oral_stability(obs, {"present": False})
        assert result["stable"] is True

    def test_confused_unstable(self):
        obs = {"temperature": 37.0, "heart_rate": 80, "respiratory_rate": 18, "systolic_bp": 115, "spo2": 96}
        result = assess_iv_to_oral_stability(obs, {"present": True})
        assert result["stable"] is False
        assert any("confusion" in m for m in result["unstable_markers"])

    def test_empty_defaults_stable(self):
        """Empty observations → all None → no unstable markers → stable."""
        result = assess_iv_to_oral_stability({}, {})
        assert result["stable"] is True

    def test_multiple_unstable(self):
        """Multiple markers unstable → all reported."""
        obs = {"temperature": 38.5, "heart_rate": 110, "respiratory_rate": 30, "systolic_bp": 85, "spo2": 88}
        result = assess_iv_to_oral_stability(obs, {"present": True})
        assert result["stable"] is False
        assert len(result["unstable_markers"]) == 6  # fever + tachy + tachypnoea + hypo + hypoxia + confusion


# ===========================================================================
# Helper: generate_iv_to_oral_recommendation
# ===========================================================================

class TestGenerateIVToOralRecommendation:
    def test_known_drugs_mapped(self):
        iv_drugs = ["Co-amoxiclav 1.2g TDS IV", "Clarithromycin 500mg BD IV"]
        result = generate_iv_to_oral_recommendation(iv_drugs)
        assert len(result["switches"]) == 2
        assert len(result["unmatched"]) == 0

    def test_unknown_drug_unmatched(self):
        iv_drugs = ["Meropenem 1g TDS IV"]
        result = generate_iv_to_oral_recommendation(iv_drugs)
        assert len(result["switches"]) == 0
        assert len(result["unmatched"]) == 1

    def test_ceftriaxone_consult(self):
        iv_drugs = ["Ceftriaxone 2g OD IV"]
        result = generate_iv_to_oral_recommendation(iv_drugs)
        assert len(result["switches"]) == 1
        assert "consult" in result["switches"][0]["oral"].lower()

    def test_empty_list(self):
        result = generate_iv_to_oral_recommendation([])
        assert len(result["switches"]) == 0
        assert len(result["unmatched"]) == 0


# ===========================================================================
# Helper: _extract_prescribed_drugs
# ===========================================================================

class TestExtractPrescribedDrugs:
    def test_extracts_from_first_line_and_cover(self):
        abx = {"first_line": "Co-amoxiclav 1.2g TDS IV", "atypical_cover": "Clarithromycin 500mg BD"}
        drugs = _extract_prescribed_drugs(abx)
        assert "co-amoxiclav" in drugs
        assert "clarithromycin" in drugs

    def test_none_atypical_cover(self):
        abx = {"first_line": "Amoxicillin 500mg TDS PO", "atypical_cover": None}
        drugs = _extract_prescribed_drugs(abx)
        assert "amoxicillin" in drugs

    def test_empty_dict(self):
        assert _extract_prescribed_drugs({}) == []


# ===========================================================================
# Backward Compatibility: existing callers pass 6 args → CR-7/8/9 skip
# ===========================================================================

class TestCR789BackwardCompat:
    """Existing callers that pass no antibiotic_recommendation or micro_results."""

    def test_six_arg_call_still_works(self):
        """Original 6-arg call → no CR-7/8/9 → backward compatible."""
        result = detect_contradictions(
            cxr={"consolidation": {"present": True, "location": "RLL"}, "pleural_effusion": {"present": False}},
            exam={"respiratory_exam": {"crackles": True, "bronchial_breathing": False}},
            labs={}, demographics={"comorbidities": []},
            curb65={"severity_tier": "moderate", "curb65": 2}, case_data={},
        )
        cr789 = [c for c in result if c["rule_id"] in ("CR-7", "CR-8", "CR-9")]
        assert len(cr789) == 0


# ===========================================================================
# CRP Trend Analysis# ===========================================================================

class TestComputeCRPTrend:
    """Test CRP trend computation for treatment monitoring."""

    def test_crp_improving_above_50_percent(self):
        """186 → 80 = 57% decrease → improving, no flag."""
        result = compute_crp_trend(186, 80, days_since_admission=3)
        assert result["trend"] == "improving"
        assert result["flag_senior_review"] is False
        assert result["percent_change"] == pytest.approx(57.0, abs=0.5)

    def test_crp_slow_response_under_50_percent(self):
        """186 → 110 = 41% decrease → slow_response, flag at day≥3."""
        result = compute_crp_trend(186, 110, days_since_admission=3)
        assert result["trend"] == "slow_response"
        assert result["flag_senior_review"] is True
        assert result["percent_change"] == pytest.approx(40.9, abs=0.5)

    def test_crp_slow_response_day2_no_flag(self):
        """Same values but day=2 → no flag yet."""
        result = compute_crp_trend(186, 110, days_since_admission=2)
        assert result["trend"] == "slow_response"
        assert result["flag_senior_review"] is False

    def test_crp_static(self):
        """186 → 186 = 0% → static, flag at day≥3."""
        result = compute_crp_trend(186, 186, days_since_admission=3)
        assert result["trend"] == "static"
        assert result["flag_senior_review"] is True
        assert result["percent_change"] == 0.0

    def test_crp_worsening(self):
        """186 → 220 = -18% → worsening, always flag."""
        result = compute_crp_trend(186, 220, days_since_admission=1)
        assert result["trend"] == "worsening"
        assert result["flag_senior_review"] is True
        assert result["percent_change"] < 0

    def test_crp_zero_admission(self):
        """0 → 50 → unknown, no flag (edge case: can't compute %)."""
        result = compute_crp_trend(0, 50)
        assert result["trend"] == "unknown"
        assert result["flag_senior_review"] is False
        assert result["percent_change"] is None

    def test_crp_exactly_50_percent(self):
        """186 → 93 = exactly 50% → improving, no flag (boundary)."""
        result = compute_crp_trend(186, 93, days_since_admission=3)
        assert result["trend"] == "improving"
        assert result["flag_senior_review"] is False


# ===========================================================================
# Monitoring Plan: Treatment Status + CRP Trend Integration
# ===========================================================================

class TestMonitoringPlanTreatmentIntegration:
    """Test compute_monitoring_plan with treatment_status and crp_trend."""

    def test_monitoring_plan_with_treatment_status(self):
        """Treatment status passed → treatment_response present + discharge blocked."""
        ts = {"days_on_treatment": 3, "symptoms_improving": False}
        result = compute_monitoring_plan(
            severity="low", observations={}, confusion_status={},
            treatment_status=ts,
        )
        assert result["treatment_response"] is not None
        assert result["treatment_response"]["reassess_needed"] is True
        # Discharge override: reassess_needed blocks discharge
        assert result["discharge_criteria_met"] is False
        assert "treatment_reassessment_needed" in result["discharge_criteria_details"]["not_met"]

    def test_monitoring_plan_with_crp_trend_flag(self):
        """CRP trend with flag=True → crp_repeat_timing mentions senior review."""
        crp_trend = {
            "flag_senior_review": True,
            "reasoning": "CRP decreased by only 41%",
        }
        result = compute_monitoring_plan(
            severity="low", observations={}, confusion_status={},
            crp_trend=crp_trend,
        )
        assert "WARNING" in result["crp_repeat_timing"]
        assert "senior review" in result["crp_repeat_timing"].lower()
        assert result["crp_trend"] == crp_trend

    def test_monitoring_plan_without_treatment_status(self):
        """No treatment_status → treatment_response is None (backward compat)."""
        result = compute_monitoring_plan(
            severity="low", observations={}, confusion_status={},
        )
        assert result["treatment_response"] is None
        assert result["crp_trend"] is None

    def test_discharge_overridden_by_treatment_reassessment(self):
        """Reassess_needed=True overrides discharge even if vitals are normal."""
        # All vitals normal → would normally pass discharge
        obs = {
            "temperature": 37.2, "respiratory_rate": 18, "heart_rate": 78,
            "systolic_bp": 125, "spo2": 97,
        }
        ts = {"days_on_treatment": 3, "symptoms_improving": False}
        result = compute_monitoring_plan(
            severity="low", observations=obs, confusion_status={},
            treatment_status=ts,
        )
        # Vitals all pass, but treatment override blocks discharge
        assert result["treatment_response"]["reassess_needed"] is True
        assert result["discharge_criteria_met"] is False
        assert "treatment_reassessment_needed" in result["discharge_criteria_details"]["not_met"]

    def test_discharge_not_overridden_when_improving(self):
        """Improving treatment → no discharge override, vitals decide."""
        obs = {
            "temperature": 37.0, "respiratory_rate": 16, "heart_rate": 72,
            "systolic_bp": 130, "spo2": 98,
        }
        ts = {"days_on_treatment": 2, "symptoms_improving": True}
        result = compute_monitoring_plan(
            severity="low", observations=obs, confusion_status={},
            treatment_status=ts,
        )
        assert result["treatment_response"]["reassess_needed"] is False
        assert result["discharge_criteria_met"] is True
        assert "treatment_reassessment_needed" not in result["discharge_criteria_details"]["not_met"]


# ===========================================================================
# PCT Trend Analysis (same logic as CRP trend)
# ===========================================================================

class TestComputePCTTrend:
    """Test PCT trend analysis (ProHOSP algorithm: 80% threshold + absolute < 0.25)."""

    def test_pct_improving_above_80_percent(self):
        """PCT decrease >= 80% → improving, no flag."""
        result = compute_pct_trend(5.0, 0.5, days_since_admission=3)
        assert result["trend"] == "improving"
        assert result["flag_senior_review"] is False
        assert result["percent_change"] == pytest.approx(90.0, abs=0.5)

    def test_pct_60_percent_decrease_is_slow_response(self):
        """PCT decrease 60% (< 80%) → slow_response, flag at day >= 3."""
        result = compute_pct_trend(5.0, 2.0, days_since_admission=3)
        assert result["trend"] == "slow_response"
        assert result["flag_senior_review"] is True

    def test_pct_absolute_below_025_improving(self):
        """PCT < 0.25 µg/L regardless of percentage → improving (ProHOSP)."""
        result = compute_pct_trend(0.5, 0.2, days_since_admission=3)
        assert result["trend"] == "improving"
        assert result["flag_senior_review"] is False
        assert "0.25" in result["reasoning"]

    def test_pct_absolute_exactly_025_not_absolute_improving(self):
        """PCT = 0.25 µg/L → does NOT trigger absolute threshold (strictly < 0.25)."""
        result = compute_pct_trend(5.0, 0.25, days_since_admission=3)
        # 95% decrease → >= 80% → improving via percentage, not absolute
        assert result["trend"] == "improving"

    def test_pct_slow_response_day3(self):
        """PCT decrease 30% at day 3 → slow_response, flag."""
        result = compute_pct_trend(5.0, 3.5, days_since_admission=3)
        assert result["trend"] == "slow_response"
        assert result["flag_senior_review"] is True

    def test_pct_worsening(self):
        """PCT increase → worsening, always flag."""
        result = compute_pct_trend(5.0, 7.0, days_since_admission=1)
        assert result["trend"] == "worsening"
        assert result["flag_senior_review"] is True

    def test_pct_zero_admission(self):
        """Admission PCT=0 → unknown, no flag."""
        result = compute_pct_trend(0, 3.0)
        assert result["trend"] == "unknown"
        assert result["flag_senior_review"] is False
        assert result["percent_change"] is None

    def test_pct_high_value_below_025_still_improving(self):
        """Even with small percent change, PCT < 0.25 = improving."""
        result = compute_pct_trend(0.3, 0.24, days_since_admission=3)
        assert result["trend"] == "improving"
        assert result["flag_senior_review"] is False


# ===========================================================================
# CR-11: Pneumococcal De-escalation
# ===========================================================================

class TestCR11PneumococcalDeescalation:
    """CR-11: Pneumococcal antigen positive + broad-spectrum → de-escalate."""

    BASE_CXR = {"consolidation": {"present": True, "location": "RLL"}, "pleural_effusion": {"present": False}}
    BASE_EXAM = {"respiratory_exam": {"crackles": True, "bronchial_breathing": False}}
    BASE_CURB65 = {"severity_tier": "moderate", "curb65": 2}

    def _run(self, abx_rec, micro):
        return detect_contradictions(
            cxr=self.BASE_CXR, exam=self.BASE_EXAM, labs={},
            demographics={"comorbidities": []}, curb65=self.BASE_CURB65,
            case_data={}, antibiotic_recommendation=abx_rec, micro_results=micro,
        )

    def test_positive_pneumococcal_broad_spectrum_fires(self):
        """Positive pneumococcal antigen + co-amoxiclav → CR-11 fires."""
        abx = {"first_line": "Co-amoxiclav 1.2g TDS IV", "atypical_cover": "Clarithromycin 500mg BD"}
        micro = [{"organism": "Streptococcus pneumoniae", "susceptibilities": {"amoxicillin": "S"}, "test_type": "pneumococcal_urine_antigen", "status": "positive"}]
        result = self._run(abx, micro)
        cr11 = [c for c in result if c["rule_id"] == "CR-11"]
        assert len(cr11) == 1
        assert cr11[0]["resolution_strategy"] == "E"
        assert "amoxicillin" in cr11[0]["pattern"].lower() or "de-escalation" in cr11[0]["pattern"].lower()

    def test_no_susceptibility_moderate_confidence(self):
        """Positive pneumococcal antigen, no lab susceptibility → moderate confidence."""
        abx = {"first_line": "Co-amoxiclav 1.2g TDS IV", "atypical_cover": None}
        micro = [{"organism": None, "susceptibilities": None, "test_type": "pneumococcal_urine_antigen", "status": "positive"}]
        result = self._run(abx, micro)
        cr11 = [c for c in result if c["rule_id"] == "CR-11"]
        assert len(cr11) == 1
        assert cr11[0]["confidence"] == "moderate"

    def test_negative_pneumococcal_no_fire(self):
        """Negative pneumococcal antigen → CR-11 does NOT fire."""
        abx = {"first_line": "Co-amoxiclav 1.2g TDS IV", "atypical_cover": None}
        micro = [{"organism": None, "susceptibilities": None, "test_type": "pneumococcal_urine_antigen", "status": "negative"}]
        result = self._run(abx, micro)
        cr11 = [c for c in result if c["rule_id"] == "CR-11"]
        assert len(cr11) == 0

    def test_narrow_spectrum_no_fire(self):
        """Amoxicillin prescribed (narrow, not broad) → CR-11 does NOT fire."""
        abx = {"first_line": "Amoxicillin 500mg TDS PO", "atypical_cover": None}
        micro = [{"organism": "Streptococcus pneumoniae", "susceptibilities": {"amoxicillin": "S"}, "test_type": "pneumococcal_urine_antigen", "status": "positive"}]
        result = self._run(abx, micro)
        cr11 = [c for c in result if c["rule_id"] == "CR-11"]
        assert len(cr11) == 0

"""Tests for T=48h temporal synthetic data and CR-10 case."""

import base64

import pytest

from cap_agent.data.synthetic import (
    get_synthetic_48h_case,
    get_synthetic_cr10_case,
    get_synthetic_day34_case,
    get_synthetic_fhir_case,
    SYNTHETIC_CLERKING_NOTE_48H,
    SYNTHETIC_CLERKING_NOTE_DAY34,
    SYNTHETIC_LAB_REPORT_48H,
    SYNTHETIC_LAB_REPORT_DAY34,
)
from cap_agent.data.fhir_utils import group_resources_by_type


@pytest.fixture
def case_48h():
    return get_synthetic_48h_case()


@pytest.fixture
def case_t0():
    return get_synthetic_fhir_case()


class TestTemporalFHIRData:
    """Verify that T=48h FHIR bundle reflects updated clinical state."""

    def test_48h_vitals_updated(self, case_48h):
        """FHIR Observations should reflect T=48h vital signs."""
        bundle = case_48h["fhir_bundle"]
        vitals_found = {}
        for entry in bundle["entry"]:
            res = entry["resource"]
            if res["resourceType"] != "Observation":
                continue
            display = res.get("code", {}).get("coding", [{}])[0].get("display", "")
            if display == "Body temperature":
                vitals_found["temp"] = res["valueQuantity"]["value"]
            elif display == "Respiratory rate":
                vitals_found["rr"] = res["valueQuantity"]["value"]
            elif display == "Heart rate":
                vitals_found["hr"] = res["valueQuantity"]["value"]
            elif display == "Oxygen saturation":
                vitals_found["spo2"] = res["valueQuantity"]["value"]
            elif display == "Blood pressure panel":
                for comp in res.get("component", []):
                    cd = comp.get("code", {}).get("coding", [{}])[0].get("display", "")
                    if cd == "Systolic blood pressure":
                        vitals_found["sbp"] = comp["valueQuantity"]["value"]
                    elif cd == "Diastolic blood pressure":
                        vitals_found["dbp"] = comp["valueQuantity"]["value"]

        assert vitals_found["temp"] == 37.0, f"Expected temp 37.0, got {vitals_found['temp']}"
        assert vitals_found["rr"] == 18
        assert vitals_found["hr"] == 82
        assert vitals_found["spo2"] == 96
        assert vitals_found["sbp"] == 115
        assert vitals_found["dbp"] == 70

    def test_48h_labs_updated(self, case_48h):
        """FHIR lab Observations should reflect T=48h values."""
        bundle = case_48h["fhir_bundle"]
        labs_found = {}
        for entry in bundle["entry"]:
            res = entry["resource"]
            if res["resourceType"] != "Observation":
                continue
            display = res.get("code", {}).get("coding", [{}])[0].get("display", "")
            if display == "C-reactive protein":
                labs_found["crp"] = res["valueQuantity"]["value"]
            elif display == "Urea":
                labs_found["urea"] = res["valueQuantity"]["value"]
            elif display == "White cell count":
                labs_found["wcc"] = res["valueQuantity"]["value"]
            elif display == "Lactate":
                labs_found["lactate"] = res["valueQuantity"]["value"]

        assert labs_found["crp"] == 95, f"Expected CRP 95, got {labs_found['crp']}"
        assert labs_found["urea"] == 6.8
        assert labs_found["wcc"] == 11.8
        assert labs_found["lactate"] == 1.2

    def test_48h_document_reference_updated(self, case_48h):
        """DocumentReference should contain 48h review keywords."""
        bundle = case_48h["fhir_bundle"]
        doc_text = None
        for entry in bundle["entry"]:
            res = entry["resource"]
            if res["resourceType"] == "DocumentReference":
                b64_data = res["content"][0]["attachment"]["data"]
                doc_text = base64.b64decode(b64_data).decode("utf-8")
                break

        assert doc_text is not None, "No DocumentReference found"
        assert "48-HOUR" in doc_text or "48h" in doc_text.lower()
        assert "Streptococcus pneumoniae" in doc_text

    def test_48h_lab_report_is_day2(self, case_48h, case_t0):
        """48h lab report content differs from T=0."""
        t48h_content = case_48h["lab_report"]["content"]
        t0_content = case_t0["lab_report"]["content"]
        assert t48h_content != t0_content
        assert "95" in t48h_content  # CRP 95 at T=48h
        assert "12/02/2026" in t48h_content  # Day 2 date

    def test_48h_no_cxr_image_path(self, case_48h):
        """CXR image_path should not be present at T=48h."""
        assert "image_path" not in case_48h["cxr"]
        assert "prior_image_path" not in case_48h["cxr"]

    def test_48h_flat_vitals_consistent(self, case_48h):
        """Flat case_data observations should match FHIR values."""
        obs = case_48h["clinical_exam"]["observations"]
        assert obs["temperature"] == 37.0
        assert obs["respiratory_rate"] == 18
        assert obs["heart_rate"] == 82
        assert obs["spo2"] == 96
        assert obs["systolic_bp"] == 115

    def test_48h_confusion_resolved(self, case_48h):
        """Patient is no longer confused at T=48h."""
        confusion = case_48h["clinical_exam"]["confusion_assessment"]
        assert confusion["confused"] is False
        assert confusion["amt_score"] == 10

    def test_48h_flat_labs_consistent(self, case_48h):
        """Flat lab_results should match 48h values."""
        labs = case_48h["lab_results"]
        assert labs["crp"]["value"] == 95
        assert labs["urea"]["value"] == 6.8
        assert labs["wcc"]["value"] == 11.8

    def test_48h_has_micro_results(self, case_48h):
        """48h case should have microbiology results."""
        assert "micro_results" in case_48h
        assert len(case_48h["micro_results"]) > 0

    def test_48h_has_treatment_status(self, case_48h):
        """48h case should have treatment status with IV details."""
        ts = case_48h["treatment_status"]
        assert ts["current_route"] == "IV"
        assert ts["hours_on_iv"] >= 48

    def test_48h_has_prior_antibiotic(self, case_48h):
        """48h case should have prior antibiotic recommendation."""
        prior = case_48h["prior_antibiotic_recommendation"]
        assert "first_line" in prior
        assert "atypical_cover" in prior

    def test_48h_has_admission_labs(self, case_48h):
        """48h case should have admission_labs with baseline CRP for trend."""
        assert "admission_labs" in case_48h
        assert case_48h["admission_labs"]["crp"] == 186

    def test_48h_fhir_has_iv_medications(self, case_48h):
        """48h FHIR bundle should include IV antibiotic MedicationRequests."""
        bundle = case_48h["fhir_bundle"]
        med_texts = []
        for entry in bundle["entry"]:
            res = entry["resource"]
            if res["resourceType"] == "MedicationRequest":
                text = res.get("medicationCodeableConcept", {}).get("text", "")
                med_texts.append(text)

        assert any("Co-amoxiclav" in t for t in med_texts)
        assert any("Clarithromycin" in t for t in med_texts)

    def test_t0_fhir_unchanged(self, case_t0):
        """T=0 case should still have original values (deep copy check)."""
        bundle = case_t0["fhir_bundle"]
        for entry in bundle["entry"]:
            res = entry["resource"]
            if res["resourceType"] != "Observation":
                continue
            display = res.get("code", {}).get("coding", [{}])[0].get("display", "")
            if display == "Body temperature":
                assert res["valueQuantity"]["value"] == 38.4
                return
        pytest.fail("No Body temperature Observation found in T=0 bundle")


class TestCR10Case:
    """Verify CR-10 synthetic case structure."""

    def test_has_penicillin_allergy(self):
        case = get_synthetic_cr10_case()
        allergies = case["demographics"]["allergies"]
        assert len(allergies) == 1
        assert allergies[0]["drug"] == "Penicillin"
        assert allergies[0]["reaction_type"] == "GI upset"

    def test_allergy_in_past_medical_history(self):
        """Allergy must also be in past_medical_history for mock extraction."""
        case = get_synthetic_cr10_case()
        pmh_allergies = case["past_medical_history"]["allergies"]
        assert len(pmh_allergies) == 1
        assert pmh_allergies[0]["drug"] == "Penicillin"
        assert pmh_allergies[0]["reaction_type"] == "GI upset"

    @pytest.mark.asyncio
    async def test_mock_extraction_preserves_allergy_reaction_type(self):
        """Mock extraction must pass through dict allergies with reaction_type."""
        from cap_agent.data.extraction import mock_extract_clinical_notes
        case = get_synthetic_cr10_case()
        result = await mock_extract_clinical_notes(case)
        allergies = result["raw_output"]["demographics"]["allergies"]
        assert len(allergies) == 1
        assert allergies[0]["drug"] == "Penicillin"
        assert allergies[0]["reaction_type"] == "GI upset"

    def test_confusion_present(self):
        case = get_synthetic_cr10_case()
        assert case["clinical_exam"]["confusion_assessment"]["confused"] is True
        assert case["clinical_exam"]["confusion_assessment"]["amt_score"] == 7

    def test_high_urea(self):
        case = get_synthetic_cr10_case()
        assert case["lab_results"]["urea"]["value"] == 10.5

    def test_no_fhir_bundle(self):
        """CR-10 case uses base case (no FHIR) for fast mock extraction."""
        case = get_synthetic_cr10_case()
        assert "fhir_bundle" not in case


class TestDay34Case:
    """Verify Day 3-4 treatment monitoring case structure."""

    @pytest.fixture
    def case_day34(self):
        return get_synthetic_day34_case()

    def test_day34_vitals_updated(self, case_day34):
        """Day 3-4 vitals: temp=37.8, RR=20, HR=92, SpO2=95."""
        obs = case_day34["clinical_exam"]["observations"]
        assert obs["temperature"] == 37.8
        assert obs["respiratory_rate"] == 20
        assert obs["heart_rate"] == 92
        assert obs["spo2"] == 95
        assert obs["systolic_bp"] == 110
        assert obs["diastolic_bp"] == 68

    def test_day34_labs_updated(self, case_day34):
        """Day 3-4 labs: CRP=110, Urea=7.0, WCC=13.5."""
        labs = case_day34["lab_results"]
        assert labs["crp"]["value"] == 110
        assert labs["urea"]["value"] == 7.0
        assert labs["wcc"]["value"] == 13.5

    def test_day34_has_treatment_status(self, case_day34):
        """Day 3-4 has treatment status: days=3, NOT improving."""
        ts = case_day34["treatment_status"]
        assert ts["days_on_treatment"] == 3
        assert ts["symptoms_improving"] is False
        assert ts["current_route"] == "PO"

    def test_day34_has_admission_labs(self, case_day34):
        """Day 3-4 has admission labs with baseline CRP."""
        assert "admission_labs" in case_day34
        assert case_day34["admission_labs"]["crp"] == 186

    def test_day34_no_cxr_images(self, case_day34):
        """CXR image_path should not be present at Day 3-4."""
        assert "image_path" not in case_day34["cxr"]
        assert "prior_image_path" not in case_day34["cxr"]

    def test_day34_flat_consistent(self, case_day34):
        """Flat case_data observations should match expected Day 3-4 values."""
        obs = case_day34["clinical_exam"]["observations"]
        assert obs["temperature"] == 37.8
        labs = case_day34["lab_results"]
        assert labs["procalcitonin"]["value"] == 0.50
        assert labs["lactate"]["value"] == 1.3

    def test_day34_fhir_deep_copy_safe(self):
        """T=0 FHIR unchanged after Day 3-4 case construction."""
        _ = get_synthetic_day34_case()
        t0 = get_synthetic_fhir_case()
        bundle = t0["fhir_bundle"]
        for entry in bundle["entry"]:
            res = entry["resource"]
            if res["resourceType"] != "Observation":
                continue
            display = res.get("code", {}).get("coding", [{}])[0].get("display", "")
            if display == "Body temperature":
                assert res["valueQuantity"]["value"] == 38.4
                return
        pytest.fail("No Body temperature Observation found in T=0 bundle")

    def test_48h_treatment_status_has_days(self):
        """48h case should have days_on_treatment retroactively added."""
        case_48h = get_synthetic_48h_case()
        ts = case_48h["treatment_status"]
        assert ts["days_on_treatment"] == 2
        assert ts["symptoms_improving"] is True

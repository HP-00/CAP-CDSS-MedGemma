"""Tests for the 5 rich demo cases."""

import base64
import os

import pytest

from cap_agent.data.demo_cases import (
    get_cxr_clear_case,
    get_cxr_bilateral_case,
    get_cxr_normal_case,
    get_cxr_subtle_case,
    get_cxr_effusion_case,
)
from cap_agent.agent.clinical_logic import compute_curb65


ALL_BUILDERS = [
    ("cxr_clear", get_cxr_clear_case),
    ("cxr_bilateral", get_cxr_bilateral_case),
    ("cxr_normal", get_cxr_normal_case),
    ("cxr_subtle", get_cxr_subtle_case),
    ("cxr_effusion", get_cxr_effusion_case),
]


@pytest.fixture(params=ALL_BUILDERS, ids=[b[0] for b in ALL_BUILDERS])
def demo_case(request):
    case_id, builder = request.param
    return case_id, builder()


class TestDemoCaseStructure:
    """All 5 cases have required fields and well-formed data."""

    def test_required_top_level_fields(self, demo_case):
        case_id, case = demo_case
        assert case["case_id"] == case_id
        assert case["patient_id"]
        assert case["demographics"]["age"] > 0
        assert case["demographics"]["sex"] in ("Male", "Female")
        assert case["presenting_complaint"]
        assert case["clinical_exam"]
        assert case["lab_results"]
        assert case["cxr"]
        assert case["past_medical_history"]
        assert case["social_history"]

    def test_fhir_bundle_present(self, demo_case):
        _, case = demo_case
        bundle = case["fhir_bundle"]
        assert bundle["resourceType"] == "Bundle"
        assert bundle["type"] == "collection"
        assert len(bundle["entry"]) > 0

    def test_fhir_has_patient_resource(self, demo_case):
        _, case = demo_case
        patients = [e for e in case["fhir_bundle"]["entry"]
                     if e["resource"]["resourceType"] == "Patient"]
        assert len(patients) == 1

    def test_fhir_has_observations(self, demo_case):
        _, case = demo_case
        observations = [e for e in case["fhir_bundle"]["entry"]
                         if e["resource"]["resourceType"] == "Observation"]
        # At least vitals (5) + labs (12) + eating (1) = 18
        assert len(observations) >= 18

    def test_fhir_has_document_references(self, demo_case):
        _, case = demo_case
        docs = [e for e in case["fhir_bundle"]["entry"]
                if e["resource"]["resourceType"] == "DocumentReference"]
        # Each case has 2-3 documents
        assert len(docs) >= 2

    def test_document_content_is_base64(self, demo_case):
        _, case = demo_case
        docs = [e for e in case["fhir_bundle"]["entry"]
                if e["resource"]["resourceType"] == "DocumentReference"]
        for doc_entry in docs:
            content = doc_entry["resource"]["content"][0]["attachment"]["data"]
            # Should be valid base64
            decoded = base64.b64decode(content)
            assert len(decoded) > 10

    def test_fhir_has_encounter(self, demo_case):
        _, case = demo_case
        encounters = [e for e in case["fhir_bundle"]["entry"]
                       if e["resource"]["resourceType"] == "Encounter"]
        assert len(encounters) == 1

    def test_lab_report_present(self, demo_case):
        _, case = demo_case
        lab_report = case["lab_report"]
        assert lab_report["format"] == "text"
        assert "CITY GENERAL HOSPITAL" in lab_report["content"]
        assert lab_report["source"] == "city_general_pathology"

    def test_lab_report_contains_values(self, demo_case):
        _, case = demo_case
        content = case["lab_report"]["content"]
        crp_val = case["lab_results"]["crp"]["value"]
        assert str(crp_val) in content

    def test_cxr_image_path_exists(self, demo_case):
        _, case = demo_case
        img_path = case["cxr"].get("image_path")
        assert img_path is not None
        assert os.path.exists(img_path), f"CXR image not found: {img_path}"

    def test_clinical_exam_complete(self, demo_case):
        _, case = demo_case
        exam = case["clinical_exam"]
        assert "respiratory_exam" in exam
        assert "observations" in exam
        assert "confusion_assessment" in exam
        obs = exam["observations"]
        for key in ["respiratory_rate", "systolic_bp", "diastolic_bp",
                     "heart_rate", "spo2", "temperature"]:
            assert key in obs

    def test_lab_results_have_standard_keys(self, demo_case):
        _, case = demo_case
        labs = case["lab_results"]
        for key in ["crp", "urea", "creatinine", "sodium", "potassium",
                     "wcc", "neutrophils", "haemoglobin", "platelets"]:
            assert key in labs, f"Missing lab key: {key}"
            assert "value" in labs[key]
            assert "unit" in labs[key]


class TestDemoCaseCURB65:
    """CURB65 scores compute correctly from case data."""

    EXPECTED_SCORES = {
        "cxr_clear": (0, "low"),       # C=0, U=0, R=0, B=0, 65=0
        "cxr_bilateral": (2, "moderate"),  # C=1, U=1, R=0, B=0, 65=1
        "cxr_normal": (0, "low"),      # C=0, U=0, R=0, B=0, 65=0
        "cxr_subtle": (0, "low"),      # C=0, U=0, R=0, B=0, 65=0
        "cxr_effusion": (2, "moderate"),   # C=1, U=1, R=0, B=0, 65=1
    }

    def test_curb65_score(self, demo_case):
        case_id, case = demo_case
        expected_score, expected_tier = self.EXPECTED_SCORES[case_id]

        exam = case["clinical_exam"]
        obs = exam["observations"]
        confusion = exam["confusion_assessment"]["confused"]

        result = compute_curb65({
            "confusion": confusion,
            "urea": case["lab_results"]["urea"]["value"],
            "respiratory_rate": obs["respiratory_rate"],
            "systolic_bp": obs["systolic_bp"],
            "diastolic_bp": obs["diastolic_bp"],
            "age": case["demographics"]["age"],
        })

        assert result["curb65"] == expected_score, \
            f"{case_id}: expected CURB65={expected_score}, got {result['curb65']}"
        assert result["severity_tier"] == expected_tier, \
            f"{case_id}: expected tier={expected_tier}, got {result['severity_tier']}"


class TestDemoCaseSpecifics:
    """Case-specific assertions."""

    def test_margaret_no_contradictions_expected(self):
        case = get_cxr_clear_case()
        assert case["case_id"] == "cxr_clear"
        assert case["demographics"]["age"] == 50
        assert case["demographics"]["sex"] == "Female"
        assert case["cxr"]["prior_image_path"] is not None

    def test_harold_has_hf_history(self):
        case = get_cxr_bilateral_case()
        assert case["case_id"] == "cxr_bilateral"
        comorbidities = case["past_medical_history"]["comorbidities"]
        assert any("heart failure" in c.lower() for c in comorbidities)
        # 3 documents: GP referral, HF discharge, clerking
        docs = [e for e in case["fhir_bundle"]["entry"]
                if e["resource"]["resourceType"] == "DocumentReference"]
        assert len(docs) == 3

    def test_susan_has_prior_effusion_history(self):
        case = get_cxr_normal_case()
        assert case["case_id"] == "cxr_normal"
        comorbidities = case["past_medical_history"]["comorbidities"]
        assert any("effusion" in c.lower() for c in comorbidities)
        # 3 documents: GP referral, respiratory OPD, clerking
        docs = [e for e in case["fhir_bundle"]["entry"]
                if e["resource"]["resourceType"] == "DocumentReference"]
        assert len(docs) == 3

    def test_david_has_no_comorbidities(self):
        case = get_cxr_subtle_case()
        assert case["case_id"] == "cxr_subtle"
        assert len(case["past_medical_history"]["comorbidities"]) == 0
        # 2 documents: GP referral, clerking
        docs = [e for e in case["fhir_bundle"]["entry"]
                if e["resource"]["resourceType"] == "DocumentReference"]
        assert len(docs) == 2

    def test_patricia_is_immunosuppressed(self):
        case = get_cxr_effusion_case()
        assert case["case_id"] == "cxr_effusion"
        assert case["social_history"]["immunosuppression"] is True
        comorbidities = case["past_medical_history"]["comorbidities"]
        assert any("methotrexate" in c.lower() for c in comorbidities)
        assert case["cxr"]["prior_image_path"] is None
        # 3 documents: GP referral, rheumatology OPD, clerking
        docs = [e for e in case["fhir_bundle"]["entry"]
                if e["resource"]["resourceType"] == "DocumentReference"]
        assert len(docs) == 3

    def test_all_cases_return_independent_copies(self):
        """Modifying one case should not affect another call."""
        case1 = get_cxr_clear_case()
        case1["demographics"]["age"] = 999
        case2 = get_cxr_clear_case()
        assert case2["demographics"]["age"] == 50

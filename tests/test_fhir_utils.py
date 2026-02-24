"""Tests for FHIR Bundle manipulation utilities."""

import pytest

from cap_agent.data.fhir_utils import (
    build_manifest,
    group_resources_by_type,
    render_resources_as_text,
    get_document_text,
    validate_and_repair_ehr_output,
    extract_lab_observations,
    validate_and_repair_lab_output,
    _is_vital_observation,
)
from cap_agent.data.synthetic import SYNTHETIC_FHIR_BUNDLE, SYNTHETIC_CLERKING_NOTE


@pytest.fixture
def bundle():
    """Return the synthetic FHIR bundle."""
    return SYNTHETIC_FHIR_BUNDLE


class TestBuildManifest:
    def test_counts_resource_types(self, bundle):
        manifest = build_manifest(bundle)
        assert "Patient: 1" in manifest
        assert "Condition: 2" in manifest
        assert "Observation: 18" in manifest  # 5 vitals + urea + CRP + 10 labs + eating
        assert "MedicationRequest: 3" in manifest

    def test_extracts_display_names(self, bundle):
        manifest = build_manifest(bundle)
        assert "COPD" in manifest
        assert "Type 2 diabetes mellitus" in manifest

    def test_empty_bundle(self):
        manifest = build_manifest({"entry": []})
        assert "Empty bundle" in manifest

    def test_missing_entry(self):
        manifest = build_manifest({})
        assert "Empty bundle" in manifest


class TestGroupResourcesByType:
    def test_correct_grouping(self, bundle):
        grouped = group_resources_by_type(bundle)
        assert "Patient" in grouped
        assert len(grouped["Patient"]) == 1
        assert len(grouped["Condition"]) == 2
        assert len(grouped["Observation"]) == 18
        assert "DocumentReference" in grouped

    def test_empty_bundle(self):
        grouped = group_resources_by_type({"entry": []})
        assert grouped == {}


class TestRenderResourcesAsText:
    def test_renders_patient(self, bundle):
        grouped = group_resources_by_type(bundle)
        text = render_resources_as_text(grouped["Patient"])
        assert "PATIENT:" in text
        assert "male" in text
        assert "1954-03-15" in text

    def test_renders_observation(self, bundle):
        grouped = group_resources_by_type(bundle)
        text = render_resources_as_text(grouped["Observation"])
        assert "VITAL:" in text
        assert "LAB:" in text
        assert "22" in text  # respiratory rate
        assert "105" in text  # systolic BP

    def test_renders_condition(self, bundle):
        grouped = group_resources_by_type(bundle)
        text = render_resources_as_text(grouped["Condition"])
        assert "CONDITION:" in text
        assert "COPD" in text
        assert "SNOMED" in text

    def test_renders_compact(self, bundle):
        """Rendered text should be reasonably compact."""
        grouped = group_resources_by_type(bundle)
        all_resources = []
        for rtype, rlist in grouped.items():
            if rtype != "DocumentReference":
                all_resources.extend(rlist)
        text = render_resources_as_text(all_resources)
        # Should be under ~3500 chars (well within 800 tokens)
        assert len(text) < 3500


class TestGetDocumentText:
    def test_extracts_clerking_note(self, bundle):
        text = get_document_text(bundle)
        assert len(text) > 100
        assert "ACUTE MEDICAL UNIT" in text
        assert "Robert JAMES" in text

    def test_no_document_reference(self):
        text = get_document_text({"entry": []})
        assert text == ""

    def test_bundle_without_document(self):
        bundle = {
            "entry": [
                {"resource": {"resourceType": "Patient", "gender": "male"}}
            ]
        }
        text = get_document_text(bundle)
        assert text == ""


class TestValidateAndRepair:
    def test_coerces_types(self):
        """String values should be coerced to correct types."""
        raw = {
            "demographics": {
                "age": "72",
                "sex": "male",
                "pregnancy": "false",
                "oral_tolerance": "true",
                "allergies": [],
                "comorbidities": ["COPD"],
                "recent_antibiotics": [],
                "travel_history": [],
            },
            "clinical_exam": {
                "respiratory_exam": {"crackles": "true", "crackles_location": "right"},
                "observations": {
                    "respiratory_rate": "22",
                    "systolic_bp": "105",
                    "diastolic_bp": "65",
                    "heart_rate": "98",
                    "spo2": "94",
                    "temperature": "38.4",
                },
                "confusion_status": {"present": "false", "amt_score": "9"},
            },
            "curb65_variables": {
                "confusion": "false",
                "urea": "8.2",
                "respiratory_rate": "22",
                "systolic_bp": "105",
                "diastolic_bp": "65",
                "age": "72",
            },
        }
        repaired, gaps = validate_and_repair_ehr_output(raw)

        assert repaired["demographics"]["age"] == 72
        assert isinstance(repaired["demographics"]["age"], int)
        assert repaired["demographics"]["pregnancy"] is False
        assert repaired["demographics"]["oral_tolerance"] is True
        assert repaired["clinical_exam"]["observations"]["respiratory_rate"] == 22
        assert isinstance(repaired["clinical_exam"]["observations"]["temperature"], float)
        assert repaired["curb65_variables"]["urea"] == 8.2
        assert repaired["curb65_variables"]["confusion"] is False

    def test_fills_defaults(self):
        """Missing keys should get safe defaults."""
        raw = {}
        repaired, gaps = validate_and_repair_ehr_output(raw)

        assert "demographics" in repaired
        assert "clinical_exam" in repaired
        assert "curb65_variables" in repaired
        # Defaults
        assert repaired["demographics"]["sex"] == "unknown"
        assert repaired["clinical_exam"]["observations"]["respiratory_rate"] == 20
        assert repaired["curb65_variables"]["confusion"] is False

    def test_normalizes_nkda(self):
        """NKDA entries should be removed from allergies."""
        raw = {
            "demographics": {
                "age": 72,
                "sex": "Male",
                "allergies": [
                    {"drug": "NKDA", "reaction_type": "none", "severity": "none"},
                ],
            },
            "clinical_exam": {},
            "curb65_variables": {},
        }
        repaired, gaps = validate_and_repair_ehr_output(raw)
        assert repaired["demographics"]["allergies"] == []

    def test_normalizes_nkda_string(self):
        """NKDA as string entries should be removed."""
        raw = {
            "demographics": {
                "age": 72,
                "sex": "Male",
                "allergies": ["NKDA"],
            },
            "clinical_exam": {},
            "curb65_variables": {},
        }
        repaired, gaps = validate_and_repair_ehr_output(raw)
        assert repaired["demographics"]["allergies"] == []

    def test_tracks_gaps(self):
        """Missing critical fields should be reported as data gaps."""
        raw = {
            "demographics": {},
            "clinical_exam": {
                "observations": {},
            },
            "curb65_variables": {},
        }
        repaired, gaps = validate_and_repair_ehr_output(raw)
        assert any("age" in g for g in gaps)
        assert any("sex" in g for g in gaps)

    def test_normalizes_gender_to_sex(self):
        """'gender' key should be mapped to 'sex'."""
        raw = {
            "demographics": {"age": 72, "gender": "male"},
            "clinical_exam": {},
            "curb65_variables": {},
        }
        repaired, gaps = validate_and_repair_ehr_output(raw)
        assert repaired["demographics"]["sex"] == "Male"

    def test_preserves_real_allergies(self):
        """Real allergies should be preserved after NKDA filtering."""
        raw = {
            "demographics": {
                "age": 65,
                "sex": "Female",
                "allergies": [
                    {"drug": "Penicillin", "reaction_type": "rash", "severity": "mild"},
                    {"drug": "NKDA"},
                ],
            },
            "clinical_exam": {},
            "curb65_variables": {},
        }
        repaired, gaps = validate_and_repair_ehr_output(raw)
        assert len(repaired["demographics"]["allergies"]) == 1
        assert repaired["demographics"]["allergies"][0]["drug"] == "Penicillin"

    def test_eating_independently_coerced_from_string(self):
        """String 'true'/'false' should be coerced to bool for eating_independently."""
        raw = {
            "demographics": {"age": 72, "sex": "Male", "eating_independently": "false"},
            "clinical_exam": {},
            "curb65_variables": {},
        }
        repaired, _ = validate_and_repair_ehr_output(raw)
        assert repaired["demographics"]["eating_independently"] is False

    def test_eating_independently_defaults_true(self):
        """Missing eating_independently should default to True (safe default)."""
        raw = {
            "demographics": {"age": 72, "sex": "Male"},
            "clinical_exam": {},
            "curb65_variables": {},
        }
        repaired, _ = validate_and_repair_ehr_output(raw)
        assert repaired["demographics"]["eating_independently"] is True

    def test_eating_independently_preserves_false(self):
        """Explicitly False eating_independently should be preserved."""
        raw = {
            "demographics": {"age": 72, "sex": "Male", "eating_independently": False},
            "clinical_exam": {},
            "curb65_variables": {},
        }
        repaired, _ = validate_and_repair_ehr_output(raw)
        assert repaired["demographics"]["eating_independently"] is False


class TestLabObservationRendering:
    """Tests for LAB/VITAL prefix classification in rendered text."""

    def test_vitals_get_vital_prefix(self, bundle):
        """Vital sign Observations should render with VITAL: prefix."""
        grouped = group_resources_by_type(bundle)
        for obs in grouped["Observation"]:
            obs_id = obs.get("id", "")
            if obs_id in ("obs-rr", "obs-bp", "obs-hr", "obs-spo2", "obs-temp"):
                assert _is_vital_observation(obs), f"{obs_id} should be vital"

    def test_labs_get_lab_prefix(self, bundle):
        """Lab Observations should render with LAB: prefix."""
        grouped = group_resources_by_type(bundle)
        for obs in grouped["Observation"]:
            obs_id = obs.get("id", "")
            if obs_id in ("obs-urea", "obs-crp", "obs-creatinine", "obs-egfr"):
                assert not _is_vital_observation(obs), f"{obs_id} should be lab"

    def test_all_10_new_labs_get_lab_prefix(self, bundle):
        """All 10 newly added lab Observations should have LAB: prefix."""
        new_lab_ids = {
            "obs-creatinine", "obs-egfr", "obs-sodium", "obs-potassium",
            "obs-wcc", "obs-neut", "obs-hb", "obs-plt", "obs-pct", "obs-lactate",
        }
        grouped = group_resources_by_type(bundle)
        text = render_resources_as_text(grouped["Observation"])
        for obs in grouped["Observation"]:
            if obs.get("id") in new_lab_ids:
                assert not _is_vital_observation(obs), f"{obs['id']} should be lab"
        # Verify LAB: prefix appears in rendered text for lab values
        assert text.count("LAB:") >= 12  # urea + crp + 10 new labs


class TestExtractLabObservations:
    """Tests for extract_lab_observations()."""

    def test_returns_lab_observations_only(self, bundle):
        """Should return lab Observations, excluding vitals."""
        labs = extract_lab_observations(bundle)
        # 12 labs: urea, crp, creatinine, egfr, sodium, potassium,
        # wcc, neut, hb, plt, pct, lactate
        assert len(labs) == 12
        for lab in labs:
            assert lab["resourceType"] == "Observation"
            assert not _is_vital_observation(lab)

    def test_excludes_vital_signs(self, bundle):
        """Vital sign Observations (RR, BP, HR, SpO2, Temp) should be excluded."""
        labs = extract_lab_observations(bundle)
        lab_ids = {lab.get("id") for lab in labs}
        vital_ids = {"obs-rr", "obs-bp", "obs-hr", "obs-spo2", "obs-temp"}
        assert lab_ids.isdisjoint(vital_ids)


class TestValidateAndRepairLabOutput:
    """Tests for validate_and_repair_lab_output()."""

    def test_normalizes_names(self):
        """Alternative test names should be normalized to canonical keys."""
        raw = {
            "lab_values": {
                "C-reactive protein": {"value": 186, "unit": "mg/L", "reference_range": "<5", "abnormal_flag": True},
                "WBC": {"value": 15.3, "unit": "x10^9/L", "reference_range": "4.0-11.0", "abnormal_flag": True},
            }
        }
        normalized, gaps = validate_and_repair_lab_output(raw)
        assert "crp" in normalized
        assert "wcc" in normalized
        assert normalized["crp"]["value"] == 186.0

    def test_coerces_types(self):
        """String values should be coerced to correct types."""
        raw = {
            "lab_values": {
                "crp": {"value": "186", "unit": "mg/L", "reference_range": "<5", "abnormal_flag": "true"},
                "urea": {"value": "8.2", "unit": "mmol/L", "reference_range": "2.5-7.8", "abnormal_flag": "true"},
            }
        }
        normalized, gaps = validate_and_repair_lab_output(raw)
        assert normalized["crp"]["value"] == 186.0
        assert isinstance(normalized["crp"]["value"], float)
        assert normalized["crp"]["abnormal_flag"] is True
        assert normalized["urea"]["value"] == 8.2

    def test_reports_missing_critical_tests(self):
        """Missing critical tests should be reported as data gaps."""
        raw = {"lab_values": {
            "sodium": {"value": 136, "unit": "mmol/L", "reference_range": "133-146", "abnormal_flag": False},
        }}
        normalized, gaps = validate_and_repair_lab_output(raw)
        assert any("crp" in g for g in gaps)
        assert any("urea" in g for g in gaps)
        assert any("egfr" in g for g in gaps)
        assert any("lactate" in g for g in gaps)

    def test_handles_abnormal_key_variant(self):
        """MedGemma may output 'abnormal' instead of 'abnormal_flag'."""
        raw = {
            "lab_values": {
                "crp": {"value": 186, "unit": "mg/L", "reference_range": "<5", "abnormal": True},
            }
        }
        normalized, gaps = validate_and_repair_lab_output(raw)
        assert normalized["crp"]["abnormal_flag"] is True

    def test_handles_empty_input(self):
        """Empty input should return empty dict with gaps for all critical tests."""
        normalized, gaps = validate_and_repair_lab_output({})
        assert normalized == {}
        assert len(gaps) == 4  # crp, egfr, lactate, urea

    def test_handles_direct_dict_without_wrapper(self):
        """Should handle raw dict without 'lab_values' wrapper key."""
        raw = {
            "crp": {"value": 186, "unit": "mg/L", "reference_range": "<5", "abnormal_flag": True},
            "urea": {"value": 8.2, "unit": "mmol/L", "reference_range": "2.5-7.8", "abnormal_flag": True},
        }
        normalized, gaps = validate_and_repair_lab_output(raw)
        assert "crp" in normalized
        assert "urea" in normalized
        assert normalized["crp"]["value"] == 186.0

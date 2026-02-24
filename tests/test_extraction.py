"""Tests for async extraction tools."""

import json
import pytest
from unittest.mock import patch, MagicMock

from cap_agent.data.extraction import (
    mock_extract_clinical_notes,
    mock_extract_lab_results,
    mock_analyze_cxr,
    extract_lab_results,
    analyze_cxr,
    extract_clinical_notes,
)
from cap_agent.data.synthetic import get_synthetic_case, get_synthetic_fhir_case


@pytest.fixture
def case_data():
    return get_synthetic_case()


@pytest.fixture
def tmp_cxr_image(tmp_path):
    """Create a minimal 10x10 RGB PNG for testing."""
    from PIL import Image
    img = Image.new("RGB", (10, 10), color=(128, 128, 128))
    path = tmp_path / "test_cxr.png"
    img.save(path)
    return str(path)


@pytest.fixture
def tmp_prior_image(tmp_path):
    """Create a second minimal PNG for longitudinal testing."""
    from PIL import Image
    img = Image.new("RGB", (10, 10), color=(64, 64, 64))
    path = tmp_path / "prior_cxr.png"
    img.save(path)
    return str(path)


# Classification JSON that MedGemma would return
MOCK_CLASSIFICATION_JSON = json.dumps({
    "consolidation": {
        "present": True,
        "confidence": "moderate",
        "location": "right lower lobe",
        "description": "Patchy air-space opacification",
    },
    "pleural_effusion": {"present": False, "confidence": "high"},
    "cardiomegaly": {"present": False, "confidence": "high"},
    "edema": {"present": False, "confidence": "high"},
    "atelectasis": {"present": False, "confidence": "moderate"},
    "image_quality": {
        "projection": "PA",
        "rotation": "minimal",
        "penetration": "adequate",
    },
})

MOCK_LOCALIZATION_JSON = json.dumps([
    {"box_2d": [450, 550, 750, 850], "label": "consolidation"}
])

MOCK_LONGITUDINAL_JSON = json.dumps({
    "consolidation": {"change": "new", "description": "New right lower lobe consolidation"},
    "pleural_effusion": {"change": "unchanged", "description": "No effusion on either study"},
    "cardiomegaly": {"change": "unchanged", "description": "Normal heart size"},
    "edema": {"change": "unchanged", "description": "No edema"},
    "atelectasis": {"change": "unchanged", "description": "No atelectasis"},
})


class TestMockExtractClinicalNotes:
    @pytest.mark.asyncio
    async def test_returns_tool_result_shape(self, case_data):
        result = await mock_extract_clinical_notes(case_data)
        assert result["tool_name"] == "ehr_qa_extraction"
        assert result["status"] == "success"
        assert "summary" in result
        assert "raw_output" in result

    @pytest.mark.asyncio
    async def test_extracts_demographics(self, case_data):
        result = await mock_extract_clinical_notes(case_data)
        demo = result["raw_output"]["demographics"]
        assert demo["age"] == 72
        assert demo["sex"] == "Male"

    @pytest.mark.asyncio
    async def test_extracts_curb65_variables(self, case_data):
        result = await mock_extract_clinical_notes(case_data)
        cv = result["raw_output"]["curb65_variables"]
        assert cv["confusion"] is False
        assert cv["urea"] == 8.2
        assert cv["age"] == 72

    @pytest.mark.asyncio
    async def test_extracts_clinical_exam(self, case_data):
        result = await mock_extract_clinical_notes(case_data)
        exam = result["raw_output"]["clinical_exam"]
        assert exam["respiratory_exam"]["crackles"] is True
        assert "observations" in exam

    @pytest.mark.asyncio
    async def test_extracts_smoking_status(self, case_data):
        result = await mock_extract_clinical_notes(case_data)
        demo = result["raw_output"]["demographics"]
        assert "smoking_status" in demo
        assert demo["smoking_status"] == "former"

    @pytest.mark.asyncio
    async def test_extracts_eating_independently(self, case_data):
        result = await mock_extract_clinical_notes(case_data)
        demo = result["raw_output"]["demographics"]
        assert "eating_independently" in demo
        assert demo["eating_independently"] is True


class TestMockExtractLabResults:
    @pytest.mark.asyncio
    async def test_returns_tool_result_shape(self, case_data):
        result = await mock_extract_lab_results(case_data)
        assert result["tool_name"] == "lab_extraction"
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_extracts_all_labs(self, case_data):
        result = await mock_extract_lab_results(case_data)
        labs = result["raw_output"]["lab_values"]
        assert "crp" in labs
        assert "urea" in labs
        assert labs["crp"]["value"] == 186
        assert labs["crp"]["abnormal_flag"] is True

    @pytest.mark.asyncio
    async def test_summary_contains_counts(self, case_data):
        result = await mock_extract_lab_results(case_data)
        assert "12 lab values" in result["summary"]
        assert "abnormal" in result["summary"]


class TestMockAnalyzeCXR:
    """Tests for mock CXR analysis passthrough."""

    @pytest.mark.asyncio
    async def test_returns_correct_shape(self, case_data):
        """ToolResult contract: tool_name, status, summary, raw_output."""
        result = await mock_analyze_cxr(case_data)
        assert result["tool_name"] == "cxr_classification"
        assert result["status"] == "success"
        assert "summary" in result
        assert "raw_output" in result
        assert "cxr_analysis" in result["raw_output"]

    @pytest.mark.asyncio
    async def test_passes_through_findings(self, case_data):
        """Consolidation present in source → present in output."""
        result = await mock_analyze_cxr(case_data)
        cxr = result["raw_output"]["cxr_analysis"]
        # case_data has nested cxr.findings.consolidation
        assert cxr["consolidation"]["present"] is True
        assert cxr["consolidation"]["location"] == "right lower lobe"

    @pytest.mark.asyncio
    async def test_empty_case(self):
        """No CXR data → empty analysis, no crash."""
        result = await mock_analyze_cxr({})
        assert result["status"] == "success"
        assert result["raw_output"]["cxr_analysis"] == {}
        assert "No significant findings" in result["summary"]

    @pytest.mark.asyncio
    async def test_summary_lists_positive_findings(self, case_data):
        """Summary includes names of present findings."""
        result = await mock_analyze_cxr(case_data)
        assert "consolidation" in result["summary"]

    @pytest.mark.asyncio
    async def test_flat_cxr_layout(self):
        """Flat layout (cxr.consolidation, not cxr.findings.consolidation)."""
        flat_case = {
            "cxr": {
                "consolidation": {"present": True, "confidence": "high", "location": "bilateral"},
                "pleural_effusion": {"present": False, "confidence": "high"},
            }
        }
        result = await mock_analyze_cxr(flat_case)
        cxr = result["raw_output"]["cxr_analysis"]
        assert cxr["consolidation"]["present"] is True


class TestAnalyzeCXR:
    """Tests for the real 3-stage CXR analysis pipeline (mocking call_medgemma)."""

    @pytest.mark.asyncio
    @patch("cap_agent.models.medgemma.call_medgemma")
    async def test_returns_tool_result_shape(self, mock_call, case_data, tmp_cxr_image):
        """Classification mock → check ToolResult contract."""
        mock_call.return_value = f"```json\n{MOCK_CLASSIFICATION_JSON}\n```"
        case_data["cxr"]["image_path"] = tmp_cxr_image
        result = await analyze_cxr(case_data)

        assert result["tool_name"] == "cxr_classification"
        assert result["status"] in ("success", "partial")
        assert "summary" in result
        assert "raw_output" in result
        assert "cxr_analysis" in result["raw_output"]

    @pytest.mark.asyncio
    @patch("cap_agent.models.medgemma.call_medgemma")
    async def test_classification_extracts_consolidation(self, mock_call, case_data, tmp_cxr_image):
        """Validate parsed finding fields from classification."""
        mock_call.return_value = f"```json\n{MOCK_CLASSIFICATION_JSON}\n```"
        case_data["cxr"]["image_path"] = tmp_cxr_image
        result = await analyze_cxr(case_data)

        cxr = result["raw_output"]["cxr_analysis"]
        assert cxr["consolidation"]["present"] is True
        assert cxr["consolidation"]["confidence"] == "moderate"
        assert cxr["consolidation"]["location"] == "right lower lobe"
        assert cxr["image_quality"]["projection"] == "PA"

    @pytest.mark.asyncio
    @patch("cap_agent.models.medgemma.call_medgemma")
    async def test_localization_adds_bounding_box(self, mock_call, case_data, tmp_cxr_image):
        """Classification + localization → check bounding_box key added."""
        def side_effect(prompt, max_new_tokens=1500, images=None, enable_thinking=True, **kwargs):
            if "Locate the" in prompt:
                return f"```json\n{MOCK_LOCALIZATION_JSON}\n```"
            return f"```json\n{MOCK_CLASSIFICATION_JSON}\n```"

        mock_call.side_effect = side_effect
        case_data["cxr"]["image_path"] = tmp_cxr_image
        result = await analyze_cxr(case_data)

        cxr = result["raw_output"]["cxr_analysis"]
        assert "bounding_box" in cxr["consolidation"]
        assert cxr["consolidation"]["bounding_box"] == [450, 550, 750, 850]
        assert result["status"] == "success"

    @pytest.mark.asyncio
    @patch("cap_agent.models.medgemma.call_medgemma")
    async def test_classification_failure_returns_error(self, mock_call, case_data, tmp_cxr_image):
        """Classification raises → status='error'."""
        mock_call.side_effect = RuntimeError("GPU OOM")
        case_data["cxr"]["image_path"] = tmp_cxr_image
        result = await analyze_cxr(case_data)

        assert result["status"] == "error"
        assert "classification failed" in result["summary"].lower()

    @pytest.mark.asyncio
    @patch("cap_agent.models.medgemma.call_medgemma")
    async def test_localization_failure_returns_partial(self, mock_call, case_data, tmp_cxr_image):
        """Classification OK, localization raises → status='partial', classification preserved."""
        call_count = [0]

        def side_effect(prompt, max_new_tokens=1500, images=None, enable_thinking=True, **kwargs):
            call_count[0] += 1
            if "Locate the" in prompt:
                raise RuntimeError("Localization OOM")
            return f"```json\n{MOCK_CLASSIFICATION_JSON}\n```"

        mock_call.side_effect = side_effect
        case_data["cxr"]["image_path"] = tmp_cxr_image
        result = await analyze_cxr(case_data)

        assert result["status"] == "partial"
        # Classification data preserved despite localization failure
        cxr = result["raw_output"]["cxr_analysis"]
        assert cxr["consolidation"]["present"] is True

    @pytest.mark.asyncio
    async def test_missing_image_path_returns_error(self, case_data):
        """Empty image path → immediate error."""
        case_data["cxr"]["image_path"] = ""
        result = await analyze_cxr(case_data)
        assert result["status"] == "error"
        assert "No CXR image path" in result["summary"]

    @pytest.mark.asyncio
    async def test_missing_cxr_section_returns_error(self, case_data):
        """No cxr key → error."""
        case_data.pop("cxr", None)
        result = await analyze_cxr(case_data)
        assert result["status"] == "error"

    @pytest.mark.asyncio
    @patch("cap_agent.models.medgemma.call_medgemma")
    async def test_longitudinal_comparison(self, mock_call, case_data, tmp_cxr_image, tmp_prior_image):
        """All 3 stages → check longitudinal_comparison in output."""
        def side_effect(prompt, max_new_tokens=1500, images=None, enable_thinking=True, **kwargs):
            if "Locate the" in prompt:
                return f"```json\n{MOCK_LOCALIZATION_JSON}\n```"
            if "PRIOR" in prompt:
                return f"```json\n{MOCK_LONGITUDINAL_JSON}\n```"
            return f"```json\n{MOCK_CLASSIFICATION_JSON}\n```"

        mock_call.side_effect = side_effect
        case_data["cxr"]["image_path"] = tmp_cxr_image
        case_data["cxr"]["prior_image_path"] = tmp_prior_image
        result = await analyze_cxr(case_data)

        cxr = result["raw_output"]["cxr_analysis"]
        assert "longitudinal_comparison" in cxr
        assert cxr["longitudinal_comparison"]["consolidation"]["change"] == "new"
        assert result["status"] == "success"

    @pytest.mark.asyncio
    @patch("cap_agent.models.medgemma.call_medgemma")
    async def test_no_positive_findings_skips_localization(self, mock_call, case_data, tmp_cxr_image):
        """All-negative CXR → only 1 call (classification), no localization calls."""
        negative_json = json.dumps({
            "consolidation": {"present": False, "confidence": "high", "location": "not found", "description": ""},
            "pleural_effusion": {"present": False, "confidence": "high"},
            "cardiomegaly": {"present": False, "confidence": "high"},
            "edema": {"present": False, "confidence": "high"},
            "atelectasis": {"present": False, "confidence": "high"},
            "image_quality": {"projection": "PA", "rotation": "none", "penetration": "adequate"},
        })
        mock_call.return_value = f"```json\n{negative_json}\n```"
        case_data["cxr"]["image_path"] = tmp_cxr_image
        result = await analyze_cxr(case_data)

        assert mock_call.call_count == 1  # Only classification, no localization
        assert result["status"] == "success"

    @pytest.mark.asyncio
    @patch("cap_agent.models.medgemma.pad_image_to_square")
    @patch("cap_agent.models.medgemma.call_medgemma")
    async def test_image_loaded_and_preprocessed(self, mock_call, mock_pad, case_data, tmp_cxr_image):
        """Verify pad_image_to_square is called on the loaded image."""
        from PIL import Image
        # Make pad return the image unchanged
        mock_pad.side_effect = lambda img: img
        mock_call.return_value = f"```json\n{MOCK_CLASSIFICATION_JSON}\n```"
        case_data["cxr"]["image_path"] = tmp_cxr_image
        result = await analyze_cxr(case_data)

        mock_pad.assert_called_once()
        # The argument should be a PIL Image
        assert isinstance(mock_pad.call_args[0][0], Image.Image)


# --- Real EHR extraction tests (mocked MedGemma) ---

MOCK_IDENTIFY = json.dumps([
    "Patient", "Condition", "Observation",
    "AllergyIntolerance", "MedicationRequest", "DocumentReference",
])

MOCK_NARRATIVE_FACTS = (
    "1. RESPIRATORY EXAMINATION: Crackles right lower zone. "
    "Bronchial breathing right lower zone. Dullness right base.\n"
    "2. CONFUSION / MENTAL STATUS: AMT 9/10, not confused. GCS 15.\n"
    "3. ALLERGIES: NKDA\n"
    "4. PAST MEDICAL HISTORY: COPD (moderate), Type 2 diabetes mellitus. "
    "Ex-smoker 30 pack-years, quit 5 years ago.\n"
    "5. DRUG HISTORY: Salbutamol 100mcg PRN, Tiotropium 18mcg OD, Metformin 500mg BD.\n"
    "6. SOCIAL HISTORY: Lives independently. Not pregnant. Tolerates oral. "
    "No recent travel.\n"
    "7. PRESENTING COMPLAINT: 3-day productive cough, fever, increasing breathlessness."
)

MOCK_STRUCTURED_FACTS = (
    "1. DEMOGRAPHICS: Robert James, male, born 1954-03-15 (age 72).\n"
    "2. VITAL SIGNS: RR 22/min, BP 105/65 mmHg, HR 98/min, SpO2 94%, Temp 38.4C.\n"
    "3. LAB VALUES: Urea 8.2 mmol/L, CRP 186 mg/L.\n"
    "4. CONDITIONS: COPD (moderate, active), Type 2 diabetes mellitus (active).\n"
    "5. ALLERGIES: NKDA (No known allergy recorded).\n"
    "6. MEDICATIONS: Salbutamol 100mcg inhaler PRN, Tiotropium 18mcg OD, "
    "Metformin 500mg BD."
)

MOCK_SYNTHESIS = json.dumps({
    "demographics": {
        "age": 72,
        "sex": "Male",
        "allergies": [],
        "comorbidities": ["COPD (moderate)", "Type 2 diabetes mellitus"],
        "recent_antibiotics": [],
        "pregnancy": False,
        "oral_tolerance": True,
        "travel_history": [],
        "smoking_status": "former",
    },
    "clinical_exam": {
        "respiratory_exam": {
            "crackles": True,
            "crackles_location": "right lower zone",
            "bronchial_breathing": True,
            "bronchial_breathing_location": "right lower zone",
        },
        "observations": {
            "respiratory_rate": 22,
            "systolic_bp": 105,
            "diastolic_bp": 65,
            "heart_rate": 98,
            "spo2": 94,
            "temperature": 38.4,
            "supplemental_o2": "room air",
        },
        "confusion_status": {
            "present": False,
            "amt_score": 9,
        },
    },
    "curb65_variables": {
        "confusion": False,
        "urea": 8.2,
        "respiratory_rate": 22,
        "systolic_bp": 105,
        "diastolic_bp": 65,
        "age": 72,
    },
})


@pytest.fixture
def fhir_case_data():
    return get_synthetic_fhir_case()


def _make_side_effect(*responses):
    """Build a side_effect function that returns responses in order."""
    call_idx = [0]

    def side_effect(prompt, max_new_tokens=1500, images=None, enable_thinking=True, **kwargs):
        idx = call_idx[0]
        call_idx[0] += 1
        if idx < len(responses):
            return responses[idx]
        return responses[-1]

    return side_effect


class TestExtractClinicalNotes:
    """Tests for real MedGemma EHR QA extraction (mocked call_medgemma)."""

    @pytest.mark.asyncio
    @patch("cap_agent.models.medgemma.call_medgemma")
    async def test_returns_tool_result_shape(self, mock_call, fhir_case_data):
        """3 calls made, ToolResult contract met."""
        mock_call.side_effect = _make_side_effect(
            MOCK_NARRATIVE_FACTS,
            MOCK_STRUCTURED_FACTS,
            f"```json\n{MOCK_SYNTHESIS}\n```",
        )
        result = await extract_clinical_notes(fhir_case_data)

        assert result["tool_name"] == "ehr_qa_extraction"
        assert result["status"] in ("success", "partial")
        assert "summary" in result
        assert "raw_output" in result
        assert "demographics" in result["raw_output"]
        assert "clinical_exam" in result["raw_output"]
        assert "curb65_variables" in result["raw_output"]
        assert mock_call.call_count == 3

    @pytest.mark.asyncio
    @patch("cap_agent.models.medgemma.call_medgemma")
    async def test_output_matches_expected_values(self, mock_call, fhir_case_data):
        """Demographics, exam, curb65 have correct values."""
        mock_call.side_effect = _make_side_effect(
            MOCK_NARRATIVE_FACTS,
            MOCK_STRUCTURED_FACTS,
            f"```json\n{MOCK_SYNTHESIS}\n```",
        )
        result = await extract_clinical_notes(fhir_case_data)
        raw = result["raw_output"]

        assert raw["demographics"]["age"] == 72
        assert raw["demographics"]["sex"] == "Male"
        assert raw["demographics"]["allergies"] == []
        assert raw["clinical_exam"]["respiratory_exam"]["crackles"] is True
        assert raw["curb65_variables"]["urea"] == 8.2
        assert raw["curb65_variables"]["confusion"] is False

    @pytest.mark.asyncio
    @patch("cap_agent.models.medgemma.call_medgemma")
    async def test_narrative_failure_partial(self, mock_call, fhir_case_data):
        """Call 1 raises → status='partial'."""
        call_idx = [0]

        def side_effect(prompt, max_new_tokens=1500, images=None, enable_thinking=True, **kwargs):
            idx = call_idx[0]
            call_idx[0] += 1
            if idx == 0:
                raise RuntimeError("Narrative extraction failed")
            if idx == 1:
                return MOCK_STRUCTURED_FACTS
            return f"```json\n{MOCK_SYNTHESIS}\n```"

        mock_call.side_effect = side_effect
        result = await extract_clinical_notes(fhir_case_data)

        assert result["status"] == "partial"
        assert "demographics" in result["raw_output"]

    @pytest.mark.asyncio
    @patch("cap_agent.models.medgemma.call_medgemma")
    async def test_structured_failure_partial(self, mock_call, fhir_case_data):
        """Call 2 raises → status='partial'."""
        call_idx = [0]

        def side_effect(prompt, max_new_tokens=1500, images=None, enable_thinking=True, **kwargs):
            idx = call_idx[0]
            call_idx[0] += 1
            if idx == 0:
                return MOCK_NARRATIVE_FACTS
            if idx == 1:
                raise RuntimeError("Structured extraction failed")
            return f"```json\n{MOCK_SYNTHESIS}\n```"

        mock_call.side_effect = side_effect
        result = await extract_clinical_notes(fhir_case_data)

        assert result["status"] == "partial"
        assert "demographics" in result["raw_output"]

    @pytest.mark.asyncio
    @patch("cap_agent.models.medgemma.call_medgemma")
    async def test_both_fetch_fail_error(self, mock_call, fhir_case_data):
        """Calls 1+2 raise → status='error'."""
        mock_call.side_effect = RuntimeError("Extraction failed")
        result = await extract_clinical_notes(fhir_case_data)

        assert result["status"] == "error"
        assert "Both" in result["summary"] or "failed" in result["summary"].lower()

    @pytest.mark.asyncio
    @patch("cap_agent.models.medgemma.call_medgemma")
    async def test_synthesis_failure_error(self, mock_call, fhir_case_data):
        """Call 3 raises → status='error'."""
        call_idx = [0]

        def side_effect(prompt, max_new_tokens=1500, images=None, enable_thinking=True, **kwargs):
            idx = call_idx[0]
            call_idx[0] += 1
            if idx == 0:
                return MOCK_NARRATIVE_FACTS
            if idx == 1:
                return MOCK_STRUCTURED_FACTS
            raise RuntimeError("Synthesis OOM")

        mock_call.side_effect = side_effect
        result = await extract_clinical_notes(fhir_case_data)

        assert result["status"] == "error"

    @pytest.mark.asyncio
    @patch("cap_agent.models.medgemma.call_medgemma")
    async def test_synthesis_malformed_partial(self, mock_call, fhir_case_data):
        """Call 3 returns bad JSON → validate_and_repair fixes, status='partial'."""
        mock_call.side_effect = _make_side_effect(
            MOCK_NARRATIVE_FACTS,
            MOCK_STRUCTURED_FACTS,
            # Partial JSON missing most fields
            '```json\n{"demographics": {"age": 72, "gender": "male"}}\n```',
        )
        result = await extract_clinical_notes(fhir_case_data)

        # Should be partial due to missing fields filled by repair
        assert result["status"] == "partial"
        raw = result["raw_output"]
        assert raw["demographics"]["age"] == 72
        # Repaired defaults filled in
        assert "clinical_exam" in raw
        assert "curb65_variables" in raw

    @pytest.mark.asyncio
    async def test_no_fhir_bundle_error(self):
        """Missing fhir_bundle key → status='error'."""
        case_data = {"demographics": {"age": 72}}
        result = await extract_clinical_notes(case_data)

        assert result["status"] == "error"
        assert "No FHIR bundle" in result["summary"]


# --- Real Lab extraction tests (mocked MedGemma) ---

MOCK_LAB_FACTS = (
    "CRP: 186 mg/L (ref <5) — ABNORMAL\n"
    "Urea: 8.2 mmol/L (ref 2.5-7.8) — ABNORMAL\n"
    "Creatinine: 98 umol/L (ref 62-106) — normal\n"
    "eGFR: 62 mL/min/1.73m2 (ref >90) — ABNORMAL\n"
    "Sodium: 136 mmol/L (ref 133-146) — normal\n"
    "Potassium: 4.1 mmol/L (ref 3.5-5.3) — normal\n"
    "White cell count: 15.3 x10^9/L (ref 4.0-11.0) — ABNORMAL\n"
    "Neutrophils: 12.8 x10^9/L (ref 2.0-7.5) — ABNORMAL\n"
    "Haemoglobin: 138 g/L (ref 130-170) — normal\n"
    "Platelets: 245 x10^9/L (ref 150-400) — normal\n"
    "Procalcitonin: 0.8 ng/mL (ref <0.1) — ABNORMAL\n"
    "Lactate: 1.4 mmol/L (ref <2.0) — normal"
)

MOCK_LAB_SYNTHESIS = json.dumps({
    "lab_values": {
        "crp": {"value": 186, "unit": "mg/L", "reference_range": "<5", "abnormal_flag": True},
        "urea": {"value": 8.2, "unit": "mmol/L", "reference_range": "2.5-7.8", "abnormal_flag": True},
        "creatinine": {"value": 98, "unit": "umol/L", "reference_range": "62-106", "abnormal_flag": False},
        "egfr": {"value": 62, "unit": "mL/min/1.73m2", "reference_range": ">90", "abnormal_flag": True},
        "sodium": {"value": 136, "unit": "mmol/L", "reference_range": "133-146", "abnormal_flag": False},
        "potassium": {"value": 4.1, "unit": "mmol/L", "reference_range": "3.5-5.3", "abnormal_flag": False},
        "wcc": {"value": 15.3, "unit": "x10^9/L", "reference_range": "4.0-11.0", "abnormal_flag": True},
        "neutrophils": {"value": 12.8, "unit": "x10^9/L", "reference_range": "2.0-7.5", "abnormal_flag": True},
        "haemoglobin": {"value": 138, "unit": "g/L", "reference_range": "130-170", "abnormal_flag": False},
        "platelets": {"value": 245, "unit": "x10^9/L", "reference_range": "150-400", "abnormal_flag": False},
        "procalcitonin": {"value": 0.8, "unit": "ng/mL", "reference_range": "<0.1", "abnormal_flag": True},
        "lactate": {"value": 1.4, "unit": "mmol/L", "reference_range": "<2.0", "abnormal_flag": False},
    }
})


class TestExtractLabResults:
    """Tests for real MedGemma lab extraction (mocked call_medgemma)."""

    @pytest.mark.asyncio
    @patch("cap_agent.models.medgemma.call_medgemma")
    async def test_returns_tool_result_shape(self, mock_call, fhir_case_data):
        """2 calls made, ToolResult contract met."""
        mock_call.side_effect = _make_side_effect(
            MOCK_LAB_FACTS,
            f"```json\n{MOCK_LAB_SYNTHESIS}\n```",
        )
        result = await extract_lab_results(fhir_case_data)

        assert result["tool_name"] == "lab_extraction"
        assert result["status"] in ("success", "partial")
        assert "summary" in result
        assert "raw_output" in result
        assert "lab_values" in result["raw_output"]
        assert mock_call.call_count == 2

    @pytest.mark.asyncio
    @patch("cap_agent.models.medgemma.call_medgemma")
    async def test_output_matches_expected_values(self, mock_call, fhir_case_data):
        """CRP=186, urea=8.2 correct."""
        mock_call.side_effect = _make_side_effect(
            MOCK_LAB_FACTS,
            f"```json\n{MOCK_LAB_SYNTHESIS}\n```",
        )
        result = await extract_lab_results(fhir_case_data)
        labs = result["raw_output"]["lab_values"]

        assert labs["crp"]["value"] == 186.0
        assert labs["urea"]["value"] == 8.2
        assert labs["crp"]["abnormal_flag"] is True

    @pytest.mark.asyncio
    @patch("cap_agent.models.medgemma.call_medgemma")
    async def test_critical_downstream_values(self, mock_call, fhir_case_data):
        """crp, egfr, lactate present for downstream nodes."""
        mock_call.side_effect = _make_side_effect(
            MOCK_LAB_FACTS,
            f"```json\n{MOCK_LAB_SYNTHESIS}\n```",
        )
        result = await extract_lab_results(fhir_case_data)
        labs = result["raw_output"]["lab_values"]

        for key in ("crp", "egfr", "lactate"):
            assert key in labs, f"Missing critical lab: {key}"
            assert "value" in labs[key]

    @pytest.mark.asyncio
    @patch("cap_agent.models.medgemma.call_medgemma")
    async def test_text_extraction_failure_partial(self, mock_call, fhir_case_data):
        """Step 1 raises, FHIR available → status=partial."""
        call_idx = [0]

        def side_effect(prompt, max_new_tokens=1500, images=None, enable_thinking=True, **kwargs):
            idx = call_idx[0]
            call_idx[0] += 1
            if idx == 0:
                raise RuntimeError("Text extraction OOM")
            return f"```json\n{MOCK_LAB_SYNTHESIS}\n```"

        mock_call.side_effect = side_effect
        result = await extract_lab_results(fhir_case_data)

        assert result["status"] == "partial"
        assert "lab_values" in result["raw_output"]

    @pytest.mark.asyncio
    @patch("cap_agent.models.medgemma.call_medgemma")
    async def test_synthesis_failure_error(self, mock_call, fhir_case_data):
        """Step 2 raises → status=error."""
        call_idx = [0]

        def side_effect(prompt, max_new_tokens=1500, images=None, enable_thinking=True, **kwargs):
            idx = call_idx[0]
            call_idx[0] += 1
            if idx == 0:
                return MOCK_LAB_FACTS
            raise RuntimeError("Synthesis OOM")

        mock_call.side_effect = side_effect
        result = await extract_lab_results(fhir_case_data)

        assert result["status"] == "error"

    @pytest.mark.asyncio
    @patch("cap_agent.models.medgemma.call_medgemma")
    async def test_synthesis_malformed_partial(self, mock_call, fhir_case_data):
        """Repair fills gaps → status=partial."""
        mock_call.side_effect = _make_side_effect(
            MOCK_LAB_FACTS,
            # Only sodium — missing crp, urea, egfr, lactate
            '```json\n{"lab_values": {"sodium": {"value": 136, "unit": "mmol/L", "reference_range": "133-146", "abnormal_flag": false}}}\n```',
        )
        result = await extract_lab_results(fhir_case_data)

        assert result["status"] == "partial"
        assert "sodium" in result["raw_output"]["lab_values"]

    @pytest.mark.asyncio
    async def test_no_lab_report_falls_back_to_mock(self, case_data):
        """Backward compatible: no lab_report key → mock fallback."""
        result = await extract_lab_results(case_data)

        assert result["tool_name"] == "lab_extraction"
        assert result["status"] == "success"
        assert "crp" in result["raw_output"]["lab_values"]

    @pytest.mark.asyncio
    @patch("cap_agent.models.medgemma.call_medgemma")
    async def test_fhir_only_path(self, mock_call, fhir_case_data):
        """No text content, FHIR labs present → 1 GPU call (synthesis only)."""
        # Remove text content but keep lab_report key
        fhir_case_data["lab_report"] = {
            "format": "text",
            "content": "",  # empty text
            "source": "test",
        }
        mock_call.side_effect = _make_side_effect(
            f"```json\n{MOCK_LAB_SYNTHESIS}\n```",
        )
        result = await extract_lab_results(fhir_case_data)

        assert result["status"] in ("success", "partial")
        assert mock_call.call_count == 1  # Only synthesis, no text extraction

    @pytest.mark.asyncio
    @patch("cap_agent.models.medgemma.call_medgemma")
    async def test_dual_source_merge(self, mock_call, fhir_case_data):
        """Both sources present → combined facts contain both."""
        prompts_seen = []

        def side_effect(prompt, max_new_tokens=1500, images=None, enable_thinking=True, **kwargs):
            prompts_seen.append(prompt)
            if "LAB REPORT" in prompt:
                return MOCK_LAB_FACTS
            return f"```json\n{MOCK_LAB_SYNTHESIS}\n```"

        mock_call.side_effect = side_effect
        result = await extract_lab_results(fhir_case_data)

        assert mock_call.call_count == 2
        # Synthesis prompt should contain facts from both sources
        synthesis_prompt = prompts_seen[1]
        assert "PATHOLOGY REPORT" in synthesis_prompt
        assert "STRUCTURED RECORDS" in synthesis_prompt

    @pytest.mark.asyncio
    @patch("cap_agent.models.medgemma.call_medgemma")
    async def test_text_name_normalization(self, mock_call, fhir_case_data):
        """'C-reactive protein' → 'crp' via normalization."""
        mock_call.side_effect = _make_side_effect(
            MOCK_LAB_FACTS,
            '```json\n{"lab_values": {"C-reactive protein": {"value": 186, "unit": "mg/L", "reference_range": "<5", "abnormal_flag": true}}}\n```',
        )
        result = await extract_lab_results(fhir_case_data)
        labs = result["raw_output"]["lab_values"]

        assert "crp" in labs
        assert "C-reactive protein" not in labs

    @pytest.mark.asyncio
    async def test_empty_sources_falls_back_to_mock(self):
        """Empty content + no FHIR labs → mock fallback."""
        case_data = get_synthetic_case()
        case_data["lab_report"] = {
            "format": "text",
            "content": "",
            "source": "test",
        }
        # No fhir_bundle either
        result = await extract_lab_results(case_data)

        assert result["tool_name"] == "lab_extraction"
        assert result["status"] == "success"

    @pytest.mark.asyncio
    @patch("cap_agent.models.medgemma.call_medgemma")
    async def test_summary_contains_counts(self, mock_call, fhir_case_data):
        """Summary has correct lab and abnormal counts."""
        mock_call.side_effect = _make_side_effect(
            MOCK_LAB_FACTS,
            f"```json\n{MOCK_LAB_SYNTHESIS}\n```",
        )
        result = await extract_lab_results(fhir_case_data)

        assert "12 lab values" in result["summary"]
        assert "6 abnormal" in result["summary"]
        assert "2-step" in result["summary"]

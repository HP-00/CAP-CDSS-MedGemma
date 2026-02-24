"""End-to-end integration tests for the 8-node CAP agent pipeline.

Each test class builds the full LangGraph graph, mocks call_medgemma at the
model level (not at the extraction tool level), and runs a complete pipeline
invocation. A prompt-keyword router returns scenario-appropriate responses
based on prompt content and image arguments.

Four scenarios tested:
    TestT0FullPipeline   — T=0 Initial Assessment (all 3 real extraction tools)
    TestT48hStewardship  — T=48h Review (CR-8, CR-9 stewardship)
    TestCR10Safety       — CR-10 Demo (mock extraction, high severity)
    TestDay34Monitoring  — Day 3-4 Treatment Monitoring (CRP trend, reassess)
"""

import tempfile
from unittest.mock import patch

import nest_asyncio
import pytest

nest_asyncio.apply()

from cap_agent.agent.graph import build_cap_agent_graph
from cap_agent.agent.state import build_initial_state
from cap_agent.data.synthetic import (
    get_synthetic_fhir_case,
    get_synthetic_48h_case,
    get_synthetic_cr10_case,
    get_synthetic_day34_case,
)

# Import shared mock responses (canonical source: server/mock_responses.py)
from server.mock_responses import (
    MOCK_EHR_NARRATIVE,
    MOCK_EHR_STRUCTURED,
    MOCK_LAB_FACTS,
    MOCK_CXR_CLASSIFICATION,
    MOCK_CXR_LOCALIZATION,
    MOCK_CXR_LONGITUDINAL,
    _mock_ehr_synthesis,
    _mock_lab_synthesis,
    _make_cxr_call_tracker,
    build_prompt_router,
)


# =====================================================================
# Fixtures
# =====================================================================

@pytest.fixture(scope="module")
def graph():
    """Build the graph once for all tests in this module."""
    return build_cap_agent_graph()


@pytest.fixture
def tmp_cxr_images(tmp_path):
    """Create temp CXR images (current + prior) for T=0 scenario."""
    from PIL import Image
    current = tmp_path / "current_cxr.png"
    prior = tmp_path / "prior_cxr.png"
    Image.new("RGB", (10, 10), (128, 128, 128)).save(current)
    Image.new("RGB", (10, 10), (64, 64, 64)).save(prior)
    return str(current), str(prior)


# =====================================================================
# Test Classes
# =====================================================================

class TestT0FullPipeline:
    """T=0 Initial Assessment: FHIR + lab_report + CXR images → all 3 real tools."""

    @patch("cap_agent.models.medgemma.call_medgemma")
    def test_full_pipeline_runs(self, mock_call, graph, tmp_cxr_images):
        """Full 8-node pipeline completes with correct CURB65 and treatment."""
        ehr_json = _mock_ehr_synthesis(urea=8.2, confusion=False, rr=22,
                                       sbp=105, dbp=65, age=72)
        lab_json = _mock_lab_synthesis(crp=186, urea=8.2)
        mock_call.side_effect = build_prompt_router(ehr_json, lab_json)

        case = get_synthetic_fhir_case()
        case["cxr"]["image_path"] = tmp_cxr_images[0]
        case["cxr"]["prior_image_path"] = tmp_cxr_images[1]
        initial_state = build_initial_state(case)

        result = graph.invoke(initial_state)

        # Pipeline completed
        assert result["current_step"] == "Output assembled"

        # CURB65 = 2: C=0, U=1 (8.2>7), R=0, B=0, 65=1
        curb65 = result["curb65_score"]
        assert curb65["curb65"] == 2
        assert curb65["severity_tier"] == "moderate"
        assert curb65["c"] == 0
        assert curb65["u"] == 1
        assert curb65["r"] == 0
        assert curb65["b"] == 0
        assert curb65["age_65"] == 1

        # Antibiotic
        abx = result["antibiotic_recommendation"]
        assert "amoxicillin" in abx["first_line"].lower()

        # Structured output has 8 sections
        structured = result["structured_output"]
        assert len(structured["sections"]) == 8

        # All 3 extraction tools ran
        tool_names = [t["tool_name"] for t in result["tool_results"]]
        assert "ehr_qa_extraction" in tool_names
        assert "lab_extraction" in tool_names
        assert "cxr_classification" in tool_names

        # Provenance shows real pipelines
        prov = structured["provenance"]["extraction_tools"]
        assert prov["ehr"] == "3-step EHR QA"
        assert prov["labs"] == "2-step lab extraction"
        assert prov["cxr"] == "3-stage CXR analysis"

        # No errors
        assert len(result["errors"]) == 0

        # Clinician summary generated
        assert len(result.get("clinician_summary", "")) > 50


class TestT48hStewardship:
    """T=48h Review: FHIR + lab_report, no CXR → CR-8 and CR-9 fire."""

    @patch("cap_agent.models.medgemma.call_medgemma")
    def test_stewardship_contradictions(self, mock_call, graph):
        """48h review detects macrolide de-escalation and IV-to-oral switch."""
        # 48h values: urea 6.8 (U=0), improving, stable vitals
        ehr_json = _mock_ehr_synthesis(urea=6.8, confusion=False, rr=18,
                                       sbp=115, dbp=70, age=72,
                                       hr=82, spo2=96, temp=37.0)
        lab_json = _mock_lab_synthesis(crp=95, urea=6.8)
        mock_call.side_effect = build_prompt_router(ehr_json, lab_json)

        case = get_synthetic_48h_case()
        initial_state = build_initial_state(case)

        result = graph.invoke(initial_state)

        # Pipeline completed
        assert result["current_step"] == "Output assembled"

        # CURB65 ≤ 1 (improved from 2)
        curb65 = result["curb65_score"]
        assert curb65["curb65"] is not None
        assert curb65["curb65"] <= 1
        assert curb65["severity_tier"] == "low"

        # Stewardship contradictions
        cr_ids = [c["rule_id"] for c in result["contradictions_detected"]]
        assert "CR-8" in cr_ids, "CR-8 should fire (macrolide without atypical)"
        assert "CR-9" in cr_ids, "CR-9 should fire (IV >48h with oral tolerance)"
        assert "CR-7" not in cr_ids, "CR-7 should NOT fire (organism susceptible)"

        # Strategy E resolutions present
        resolutions = result["resolution_results"]
        assert any("(E" in r for r in resolutions), \
            "Strategy E deterministic resolutions expected"

        # No errors
        assert len(result["errors"]) == 0


class TestCR10Safety:
    """CR-10 Demo: mock extraction, high severity, penicillin intolerance.

    After E2 stratification (pen allergy → cephalosporin/co-amoxiclav instead of
    levofloxacin for non-anaphylaxis), intolerance patients get co-amoxiclav at
    high severity. CR-10 no longer fires because no fluoroquinolone is prescribed.
    """

    @patch("cap_agent.models.medgemma.call_medgemma")
    def test_cr10_intolerance_gets_standard_treatment(self, mock_call, graph):
        """High severity + penicillin intolerance → co-amoxiclav (not levofloxacin)."""
        # CR-10 case uses mock extraction (no FHIR, no lab_report, no CXR)
        # Only pipeline-level nodes call MedGemma: summary
        ehr_json = _mock_ehr_synthesis()  # Won't be called (mock extraction)
        lab_json = _mock_lab_synthesis()  # Won't be called (mock extraction)
        mock_call.side_effect = build_prompt_router(ehr_json, lab_json)

        case = get_synthetic_cr10_case()
        initial_state = build_initial_state(case)

        result = graph.invoke(initial_state)

        # Pipeline completed
        assert result["current_step"] == "Output assembled"

        # High severity
        curb65 = result["curb65_score"]
        assert curb65["severity_tier"] == "high"

        # CR-10 does NOT fire — intolerance patients now get co-amoxiclav, not
        # levofloxacin, so there's no fluoroquinolone to flag
        cr_ids = [c["rule_id"] for c in result["contradictions_detected"]]
        assert "CR-10" not in cr_ids, (
            "CR-10 should NOT fire — intolerance gets co-amoxiclav, not levofloxacin"
        )

        # Co-amoxiclav prescribed (standard high severity for intolerance)
        abx = result["antibiotic_recommendation"]
        assert "co-amoxiclav" in str(abx).lower()

        # No errors
        assert len(result["errors"]) == 0


class TestDay34Monitoring:
    """Day 3-4 Monitoring: CRP trend + treatment response assessment."""

    @patch("cap_agent.models.medgemma.call_medgemma")
    def test_treatment_reassessment(self, mock_call, graph):
        """Day 3, CRP only 41% decrease → reassess_needed, CRP flagged."""
        # Day 3-4 values: urea 7.0 (boundary: U=0, strictly >7), CRP 110
        ehr_json = _mock_ehr_synthesis(urea=7.0, confusion=False, rr=20,
                                       sbp=110, dbp=68, age=72,
                                       hr=92, spo2=95, temp=37.8)
        lab_json = _mock_lab_synthesis(crp=110, urea=7.0)
        mock_call.side_effect = build_prompt_router(ehr_json, lab_json)

        case = get_synthetic_day34_case()
        initial_state = build_initial_state(case)

        result = graph.invoke(initial_state)

        # Pipeline completed
        assert result["current_step"] == "Output assembled"

        # CURB65: urea 7.0 → U=0 (strictly >7), age 72 → 65=1, total=1
        curb65 = result["curb65_score"]
        assert curb65["u"] == 0, "Urea exactly 7.0 → U=0 (strictly >7)"
        assert curb65["age_65"] == 1

        # Monitoring plan
        monitoring = result["monitoring_plan"]

        # Treatment response: reassess_needed=True
        treatment_resp = monitoring.get("treatment_response")
        assert treatment_resp is not None, "Treatment response should be present"
        assert treatment_resp["reassess_needed"] is True

        # CRP trend flagged for senior review
        crp_trend = monitoring.get("crp_trend")
        assert crp_trend is not None, "CRP trend should be present"
        assert crp_trend["flag_senior_review"] is True

        # CRP percent_change in expected range (~40.9%)
        pct = crp_trend["percent_change"]
        assert 35 <= pct <= 45, f"Expected ~41% CRP decrease, got {pct}%"

        # Discharge blocked by treatment reassessment
        assert monitoring["discharge_criteria_met"] is False

        # No errors
        assert len(result["errors"]) == 0

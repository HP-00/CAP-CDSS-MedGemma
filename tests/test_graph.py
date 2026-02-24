"""Tests for graph compilation and structure."""

import pytest

from cap_agent.agent.graph import build_cap_agent_graph
from cap_agent.agent.nodes import (
    should_resolve_contradictions,
    _parse_resolution_confidence,
    _build_data_sources,
)


class TestGraphCompilation:
    def test_graph_compiles(self):
        graph = build_cap_agent_graph()
        assert graph is not None

    def test_graph_has_8_user_nodes(self):
        graph = build_cap_agent_graph()
        g = graph.get_graph()
        # Filter out __start__ and __end__
        user_nodes = [n for n in g.nodes if not n.startswith("__")]
        assert len(user_nodes) == 8

    def test_graph_node_names(self):
        graph = build_cap_agent_graph()
        g = graph.get_graph()
        expected = {
            "load_case", "parallel_extraction", "severity_scoring",
            "check_contradictions", "contradiction_resolution",
            "treatment_selection", "monitoring_plan", "output_assembly",
        }
        user_nodes = {n for n in g.nodes if not n.startswith("__")}
        assert user_nodes == expected

    def test_entry_point_is_load_case(self):
        graph = build_cap_agent_graph()
        g = graph.get_graph()
        # __start__ should connect to load_case
        start_edges = [e for e in g.edges if e[0] == "__start__"]
        assert any(e[1] == "load_case" for e in start_edges)


class TestRoutingFunction:
    def test_routes_to_resolution_with_contradictions(self):
        state = {"contradictions_detected": [{"rule_id": "CR-1"}]}
        assert should_resolve_contradictions(state) == "contradiction_resolution"

    def test_routes_to_treatment_without_contradictions(self):
        state = {"contradictions_detected": []}
        assert should_resolve_contradictions(state) == "treatment_selection"

    def test_routes_to_treatment_with_none(self):
        state = {}
        assert should_resolve_contradictions(state) == "treatment_selection"


class TestNodeReturnShapes:
    """Verify deterministic nodes return expected state update keys."""

    def test_load_case_returns_expected_keys(self):
        from cap_agent.agent.nodes import load_case_node
        state = {
            "case_data": {
                "demographics": {}, "clinical_exam": {}, "lab_results": {},
                "cxr": {}, "past_medical_history": {},
            }
        }
        result = load_case_node(state)
        assert "current_step" in result
        assert "messages" in result
        assert "reasoning_trace" in result
        assert isinstance(result["messages"], list)

    def test_severity_scoring_returns_expected_keys(self):
        from cap_agent.agent.nodes import severity_scoring_node
        state = {
            "curb65_variables": {
                "confusion": False, "urea": 8.2, "respiratory_rate": 22,
                "systolic_bp": 105, "diastolic_bp": 65, "age": 72,
            }
        }
        result = severity_scoring_node(state)
        assert "curb65_score" in result
        assert result["curb65_score"]["curb65"] == 2
        assert result["curb65_score"]["severity_tier"] == "moderate"

    def test_check_contradictions_returns_expected_keys(self):
        from cap_agent.agent.nodes import check_contradictions_node
        state = {
            "cxr_analysis": {"consolidation": {"present": True, "location": "RLL"}, "pleural_effusion": {"present": False}},
            "clinical_exam": {"respiratory_exam": {"crackles": True, "bronchial_breathing": True}},
            "lab_values": {"crp": {"value": 186}},
            "patient_demographics": {"comorbidities": []},
            "curb65_score": {"severity_tier": "moderate", "curb65": 2},
            "case_data": {"social_history": {"immunosuppression": False}},
        }
        result = check_contradictions_node(state)
        assert "contradictions_detected" in result
        assert isinstance(result["contradictions_detected"], list)

    def test_treatment_selection_returns_expected_keys(self):
        from cap_agent.agent.nodes import treatment_selection_node
        state = {
            "curb65_score": {"severity_tier": "moderate", "curb65": 2},
            "patient_demographics": {"allergies": [], "oral_tolerance": True, "pregnancy": False, "travel_history": []},
            "lab_values": {"egfr": {"value": 62}},
            "clinical_exam": {"observations": {"heart_rate": 98, "temperature": 38.4, "systolic_bp": 105}},
        }
        result = treatment_selection_node(state)
        assert "antibiotic_recommendation" in result
        assert "investigation_plan" in result
        assert "Amoxicillin" in result["antibiotic_recommendation"]["first_line"]

    def test_monitoring_plan_returns_expected_keys(self):
        from cap_agent.agent.nodes import monitoring_plan_node
        state = {
            "curb65_score": {"severity_tier": "moderate"},
            "clinical_exam": {
                "observations": {
                    "temperature": 38.4, "respiratory_rate": 22,
                    "heart_rate": 98, "systolic_bp": 105, "spo2": 94,
                },
                "confusion_status": {"present": False},
            },
        }
        result = monitoring_plan_node(state)
        assert "monitoring_plan" in result
        assert "discharge_criteria_met" in result["monitoring_plan"]


class TestParseResolutionConfidence:
    """Test _parse_resolution_confidence helper."""

    def test_parses_high(self):
        assert _parse_resolution_confidence("My confidence: high") == "high"

    def test_parses_moderate(self):
        assert _parse_resolution_confidence("confidence is moderate overall") == "moderate"

    def test_parses_low(self):
        assert _parse_resolution_confidence("Confidence: low given limited data") == "low"

    def test_returns_none_when_absent(self):
        assert _parse_resolution_confidence("No rating provided") is None

    def test_case_insensitive(self):
        assert _parse_resolution_confidence("CONFIDENCE: HIGH") == "high"

    def test_parses_confidence_as(self):
        assert _parse_resolution_confidence("I would rate confidence as moderate") == "moderate"

    def test_parses_reversed_order(self):
        assert _parse_resolution_confidence("I have moderate confidence in this finding") == "moderate"

    def test_parses_confidence_level(self):
        assert _parse_resolution_confidence("confidence level: high overall") == "high"

    def test_parses_confidence_rating(self):
        assert _parse_resolution_confidence("My confidence rating: low") == "low"

    def test_returns_none_for_unrelated_high(self):
        """'high' without 'confidence' nearby should not match."""
        assert _parse_resolution_confidence("This patient has high CRP levels") is None


class TestBuildDataSources:
    """Test _build_data_sources provenance helper."""

    def test_fhir_bundle_with_clerking_note(self):
        case_data = {
            "fhir_bundle": {
                "entry": [
                    {"resource": {"resourceType": "Patient"}},
                    {"resource": {"resourceType": "DocumentReference"}},
                ]
            },
            "lab_report": "CRP: 186 mg/L",
        }
        ds = _build_data_sources(case_data)
        assert "fhir_r4_bundle" in ds["ehr"]
        assert "clerking_note" in ds["ehr"]
        assert "nhs_pathology_report" in ds["labs"]
        assert "fhir_lab_observations" in ds["labs"]
        assert "synthetic_flat_data" in ds["cxr"]  # no image_path

    def test_mock_fallback(self):
        ds = _build_data_sources({})
        assert ds["ehr"] == ["synthetic_flat_data"]
        assert ds["labs"] == ["synthetic_flat_data"]
        assert ds["cxr"] == ["synthetic_flat_data"]

    def test_cxr_with_prior(self):
        case_data = {
            "cxr": {"image_path": "/path/to/cxr.jpg", "prior_image_path": "/path/to/prior.jpg"},
        }
        ds = _build_data_sources(case_data)
        assert "cxr_image" in ds["cxr"]
        assert "prior_cxr_image" in ds["cxr"]

    def test_cxr_without_prior(self):
        case_data = {"cxr": {"image_path": "/path/to/cxr.jpg"}}
        ds = _build_data_sources(case_data)
        assert "cxr_image" in ds["cxr"]
        assert "prior_cxr_image" not in ds["cxr"]

    def test_fhir_without_clerking_note(self):
        case_data = {
            "fhir_bundle": {
                "entry": [{"resource": {"resourceType": "Patient"}}]
            }
        }
        ds = _build_data_sources(case_data)
        assert "fhir_r4_bundle" in ds["ehr"]
        assert "clerking_note" not in ds["ehr"]

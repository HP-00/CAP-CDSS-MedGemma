"""Tests for agent state schema."""

import operator
from typing import Annotated, List, Optional, get_type_hints

from cap_agent.agent.state import (
    CAPAgentState,
    CURB65Variables,
    CURB65Score,
    LabValues,
    CXRFindings,
    ClinicalExamFindings,
    PatientDemographics,
    MicrobiologyResult,
    ContradictionAlert,
    AntibioticRecommendation,
    InvestigationPlan,
    MonitoringPlan,
    ToolResult,
    build_initial_state,
)


class TestCAPAgentState:
    def test_has_expected_field_count(self):
        # 28 fields in CAPAgentState (27 original + micro_results; place_of_care removed)
        assert len(CAPAgentState.__annotations__) == 28

    def test_input_fields(self):
        hints = CAPAgentState.__annotations__
        assert "case_id" in hints
        assert "patient_id" in hints
        assert "case_data" in hints

    def test_streaming_fields(self):
        hints = CAPAgentState.__annotations__
        assert "messages" in hints
        assert "thinking_traces" in hints
        assert "reasoning_trace" in hints
        assert "current_step" in hints

    def test_extraction_fields(self):
        hints = CAPAgentState.__annotations__
        assert "tool_results" in hints
        assert "clinical_findings" in hints
        assert "lab_findings" in hints
        assert "cxr_findings" in hints

    def test_list_fields_use_annotated_add(self):
        """Verify that list accumulation fields use Annotated[List, operator.add]."""
        hints = get_type_hints(CAPAgentState, include_extras=True)
        accumulate_fields = [
            "messages", "thinking_traces", "reasoning_trace",
            "tool_results", "clinical_findings", "lab_findings", "cxr_findings",
            "contradictions_detected", "resolution_results",
            "errors", "data_gaps",
        ]
        for field in accumulate_fields:
            hint = hints[field]
            # Check it's Annotated with operator.add
            assert hasattr(hint, "__metadata__"), f"{field} should be Annotated"
            assert operator.add in hint.__metadata__, f"{field} should use operator.add"


class TestSupportingTypedDicts:
    def test_curb65_variables_fields(self):
        fields = CURB65Variables.__annotations__
        assert "confusion" in fields
        assert "urea" in fields
        assert "respiratory_rate" in fields
        assert "age" in fields

    def test_curb65_score_fields(self):
        fields = CURB65Score.__annotations__
        for key in ["c", "u", "r", "b", "age_65", "crb65", "curb65", "severity_tier"]:
            assert key in fields

    def test_contradiction_alert_fields(self):
        fields = ContradictionAlert.__annotations__
        for key in ["rule_id", "pattern", "evidence_for", "evidence_against", "severity", "confidence", "resolution_strategy"]:
            assert key in fields

    def test_tool_result_fields(self):
        fields = ToolResult.__annotations__
        for key in ["tool_name", "status", "summary", "raw_output"]:
            assert key in fields

    def test_patient_demographics_has_smoking_status(self):
        fields = PatientDemographics.__annotations__
        assert "smoking_status" in fields

    def test_antibiotic_recommendation_has_corticosteroid(self):
        fields = AntibioticRecommendation.__annotations__
        assert "corticosteroid_recommendation" in fields

    def test_monitoring_plan_has_treatment_duration(self):
        fields = MonitoringPlan.__annotations__
        assert "treatment_duration" in fields

    def test_cap_agent_state_has_micro_results(self):
        hints = CAPAgentState.__annotations__
        assert "micro_results" in hints

    def test_microbiology_result_fields(self):
        fields = MicrobiologyResult.__annotations__
        for key in ["organism", "susceptibilities", "test_type", "status"]:
            assert key in fields

    def test_contradiction_alert_has_recommendation(self):
        """ContradictionAlert supports optional 'recommendation' field."""
        fields = ContradictionAlert.__annotations__
        assert "recommendation" in fields


class TestBuildInitialState:
    SAMPLE_CASE = {
        "case_id": "CAP-001",
        "patient_id": "PT-42",
        "demographics": {"age": 72, "sex": "Male"},
    }

    ACCUMULATOR_FIELDS = [
        "messages", "thinking_traces", "reasoning_trace",
        "tool_results", "clinical_findings", "lab_findings", "cxr_findings",
        "contradictions_detected", "resolution_results",
        "errors", "data_gaps",
    ]

    def test_field_count_matches_state(self):
        state = build_initial_state(self.SAMPLE_CASE)
        assert len(state) == len(CAPAgentState.__annotations__)

    def test_all_fields_present(self):
        state = build_initial_state(self.SAMPLE_CASE)
        assert set(state.keys()) == set(CAPAgentState.__annotations__.keys())

    def test_case_id_populated(self):
        state = build_initial_state(self.SAMPLE_CASE)
        assert state["case_id"] == "CAP-001"

    def test_patient_id_populated(self):
        state = build_initial_state(self.SAMPLE_CASE)
        assert state["patient_id"] == "PT-42"

    def test_case_data_is_case_dict(self):
        state = build_initial_state(self.SAMPLE_CASE)
        assert state["case_data"] is self.SAMPLE_CASE

    def test_accumulator_fields_default_to_empty_list(self):
        state = build_initial_state(self.SAMPLE_CASE)
        for field in self.ACCUMULATOR_FIELDS:
            assert state[field] == [], f"{field} should default to []"

    def test_optional_fields_default_to_none(self):
        state = build_initial_state(self.SAMPLE_CASE)
        optional_fields = [
            "curb65_variables", "lab_values", "cxr_analysis",
            "clinical_exam", "patient_demographics", "curb65_score",
            "antibiotic_recommendation",
            "investigation_plan", "monitoring_plan",
            "synthesized_findings", "clinician_summary", "structured_output",
            "micro_results",
        ]
        for field in optional_fields:
            assert state[field] is None, f"{field} should default to None"

    def test_current_step_initialized(self):
        state = build_initial_state(self.SAMPLE_CASE)
        assert state["current_step"] == "Initializing..."

    def test_missing_case_id_defaults_to_empty_string(self):
        state = build_initial_state({"demographics": {}})
        assert state["case_id"] == ""
        assert state["patient_id"] == ""

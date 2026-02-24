"""Tests for utils: config and trace."""

from cap_agent.utils.config import MODEL_ID, MODEL_KWARGS, TOKEN_BUDGETS
from cap_agent.utils.trace import create_trace_step, complete_trace_step


class TestConfig:
    def test_model_id(self):
        assert MODEL_ID == "google/medgemma-1.5-4b-it"

    def test_model_kwargs_keys(self):
        assert "attn_implementation" in MODEL_KWARGS
        assert "dtype" in MODEL_KWARGS
        assert "device_map" in MODEL_KWARGS

    def test_model_kwargs_values(self):
        assert MODEL_KWARGS["attn_implementation"] == "sdpa"
        assert MODEL_KWARGS["dtype"] == "bfloat16"
        assert MODEL_KWARGS["device_map"] == "auto"


class TestTokenBudgets:
    """Verify TOKEN_BUDGETS dict is complete and well-formed."""

    EXPECTED_KEYS = {
        "lab_extraction", "lab_synthesis",
        "ehr_narrative_filter", "ehr_structured_filter", "ehr_synthesis",
        "cxr_classification", "cxr_localization", "cxr_longitudinal",
        "contradiction_resolution", "clinician_summary",
    }

    def test_all_keys_present(self):
        assert set(TOKEN_BUDGETS.keys()) == self.EXPECTED_KEYS

    def test_all_positive_ints(self):
        for key, value in TOKEN_BUDGETS.items():
            assert isinstance(value, int), f"{key} is not int: {type(value)}"
            assert value > 0, f"{key} is not positive: {value}"

    def test_lab_synthesis_minimum(self):
        """lab_synthesis must be >= 3500 to avoid token truncation."""
        assert TOKEN_BUDGETS["lab_synthesis"] >= 3500


class TestTrace:
    def test_create_trace_step_has_all_fields(self):
        step = create_trace_step(1, "test_action", "input", "reasoning")
        required = [
            "step_number", "action", "input_summary",
            "output_summary", "reasoning", "timestamp", "duration_ms",
        ]
        for field in required:
            assert field in step, f"Missing field: {field}"
        assert "_start_time" in step  # internal, removed on complete

    def test_create_trace_step_values(self):
        step = create_trace_step(3, "my_action", "my_input", "my_reasoning")
        assert step["step_number"] == 3
        assert step["action"] == "my_action"
        assert step["input_summary"] == "my_input"
        assert step["reasoning"] == "my_reasoning"
        assert step["output_summary"] is None
        assert step["duration_ms"] is None

    def test_complete_trace_step(self):
        step = create_trace_step(1, "test", "in", "reason")
        completed = complete_trace_step(step, "done")
        assert completed["output_summary"] == "done"
        assert isinstance(completed["duration_ms"], int)
        assert completed["duration_ms"] >= 0
        assert "_start_time" not in completed

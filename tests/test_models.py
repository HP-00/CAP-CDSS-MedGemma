"""Tests for model utilities: extract_thinking, parse_json_response, prompt builders."""

import pytest
from unittest.mock import patch, MagicMock

from cap_agent.models.medgemma import (
    extract_thinking,
    parse_json_response,
    get_model_and_processor,
    pad_image_to_square,
    _is_json_complete,
)
from cap_agent.models.prompts import (
    CAP_SYSTEM_INSTRUCTION,
    CAP_SYSTEM_INSTRUCTION_NO_THINKING,
    CAP_EXTRACTION_INSTRUCTION,
    build_contradiction_prompt,
    build_synthesis_prompt,
    build_clinician_summary_prompt,
    build_cxr_classification_prompt,
    build_cxr_localization_prompt,
    build_cxr_longitudinal_prompt,
    build_ehr_identify_prompt,
    build_ehr_narrative_filter_prompt,
    build_ehr_structured_filter_prompt,
    build_ehr_synthesis_prompt,
    build_lab_extraction_prompt,
    build_lab_synthesis_prompt,
)


class TestExtractThinking:
    def test_with_thinking_tokens(self):
        text = "<unused94>thought\nI am thinking about this<unused95>The final answer"
        thinking, response = extract_thinking(text)
        assert thinking == "I am thinking about this"
        assert response == "The final answer"

    def test_without_thinking_tokens(self):
        text = "Just a plain response"
        thinking, response = extract_thinking(text)
        assert thinking == ""
        assert response == "Just a plain response"

    def test_empty_thinking(self):
        text = "<unused94><unused95>Only response"
        thinking, response = extract_thinking(text)
        assert thinking == ""
        assert response == "Only response"

    def test_multiline_thinking(self):
        text = "<unused94>thought\nLine 1\nLine 2\nLine 3<unused95>Answer here"
        thinking, response = extract_thinking(text)
        assert "Line 1" in thinking
        assert "Line 3" in thinking
        assert response == "Answer here"

    def test_whitespace_stripping(self):
        text = "<unused94>thought\n  thinking  <unused95>  answer  "
        thinking, response = extract_thinking(text)
        assert thinking == "thinking"
        assert response == "answer"


class TestParseJsonResponse:
    def test_markdown_code_block(self):
        text = 'Some text\n```json\n{"key": "value"}\n```\nMore text'
        result = parse_json_response(text)
        assert result == {"key": "value"}

    def test_bare_json(self):
        text = '{"status": "ok", "count": 5}'
        result = parse_json_response(text)
        assert result == {"status": "ok", "count": 5}

    def test_nested_json(self):
        text = 'Result: {"outer": {"inner": 42}}'
        result = parse_json_response(text)
        assert result["outer"]["inner"] == 42

    def test_invalid_json(self):
        text = "No JSON here at all"
        result = parse_json_response(text)
        assert result == {}

    def test_malformed_json(self):
        """json_repair can fix malformed JSON like missing quotes."""
        text = '{"broken: json}'
        result = parse_json_response(text)
        # json_repair infers the missing quote → {"broken": "json"}
        assert result == {"broken": "json"}

    def test_code_block_without_json_tag(self):
        text = '```\n{"key": "value"}\n```'
        result = parse_json_response(text)
        assert result == {"key": "value"}

    def test_json_embedded_in_prose(self):
        text = 'The result is {"severity": "high"} which indicates urgency.'
        result = parse_json_response(text)
        assert result == {"severity": "high"}


class TestGetModelAndProcessor:
    def test_raises_without_cuda(self):
        """get_model_and_processor should raise RuntimeError on CPU-only machines."""
        import torch
        import cap_agent.models.medgemma as mod

        # Reset singleton
        mod._model = None
        mod._processor = None

        # Mock torch.cuda.is_available on the real torch module
        with patch.object(torch.cuda, "is_available", return_value=False):
            with pytest.raises(RuntimeError, match="CUDA GPU"):
                mod.get_model_and_processor()

        # Clean up singleton state
        mod._model = None
        mod._processor = None


class TestPrompts:
    def test_system_instruction_contains_key_phrases(self):
        assert "evidence-based" in CAP_SYSTEM_INSTRUCTION
        assert "CURB65" in CAP_SYSTEM_INSTRUCTION
        assert "think silently" in CAP_SYSTEM_INSTRUCTION
        assert "SAFETY PRINCIPLES" in CAP_SYSTEM_INSTRUCTION

    def test_build_contradiction_prompt_strategy_a(self):
        prompt = build_contradiction_prompt("A", "CR-1", "test pattern", "evidence for", "evidence against")
        assert "CR-1" in prompt
        assert "cross-modal mismatch" in prompt
        assert "evidence for" in prompt
        assert "confidence" in prompt.lower()  # confidence question present

    def test_build_contradiction_prompt_strategy_b(self):
        prompt = build_contradiction_prompt("B", "CR-2", "test", "for", "against")
        assert "temporal" in prompt.lower()
        assert "confidence" in prompt.lower()  # confidence question present

    def test_build_contradiction_prompt_strategy_c(self):
        prompt = build_contradiction_prompt("C", "CR-3", "test", "for", "against")
        assert "differential" in prompt.lower()
        assert "Evidence: for" in prompt  # strategy C uses "Evidence:"/"Counter-evidence:"
        assert "Counter-evidence: against" in prompt
        assert "confidence" in prompt.lower()  # confidence question present

    def test_build_contradiction_prompt_strategy_d(self):
        prompt = build_contradiction_prompt("D", "CR-4", "test", "for", "against")
        assert "severity" in prompt.lower()
        assert "Current severity: for" in prompt  # strategy D uses "Current severity:"/"Override trigger:"
        assert "Override trigger: against" in prompt
        assert "confidence" in prompt.lower()  # confidence question present

    def test_build_contradiction_prompt_strategy_e(self):
        prompt = build_contradiction_prompt("E", "CR-7", "test pattern", "regimen info", "micro data")
        assert "STEWARDSHIP ALERT" in prompt
        assert "CR-7" in prompt
        assert "regimen info" in prompt
        assert "micro data" in prompt
        # Strategy E is deterministic — no confidence format instruction
        assert "CONFIDENCE:" not in prompt

    def test_build_contradiction_prompt_unknown_strategy(self):
        prompt = build_contradiction_prompt("X", "CR-99", "pattern", "for", "against")
        assert "pattern" in prompt

    def test_build_synthesis_prompt(self):
        prompt = build_synthesis_prompt(
            demographics={"age": 72, "sex": "Male", "comorbidities": ["COPD"], "allergies": []},
            exam={},
            labs={"crp": {"value": 186, "unit": "mg/L", "reference_range": "<5", "abnormal_flag": True}},
            cxr={},
            curb65={"curb65": 2, "severity_tier": "moderate", "c": 0, "u": 1, "r": 0, "b": 0, "age_65": 1},
            contradictions=[],
            resolutions=[],
            data_gaps=[],
        )
        assert "72yo Male" in prompt
        assert "COPD" in prompt
        assert "moderate" in prompt

    def test_build_clinician_summary_prompt(self):
        prompt = build_clinician_summary_prompt(
            demographics={"age": 72, "sex": "Male", "comorbidities": [], "allergies": []},
            curb65={"curb65": 2, "severity_tier": "moderate", "c": 0, "u": 1, "r": 0, "b": 0, "age_65": 1, "missing_variables": []},
            cxr={"consolidation": {"present": True, "confidence": "moderate", "location": "RLL"}, "image_quality": {"projection": "PA"}},
            labs={},
            contradictions=[],
            treatment={"first_line": "Amoxicillin 500mg TDS PO"},
            monitoring={"crp_repeat_timing": "48-72h", "next_review": "24h"},
            data_gaps=[],
        )
        assert "8 sections" in prompt
        assert "Amoxicillin" in prompt
        assert "clinician" in prompt.lower()


class TestCXRPrompts:
    """Tests for the 3 CXR prompt builders."""

    def test_classification_prompt_lists_5_conditions(self):
        prompt = build_cxr_classification_prompt()
        for condition in ["Consolidation", "Pleural effusion", "Cardiomegaly", "edema", "Atelectasis"]:
            assert condition.lower() in prompt.lower()

    def test_classification_prompt_requests_image_quality(self):
        prompt = build_cxr_classification_prompt()
        assert "image_quality" in prompt
        assert "projection" in prompt
        assert "rotation" in prompt
        assert "penetration" in prompt

    def test_classification_prompt_requests_json(self):
        prompt = build_cxr_classification_prompt()
        assert "json" in prompt.lower()
        assert "consolidation" in prompt

    def test_localization_prompt_contains_finding_name(self):
        prompt = build_cxr_localization_prompt("consolidation", "right lower lobe")
        assert "consolidation" in prompt
        assert "right lower lobe" in prompt
        assert "box_2d" in prompt
        assert "[y0, x0, y1, x1]" in prompt

    def test_localization_prompt_without_location(self):
        prompt = build_cxr_localization_prompt("atelectasis")
        assert "atelectasis" in prompt
        assert "in the" not in prompt.split("Locate the atelectasis")[1].split("\n")[0]

    def test_longitudinal_prompt_mentions_prior_and_current(self):
        prompt = build_cxr_longitudinal_prompt()
        assert "PRIOR" in prompt
        assert "CURRENT" in prompt
        for change_type in ["new", "unchanged", "improved", "worsened", "resolved"]:
            assert change_type in prompt

    def test_longitudinal_prompt_has_explicit_category_definitions(self):
        prompt = build_cxr_longitudinal_prompt()
        assert "ABSENT in prior, PRESENT in current" in prompt
        assert "PRESENT in prior, ABSENT in current" in prompt
        assert "PRESENT in both" in prompt
        assert "use EXACTLY one per finding" in prompt


class TestParseJsonResponseList:
    """Tests for parse_json_response with expect_list=True."""

    def test_list_in_code_block(self):
        text = '```json\n[{"box_2d": [100, 200, 300, 400], "label": "consolidation"}]\n```'
        result = parse_json_response(text, expect_list=True)
        assert isinstance(result, list)
        assert result[0]["box_2d"] == [100, 200, 300, 400]

    def test_bare_list(self):
        text = '[{"box_2d": [10, 20, 30, 40], "label": "test"}]'
        result = parse_json_response(text, expect_list=True)
        assert isinstance(result, list)
        assert len(result) == 1

    def test_list_failure_returns_empty_list(self):
        text = "No JSON here"
        result = parse_json_response(text, expect_list=True)
        assert result == []

    def test_default_mode_backward_compat(self):
        """Default mode (expect_list=False) still returns dict."""
        text = '{"key": "value"}'
        result = parse_json_response(text)
        assert isinstance(result, dict)
        assert result == {"key": "value"}

    def test_list_mode_can_also_parse_dict(self):
        """expect_list=True should also handle a dict response."""
        text = '{"key": "value"}'
        result = parse_json_response(text, expect_list=True)
        assert isinstance(result, dict)


class TestPadImageToSquare:
    """Tests for CXR image preprocessing."""

    def test_square_image_unchanged(self):
        from PIL import Image
        img = Image.new("RGB", (100, 100), color=(128, 128, 128))
        result = pad_image_to_square(img)
        assert result.size == (100, 100)

    def test_landscape_padded_to_square(self):
        from PIL import Image
        img = Image.new("RGB", (200, 100), color=(128, 128, 128))
        result = pad_image_to_square(img)
        w, h = result.size
        assert w == h == 200  # max dim

    def test_portrait_padded_to_square(self):
        from PIL import Image
        img = Image.new("RGB", (100, 200), color=(128, 128, 128))
        result = pad_image_to_square(img)
        w, h = result.size
        assert w == h == 200  # max dim

    def test_grayscale_converted_to_rgb(self):
        from PIL import Image
        img = Image.new("L", (50, 50), color=128)
        result = pad_image_to_square(img)
        assert result.mode == "RGB"
        assert result.size == (50, 50)


class TestEHRPrompts:
    """Tests for the 4 EHR QA prompt builders."""

    def test_identify_prompt_contains_manifest(self):
        manifest = "Available FHIR resources: Patient: 1, Condition: 2 (COPD, T2DM)"
        prompt = build_ehr_identify_prompt(manifest)
        assert manifest in prompt

    def test_identify_prompt_asks_for_json_list(self):
        prompt = build_ehr_identify_prompt("Patient: 1")
        assert "JSON list" in prompt or "json" in prompt.lower()
        assert "resource type" in prompt.lower()

    def test_narrative_filter_prompt_contains_note(self):
        note = "PC: 72yo gentleman with cough and fever."
        prompt = build_ehr_narrative_filter_prompt(note)
        assert note in prompt

    def test_narrative_filter_prompt_requests_categories(self):
        prompt = build_ehr_narrative_filter_prompt("test note")
        assert "RESPIRATORY" in prompt
        assert "CONFUSION" in prompt or "MENTAL STATUS" in prompt
        assert "ALLERGIES" in prompt
        assert "PAST MEDICAL" in prompt or "PMH" in prompt

    def test_structured_filter_prompt_contains_resources(self):
        resources = "PATIENT: Robert James, male\nVITAL: RR 22/min"
        prompt = build_ehr_structured_filter_prompt(resources)
        assert resources in prompt

    def test_synthesis_prompt_contains_both_facts(self):
        narrative = "Crackles right lower zone."
        structured = "RR 22/min, BP 105/65."
        prompt = build_ehr_synthesis_prompt(narrative, structured)
        assert narrative in prompt
        assert structured in prompt

    def test_synthesis_prompt_specifies_schema(self):
        prompt = build_ehr_synthesis_prompt("facts1", "facts2")
        # Check exact field names from the schema
        assert '"demographics"' in prompt
        assert '"clinical_exam"' in prompt
        assert '"curb65_variables"' in prompt
        assert '"respiratory_exam"' in prompt
        assert '"observations"' in prompt
        assert '"confusion_status"' in prompt
        assert '"age"' in prompt
        assert '"urea"' in prompt


class TestLabPrompts:
    """Tests for the 2 lab prompt builders."""

    def test_extraction_prompt_contains_input_text(self):
        lab_text = "CRP 186 mg/L, Urea 8.2 mmol/L"
        prompt = build_lab_extraction_prompt(lab_text)
        assert lab_text in prompt

    def test_extraction_prompt_lists_key_tests(self):
        prompt = build_lab_extraction_prompt("test report")
        for test in ["CRP", "Urea", "Creatinine", "eGFR", "Lactate", "Procalcitonin"]:
            assert test.lower() in prompt.lower()

    def test_synthesis_prompt_contains_facts(self):
        facts = "CRP: 186 mg/L (abnormal), Urea: 8.2 mmol/L (abnormal)"
        prompt = build_lab_synthesis_prompt(facts)
        assert facts in prompt

    def test_synthesis_prompt_specifies_schema(self):
        prompt = build_lab_synthesis_prompt("test facts")
        assert '"lab_values"' in prompt
        assert '"value"' in prompt
        assert '"unit"' in prompt
        assert '"reference_range"' in prompt
        assert '"abnormal_flag"' in prompt
        assert "crp" in prompt
        assert "urea" in prompt
        assert "lactate" in prompt


class TestNoThinkingInstruction:
    """Tests for CAP_SYSTEM_INSTRUCTION_NO_THINKING."""

    def test_no_thinking_instruction_omits_prefix(self):
        assert "think silently" not in CAP_SYSTEM_INSTRUCTION_NO_THINKING

    def test_no_thinking_instruction_retains_clinical_content(self):
        assert "evidence-based" in CAP_SYSTEM_INSTRUCTION_NO_THINKING
        assert "SAFETY PRINCIPLES" in CAP_SYSTEM_INSTRUCTION_NO_THINKING
        assert "CURB65" in CAP_SYSTEM_INSTRUCTION_NO_THINKING


class TestParseJsonResponseRepair:
    """Tests for json_repair Tier 0 in parse_json_response."""

    def test_truncated_json_repaired(self):
        """Missing closing brace → json_repair reconstructs."""
        text = '{"consolidation": {"present": true, "confidence": "high"}'
        result = parse_json_response(text)
        assert isinstance(result, dict)
        assert result["consolidation"]["present"] is True

    def test_trailing_comma_repaired(self):
        """Trailing comma in JSON → json_repair fixes."""
        text = '{"key": "value", "other": 42,}'
        result = parse_json_response(text)
        assert result == {"key": "value", "other": 42}

    def test_plain_text_still_returns_empty(self):
        """Non-JSON text → still returns {}."""
        text = "This is just some clinical notes with no JSON at all."
        result = parse_json_response(text)
        assert result == {}

    def test_repair_list_mode(self):
        """Truncated array → repaired in list mode."""
        text = '[{"box_2d": [100, 200, 300, 400], "label": "consolidation"'
        result = parse_json_response(text, expect_list=True)
        assert isinstance(result, list)
        assert len(result) >= 1
        assert result[0]["box_2d"] == [100, 200, 300, 400]


class TestJSONCompleteCheck:
    """Tests for _is_json_complete() — the JSON StoppingCriteria helper."""

    def test_complete_simple_json(self):
        assert _is_json_complete('{"key": "value"}') is True

    def test_incomplete_json(self):
        assert _is_json_complete('{"key": "value"') is False

    def test_braces_in_strings_ignored(self):
        """Braces inside quoted strings should not affect depth tracking."""
        assert _is_json_complete('{"key": "value with } brace"}') is True

    def test_no_json_in_text(self):
        """Plain English text with no braces → False."""
        assert _is_json_complete("This is just clinical notes.") is False

    def test_empty_string(self):
        assert _is_json_complete("") is False

    def test_json_after_preamble(self):
        """JSON preceded by English text → True (finds first { and tracks)."""
        assert _is_json_complete('Here is the result: {"status": "ok"}') is True

    def test_escaped_quotes_handled(self):
        r"""Escaped quotes inside strings should not toggle in_string."""
        assert _is_json_complete('{"key": "val\\"ue"}') is True

    def test_clinical_narrative_with_braces(self):
        """Balanced braces in clinical text should still return True —
        callers must guard against applying StoppingCriteria to free text."""
        assert _is_json_complete("CURB65 score is 2 {moderate severity}.") is True


class TestExtractionInstruction:
    """Tests for CAP_EXTRACTION_INSTRUCTION constant."""

    def test_exists_and_is_string(self):
        assert isinstance(CAP_EXTRACTION_INSTRUCTION, str)
        assert len(CAP_EXTRACTION_INSTRUCTION) > 0

    def test_contains_extraction_keyword(self):
        assert "extraction" in CAP_EXTRACTION_INSTRUCTION.lower()

    def test_contains_uncertainty_keyword(self):
        assert "uncertainty" in CAP_EXTRACTION_INSTRUCTION.lower()

    def test_does_not_contain_clinical_reasoning(self):
        """Extraction instruction should be lightweight — no clinical directives."""
        text = CAP_EXTRACTION_INSTRUCTION.lower()
        assert "think silently" not in text
        assert "curb65" not in text
        assert "antibiotic" not in text
        assert "ng250" not in text


class TestLabSynthesisExample:
    """Tests for the 1-shot example in build_lab_synthesis_prompt."""

    def test_prompt_contains_example(self):
        prompt = build_lab_synthesis_prompt("test facts")
        assert "EXAMPLE:" in prompt

    def test_example_uses_divergent_names(self):
        """Example uses albumin/bilirubin — not CAP canonical tests."""
        prompt = build_lab_synthesis_prompt("test facts")
        assert "albumin" in prompt
        assert "bilirubin" in prompt

    def test_example_is_valid_json(self):
        """The example JSON should be parseable."""
        import json
        prompt = build_lab_synthesis_prompt("test facts")
        # Extract JSON between EXAMPLE: and CANONICAL
        start = prompt.index("EXAMPLE:\n") + len("EXAMPLE:\n")
        end = prompt.index("\n\nCANONICAL")
        example_json = prompt[start:end]
        parsed = json.loads(example_json)
        assert "lab_values" in parsed
        assert "albumin" in parsed["lab_values"]
        assert "bilirubin" in parsed["lab_values"]

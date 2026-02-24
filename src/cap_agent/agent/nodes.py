"""8 pipeline node functions + routing function for the CAP agent graph.

Each node is a thin wrapper that:
1. Creates a trace step
2. Extracts relevant data from state
3. Calls clinical_logic (deterministic) or medgemma (model)
4. Returns a state update dict
"""

import asyncio
import re
import threading
from datetime import datetime

from cap_agent.utils.config import TOKEN_BUDGETS
from cap_agent.utils.trace import create_trace_step, complete_trace_step
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
)
from cap_agent.data.extraction import (
    mock_extract_clinical_notes,
    mock_extract_lab_results,
    mock_analyze_cxr,
    extract_lab_results,
    analyze_cxr,
    extract_clinical_notes,
)
from cap_agent.models.prompts import (
    build_contradiction_prompt,
    build_clinician_summary_prompt,
)


_streaming_context = threading.local()


def set_streaming_callbacks(progress_cb=None, token_cb=None):
    """Set thread-local streaming callbacks for SSE bridge.

    Args:
        progress_cb: Called as progress_cb(sub_node, label, gpu_call, total)
                     before each GPU call during extraction.
        token_cb:    Called as token_cb(token_text, is_thinking) for each
                     generated token during contradiction resolution and
                     output assembly.
    """
    _streaming_context.progress_callback = progress_cb
    _streaming_context.token_callback = token_cb


def clear_streaming_callbacks():
    """Remove thread-local streaming callbacks."""
    _streaming_context.progress_callback = None
    _streaming_context.token_callback = None


def _parse_resolution_confidence(text: str):
    """Extract confidence rating from MedGemma resolution response.

    Returns "high", "moderate", or "low" if found, else None
    (keeps detection-phase confidence).

    Three-tier matching:
    1. Structured format: "CONFIDENCE: high" (our requested format)
    2. Natural language: "confidence is/as/level/rating high"
    3. Reversed order: "high confidence"
    """
    text_lower = text.lower()
    # 1. Structured: "confidence: high" / "confidence:high"
    m = re.search(r"confidence:\s*(high|moderate|low)", text_lower)
    if m:
        return m.group(1)
    # 2. Natural language variants
    m = re.search(
        r"confidence\s+(?:is|as|level[:\s]|rating[:\s])\s*(high|moderate|low)",
        text_lower,
    )
    if m:
        return m.group(1)
    # 3. Reversed: "high confidence", "moderate confidence"
    m = re.search(r"\b(high|moderate|low)\s+confidence\b", text_lower)
    if m:
        return m.group(1)
    return None


def load_case_node(state: dict) -> dict:
    """Validate and load the clinical case data."""
    trace = create_trace_step(
        1, "load_case", "Raw case data",
        "Validating case structure and required fields"
    )

    case_data = state["case_data"]
    errors = []

    required = ["demographics", "clinical_exam", "lab_results", "cxr", "past_medical_history"]
    for field in required:
        if field not in case_data:
            errors.append(f"Missing required field: {field}")

    status = "Case loaded successfully" if not errors else f"Case loaded with {len(errors)} errors"
    complete_trace_step(trace, status)

    return {
        "current_step": "Case loaded",
        "messages": [f"[load_case] {status}"],
        "reasoning_trace": [trace],
        "errors": errors,
    }


def parallel_extraction_node(state: dict) -> dict:
    """Run all three extraction tools in parallel."""
    trace = create_trace_step(
        2, "parallel_extraction",
        "Case data -> 3 extraction tools",
        "Running EHR QA, Lab Extraction, and CXR Classification concurrently"
    )

    case_data = state["case_data"]
    progress_cb = getattr(_streaming_context, "progress_callback", None)

    # Use real EHR extraction if FHIR bundle present, else mock
    if "fhir_bundle" in case_data:
        ehr_task = extract_clinical_notes(case_data, progress_callback=progress_cb)
    else:
        ehr_task = mock_extract_clinical_notes(case_data)

    # Use real lab extraction if lab_report present, else mock
    if "lab_report" in case_data:
        lab_task = extract_lab_results(case_data, progress_callback=progress_cb)
    else:
        lab_task = mock_extract_lab_results(case_data)

    # Use real CXR extraction if image_path present, else mock passthrough
    if case_data.get("cxr", {}).get("image_path"):
        cxr_task = analyze_cxr(case_data, progress_callback=progress_cb)
    else:
        cxr_task = mock_analyze_cxr(case_data)

    loop = asyncio.get_event_loop()
    results = loop.run_until_complete(asyncio.gather(
        ehr_task,
        lab_task,
        cxr_task,
        return_exceptions=True,
    ))

    tool_results = []
    clinical_findings, lab_findings, cxr_findings = [], [], []
    data_gaps, errors = [], []
    curb65_variables = None
    lab_values = None
    cxr_analysis = None
    clinical_exam = None
    patient_demographics = None

    tool_names = ["ehr_qa_extraction", "lab_extraction", "cxr_classification"]
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            errors.append(f"{tool_names[i]} failed: {str(result)}")
            data_gaps.append(f"{tool_names[i]} extraction unavailable")
            continue

        tool_results.append(result)
        raw = result["raw_output"]

        if result["tool_name"] == "ehr_qa_extraction":
            curb65_variables = raw.get("curb65_variables")
            clinical_exam = raw.get("clinical_exam")
            patient_demographics = raw.get("demographics")
            clinical_findings.append(result["summary"])
        elif result["tool_name"] == "lab_extraction":
            lab_values = raw.get("lab_values")
            lab_findings.append(result["summary"])
        elif result["tool_name"] == "cxr_classification":
            cxr_analysis = raw.get("cxr_analysis")
            cxr_findings.append(result["summary"])

    # Fallback: if MedGemma EHR extraction returned empty/incomplete data,
    # fill from case_data flat fields (always present, source of truth)
    case_data_demographics = case_data.get("demographics", {})
    case_data_exam = case_data.get("clinical_exam", {})
    case_data_pmh = case_data.get("past_medical_history", {})
    case_data_social = case_data.get("social_history", {})

    # Demographics fallback
    if not patient_demographics or not patient_demographics.get("age"):
        patient_demographics = {
            "age": case_data_demographics.get("age"),
            "sex": case_data_demographics.get("sex"),
            "allergies": case_data_pmh.get("allergies", []),
            "comorbidities": case_data_pmh.get("comorbidities", []),
            "recent_antibiotics": case_data_pmh.get("recent_antibiotics", []),
            "pregnancy": case_data_social.get("pregnancy", False),
            "oral_tolerance": case_data_social.get("oral_tolerance", True),
            "eating_independently": case_data_social.get("eating_independently", True),
            "travel_history": case_data_social.get("travel_history", []),
            "smoking_status": case_data_social.get("smoking_status"),
        }
        data_gaps.append("Demographics from case data (MedGemma EHR extraction incomplete)")

    # Clinical exam fallback
    if not clinical_exam or not clinical_exam.get("observations"):
        if case_data_exam.get("observations"):
            clinical_exam = case_data_exam
            data_gaps.append("Clinical exam from case data (MedGemma EHR extraction incomplete)")

    # CURB-65 variables fallback
    if not curb65_variables or not curb65_variables.get("age"):
        obs = (case_data_exam.get("observations") or {})
        confusion_data = case_data_exam.get("confusion_assessment", {})
        curb65_variables = {
            "confusion": confusion_data.get("confused", False),
            "urea": (case_data.get("lab_results", {}).get("urea", {}) or {}).get("value"),
            "respiratory_rate": obs.get("respiratory_rate"),
            "systolic_bp": obs.get("systolic_bp"),
            "diastolic_bp": obs.get("diastolic_bp"),
            "age": case_data_demographics.get("age"),
        }
        data_gaps.append("CURB-65 variables from case data (MedGemma EHR extraction incomplete)")

    complete_trace_step(trace, f"Extracted from {len(tool_results)}/3 tools")

    return {
        "current_step": "Extraction complete",
        "messages": [f"[parallel_extraction] Completed {len(tool_results)}/3 tools"],
        "reasoning_trace": [trace],
        "tool_results": tool_results,
        "clinical_findings": clinical_findings,
        "lab_findings": lab_findings,
        "cxr_findings": cxr_findings,
        "curb65_variables": curb65_variables,
        "lab_values": lab_values,
        "cxr_analysis": cxr_analysis,
        "clinical_exam": clinical_exam,
        "patient_demographics": patient_demographics,
        "data_gaps": data_gaps,
        "errors": errors,
    }


def severity_scoring_node(state: dict) -> dict:
    """Compute CURB65 score using deterministic logic (no model involvement)."""
    trace = create_trace_step(
        3, "severity_scoring",
        "CURB65 variables from extraction",
        "Deterministic CURB65 computation"
    )

    cv = state.get("curb65_variables") or {}
    curb65_score = compute_curb65(cv)
    data_gaps = compute_curb65_data_gaps(curb65_score, curb65_score["crb65"])
    demographics = state.get("patient_demographics") or {}
    obs = (state.get("clinical_exam") or {}).get("observations", {})
    labs = state.get("lab_values") or {}
    curb65 = curb65_score["curb65"]
    crb65 = curb65_score["crb65"]
    severity_tier = curb65_score["severity_tier"]

    score_str = (
        f"CURB65={curb65}" if curb65 is not None
        else f"CRB65={crb65} (urea unavailable)"
    )
    complete_trace_step(trace, f"{score_str}, severity={severity_tier}")

    return {
        "current_step": f"Severity scored: {severity_tier}",
        "messages": [f"[severity_scoring] {score_str} -> {severity_tier} severity"],
        "reasoning_trace": [trace],
        "curb65_score": curb65_score,
        "data_gaps": data_gaps,
    }


def check_contradictions_node(state: dict) -> dict:
    """Evaluate all 10 cross-modal contradiction rules."""
    trace = create_trace_step(
        4, "check_contradictions",
        "All extraction outputs + CURB65 score",
        "Evaluating 10 contradiction rules against current state"
    )

    case_data = state.get("case_data", {})
    contradictions = detect_contradictions(
        cxr=state.get("cxr_analysis") or {},
        exam=state.get("clinical_exam") or {},
        labs=state.get("lab_values") or {},
        demographics=state.get("patient_demographics") or {},
        curb65=state.get("curb65_score") or {},
        case_data=case_data,
        antibiotic_recommendation=(
            state.get("antibiotic_recommendation")
            or case_data.get("prior_antibiotic_recommendation")
        ),
        micro_results=case_data.get("micro_results"),
    )

    n_fired = len(contradictions)
    complete_trace_step(trace, f"{n_fired} contradiction(s) detected out of 10 rules evaluated")

    return {
        "current_step": f"Contradictions: {n_fired} detected",
        "messages": [f"[check_contradictions] {n_fired}/10 rules triggered"],
        "reasoning_trace": [trace],
        "contradictions_detected": contradictions,
    }


def should_resolve_contradictions(state: dict) -> str:
    """Route to contradiction resolution if any were detected, else skip to treatment."""
    if state.get("contradictions_detected"):
        return "contradiction_resolution"
    return "treatment_selection"


def contradiction_resolution_node(state: dict) -> dict:
    """Use MedGemma to reason about detected contradictions."""
    from cap_agent.models.medgemma import call_medgemma, call_medgemma_streaming, extract_thinking

    token_cb = getattr(_streaming_context, "token_callback", None)

    trace = create_trace_step(
        5, "contradiction_resolution",
        f"{len(state['contradictions_detected'])} contradiction(s) to resolve",
        "Applying resolution strategies A-D using MedGemma reasoning"
    )

    resolutions = []
    thinking_traces = []

    for contradiction in state["contradictions_detected"]:
        rule_id = contradiction["rule_id"]
        strategy = contradiction["resolution_strategy"]

        # Strategy E: deterministic short-circuit (no GPU call)
        if strategy == "E":
            rec = contradiction.get("recommendation")
            rec_str = f" Recommendation: {rec}" if rec else ""
            resolutions.append(
                f"**{rule_id} Resolution (E — deterministic):** "
                f"{contradiction['pattern']}.{rec_str}"
            )
            continue

        prompt = build_contradiction_prompt(
            strategy=strategy,
            rule_id=rule_id,
            pattern=contradiction["pattern"],
            evidence_for=contradiction["evidence_for"],
            evidence_against=contradiction["evidence_against"],
        )

        if token_cb:
            response = call_medgemma_streaming(
                prompt,
                max_new_tokens=TOKEN_BUDGETS["contradiction_resolution"],
                token_callback=token_cb,
            )
        else:
            response = call_medgemma(prompt, max_new_tokens=TOKEN_BUDGETS["contradiction_resolution"])
        thinking, answer = extract_thinking(response)

        if thinking:
            thinking_traces.append(f"[{rule_id}] {thinking[:500]}")

        # Update detection-phase confidence if MedGemma provides a resolution confidence
        resolution_confidence = _parse_resolution_confidence(answer)
        if resolution_confidence:
            contradiction["confidence"] = resolution_confidence

        resolutions.append(f"**{rule_id} Resolution ({strategy}):** {answer}")

    complete_trace_step(trace, f"Resolved {len(resolutions)} contradiction(s)")

    return {
        "current_step": "Contradictions resolved",
        "messages": [f"[contradiction_resolution] Resolved {len(resolutions)} contradictions"],
        "reasoning_trace": [trace],
        "resolution_results": resolutions,
        "thinking_traces": thinking_traces,
    }


def treatment_selection_node(state: dict) -> dict:
    """Select evidence-based treatment: deterministic antibiotic lookup + investigation planning."""
    trace = create_trace_step(
        7, "treatment_selection",
        "CURB65 severity + patient factors",
        "Deterministic antibiotic selection + investigation planning"
    )

    curb65 = state.get("curb65_score", {})
    demographics = state.get("patient_demographics", {})
    labs = state.get("lab_values", {})
    severity = curb65.get("severity_tier", "moderate")

    egfr = None
    if labs and "egfr" in labs:
        egfr = labs["egfr"].get("value")

    antibiotic_rec = select_antibiotic(
        severity=severity,
        allergies=demographics.get("allergies", []),
        oral_tolerance=demographics.get("oral_tolerance", True),
        pregnancy=demographics.get("pregnancy", False),
        travel_history=demographics.get("travel_history", []),
        egfr=egfr,
        recent_antibiotics=demographics.get("recent_antibiotics", []),
        atypical_indicators=demographics.get("atypical_indicators", []),
    )
    # Add CURB65 info to reasoning
    antibiotic_rec["reasoning"] = (
        f"Severity {severity} (CURB65={curb65.get('curb65', '?')}), "
        + antibiotic_rec["reasoning"].split(", ", 1)[1]
    )

    obs = (state.get("clinical_exam") or {}).get("observations", {})
    social = state.get("case_data", {}).get("social_history", {})
    investigation_plan = plan_investigations(
        severity=severity,
        observations=obs,
        lab_values=labs or {},
        travel_history=demographics.get("travel_history", []),
        legionella_risk_factors=social.get("legionella_risk_factors", []),
    )

    # CR-10: Check for fluoroquinolone + penicillin intolerance
    cr10_contradictions = []
    cr10 = detect_cr10(antibiotic_rec, demographics.get("allergies", []))
    if cr10:
        cr10_contradictions.append(cr10)

    inv_count = sum(1 for v in investigation_plan.values() if v.get("recommended"))
    first_line_short = antibiotic_rec["first_line"].split(" + ")[0]
    cr10_msg = f" | CR-10 fired" if cr10_contradictions else ""
    complete_trace_step(
        trace,
        f"Treatment: {first_line_short} | Investigations: {inv_count}/4 recommended{cr10_msg}"
    )

    return {
        "current_step": "Treatment selected",
        "messages": [f"[treatment_selection] {severity} severity -> {first_line_short}"],
        "reasoning_trace": [trace],
        "antibiotic_recommendation": antibiotic_rec,
        "investigation_plan": investigation_plan,
        "contradictions_detected": cr10_contradictions,
    }


def monitoring_plan_node(state: dict) -> dict:
    """Generate monitoring plan with discharge criteria check."""
    trace = create_trace_step(
        8, "monitoring_plan",
        "Severity tier + current observations",
        "Deterministic monitoring plan + discharge criteria"
    )

    curb65 = state.get("curb65_score", {})
    severity = curb65.get("severity_tier", "moderate")
    obs = (state.get("clinical_exam") or {}).get("observations", {})
    confusion = (state.get("clinical_exam") or {}).get("confusion_status", {})
    demographics = state.get("patient_demographics") or {}
    case_data = state.get("case_data", {})

    # Treatment status (Day 3-4 monitoring)
    treatment_status = case_data.get("treatment_status")

    # CRP trend: compare admission baseline vs current lab values
    crp_trend_result = None
    admission_labs = case_data.get("admission_labs")
    lab_values = state.get("lab_values") or {}
    if admission_labs and "crp" in admission_labs:
        current_crp_entry = lab_values.get("crp", {})
        current_crp = current_crp_entry.get("value") if isinstance(current_crp_entry, dict) else None
        if current_crp is not None:
            days = 0
            if treatment_status:
                days = treatment_status.get("days_on_treatment", 0)
            crp_trend_result = compute_crp_trend(
                admission_crp=admission_labs["crp"],
                current_crp=current_crp,
                days_since_admission=days,
            )

    # PCT trend: compare admission baseline vs current lab values
    pct_trend_result = None
    if admission_labs and "pct" in admission_labs:
        current_pct_entry = lab_values.get("procalcitonin", {})
        current_pct = current_pct_entry.get("value") if isinstance(current_pct_entry, dict) else None
        if current_pct is not None:
            days = 0
            if treatment_status:
                days = treatment_status.get("days_on_treatment", 0)
            pct_trend_result = compute_pct_trend(
                admission_pct=admission_labs["pct"],
                current_pct=current_pct,
                days_since_admission=days,
            )

    monitoring = compute_monitoring_plan(
        severity=severity,
        observations=obs,
        confusion_status=confusion,
        demographics=demographics,
        treatment_status=treatment_status,
        crp_trend=crp_trend_result,
        pct_trend=pct_trend_result,
        micro_results=case_data.get("micro_results"),
    )

    status = "met" if monitoring["discharge_criteria_met"] else "NOT met"
    complete_trace_step(trace, f"Monitoring plan set. Discharge criteria: {status}")

    return {
        "current_step": "Monitoring plan set",
        "messages": [f"[monitoring_plan] Next: {monitoring['next_review'].split('.')[0]}"],
        "reasoning_trace": [trace],
        "monitoring_plan": monitoring,
    }


def _build_data_sources(case_data: dict) -> dict:
    """Build per-section data source metadata by inspecting case_data keys."""
    data_sources = {
        "ehr": [],
        "labs": [],
        "cxr": [],
    }
    # EHR sources
    if "fhir_bundle" in case_data:
        data_sources["ehr"].append("fhir_r4_bundle")
        for entry in (case_data.get("fhir_bundle", {}).get("entry") or []):
            if entry.get("resource", {}).get("resourceType") == "DocumentReference":
                data_sources["ehr"].append("clerking_note")
                break
    if not data_sources["ehr"]:
        data_sources["ehr"].append("synthetic_flat_data")

    # Lab sources
    if "lab_report" in case_data:
        data_sources["labs"].append("nhs_pathology_report")
    if "fhir_bundle" in case_data:
        data_sources["labs"].append("fhir_lab_observations")
    if not data_sources["labs"]:
        data_sources["labs"].append("synthetic_flat_data")

    # CXR sources
    if case_data.get("cxr", {}).get("image_path"):
        data_sources["cxr"].append("cxr_image")
        if case_data.get("cxr", {}).get("prior_image_path"):
            data_sources["cxr"].append("prior_cxr_image")
    else:
        data_sources["cxr"].append("synthetic_flat_data")

    return data_sources


def output_assembly_node(state: dict) -> dict:
    """Assemble structured JSON output and generate clinician summary."""
    from cap_agent.models.medgemma import call_medgemma, call_medgemma_streaming, extract_thinking

    trace = create_trace_step(
        9, "output_assembly",
        "All pipeline outputs",
        "Assembling structured output + MedGemma clinician summary"
    )

    demographics = state.get("patient_demographics", {})
    curb65 = state.get("curb65_score", {})
    cxr = state.get("cxr_analysis", {})
    labs = state.get("lab_values", {})
    contradictions = state.get("contradictions_detected", [])
    resolutions = state.get("resolution_results", [])
    treatment = state.get("antibiotic_recommendation", {})
    investigations = state.get("investigation_plan", {})
    monitoring = state.get("monitoring_plan", {})
    data_gaps = state.get("data_gaps", [])
    synthesis = state.get("synthesized_findings", "")
    case_data = state.get("case_data", {})

    # Source attribution: build per-section data sources
    data_sources = _build_data_sources(case_data)

    # Confidence-weighted contradiction tiers
    alerts = [c for c in contradictions if c.get("confidence") != "low"]
    informational = [c for c in contradictions if c.get("confidence") == "low"]

    # Structured JSON
    structured = {
        "case_id": state.get("case_id"),
        "patient_id": state.get("patient_id"),
        "generated_at": datetime.now().isoformat(),
        "ai_disclaimer": (
            "AI-generated observations for clinician review. "
            "Not a substitute for clinical judgement."
        ),
        "provenance": {
            "extraction_pipeline": "medgemma_1.5_4b_agentic",
            "data_sources": data_sources,
            "extraction_tools": {
                "ehr": "3-step EHR QA" if "fhir_bundle" in case_data else "mock_passthrough",
                "labs": "2-step lab extraction" if "lab_report" in case_data else "mock_passthrough",
                "cxr": "3-stage CXR analysis" if case_data.get("cxr", {}).get("image_path") else "mock_passthrough",
            },
        },
        "sections": {
            "1_patient": {
                "demographics": demographics,
                "source": "ehr_qa_extraction",
                "data_sources": data_sources["ehr"],
            },
            "2_severity": {
                "curb65": curb65,
                "source": "deterministic_scoring",
            },
            "3_cxr": {
                "findings": cxr,
                "source": "cxr_classification",
                "data_sources": data_sources["cxr"],
            },
            "4_key_bloods": {
                "values": labs,
                "source": "lab_extraction",
                "data_sources": data_sources["labs"],
            },
            "5_contradiction_alert": {
                "detected": len(contradictions),
                "alerts": alerts,
                "informational": informational,
                "resolutions": resolutions,
                "source": "cross_modal_contradiction_engine",
            },
            "6_treatment_pathway": {
                "antibiotic": treatment,
                "corticosteroid": treatment.get("corticosteroid_recommendation"),
                "investigations": investigations,
                "source": "evidence_based_treatment_selection",
            },
            "7_data_gaps": {"gaps": data_gaps, "source": "gap_detection"},
            "8_monitoring": {"plan": monitoring, "source": "monitoring_plan"},
        },
        "synthesis": synthesis,
        "reasoning_trace": state.get("reasoning_trace", []),
    }

    # Clinician summary via MedGemma (with deterministic fallback)
    summary_prompt = build_clinician_summary_prompt(
        demographics=demographics,
        curb65=curb65,
        cxr=cxr,
        labs=labs,
        contradictions=contradictions,
        treatment=treatment,
        monitoring=monitoring,
        data_gaps=data_gaps,
    )

    clinician_summary = ""
    try:
        token_cb = getattr(_streaming_context, "token_callback", None)
        if token_cb:
            response = call_medgemma_streaming(
                summary_prompt,
                max_new_tokens=TOKEN_BUDGETS["clinician_summary"],
                enable_thinking=False,
                token_callback=token_cb,
            )
        else:
            response = call_medgemma(summary_prompt, max_new_tokens=TOKEN_BUDGETS["clinician_summary"], enable_thinking=False)
        _, clinician_summary = extract_thinking(response)
    except Exception:
        import logging
        logging.getLogger(__name__).exception("MedGemma summary failed, using deterministic fallback")

    if not clinician_summary or not clinician_summary.strip():
        # Deterministic fallback: build summary from structured data
        age = demographics.get("age", "?")
        sex = demographics.get("sex", "Unknown")
        score = curb65.get("curb65") if curb65.get("curb65") is not None else curb65.get("crb65", "?")
        score_label = "CURB65" if curb65.get("curb65") is not None else "CRB65"
        severity = curb65.get("severity_tier", "unknown")
        cxr_desc = cxr.get("classification", "not assessed") if cxr else "not assessed"
        crp_val = labs.get("crp", {}).get("value", "?") if labs else "?"
        urea_val = labs.get("urea", {}).get("value", "?") if labs else "?"
        first_line = treatment.get("first_line", "pending") if treatment else "pending"
        n_contradictions = len(contradictions)
        contradiction_line = f"{n_contradictions} contradiction(s) detected — see alerts" if n_contradictions else "None"
        gap_line = ", ".join(data_gaps) if data_gaps else "None"
        next_review = monitoring.get("next_review", "As per clinical judgement") if monitoring else "As per clinical judgement"

        clinician_summary = (
            f"1. PATIENT: {age}yo {sex}, "
            + ", ".join(demographics.get("comorbidities", [])[:3] or ["no listed comorbidities"])
            + f"\n2. SEVERITY: {score_label}={score} ({severity})"
            + f"\n3. CXR: {cxr_desc}"
            + f"\n4. KEY BLOODS: CRP {crp_val}, Urea {urea_val}"
            + f"\n5. CONTRADICTIONS: {contradiction_line}"
            + f"\n6. TREATMENT: {first_line}"
            + f"\n7. DATA GAPS: {gap_line}"
            + f"\n8. MONITORING: {next_review}"
            + "\nAI-generated observations for clinician review."
        )
        data_gaps.append("Clinician summary from deterministic fallback (MedGemma unavailable)")

    complete_trace_step(trace, "Output assembled: structured JSON + clinician summary")

    return {
        "current_step": "Output assembled",
        "messages": ["[output_assembly] Pipeline complete"],
        "reasoning_trace": [trace],
        "clinician_summary": clinician_summary,
        "structured_output": structured,
    }

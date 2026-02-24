"""Extraction tools for CAP case data.

Clinical notes extraction supports two modes:
  - Mock: passthrough from flat synthetic dict (when no fhir_bundle present)
  - Real: 3-step MedGemma EHR QA pipeline (when fhir_bundle present)

Lab extraction supports two modes:
  - Mock: passthrough from flat synthetic dict (when no lab_report present)
  - Real: 2-step MedGemma pipeline (when lab_report present)

CXR analysis supports two modes:
  - Mock: passthrough from flat synthetic dict (when no image_path present)
  - Real: 3-stage MedGemma pipeline (when image_path present)

Each tool returns a ToolResult dict: {tool_name, status, summary, raw_output}.
"""

import logging

from cap_agent.utils.config import TOKEN_BUDGETS
from cap_agent.models import medgemma

logger = logging.getLogger(__name__)
from cap_agent.models.prompts import (
    CAP_EXTRACTION_INSTRUCTION,
    build_cxr_classification_prompt,
    build_cxr_localization_prompt,
    build_cxr_longitudinal_prompt,
    build_ehr_narrative_filter_prompt,
    build_ehr_structured_filter_prompt,
    build_ehr_synthesis_prompt,
    build_lab_extraction_prompt,
    build_lab_synthesis_prompt,
)
from cap_agent.data.fhir_utils import (
    group_resources_by_type,
    render_resources_as_text,
    get_document_text,
    validate_and_repair_ehr_output,
    extract_lab_observations,
    validate_and_repair_lab_output,
)

# Default resource types to use if Step 1 (identify) fails
DEFAULT_RESOURCE_TYPES = [
    "Patient", "Condition", "Observation",
    "AllergyIntolerance", "MedicationRequest",
    "DocumentReference", "Encounter",
]


async def mock_extract_clinical_notes(case_data: dict) -> dict:
    """Mock EHR QA: extracts CURB65 variables, allergies, comorbidities, exam findings."""
    exam = case_data["clinical_exam"]
    obs = exam["observations"]
    confusion = exam["confusion_assessment"]
    pmh = case_data["past_medical_history"]
    social = case_data["social_history"]

    demographics = {
        "age": case_data["demographics"]["age"],
        "sex": case_data["demographics"]["sex"],
        "allergies": [
            a if isinstance(a, dict) else {"drug": a, "reaction_type": "unknown", "severity": "unknown"}
            for a in pmh["allergies"]
        ],
        "comorbidities": pmh["comorbidities"],
        "recent_antibiotics": pmh["recent_antibiotics"],
        "pregnancy": social["pregnancy"],
        "oral_tolerance": social["oral_tolerance"],
        "eating_independently": social.get("eating_independently", True),
        "travel_history": social["travel_history"],
        "smoking_status": social.get("smoking_status"),
    }

    clinical_exam_findings = {
        "respiratory_exam": {
            "crackles": exam["respiratory_exam"]["crackles"],
            "crackles_location": exam["respiratory_exam"].get("crackles_location"),
            "bronchial_breathing": exam["respiratory_exam"]["bronchial_breathing"],
            "bronchial_breathing_location": exam["respiratory_exam"].get(
                "bronchial_breathing_location"
            ),
        },
        "observations": obs,
        "confusion_status": {
            "present": confusion["confused"],
            "amt_score": confusion["amt_score"],
        },
    }

    curb65_vars = {
        "confusion": confusion["confused"],
        "urea": case_data["lab_results"]["urea"]["value"],
        "respiratory_rate": obs["respiratory_rate"],
        "systolic_bp": obs["systolic_bp"],
        "diastolic_bp": obs["diastolic_bp"],
        "age": case_data["demographics"]["age"],
    }

    return {
        "tool_name": "ehr_qa_extraction",
        "status": "success",
        "summary": (
            f"Extracted demographics, exam findings, CURB65 variables for "
            f"{case_data['demographics']['age']}yo {case_data['demographics']['sex']}"
        ),
        "raw_output": {
            "demographics": demographics,
            "clinical_exam": clinical_exam_findings,
            "curb65_variables": curb65_vars,
        },
    }


async def mock_extract_lab_results(case_data: dict) -> dict:
    """Mock Lab Extraction: extracts all lab values with units and flags."""
    labs = case_data["lab_results"]
    lab_values = {}
    for test_name, test_data in labs.items():
        lab_values[test_name] = {
            "value": test_data["value"],
            "unit": test_data["unit"],
            "reference_range": test_data["reference_range"],
            "abnormal_flag": test_data["abnormal"],
        }

    abnormal_count = sum(1 for v in labs.values() if v["abnormal"])
    return {
        "tool_name": "lab_extraction",
        "status": "success",
        "summary": f"Extracted {len(labs)} lab values, {abnormal_count} abnormal",
        "raw_output": {"lab_values": lab_values},
    }


async def mock_analyze_cxr(case_data: dict) -> dict:
    """Mock CXR analysis: passes through CXR data from flat case_data.

    Used when no CXR image is available (e.g. T=48h — CXR not repeated).
    Passes through the existing findings from case_data["cxr"]["findings"]
    or case_data["cxr"] directly.
    """
    cxr = case_data.get("cxr", {})
    # Support both nested (cxr.findings) and flat (cxr.consolidation) layouts
    findings = cxr.get("findings", cxr)

    summary_parts = []
    for finding in ["consolidation", "pleural_effusion", "cardiomegaly", "edema", "atelectasis"]:
        info = findings.get(finding, {})
        if isinstance(info, dict) and info.get("present"):
            summary_parts.append(f"{finding}: {info.get('location', 'present')}")
    summary = "; ".join(summary_parts) if summary_parts else "No significant findings"

    return {
        "tool_name": "cxr_classification",
        "status": "success",
        "summary": f"CXR mock passthrough: {summary}",
        "raw_output": {"cxr_analysis": findings},
    }


async def extract_lab_results(case_data: dict, progress_callback=None) -> dict:
    """Real MedGemma lab extraction using 2-step fact-filter pattern.

    Steps:
        1a. Extract English facts from plaintext lab report (MedGemma call, if text)
        1b. Render FHIR lab Observations as text (deterministic, 0 GPU calls)
        2.  Synthesize combined facts into canonical JSON (MedGemma call)

    Supports dual-source merge: both plaintext and FHIR can contribute facts.
    Falls back to mock_extract_lab_results when no lab_report key present.

    Requires GPU + HF_TOKEN for real extraction.
    Returns ToolResult with {lab_values: {...}}.
    """
    lab_report = case_data.get("lab_report")
    if not lab_report:
        return await mock_extract_lab_results(case_data)

    has_text = (
        lab_report.get("format") == "text"
        and lab_report.get("content", "").strip()
    )

    # Check for FHIR lab observations
    fhir_labs = []
    bundle = case_data.get("fhir_bundle")
    if bundle:
        fhir_labs = extract_lab_observations(bundle)
    has_fhir_labs = len(fhir_labs) > 0

    if not has_text and not has_fhir_labs:
        return await mock_extract_lab_results(case_data)

    status = "success"
    data_gaps: list[str] = []
    all_facts: list[str] = []

    # --- Step 1a: Extract facts from plaintext (1 GPU call) ---
    logger.debug("Lab sources: has_text=%s, has_fhir_labs=%s (%d obs)", has_text, has_fhir_labs, len(fhir_labs))
    text_facts = ""
    if has_text:
        try:
            if progress_callback:
                progress_callback("lab_extraction", "Extracting lab values...", 1, 2)
            extraction_prompt = build_lab_extraction_prompt(lab_report["content"])
            raw_response = medgemma.call_medgemma(extraction_prompt, max_new_tokens=TOKEN_BUDGETS["lab_extraction"], enable_thinking=False, system_instruction=CAP_EXTRACTION_INSTRUCTION)
            _, text_facts = medgemma.extract_thinking(raw_response)
            logger.debug("Lab step 1a response (%d chars): %s", len(raw_response), text_facts[:500])
            all_facts.append(f"FROM PATHOLOGY REPORT:\n{text_facts}")
        except (RuntimeError, ValueError) as e:
            logger.warning("Lab text extraction failed: %s", e)
            if not has_fhir_labs:
                return {
                    "tool_name": "lab_extraction",
                    "status": "error",
                    "summary": "Lab text extraction failed and no FHIR labs available",
                    "raw_output": {"lab_values": {}},
                }
            status = "partial"
            data_gaps.append("Plaintext lab extraction failed, using FHIR only")

    # --- Step 1b: Render FHIR lab observations (0 GPU calls) ---
    if has_fhir_labs:
        fhir_text = render_resources_as_text(fhir_labs)
        logger.debug("Lab step 1b FHIR text (%d chars): %s", len(fhir_text), fhir_text[:300])
        all_facts.append(f"FROM STRUCTURED RECORDS:\n{fhir_text}")

    if not all_facts:
        logger.debug("No lab facts from any source — returning error")
        return {
            "tool_name": "lab_extraction",
            "status": "error",
            "summary": "No lab facts extracted from any source",
            "raw_output": {"lab_values": {}},
        }

    # --- Step 2: Synthesize into JSON (1 GPU call) ---
    combined_facts = "\n\n".join(all_facts)
    logger.debug("Lab combined facts (%d chars) -> synthesizing", len(combined_facts))
    try:
        if progress_callback:
            progress_callback("lab_synthesis", "Synthesizing lab results...", 2, 2)
        synthesis_prompt = build_lab_synthesis_prompt(combined_facts)
        raw_synthesis = medgemma.call_medgemma(synthesis_prompt, max_new_tokens=TOKEN_BUDGETS["lab_synthesis"], enable_thinking=False, system_instruction=CAP_EXTRACTION_INSTRUCTION)
        _, synthesis_text = medgemma.extract_thinking(raw_synthesis)
        logger.debug("Lab step 2 response (%d chars): %s", len(raw_synthesis), synthesis_text[:500])
        raw_output = medgemma.parse_json_response(synthesis_text)
        logger.debug("Lab parsed keys: %s", list(raw_output.keys()) if raw_output else "EMPTY")

        if not raw_output:
            raise ValueError("Empty JSON from lab synthesis step")

        normalized, repair_gaps = validate_and_repair_lab_output(raw_output)
        data_gaps.extend(repair_gaps)
        logger.debug("Lab normalized: %d labs, gaps: %s", len(normalized), repair_gaps)

        if repair_gaps:
            status = "partial"

    except (RuntimeError, ValueError) as e:
        logger.error("Lab synthesis failed: %s", e)
        return {
            "tool_name": "lab_extraction",
            "status": "error",
            "summary": f"Lab synthesis failed — {e}",
            "raw_output": {"lab_values": {}},
        }

    # Build summary
    abnormal_count = sum(1 for v in normalized.values() if v.get("abnormal_flag"))
    summary = (
        f"Extracted {len(normalized)} lab values, {abnormal_count} abnormal "
        f"via 2-step lab pipeline"
    )

    return {
        "tool_name": "lab_extraction",
        "status": status,
        "summary": summary,
        "raw_output": {"lab_values": normalized},
    }


async def extract_clinical_notes(case_data: dict, progress_callback=None) -> dict:
    """Real MedGemma EHR QA extraction using 3-step pattern.

    Steps:
        1. Fetch+Filter narrative from clerking note (MedGemma call 1)
        2. Fetch+Filter structured FHIR data (MedGemma call 2)
        3. Synthesize into canonical JSON schema (MedGemma call 3)

    The identify step (selecting FHIR resource types) was eliminated because
    DEFAULT_RESOURCE_TYPES already covers all CAP-relevant types, saving 1 GPU call.

    Requires GPU + HF_TOKEN. Reads from case_data["fhir_bundle"].
    Returns ToolResult with {demographics, clinical_exam, curb65_variables}.
    """
    bundle = case_data.get("fhir_bundle")
    if not bundle:
        return {
            "tool_name": "ehr_qa_extraction",
            "status": "error",
            "summary": "No FHIR bundle provided in case data",
            "raw_output": {"demographics": {}, "clinical_exam": {}, "curb65_variables": {}},
        }

    status = "success"
    data_gaps = []
    resource_types = list(DEFAULT_RESOURCE_TYPES)

    # --- Step 1: Fetch+Filter narrative (clerking note) ---
    narrative_facts = ""
    narrative_ok = False
    try:
        doc_text = get_document_text(bundle)
        if doc_text:
            if progress_callback:
                progress_callback("ehr_narrative", "Filtering clinical notes...", 1, 3)
            narrative_prompt = build_ehr_narrative_filter_prompt(doc_text)
            raw_narrative = medgemma.call_medgemma(narrative_prompt, max_new_tokens=TOKEN_BUDGETS["ehr_narrative_filter"], enable_thinking=False, system_instruction=CAP_EXTRACTION_INSTRUCTION)
            _, narrative_facts = medgemma.extract_thinking(raw_narrative)
            narrative_ok = True
        else:
            data_gaps.append("No DocumentReference/clerking note in FHIR bundle")
    except (RuntimeError, ValueError, UnicodeDecodeError) as e:
        logger.warning("EHR narrative extraction failed: %s", e)
        status = "partial"
        data_gaps.append("Narrative extraction failed")

    # --- Step 2: Fetch+Filter structured FHIR data ---
    structured_facts = ""
    structured_ok = False
    try:
        grouped = group_resources_by_type(bundle)
        structured_resources = []
        for rtype in resource_types:
            if rtype != "DocumentReference" and rtype in grouped:
                structured_resources.extend(grouped[rtype])
        if structured_resources:
            if progress_callback:
                progress_callback("ehr_structured", "Filtering structured data...", 2, 3)
            rendered = render_resources_as_text(structured_resources)
            structured_prompt = build_ehr_structured_filter_prompt(rendered)
            raw_structured = medgemma.call_medgemma(structured_prompt, max_new_tokens=TOKEN_BUDGETS["ehr_structured_filter"], enable_thinking=False, system_instruction=CAP_EXTRACTION_INSTRUCTION)
            _, structured_facts = medgemma.extract_thinking(raw_structured)
            structured_ok = True
        else:
            data_gaps.append("No structured FHIR resources matched identified types")
    except (RuntimeError, ValueError, TypeError) as e:
        logger.warning("EHR structured extraction failed: %s", e)
        status = "partial"
        data_gaps.append("Structured extraction failed")

    # If both fetch steps failed, nothing to synthesize
    if not narrative_ok and not structured_ok:
        return {
            "tool_name": "ehr_qa_extraction",
            "status": "error",
            "summary": "Both narrative and structured extraction failed",
            "raw_output": {"demographics": {}, "clinical_exam": {}, "curb65_variables": {}},
        }

    # --- Step 3: Synthesize into structured JSON ---
    try:
        if progress_callback:
            progress_callback("ehr_synthesis", "Synthesizing patient data...", 3, 3)
        synthesis_prompt = build_ehr_synthesis_prompt(
            narrative_facts or "No narrative data available.",
            structured_facts or "No structured data available.",
        )
        raw_synthesis = medgemma.call_medgemma(synthesis_prompt, max_new_tokens=TOKEN_BUDGETS["ehr_synthesis"], enable_thinking=False, system_instruction=CAP_EXTRACTION_INSTRUCTION)
        _, synthesis_text = medgemma.extract_thinking(raw_synthesis)
        raw_output = medgemma.parse_json_response(synthesis_text)

        if not raw_output:
            raise ValueError("Empty JSON from synthesis step")

        repaired, repair_gaps = validate_and_repair_ehr_output(raw_output)
        data_gaps.extend(repair_gaps)

        if repair_gaps:
            status = "partial"

    except (RuntimeError, ValueError) as e:
        logger.error("EHR synthesis failed: %s", e)
        return {
            "tool_name": "ehr_qa_extraction",
            "status": "error",
            "summary": "EHR synthesis failed — could not produce structured output",
            "raw_output": {"demographics": {}, "clinical_exam": {}, "curb65_variables": {}},
        }

    # Build summary
    demo = repaired.get("demographics", {})
    age = demo.get("age", "?")
    sex = demo.get("sex", "?")
    summary = (
        f"Extracted demographics, exam findings, CURB65 variables for "
        f"{age}yo {sex} via 3-step EHR QA pipeline"
    )

    return {
        "tool_name": "ehr_qa_extraction",
        "status": status,
        "summary": summary,
        "raw_output": repaired,
    }


async def analyze_cxr(case_data: dict, progress_callback=None) -> dict:
    """Real 3-stage CXR analysis pipeline using MedGemma.

    Stage A — Classification: 5 CheXpert conditions + image quality
    Stage B — Localization: Bounding boxes for positive localizable findings
    Stage C — Longitudinal: Prior vs current comparison (if prior_image_path exists)

    Error handling cascade:
        - Classification failure → status="error", skip B+C
        - Localization failure for one finding → status="partial", classification preserved
        - Longitudinal failure → status="partial", classification+localization preserved
        - Missing image path → status="error" immediately
    """
    from PIL import Image

    cxr = case_data.get("cxr", {})
    image_path = cxr.get("image_path")
    if not image_path:
        return {
            "tool_name": "cxr_classification",
            "status": "error",
            "summary": "No CXR image path provided",
            "raw_output": {"cxr_analysis": {}},
        }

    # Load and preprocess current image
    try:
        current_image = Image.open(image_path)
        current_image = medgemma.pad_image_to_square(current_image)
    except (OSError, RuntimeError, ValueError) as e:
        logger.error("CXR image load failed: %s", e)
        return {
            "tool_name": "cxr_classification",
            "status": "error",
            "summary": f"Failed to load CXR image: {e}",
            "raw_output": {"cxr_analysis": {}},
        }

    status = "success"

    # --- Stage A: Classification ---
    # Calculate total GPU calls for CXR: 1 classification + conditionals
    cxr_total = 1  # classification always runs
    try:
        if progress_callback:
            progress_callback("cxr_classification", "Classifying chest X-ray...", 1, cxr_total)
        classification_prompt = build_cxr_classification_prompt()
        raw_response = medgemma.call_medgemma(
            classification_prompt, max_new_tokens=TOKEN_BUDGETS["cxr_classification"], images=[current_image]
        )
        _, response_text = medgemma.extract_thinking(raw_response)
        logger.debug("CXR stage A response (%d chars): %s", len(raw_response), response_text[:500])
        cxr_analysis = medgemma.parse_json_response(response_text)
        logger.debug("CXR parsed keys: %s", list(cxr_analysis.keys()) if cxr_analysis else "EMPTY")
        if not cxr_analysis:
            raise ValueError("Empty classification response from MedGemma")
    except (RuntimeError, ValueError) as e:
        logger.error("CXR classification failed: %s", e)
        return {
            "tool_name": "cxr_classification",
            "status": "error",
            "summary": f"CXR classification failed: {e}",
            "raw_output": {"cxr_analysis": {}},
        }

    # --- Stage B: Localization (per positive localizable finding) ---
    localizable = ["consolidation", "pleural_effusion", "atelectasis"]
    loc_call_num = 1
    for finding_name in localizable:
        finding = cxr_analysis.get(finding_name, {})
        if not isinstance(finding, dict) or not finding.get("present"):
            continue
        try:
            loc_call_num += 1
            if progress_callback:
                progress_callback("cxr_localization", f"Localizing {finding_name}...", loc_call_num, loc_call_num)
            location = finding.get("location", "")
            loc_prompt = build_cxr_localization_prompt(finding_name, location)
            raw_loc = medgemma.call_medgemma(
                loc_prompt, max_new_tokens=TOKEN_BUDGETS["cxr_localization"], images=[current_image]
            )
            _, loc_text = medgemma.extract_thinking(raw_loc)
            bbox_result = medgemma.parse_json_response(loc_text, expect_list=True)
            if isinstance(bbox_result, list) and bbox_result:
                finding["bounding_box"] = bbox_result[0].get("box_2d")
            elif isinstance(bbox_result, dict) and bbox_result.get("box_2d"):
                finding["bounding_box"] = bbox_result["box_2d"]
        except (RuntimeError, ValueError, TypeError, KeyError) as e:
            logger.warning("CXR localization failed for finding: %s", e)
            status = "partial"

    # --- Stage C: Longitudinal comparison (if prior exists) ---
    prior_image_path = cxr.get("prior_image_path")
    if prior_image_path:
        try:
            if progress_callback:
                progress_callback("cxr_longitudinal", "Comparing with prior...", loc_call_num + 1, loc_call_num + 1)
            prior_image = Image.open(prior_image_path)
            prior_image = medgemma.pad_image_to_square(prior_image)
            long_prompt = build_cxr_longitudinal_prompt()
            raw_long = medgemma.call_medgemma(
                long_prompt, max_new_tokens=TOKEN_BUDGETS["cxr_longitudinal"], images=[prior_image, current_image]
            )
            _, long_text = medgemma.extract_thinking(raw_long)
            logger.debug("CXR stage C response (%d chars): %s", len(raw_long), long_text[:500])
            longitudinal = medgemma.parse_json_response(long_text)
            logger.debug("CXR longitudinal keys: %s", list(longitudinal.keys()) if longitudinal else "EMPTY")
            if longitudinal:
                cxr_analysis["longitudinal_comparison"] = longitudinal
            else:
                status = "partial"
        except (OSError, RuntimeError, ValueError) as e:
            logger.warning("CXR longitudinal failed: %s", e)
            status = "partial"

    # Build summary
    consol = cxr_analysis.get("consolidation", {})
    consol_status = "present" if consol.get("present") else "absent"
    consol_conf = consol.get("confidence", "unknown")
    summary = f"CXR analysis: consolidation={consol_status} ({consol_conf} confidence)"

    return {
        "tool_name": "cxr_classification",
        "status": status,
        "summary": summary,
        "raw_output": {"cxr_analysis": cxr_analysis},
    }

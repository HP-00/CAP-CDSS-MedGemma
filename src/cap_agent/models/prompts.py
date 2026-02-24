"""MedGemma prompt templates for CAP clinical decision support."""

CAP_SYSTEM_INSTRUCTION = (
    "SYSTEM INSTRUCTION: think silently if needed. "
    "You are a senior acute medicine physician with expertise in respiratory medicine "
    "and antimicrobial stewardship. Your role is to synthesise multi-modal clinical data "
    "for community-acquired pneumonia cases, following evidence-based UK CAP management principles.\n\n"
    "CLINICAL REASONING:\n"
    "- Correlate findings across clinical examination, blood results, and chest imaging\n"
    "- Flag cross-modal contradictions (e.g., negative CXR with positive clinical signs)\n"
    "- Assess severity using CURB65 criteria\n"
    "- Consider all 7 factors for antibiotic selection per current evidence base\n\n"
    "SAFETY PRINCIPLES:\n"
    "- You are PREPARING information for clinician review, NOT making clinical decisions\n"
    "- Flag uncertainty explicitly\n"
    "- Never omit concerning findings\n"
    "- Label all outputs as AI-generated observations"
)

# Lightweight instruction for extraction/synthesis calls (~30 tokens).
# Avoids clinical reasoning directives that conflict with "extract only" prompts.
CAP_EXTRACTION_INSTRUCTION = (
    "You are a clinical data extraction specialist. "
    "Extract only documented facts. Flag uncertainty explicitly."
)

# Same instruction but WITHOUT the thinking prefix — used for clinician summary
# and other calls that need full clinical context but not thinking tokens.
CAP_SYSTEM_INSTRUCTION_NO_THINKING = (
    "You are a senior acute medicine physician with expertise in respiratory medicine "
    "and antimicrobial stewardship. Your role is to synthesise multi-modal clinical data "
    "for community-acquired pneumonia cases, following evidence-based UK CAP management principles.\n\n"
    "CLINICAL REASONING:\n"
    "- Correlate findings across clinical examination, blood results, and chest imaging\n"
    "- Flag cross-modal contradictions (e.g., negative CXR with positive clinical signs)\n"
    "- Assess severity using CURB65 criteria\n"
    "- Consider all 7 factors for antibiotic selection per current evidence base\n\n"
    "SAFETY PRINCIPLES:\n"
    "- You are PREPARING information for clinician review, NOT making clinical decisions\n"
    "- Flag uncertainty explicitly\n"
    "- Never omit concerning findings\n"
    "- Label all outputs as AI-generated observations"
)


def build_contradiction_prompt(
    strategy: str,
    rule_id: str,
    pattern: str,
    evidence_for: str,
    evidence_against: str,
) -> str:
    """Build a MedGemma prompt for contradiction resolution.

    Strategy types:
        A — Zone-specific re-analysis (CR-1, CR-5)
        B — Temporal context assessment / CXR lag (CR-2)
        C — Differential diagnosis (CR-3, CR-6)
        D — Severity override reasoning (CR-4)
    """
    if strategy == "A":
        return (
            f"CONTRADICTION DETECTED ({rule_id}): {pattern}\n\n"
            f"Evidence FOR pneumonia: {evidence_for}\n"
            f"Evidence AGAINST: {evidence_against}\n\n"
            "As a senior acute medicine physician, analyse this discordance:\n"
            "1. What is the most likely explanation for this cross-modal mismatch?\n"
            "2. Should the clinical exam findings override the imaging?\n"
            "3. What additional investigation would you recommend?\n"
            "4. What is your calibrated assessment -- is this likely CAP despite the discordance?\n\n"
            "Provide a structured clinical reasoning response.\n\n"
            "End with a confidence rating on its own line using EXACTLY this format — "
            "CONFIDENCE: high, CONFIDENCE: moderate, or CONFIDENCE: low"
        )
    elif strategy == "B":
        return (
            f"CONTRADICTION DETECTED ({rule_id}): {pattern}\n\n"
            f"Evidence FOR pneumonia: {evidence_for}\n"
            f"Evidence AGAINST: {evidence_against}\n\n"
            "Consider the temporal relationship between symptom onset and imaging:\n"
            "1. Could the CXR be falsely negative due to early presentation?\n"
            "2. Radiological changes typically lag clinical and biochemical markers by how long?\n"
            "3. Should empirical treatment proceed despite negative CXR?\n"
            "4. When should repeat imaging be considered?\n\n"
            "Provide a calibrated clinical assessment.\n\n"
            "End with a confidence rating on its own line using EXACTLY this format — "
            "CONFIDENCE: high, CONFIDENCE: moderate, or CONFIDENCE: low"
        )
    elif strategy == "C":
        return (
            f"CONTRADICTION DETECTED ({rule_id}): {pattern}\n\n"
            f"Evidence: {evidence_for}\n"
            f"Counter-evidence: {evidence_against}\n\n"
            "Consider the differential diagnosis:\n"
            "1. Could this represent a non-pneumonic cause (e.g., heart failure, atelectasis, malignancy)?\n"
            "2. What additional investigations would help differentiate?\n"
            "3. What is the pre-test probability of CAP given all available data?\n"
            "4. Should the CXR finding be treated as an incidental finding?\n\n"
            "Provide a structured differential diagnosis assessment.\n\n"
            "End with a confidence rating on its own line using EXACTLY this format — "
            "CONFIDENCE: high, CONFIDENCE: moderate, or CONFIDENCE: low"
        )
    elif strategy == "D":
        return (
            f"CONTRADICTION DETECTED ({rule_id}): {pattern}\n\n"
            f"Current severity: {evidence_for}\n"
            f"Override trigger: {evidence_against}\n\n"
            "As a senior physician, assess whether severity should be overridden:\n"
            "1. Does the override factor meaningfully increase mortality risk?\n"
            "2. What severity tier would you recommend and why?\n"
            "3. Does this change the treatment pathway?\n"
            "4. What additional monitoring is needed?\n\n"
            "Provide a clinical reasoning response with recommended severity tier.\n\n"
            "End with a confidence rating on its own line using EXACTLY this format — "
            "CONFIDENCE: high, CONFIDENCE: moderate, or CONFIDENCE: low"
        )
    elif strategy == "E":
        return (
            f"STEWARDSHIP ALERT ({rule_id}): {pattern}\n\n"
            f"Current regimen: {evidence_for}\n"
            f"Micro/allergy data: {evidence_against}\n\n"
            "This is a deterministic antibiotic stewardship alert.\n"
            "Action: Review prescribing in light of available microbiology "
            "and allergy data. Consult microbiologist if required."
        )
    else:
        return f"Analyse this clinical contradiction: {pattern}"


def build_synthesis_prompt(
    demographics: dict,
    exam: dict,
    labs: dict,
    cxr: dict,
    curb65: dict,
    contradictions: list,
    resolutions: list,
    data_gaps: list,
) -> str:
    """Build a MedGemma prompt for clinical synthesis of all findings."""
    import json

    # Format abnormal labs
    abnormal_labs = []
    for test, data in (labs or {}).items():
        if isinstance(data, dict) and data.get("abnormal_flag"):
            abnormal_labs.append(
                f"  - {test}: {data['value']} {data['unit']} (ref: {data['reference_range']})"
            )

    nl = chr(10)
    comorbidities = ", ".join(demographics.get("comorbidities", [])) or "None"
    allergy_list = demographics.get("allergies", [])
    allergies_str = ", ".join(
        [a.get("drug", str(a)) for a in allergy_list]
    ) if allergy_list else "None documented"

    contradiction_lines = nl.join(
        [f"  - {c['rule_id']}: {c['pattern']}" for c in contradictions]
    ) if contradictions else "  None"

    resolution_lines = nl.join(resolutions) if resolutions else "  N/A"
    gap_str = ", ".join(data_gaps) if data_gaps else "None"

    return (
        f"Synthesise the following multi-modal clinical data for a CAP case:\n\n"
        f"PATIENT: {demographics.get('age', 'unknown')}yo {demographics.get('sex', 'unknown')}\n"
        f"Comorbidities: {comorbidities}\n"
        f"Allergies: {allergies_str}\n\n"
        f"CLINICAL EXAMINATION:\n{json.dumps(exam, indent=2, default=str)}\n\n"
        f"CHEST X-RAY:\n{json.dumps(cxr, indent=2, default=str)}\n\n"
        f"CURB65 SCORE: {curb65.get('curb65', curb65.get('crb65', 'N/A'))} "
        f"({curb65.get('severity_tier', 'unknown')} severity)\n"
        f"  C={curb65.get('c', '?')} U={curb65.get('u', '?')} "
        f"R={curb65.get('r', '?')} B={curb65.get('b', '?')} "
        f"65={curb65.get('age_65', '?')}\n\n"
        f"ABNORMAL LABS:\n{nl.join(abnormal_labs) if abnormal_labs else '  None'}\n\n"
        f"CONTRADICTIONS DETECTED: {len(contradictions)}\n{contradiction_lines}\n\n"
        f"CONTRADICTION RESOLUTIONS:\n{resolution_lines}\n\n"
        f"DATA GAPS: {gap_str}\n\n"
        "Provide a senior physician-level clinical synthesis:\n"
        "1. Overall clinical picture\n"
        "2. Are the findings concordant across modalities?\n"
        "3. Key concerns and risk factors\n"
        "4. Confidence assessment in the CAP diagnosis\n"
        "5. Any findings that warrant additional investigation\n\n"
        "Be concise but thorough."
    )


def build_cxr_classification_prompt() -> str:
    """Build a MedGemma prompt for CXR classification of 5 CheXpert conditions.

    Returns a prompt requesting structured JSON with consolidation,
    pleural_effusion, cardiomegaly, edema, atelectasis findings plus
    image_quality assessment.
    """
    return (
        "Analyse this chest X-ray for community-acquired pneumonia assessment.\n\n"
        "For EACH of the following 5 conditions, determine presence, confidence, "
        "and location (if applicable):\n"
        "1. Consolidation (most important for CAP)\n"
        "2. Pleural effusion\n"
        "3. Cardiomegaly\n"
        "4. Pulmonary edema\n"
        "5. Atelectasis\n\n"
        "Also assess image quality.\n\n"
        "Report only what is visible in the image. Be concise.\n\n"
        "IMPORTANT:\n"
        "- Assign confidence even for ABSENT findings (how confident are you it is absent)\n"
        "- For consolidation, ALWAYS specify the anatomical location\n"
        "- Use 'not found' for location if the finding is absent\n\n"
        "Respond with ONLY this JSON structure:\n"
        "```json\n"
        "{\n"
        '  "consolidation": {"present": bool, "confidence": "high|moderate|low", '
        '"location": "string", "description": "string"},\n'
        '  "pleural_effusion": {"present": bool, "confidence": "high|moderate|low"},\n'
        '  "cardiomegaly": {"present": bool, "confidence": "high|moderate|low"},\n'
        '  "edema": {"present": bool, "confidence": "high|moderate|low"},\n'
        '  "atelectasis": {"present": bool, "confidence": "high|moderate|low"},\n'
        '  "image_quality": {"projection": "PA|AP|lateral", '
        '"rotation": "none|minimal|moderate|severe", '
        '"penetration": "adequate|under|over"}\n'
        "}\n"
        "```"
    )


def build_cxr_localization_prompt(finding: str, location: str = "") -> str:
    """Build a MedGemma prompt for bounding box localization of a CXR finding.

    Uses the exact format from Google's MedGemma localization notebook.
    Bounding box coordinates: [y0, x0, y1, x1] normalized to [0, 1000].

    Args:
        finding: The finding to localize (e.g. 'consolidation').
        location: Optional location hint (e.g. 'right lower lobe').
    """
    location_hint = f" in the {location}" if location else ""
    return (
        f"Locate the {finding}{location_hint} on this chest X-ray.\n\n"
        "INSTRUCTIONS:\n"
        "- Left side of the image = patient's left side\n"
        "- Provide bounding box coordinates as [y0, x0, y1, x1]\n"
        "- Coordinates are normalized to range [0, 1000]\n"
        "- Reason about the location before providing the final answer\n\n"
        "Be concise. Respond with ONLY a JSON array of detected regions:\n"
        "```json\n"
        '[{"box_2d": [y0, x0, y1, x1], "label": "finding name"}]\n'
        "```"
    )


def build_cxr_longitudinal_prompt() -> str:
    """Build a MedGemma prompt for longitudinal comparison of two CXR images.

    Expects two images: image 1 = PRIOR, image 2 = CURRENT.
    Returns per-finding change assessment.
    """
    return (
        "Compare these two chest X-rays. Image 1 is the PRIOR study, "
        "Image 2 is the CURRENT study.\n\n"
        "For each of the following 5 conditions, assess the change between "
        "the prior and current study:\n"
        "1. Consolidation\n"
        "2. Pleural effusion\n"
        "3. Cardiomegaly\n"
        "4. Pulmonary edema\n"
        "5. Atelectasis\n\n"
        "Change categories (use EXACTLY one per finding):\n"
        "- new: finding is ABSENT in prior, PRESENT in current\n"
        "- resolved: finding is PRESENT in prior, ABSENT in current\n"
        "- worsened: finding is PRESENT in both, larger or denser in current\n"
        "- improved: finding is PRESENT in both, smaller or less dense in current\n"
        "- unchanged: same status in both studies (including absent in both)\n\n"
        "Respond with ONLY this JSON structure:\n"
        "```json\n"
        "{\n"
        '  "consolidation": {"change": "string", "description": "string"},\n'
        '  "pleural_effusion": {"change": "string", "description": "string"},\n'
        '  "cardiomegaly": {"change": "string", "description": "string"},\n'
        '  "edema": {"change": "string", "description": "string"},\n'
        '  "atelectasis": {"change": "string", "description": "string"}\n'
        "}\n"
        "```"
    )


def build_ehr_identify_prompt(manifest_text: str) -> str:
    """Build a MedGemma prompt for Step 1: identify relevant FHIR resource types.

    Args:
        manifest_text: Human-readable manifest from build_manifest().
    """
    return (
        "You are a clinical data navigation specialist assessing a patient "
        "with suspected community-acquired pneumonia (CAP).\n\n"
        f"The following FHIR resources are available in this patient's record:\n"
        f"{manifest_text}\n\n"
        "TASK: Identify which resource types are relevant for CAP assessment.\n"
        "Consider what data is needed for:\n"
        "- Demographics (age, sex)\n"
        "- CURB65 scoring (confusion, urea, respiratory rate, blood pressure, age)\n"
        "- Clinical examination findings\n"
        "- Allergies and drug history\n"
        "- Comorbidities\n"
        "- Social history (pregnancy, oral tolerance, travel)\n\n"
        "Respond with ONLY a JSON list of relevant resource type strings.\n"
        "Example: [\"Patient\", \"Condition\", \"Observation\"]\n"
        "```json\n"
        "[...]\n"
        "```"
    )


def build_ehr_narrative_filter_prompt(clerking_note: str) -> str:
    """Build a MedGemma prompt for Step 2: extract facts from freetext notes.

    This is a fact-filter step: output is concise English text, NOT JSON.
    """
    return (
        "You are a clinical fact extraction specialist. Extract structured "
        "clinical facts from this admission clerking note.\n\n"
        "CLERKING NOTE:\n"
        f"{clerking_note}\n\n"
        "Extract facts in these 7 categories. For each, list the key findings "
        "as concise bullet points:\n\n"
        "1. RESPIRATORY EXAMINATION: Crackles (yes/no + location), bronchial "
        "breathing (yes/no + location), dullness, air entry changes\n"
        "2. CONFUSION / MENTAL STATUS: AMT score, GCS, orientation\n"
        "3. ALLERGIES: Drug allergies and reaction types (state NKDA if none)\n"
        "4. PAST MEDICAL HISTORY: Conditions, severity, relevant details\n"
        "5. DRUG HISTORY: Current medications with doses and frequency\n"
        "6. SOCIAL HISTORY: Smoking status (pack-years, current/former/never), "
        "living situation, pregnancy status, oral tolerance, "
        "eating independently (can patient eat without assistance), recent travel\n"
        "7. PRESENTING COMPLAINT: Duration, symptoms, progression\n\n"
        "IMPORTANT:\n"
        "- If information is not documented, state 'Not documented'\n"
        "- Quote specific values (e.g., 'AMT 9/10', 'RR 22')\n"
        "- Do NOT interpret or diagnose — only extract documented facts\n"
        "- Keep each category to 1-3 lines maximum"
    )


def build_ehr_structured_filter_prompt(fhir_resources_text: str) -> str:
    """Build a MedGemma prompt for Step 3: extract facts from structured FHIR data.

    This is a fact-filter step: output is concise English text, NOT JSON.
    """
    return (
        "You are a clinical data extraction specialist. Extract clinical facts "
        "from these structured FHIR resources for a CAP assessment.\n\n"
        "STRUCTURED DATA:\n"
        f"{fhir_resources_text}\n\n"
        "Extract facts in these categories:\n\n"
        "1. DEMOGRAPHICS: Age, sex, name\n"
        "2. VITAL SIGNS: Respiratory rate, blood pressure (systolic/diastolic), "
        "heart rate, SpO2, temperature — include exact values and units\n"
        "3. LAB VALUES: Urea, CRP, and any other available results with values and units\n"
        "4. CONDITIONS: Active medical conditions with severity\n"
        "5. ALLERGIES: Drug allergies (state NKDA if 'No known allergy' recorded)\n"
        "6. MEDICATIONS: Current medications with doses\n"
        "7. FUNCTIONAL STATUS: Eating independently (can/cannot eat without assistance)\n\n"
        "IMPORTANT:\n"
        "- Report exact numeric values from the data\n"
        "- Do NOT interpret or diagnose — only report what is documented\n"
        "- If a category has no data, state 'No data available'\n"
        "- Keep each category to 1-3 lines maximum"
    )


def build_ehr_synthesis_prompt(narrative_facts: str, structured_facts: str) -> str:
    """Build a MedGemma prompt for Step 4: synthesize extracted facts into JSON.

    Combines narrative (freetext) and structured (FHIR) facts into the
    canonical {demographics, clinical_exam, curb65_variables} schema.
    """
    return (
        "You are a clinical data synthesis specialist. Combine the following "
        "extracted clinical facts into a structured JSON output.\n\n"
        "FACTS FROM CLINICAL NOTES (narrative):\n"
        f"{narrative_facts}\n\n"
        "FACTS FROM STRUCTURED RECORDS (FHIR):\n"
        f"{structured_facts}\n\n"
        "PRIORITY RULE: Prefer structured records for numeric values (vitals, "
        "lab results, age). Prefer clinical notes for descriptive findings "
        "(exam findings, locations, social history).\n\n"
        "COMORBIDITIES RULE: Only list PRE-EXISTING conditions (e.g. COPD, "
        "diabetes, heart failure). Do NOT include the current presenting "
        "diagnosis (community-acquired pneumonia / CAP) as a comorbidity.\n\n"
        "Produce EXACTLY this JSON structure:\n"
        "```json\n"
        "{\n"
        '  "demographics": {\n'
        '    "age": <int>,\n'
        '    "sex": "<Male|Female>",\n'
        '    "allergies": [{"drug": "<name>", "reaction_type": "<type>", '
        '"severity": "<severity>"}],\n'
        '    "comorbidities": ["<condition 1>", "<condition 2>"],\n'
        '    "recent_antibiotics": [],\n'
        '    "pregnancy": <true|false>,\n'
        '    "oral_tolerance": <true|false>,\n'
        '    "eating_independently": <true|false>,\n'
        '    "travel_history": [],\n'
        '    "smoking_status": "<current|former|never|null>"\n'
        "  },\n"
        '  "clinical_exam": {\n'
        '    "respiratory_exam": {\n'
        '      "crackles": <true|false>,\n'
        '      "crackles_location": "<location or null>",\n'
        '      "bronchial_breathing": <true|false>,\n'
        '      "bronchial_breathing_location": "<location or null>"\n'
        "    },\n"
        '    "observations": {\n'
        '      "respiratory_rate": <int>,\n'
        '      "systolic_bp": <int>,\n'
        '      "diastolic_bp": <int>,\n'
        '      "heart_rate": <int>,\n'
        '      "spo2": <int>,\n'
        '      "temperature": <float>,\n'
        '      "supplemental_o2": "<room air|nasal cannula|mask>"\n'
        "    },\n"
        '    "confusion_status": {\n'
        '      "present": <true|false>,\n'
        '      "amt_score": <int 0-10>\n'
        "    }\n"
        "  },\n"
        '  "curb65_variables": {\n'
        '    "confusion": <true|false>,\n'
        '    "urea": <float or null if not available>,\n'
        '    "respiratory_rate": <int>,\n'
        '    "systolic_bp": <int>,\n'
        '    "diastolic_bp": <int>,\n'
        '    "age": <int>\n'
        "  }\n"
        "}\n"
        "```\n\n"
        "EXAMPLE (for a different patient):\n"
        "```json\n"
        "{\n"
        '  "demographics": {\n'
        '    "age": 65,\n'
        '    "sex": "Female",\n'
        '    "allergies": [{"drug": "Penicillin", "reaction_type": "rash", '
        '"severity": "mild"}],\n'
        '    "comorbidities": ["Asthma", "Hypertension"],\n'
        '    "recent_antibiotics": [],\n'
        '    "pregnancy": false,\n'
        '    "oral_tolerance": true,\n'
        '    "eating_independently": true,\n'
        '    "travel_history": [],\n'
        '    "smoking_status": "never"\n'
        "  },\n"
        '  "clinical_exam": {\n'
        '    "respiratory_exam": {\n'
        '      "crackles": true,\n'
        '      "crackles_location": "left lower zone",\n'
        '      "bronchial_breathing": false,\n'
        '      "bronchial_breathing_location": null\n'
        "    },\n"
        '    "observations": {\n'
        '      "respiratory_rate": 28,\n'
        '      "systolic_bp": 95,\n'
        '      "diastolic_bp": 58,\n'
        '      "heart_rate": 110,\n'
        '      "spo2": 91,\n'
        '      "temperature": 39.1,\n'
        '      "supplemental_o2": "nasal cannula"\n'
        "    },\n"
        '    "confusion_status": {\n'
        '      "present": true,\n'
        '      "amt_score": 6\n'
        "    }\n"
        "  },\n"
        '  "curb65_variables": {\n'
        '    "confusion": true,\n'
        '    "urea": 9.5,\n'
        '    "respiratory_rate": 28,\n'
        '    "systolic_bp": 95,\n'
        '    "diastolic_bp": 58,\n'
        '    "age": 65\n'
        "  }\n"
        "}\n"
        "```\n\n"
        "IMPORTANT:\n"
        "- Use [] for allergies if NKDA (no known drug allergies)\n"
        "- Use null for urea if not documented in either source\n"
        "- confusion is true only if AMT <= 8 or documented as confused\n"
        "- Respond with ONLY the JSON, no additional text"
    )


def build_lab_extraction_prompt(lab_text: str) -> str:
    """Build a MedGemma prompt for Step 1: extract English facts from lab report.

    This is a fact-filter step: output is concise English text, NOT JSON.
    Works with both NHS pathology printouts and rendered FHIR Observations.
    """
    return (
        "You are a clinical laboratory data extraction specialist. Extract "
        "laboratory test results from this report.\n\n"
        "LAB REPORT:\n"
        f"{lab_text}\n\n"
        "Extract results for these key tests (if available):\n"
        "CRP, Urea, Creatinine, eGFR, Sodium, Potassium, WCC, "
        "Neutrophils, Haemoglobin, Platelets, Procalcitonin, Lactate\n\n"
        "For each test found, report:\n"
        "- Test name, result value, units, and reference range\n"
        "- Whether the result is flagged as abnormal\n\n"
        "IMPORTANT:\n"
        "- Report exact numeric values as written\n"
        "- State 'Not reported' for tests not present in the report\n"
        "- Do NOT interpret results or provide clinical commentary\n"
        "- Keep output concise: one line per test"
    )


def build_lab_synthesis_prompt(extracted_facts: str) -> str:
    """Build a MedGemma prompt for Step 2: synthesize extracted lab facts into JSON.

    Converts English-text lab facts into the canonical lab_values JSON schema.
    """
    return (
        "You are a clinical data synthesis specialist. Convert the following "
        "extracted laboratory results into a structured JSON output.\n\n"
        "EXTRACTED LAB FACTS:\n"
        f"{extracted_facts}\n\n"
        "Produce EXACTLY this JSON structure:\n"
        "```json\n"
        "{\n"
        '  "lab_values": {\n'
        '    "<test_name>": {\n'
        '      "value": <float>,\n'
        '      "unit": "<string>",\n'
        '      "reference_range": "<string>",\n'
        '      "abnormal_flag": <true|false>\n'
        "    }\n"
        "  }\n"
        "}\n"
        "```\n\n"
        "EXAMPLE:\n"
        '{"lab_values": {"albumin": {"value": 35.0, "unit": "g/L", '
        '"reference_range": "35-50", "abnormal_flag": false}, '
        '"bilirubin": {"value": 22.0, "unit": "umol/L", '
        '"reference_range": "0-21", "abnormal_flag": true}}}\n\n'
        "CANONICAL TEST NAMES (use these exact lowercase keys):\n"
        "crp, urea, creatinine, egfr, sodium, potassium, wcc, "
        "neutrophils, haemoglobin, platelets, procalcitonin, lactate\n\n"
        "RULES:\n"
        "- Use lowercase canonical test names as keys\n"
        "- value must be a number (float)\n"
        "- Omit tests that were 'Not reported' — do not include them\n"
        "- abnormal_flag is true if the result is outside the reference range\n"
        "- Respond with ONLY the JSON object, no explanation or commentary\n"
        "- Be concise — do not restate the schema in your reasoning"
    )


def build_clinician_summary_prompt(
    demographics: dict,
    curb65: dict,
    cxr: dict,
    labs: dict,
    contradictions: list,
    treatment: dict,
    monitoring: dict,
    data_gaps: list,
) -> str:
    """Build a MedGemma prompt for the 8-section clinician summary."""
    comorbidities = ", ".join(demographics.get("comorbidities", [])) or "None"
    allergy_list = demographics.get("allergies", [])
    allergies_str = ", ".join(
        [a.get("drug", str(a)) for a in allergy_list]
    ) if allergy_list else "None"

    consol_present = "present" if cxr.get("consolidation", {}).get("present") else "absent"
    consol_conf = cxr.get("consolidation", {}).get("confidence", "?")
    consol_loc = cxr.get("consolidation", {}).get("location", "N/A")
    projection = cxr.get("image_quality", {}).get("projection", "?")

    lab_items = []
    for k, v in (labs or {}).items():
        if isinstance(v, dict):
            flag = " (abnormal)" if v.get("abnormal_flag") else ""
            lab_items.append(f"{k}={v.get('value', '?')}{flag}")
    lab_str = ", ".join(lab_items)

    contradict_str = (
        f"{len(contradictions)} detected" if contradictions
        else "None -- findings concordant across modalities"
    )

    gap_str = ", ".join(data_gaps) if data_gaps else "None identified"
    atypical = treatment.get("atypical_cover", "") or ""
    corticosteroid = treatment.get("corticosteroid_recommendation", "") or ""
    corticosteroid_section = f" Corticosteroid: {corticosteroid}" if corticosteroid else ""

    return (
        "Generate a concise clinician-facing summary for this CAP case, "
        "readable in under 30 seconds. Use EXACTLY these 8 sections:\n\n"
        f"1. PATIENT: {demographics.get('age', '?')}yo {demographics.get('sex', '?')}, "
        f"PMH: {comorbidities}, Allergies: {allergies_str}\n\n"
        f"2. SEVERITY: CURB65={curb65.get('curb65', '?')} ({curb65.get('severity_tier', '?')}). "
        f"C={curb65.get('c', '?')} U={curb65.get('u', '?')} R={curb65.get('r', '?')} "
        f"B={curb65.get('b', '?')} 65={curb65.get('age_65', '?')}. "
        f"Missing: {', '.join(curb65.get('missing_variables', [])) or 'None'}\n\n"
        f"3. CXR: Consolidation={consol_present} ({consol_conf} confidence) at {consol_loc}. "
        f"Quality: {projection} projection.\n\n"
        f"4. KEY BLOODS: {lab_str}\n\n"
        f"5. CONTRADICTION ALERT: {contradict_str}\n\n"
        f"6. TREATMENT PATHWAY: {treatment.get('first_line', 'N/A')}. {atypical}."
        f"{corticosteroid_section}\n\n"
        f"7. DATA GAPS: {gap_str}\n\n"
        f"8. MONITORING: {monitoring.get('crp_repeat_timing', 'N/A')} "
        f"Next review: {monitoring.get('next_review', 'N/A')}\n\n"
        "Format as a clear, structured clinical summary. "
        "End with: 'AI-generated observations for clinician review -- "
        "not a substitute for clinical judgement.'"
    )

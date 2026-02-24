"""FHIR Bundle manipulation utilities for EHR QA extraction.

Provides functions to parse FHIR R4 Bundles into human-readable text
for MedGemma prompt construction, and to validate/repair extraction output.
"""

from __future__ import annotations

import base64
import binascii
import logging
from datetime import date, datetime

logger = logging.getLogger(__name__)


# LOINC codes that represent vital signs (not lab tests)
_VITAL_LOINC_CODES = {
    "9279-1",   # Respiratory rate
    "85354-9",  # Blood pressure panel
    "8480-6",   # Systolic blood pressure
    "8462-4",   # Diastolic blood pressure
    "8867-4",   # Heart rate
    "2708-6",   # Oxygen saturation (arterial)
    "59408-5",  # Oxygen saturation (pulse oximetry)
    "8310-5",   # Body temperature
}


# LOINC codes for functional/clinical status observations (not lab tests)
_FUNCTIONAL_LOINC_CODES = {
    "75244-9",  # Ability to eat independently
}


def _is_vital_observation(resource: dict) -> bool:
    """Check if an Observation resource is a vital sign (not a lab test).

    Checks both top-level code and component codes against LOINC vital codes.
    """
    # Check top-level code
    for coding in resource.get("code", {}).get("coding", []):
        if coding.get("code") in _VITAL_LOINC_CODES:
            return True
    # Check component codes (e.g., BP panel with SBP/DBP components)
    for comp in resource.get("component", []):
        for coding in comp.get("code", {}).get("coding", []):
            if coding.get("code") in _VITAL_LOINC_CODES:
                return True
    return False


def build_manifest(bundle: dict) -> str:
    """Build a human-readable manifest of FHIR resource types and counts.

    Args:
        bundle: A FHIR Bundle dict with "entry" list.

    Returns:
        Manifest string like "Patient: 1, Condition: 2 (COPD, T2DM), Observation: 6"
    """
    entries = bundle.get("entry", [])
    if not entries:
        return "Empty bundle — no resources available."

    type_counts: dict[str, int] = {}
    type_displays: dict[str, list[str]] = {}
    for entry in entries:
        resource = entry.get("resource", {})
        rtype = resource.get("resourceType", "Unknown")
        type_counts[rtype] = type_counts.get(rtype, 0) + 1
        if rtype not in type_displays:
            type_displays[rtype] = []

        # Extract display name for context
        display = _get_resource_display(resource)
        if display:
            type_displays[rtype].append(display)

    parts = []
    for rtype, count in type_counts.items():
        displays = type_displays.get(rtype, [])
        if displays:
            label = ", ".join(displays[:4])
            parts.append(f"{rtype}: {count} ({label})")
        else:
            parts.append(f"{rtype}: {count}")

    return "Available FHIR resources: " + ", ".join(parts)


def _get_resource_display(resource: dict) -> str:
    """Extract a short display name from a FHIR resource."""
    rtype = resource.get("resourceType", "")

    if rtype == "Condition":
        code = resource.get("code", {})
        for coding in code.get("coding", []):
            if coding.get("display"):
                return coding["display"]
        return code.get("text", "")

    if rtype == "Observation":
        code = resource.get("code", {})
        for coding in code.get("coding", []):
            if coding.get("display"):
                return coding["display"]
        return code.get("text", "")

    if rtype == "MedicationRequest":
        med = resource.get("medicationCodeableConcept", {})
        return med.get("text", "")

    if rtype == "AllergyIntolerance":
        code = resource.get("code", {})
        return code.get("text", "")

    if rtype == "DocumentReference":
        return resource.get("description", "clinical note")

    if rtype == "Encounter":
        return resource.get("class", {}).get("display", "")

    return ""


def group_resources_by_type(bundle: dict) -> dict[str, list[dict]]:
    """Group FHIR Bundle entries by resourceType.

    Returns:
        Dict mapping resourceType string to list of resource dicts.
    """
    grouped: dict[str, list[dict]] = {}
    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        rtype = resource.get("resourceType", "Unknown")
        if rtype not in grouped:
            grouped[rtype] = []
        grouped[rtype].append(resource)
    return grouped


def render_resources_as_text(resources: list[dict]) -> str:
    """Convert FHIR resource dicts to compact readable text.

    Target: ~500-800 tokens for a typical CAP patient's structured data.
    """
    lines = []
    for resource in resources:
        line = _render_single_resource(resource)
        if line:
            lines.append(line)
    return "\n".join(lines)


def _render_single_resource(resource: dict) -> str:
    """Render one FHIR resource as a single compact text line."""
    rtype = resource.get("resourceType", "")

    if rtype == "Patient":
        return _render_patient(resource)
    if rtype == "Condition":
        return _render_condition(resource)
    if rtype == "Observation":
        return _render_observation(resource)
    if rtype == "MedicationRequest":
        return _render_medication(resource)
    if rtype == "AllergyIntolerance":
        return _render_allergy(resource)
    if rtype == "Encounter":
        return _render_encounter(resource)

    return ""


def _render_patient(resource: dict) -> str:
    gender = resource.get("gender", "unknown")
    birth = resource.get("birthDate", "unknown")
    age_str = ""
    if birth and birth != "unknown":
        try:
            birth_date = datetime.strptime(birth, "%Y-%m-%d").date()
            today = date.today()
            age = today.year - birth_date.year - (
                (today.month, today.day) < (birth_date.month, birth_date.day)
            )
            age_str = f" (age {age})"
        except ValueError:
            logger.debug("Could not parse birthDate: %s", birth)

    name_parts = []
    for name in resource.get("name", []):
        given = " ".join(name.get("given", []))
        family = name.get("family", "")
        if given or family:
            name_parts.append(f"{given} {family}".strip())

    name_str = name_parts[0] if name_parts else "Unknown"
    return f"PATIENT: {name_str}, {gender}, born {birth}{age_str}"


def _render_condition(resource: dict) -> str:
    code = resource.get("code", {})
    display = ""
    snomed = ""
    for coding in code.get("coding", []):
        if coding.get("display"):
            display = coding["display"]
        if coding.get("system", "").endswith("sct"):
            snomed = coding.get("code", "")

    status = resource.get("clinicalStatus", {})
    status_text = ""
    for coding in status.get("coding", []):
        status_text = coding.get("code", "")

    severity = resource.get("severity", {})
    sev_text = ""
    for coding in severity.get("coding", []):
        sev_text = coding.get("display", "")

    parts = [f"CONDITION: {display or code.get('text', 'unknown')}"]
    if sev_text:
        parts[0] += f" ({sev_text})"
    if snomed:
        parts[0] += f" [SNOMED {snomed}]"
    if status_text:
        parts[0] += f" — {status_text}"
    return parts[0]


def _render_observation(resource: dict) -> str:
    code = resource.get("code", {})
    display = ""
    for coding in code.get("coding", []):
        if coding.get("display"):
            display = coding["display"]

    prefix = "VITAL" if _is_vital_observation(resource) else "LAB"

    # Simple value
    vq = resource.get("valueQuantity")
    if vq:
        value = vq.get("value", "?")
        unit = vq.get("unit", "")
        dt = resource.get("effectiveDateTime", "")
        return f"{prefix}: {display or 'Observation'}: {value} {unit} ({dt})"

    # Blood pressure with components
    components = resource.get("component", [])
    if components:
        comp_parts = []
        for comp in components:
            comp_code = comp.get("code", {})
            comp_display = ""
            for coding in comp_code.get("coding", []):
                comp_display = coding.get("display", "")
            comp_vq = comp.get("valueQuantity", {})
            comp_parts.append(f"{comp_display}: {comp_vq.get('value', '?')} {comp_vq.get('unit', '')}")
        dt = resource.get("effectiveDateTime", "")
        return f"{prefix}: {display or 'Observation'}: {', '.join(comp_parts)} ({dt})"

    # Coded value (e.g., functional status observations)
    vcc = resource.get("valueCodeableConcept")
    if vcc:
        text = vcc.get("text", "")
        if not text:
            for coding in vcc.get("coding", []):
                text = coding.get("display", "")
                if text:
                    break
        dt = resource.get("effectiveDateTime", "")
        return f"{prefix}: {display or 'Observation'}: {text} ({dt})"

    return ""


def _render_medication(resource: dict) -> str:
    med = resource.get("medicationCodeableConcept", {})
    text = med.get("text", "unknown medication")
    dosage_parts = []
    for d in resource.get("dosageInstruction", []):
        dosage_parts.append(d.get("text", ""))
    dosage = "; ".join(d for d in dosage_parts if d)
    if dosage:
        return f"MEDICATION: {text} — {dosage}"
    return f"MEDICATION: {text}"


def _render_allergy(resource: dict) -> str:
    code = resource.get("code", {})
    display = code.get("text", "unknown")
    for coding in code.get("coding", []):
        if coding.get("display"):
            display = coding["display"]
            break

    parts = [f"ALLERGY: {display}"]

    # Include type and criticality if available
    allergy_type = resource.get("type")
    if allergy_type:
        parts.append(f"type={allergy_type}")
    criticality = resource.get("criticality")
    if criticality:
        parts.append(f"criticality={criticality}")

    # Include reaction manifestations
    for reaction in resource.get("reaction", []):
        manifestations = []
        for m in reaction.get("manifestation", []):
            for coding in m.get("coding", []):
                if coding.get("display"):
                    manifestations.append(coding["display"])
            if not manifestations and m.get("text"):
                manifestations.append(m["text"])
        if manifestations:
            parts.append(f"reaction={', '.join(manifestations)}")
        severity = reaction.get("severity")
        if severity:
            parts.append(f"severity={severity}")

    return " | ".join(parts)


def _render_encounter(resource: dict) -> str:
    enc_class = resource.get("class", {})
    class_display = enc_class.get("display", enc_class.get("code", "unknown"))
    period = resource.get("period", {})
    start = period.get("start", "")
    reasons = []
    for reason in resource.get("reasonCode", []):
        reasons.append(reason.get("text", ""))
    reason_str = "; ".join(r for r in reasons if r)
    parts = [f"ENCOUNTER: {class_display}"]
    if start:
        parts[0] += f" ({start})"
    if reason_str:
        parts[0] += f" — {reason_str}"
    return parts[0]


def get_document_text(bundle: dict) -> str:
    """Extract freetext clinical note from DocumentReference resources.

    Handles both plain text content and base64-encoded content.

    Returns:
        Combined text from all DocumentReference resources, or empty string.
    """
    texts = []
    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        if resource.get("resourceType") != "DocumentReference":
            continue

        for content_item in resource.get("content", []):
            attachment = content_item.get("attachment", {})

            # Try plain text data first
            data = attachment.get("data", "")
            content_type = attachment.get("contentType", "")

            if data:
                if content_type == "text/plain" or not content_type:
                    # Could be base64 encoded
                    try:
                        decoded = base64.b64decode(data).decode("utf-8")
                        texts.append(decoded)
                    except (binascii.Error, UnicodeDecodeError) as e:
                        logger.debug("Base64 text decode fallback: %s", e)
                        texts.append(data)
                else:
                    try:
                        decoded = base64.b64decode(data).decode("utf-8")
                        texts.append(decoded)
                    except (binascii.Error, UnicodeDecodeError) as e:
                        logger.debug("Base64 non-text decode fallback: %s", e)
                        texts.append(data)

    return "\n\n".join(texts)


# --- Output Validation & Repair ---

# Safe defaults for missing fields (matching mock_extract_clinical_notes output shape)
_DEMOGRAPHICS_DEFAULTS = {
    "age": 0,
    "sex": "unknown",
    "allergies": [],
    "comorbidities": [],
    "recent_antibiotics": [],
    "pregnancy": False,
    "oral_tolerance": True,
    "eating_independently": True,
    "travel_history": [],
    "smoking_status": None,
}

_CLINICAL_EXAM_DEFAULTS = {
    "respiratory_exam": {
        "crackles": False,
        "crackles_location": None,
        "bronchial_breathing": False,
        "bronchial_breathing_location": None,
    },
    "observations": {
        "respiratory_rate": 20,
        "systolic_bp": 120,
        "diastolic_bp": 80,
        "heart_rate": 80,
        "spo2": 98,
        "temperature": 37.0,
        "supplemental_o2": "room air",
    },
    "confusion_status": {
        "present": False,
        "amt_score": 10,
    },
}

_CURB65_DEFAULTS = {
    "confusion": False,
    "urea": None,
    "respiratory_rate": 20,
    "systolic_bp": 120,
    "diastolic_bp": 80,
    "age": 0,
}


def _coerce_bool(val) -> bool:
    """Coerce a value to bool."""
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.lower() in ("true", "yes", "1")
    return bool(val)


def _coerce_int(val) -> int | None:
    """Coerce a value to int, return None if impossible."""
    if val is None:
        return None
    try:
        return int(float(val))
    except (ValueError, TypeError):
        logger.debug("Could not coerce to int: %r", val)
        return None


def _coerce_float(val) -> float | None:
    """Coerce a value to float, return None if impossible."""
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        logger.debug("Could not coerce to float: %r", val)
        return None


def validate_and_repair_ehr_output(raw: dict) -> tuple[dict, list[str]]:
    """Validate and repair MedGemma synthesis output.

    Accepts parsed JSON from the synthesis step, type-coerces values,
    fills missing keys with safe defaults, and normalizes edge cases.

    Args:
        raw: Parsed JSON dict from MedGemma synthesis.

    Returns:
        (repaired_output, data_gaps) where data_gaps lists missing critical fields.
    """
    data_gaps: list[str] = []

    # --- Demographics ---
    demo_raw = raw.get("demographics", {})
    if not demo_raw:
        data_gaps.append("demographics section missing from EHR extraction")
        demo_raw = {}

    demographics = {}
    for key, default in _DEMOGRAPHICS_DEFAULTS.items():
        val = demo_raw.get(key)
        if val is None:
            # Try alternate key names
            if key == "sex":
                val = demo_raw.get("gender")
            if val is None:
                demographics[key] = default
                if key in ("age", "sex"):
                    data_gaps.append(f"demographics.{key} not extracted")
                continue
        # Type coercion
        if key == "age":
            coerced = _coerce_int(val)
            demographics[key] = coerced if coerced is not None else default
        elif key == "sex":
            demographics[key] = str(val).capitalize()
        elif key in ("pregnancy", "oral_tolerance", "eating_independently"):
            demographics[key] = _coerce_bool(val)
        elif key in ("allergies", "comorbidities", "recent_antibiotics", "travel_history"):
            if isinstance(val, list):
                demographics[key] = val
            else:
                demographics[key] = default
        else:
            demographics[key] = val

    # Normalize NKDA — remove "NKDA" entries from allergies
    allergies = demographics.get("allergies", [])
    if isinstance(allergies, list):
        cleaned = []
        for a in allergies:
            if isinstance(a, dict):
                drug = a.get("drug", "").upper()
                if drug in ("NKDA", "NO KNOWN DRUG ALLERGIES", "NONE", "NIL", ""):
                    continue
                cleaned.append(a)
            elif isinstance(a, str):
                if a.upper() in ("NKDA", "NO KNOWN DRUG ALLERGIES", "NONE", "NIL", ""):
                    continue
                cleaned.append({"drug": a, "reaction_type": "unknown", "severity": "unknown"})
        demographics["allergies"] = cleaned

    # --- Clinical Exam ---
    exam_raw = raw.get("clinical_exam", {})
    if not exam_raw:
        data_gaps.append("clinical_exam section missing from EHR extraction")
        exam_raw = {}

    clinical_exam = {}

    # Respiratory exam
    resp_raw = exam_raw.get("respiratory_exam", {})
    resp = {}
    resp_defaults = _CLINICAL_EXAM_DEFAULTS["respiratory_exam"]
    for key, default in resp_defaults.items():
        val = resp_raw.get(key)
        if val is None:
            resp[key] = default
        elif key in ("crackles", "bronchial_breathing"):
            resp[key] = _coerce_bool(val)
        else:
            resp[key] = val
    clinical_exam["respiratory_exam"] = resp

    # Observations
    obs_raw = exam_raw.get("observations", {})
    obs = {}
    obs_defaults = _CLINICAL_EXAM_DEFAULTS["observations"]
    for key, default in obs_defaults.items():
        val = obs_raw.get(key)
        if val is None:
            obs[key] = default
            if key in ("respiratory_rate", "systolic_bp", "diastolic_bp"):
                data_gaps.append(f"observations.{key} not extracted")
        elif key == "supplemental_o2":
            obs[key] = str(val)
        elif key == "temperature":
            coerced = _coerce_float(val)
            obs[key] = coerced if coerced is not None else default
        else:
            coerced = _coerce_int(val)
            obs[key] = coerced if coerced is not None else default
    clinical_exam["observations"] = obs

    # Confusion status
    conf_raw = exam_raw.get("confusion_status", {})
    conf = {}
    conf_defaults = _CLINICAL_EXAM_DEFAULTS["confusion_status"]
    for key, default in conf_defaults.items():
        val = conf_raw.get(key)
        if val is None:
            conf[key] = default
        elif key == "present":
            conf[key] = _coerce_bool(val)
        elif key == "amt_score":
            coerced = _coerce_int(val)
            conf[key] = coerced if coerced is not None else default
    clinical_exam["confusion_status"] = conf

    # --- CURB65 Variables ---
    curb_raw = raw.get("curb65_variables", {})
    if not curb_raw:
        data_gaps.append("curb65_variables section missing from EHR extraction")
        curb_raw = {}

    curb65 = {}
    for key, default in _CURB65_DEFAULTS.items():
        val = curb_raw.get(key)
        if val is None:
            curb65[key] = default
            if key in ("confusion", "respiratory_rate", "systolic_bp", "diastolic_bp", "age"):
                data_gaps.append(f"curb65_variables.{key} not extracted")
        elif key == "confusion":
            curb65[key] = _coerce_bool(val)
        elif key == "urea":
            coerced = _coerce_float(val)
            curb65[key] = coerced  # None is valid (means urea unavailable)
        elif key == "age":
            coerced = _coerce_int(val)
            curb65[key] = coerced if coerced is not None else default
        else:
            coerced = _coerce_int(val)
            curb65[key] = coerced if coerced is not None else default

    return {
        "demographics": demographics,
        "clinical_exam": clinical_exam,
        "curb65_variables": curb65,
    }, data_gaps


# --- Lab Observation Extraction & Validation ---


def _is_functional_observation(resource: dict) -> bool:
    """Check if an Observation resource is a functional status (not a lab test)."""
    for coding in resource.get("code", {}).get("coding", []):
        if coding.get("code") in _FUNCTIONAL_LOINC_CODES:
            return True
    return False


def extract_lab_observations(bundle: dict) -> list[dict]:
    """Extract Observation resources that are lab tests (not vital signs).

    Args:
        bundle: A FHIR Bundle dict with "entry" list.

    Returns:
        List of Observation resource dicts classified as lab tests.
    """
    labs = []
    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        if resource.get("resourceType") != "Observation":
            continue
        if not _is_vital_observation(resource) and not _is_functional_observation(resource):
            labs.append(resource)
    return labs


# Canonical lab name normalization map: canonical_key -> set of alternatives
_LAB_NAME_NORMALIZATION: dict[str, set[str]] = {
    "crp": {"c-reactive protein", "crp", "c reactive protein"},
    "urea": {"urea", "blood urea nitrogen", "bun"},
    "creatinine": {"creatinine", "serum creatinine"},
    "egfr": {"egfr", "egfr (ckd-epi)", "estimated gfr", "glomerular filtration rate"},
    "sodium": {"sodium", "na", "na+"},
    "potassium": {"potassium", "k", "k+"},
    "wcc": {"wcc", "white cell count", "white blood cell count", "wbc", "leucocytes"},
    "neutrophils": {"neutrophils", "neutrophil count", "neut"},
    "haemoglobin": {"haemoglobin", "hemoglobin", "hb", "hgb"},
    "platelets": {"platelets", "platelet count", "plt"},
    "procalcitonin": {"procalcitonin", "pct"},
    "lactate": {"lactate", "lactic acid"},
}

# Build reverse lookup: lowercase alternative -> canonical key
_LAB_NAME_REVERSE: dict[str, str] = {}
for _canon, _alts in _LAB_NAME_NORMALIZATION.items():
    for _alt in _alts:
        _LAB_NAME_REVERSE[_alt] = _canon


def _normalize_lab_name(name: str) -> str:
    """Normalize a lab test name to its canonical key."""
    lower = name.strip().lower()
    return _LAB_NAME_REVERSE.get(lower, lower)


# Critical lab tests that downstream nodes depend on
_CRITICAL_LAB_TESTS = {"crp", "urea", "egfr", "lactate"}


def validate_and_repair_lab_output(raw: dict) -> tuple[dict, list[str]]:
    """Validate and repair MedGemma lab synthesis output.

    Normalizes test names, coerces types, and reports missing critical tests.

    Args:
        raw: Parsed JSON dict from MedGemma lab synthesis. May have a
             "lab_values" wrapper key or be a direct dict of test results.

    Returns:
        (normalized_lab_dict, data_gaps) where normalized_lab_dict has the
        shape {test_name: {value, unit, reference_range, abnormal_flag}}.
    """
    data_gaps: list[str] = []

    # Handle both {lab_values: {...}} wrapper and direct dict
    if "lab_values" in raw and isinstance(raw["lab_values"], dict):
        lab_raw = raw["lab_values"]
    else:
        lab_raw = raw

    normalized: dict[str, dict] = {}
    for name, entry in lab_raw.items():
        if name == "lab_values":
            continue  # skip wrapper key if iterating raw
        if not isinstance(entry, dict):
            continue

        canon = _normalize_lab_name(name)

        # Type coercion
        value = _coerce_float(entry.get("value"))
        if value is None:
            continue  # skip entries with no parseable value

        unit = str(entry.get("unit", ""))
        ref = str(entry.get("reference_range", ""))

        # Handle both "abnormal_flag" and "abnormal" key variants
        flag_val = entry.get("abnormal_flag")
        if flag_val is None:
            flag_val = entry.get("abnormal")
        abnormal = _coerce_bool(flag_val) if flag_val is not None else False

        normalized[canon] = {
            "value": value,
            "unit": unit,
            "reference_range": ref,
            "abnormal_flag": abnormal,
        }

    # Report missing critical tests
    for test in sorted(_CRITICAL_LAB_TESTS):
        if test not in normalized:
            data_gaps.append(f"lab.{test} not extracted")

    return normalized, data_gaps

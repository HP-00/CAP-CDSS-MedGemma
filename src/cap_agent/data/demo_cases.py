"""Rich demo cases for the Clinical Workstation frontend.

5 cases — one per CXR category — each with full FHIR R4 bundles,
lab reports, clerking notes, historical documents, and real RSNA CXR images.
"""

import base64
import copy
from pathlib import Path

# ---------------------------------------------------------------------------
# Image path resolver
# ---------------------------------------------------------------------------

_RSNA_DIR = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "benchmark_data" / "rsna" / "images"
)


def _rsna_image(filename: str) -> str:
    abs_path = _RSNA_DIR / filename
    return str(abs_path) if abs_path.exists() else f"benchmark_data/rsna/images/{filename}"


# ---------------------------------------------------------------------------
# FHIR R4 resource factory functions
# ---------------------------------------------------------------------------

def _build_patient_resource(patient_id, family, given, gender, birth_date, nhs_number):
    return {
        "resource": {
            "resourceType": "Patient",
            "id": patient_id,
            "name": [{"family": family, "given": [given]}],
            "gender": gender,
            "birthDate": birth_date,
            "identifier": [
                {"system": "https://fhir.nhs.uk/Id/nhs-number", "value": nhs_number},
            ],
        }
    }


def _build_condition_resource(cond_id, snomed_code, display, text, severity=None):
    resource = {
        "resourceType": "Condition",
        "id": cond_id,
        "code": {
            "coding": [{"system": "http://snomed.info/sct", "code": snomed_code, "display": display}],
            "text": text,
        },
        "clinicalStatus": {"coding": [{"code": "active"}]},
        "subject": {"reference": "Patient/pt-001"},
    }
    if severity:
        resource["severity"] = {"coding": [{"display": severity}]}
    return {"resource": resource}


def _build_allergy_resource(allergy_id, code, display, text, reaction_type=None):
    resource = {
        "resourceType": "AllergyIntolerance",
        "id": allergy_id,
        "code": {
            "coding": [{"system": "http://snomed.info/sct", "code": code, "display": display}],
            "text": text,
        },
        "clinicalStatus": {"coding": [{"code": "active"}]},
        "patient": {"reference": "Patient/pt-001"},
    }
    if reaction_type:
        resource["reaction"] = [{"manifestation": [{"text": reaction_type}]}]
    return {"resource": resource}


def _build_nkda_resource():
    return _build_allergy_resource(
        "allergy-nkda", "716186003", "No known allergy", "No known drug allergies"
    )


def _build_observation_resource(obs_id, loinc_code, display, value, unit, datetime_str):
    return {
        "resource": {
            "resourceType": "Observation",
            "id": obs_id,
            "code": {
                "coding": [{"system": "http://loinc.org", "code": loinc_code, "display": display}],
            },
            "valueQuantity": {"value": value, "unit": unit},
            "effectiveDateTime": datetime_str,
            "subject": {"reference": "Patient/pt-001"},
        }
    }


def _build_bp_observation(obs_id, systolic, diastolic, datetime_str):
    return {
        "resource": {
            "resourceType": "Observation",
            "id": obs_id,
            "code": {
                "coding": [{"system": "http://loinc.org", "code": "85354-9", "display": "Blood pressure panel"}],
            },
            "component": [
                {
                    "code": {"coding": [{"system": "http://loinc.org", "code": "8480-6", "display": "Systolic blood pressure"}]},
                    "valueQuantity": {"value": systolic, "unit": "mmHg"},
                },
                {
                    "code": {"coding": [{"system": "http://loinc.org", "code": "8462-4", "display": "Diastolic blood pressure"}]},
                    "valueQuantity": {"value": diastolic, "unit": "mmHg"},
                },
            ],
            "effectiveDateTime": datetime_str,
            "subject": {"reference": "Patient/pt-001"},
        }
    }


def _build_medication_resource(med_id, text, dosage):
    return {
        "resource": {
            "resourceType": "MedicationRequest",
            "id": med_id,
            "medicationCodeableConcept": {"text": text},
            "dosageInstruction": [{"text": dosage}],
            "subject": {"reference": "Patient/pt-001"},
        }
    }


def _build_document_resource(doc_id, description, content_text):
    b64 = base64.b64encode(content_text.encode("utf-8")).decode("ascii")
    return {
        "resource": {
            "resourceType": "DocumentReference",
            "id": doc_id,
            "description": description,
            "content": [{"attachment": {"contentType": "text/plain", "data": b64}}],
            "subject": {"reference": "Patient/pt-001"},
        }
    }


def _build_encounter_resource(enc_id, class_code, period_start, reason):
    return {
        "resource": {
            "resourceType": "Encounter",
            "id": enc_id,
            "class": {
                "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
                "code": class_code,
                "display": "Acute Medical Unit",
            },
            "period": {"start": period_start},
            "reasonCode": [{"text": reason}],
            "subject": {"reference": "Patient/pt-001"},
        }
    }


def _build_eating_observation(obs_id, text, datetime_str):
    return {
        "resource": {
            "resourceType": "Observation",
            "id": obs_id,
            "code": {
                "coding": [{"system": "http://loinc.org", "code": "75244-9", "display": "Ability to eat independently"}],
            },
            "valueCodeableConcept": {"text": text},
            "effectiveDateTime": datetime_str,
            "subject": {"reference": "Patient/pt-001"},
        }
    }


# ---------------------------------------------------------------------------
# Standard observations builder (vitals + labs)
# ---------------------------------------------------------------------------

def _build_standard_observations(vitals, labs, datetime_str):
    """Build the standard set of vital and lab Observation entries."""
    entries = []
    # Vitals
    entries.append(_build_observation_resource("obs-rr", "9279-1", "Respiratory rate", vitals["rr"], "/min", datetime_str))
    entries.append(_build_bp_observation("obs-bp", vitals["sbp"], vitals["dbp"], datetime_str))
    entries.append(_build_observation_resource("obs-hr", "8867-4", "Heart rate", vitals["hr"], "/min", datetime_str))
    entries.append(_build_observation_resource("obs-spo2", "2708-6", "Oxygen saturation", vitals["spo2"], "%", datetime_str))
    entries.append(_build_observation_resource("obs-temp", "8310-5", "Body temperature", vitals["temp"], "Cel", datetime_str))
    # Labs
    entries.append(_build_observation_resource("obs-urea", "3094-0", "Urea", labs["urea"], "mmol/L", datetime_str))
    entries.append(_build_observation_resource("obs-crp", "1988-5", "C-reactive protein", labs["crp"], "mg/L", datetime_str))
    entries.append(_build_observation_resource("obs-creatinine", "2160-0", "Creatinine", labs["creatinine"], "umol/L", datetime_str))
    entries.append(_build_observation_resource("obs-egfr", "33914-3", "eGFR", labs["egfr"], "mL/min/1.73m2", datetime_str))
    entries.append(_build_observation_resource("obs-sodium", "2951-2", "Sodium", labs["sodium"], "mmol/L", datetime_str))
    entries.append(_build_observation_resource("obs-potassium", "2823-3", "Potassium", labs["potassium"], "mmol/L", datetime_str))
    entries.append(_build_observation_resource("obs-wcc", "6690-2", "White cell count", labs["wcc"], "x10^9/L", datetime_str))
    entries.append(_build_observation_resource("obs-neut", "751-8", "Neutrophils", labs["neutrophils"], "x10^9/L", datetime_str))
    entries.append(_build_observation_resource("obs-hb", "718-7", "Haemoglobin", labs["hb"], "g/L", datetime_str))
    entries.append(_build_observation_resource("obs-plt", "777-3", "Platelets", labs["platelets"], "x10^9/L", datetime_str))
    entries.append(_build_observation_resource("obs-pct", "33959-8", "Procalcitonin", labs["pct"], "ng/mL", datetime_str))
    entries.append(_build_observation_resource("obs-lactate", "2524-7", "Lactate", labs["lactate"], "mmol/L", datetime_str))
    return entries


# ---------------------------------------------------------------------------
# Lab report builder
# ---------------------------------------------------------------------------

def _build_lab_report(patient_name, dob, nhs, mrn, labs, collected_date, requested_by):
    """Build a tabular text lab report matching synthetic.py format."""
    def _flag(key, val):
        ref = labs[key]
        if ref.get("abnormal"):
            return "H" if ref.get("flag", "H") == "H" else "L"
        return ""

    lines = [
        "=" * 68,
        "  CITY GENERAL HOSPITAL NHS FOUNDATION TRUST",
        "  Department of Clinical Biochemistry & Haematology",
        "=" * 68,
        f"Patient: {patient_name}   DOB: {dob}   NHS: {nhs}",
        f"MRN: {mrn}       Ward: AMU         Collected: {collected_date}",
        f"Requested by: {requested_by}",
        "Sample: Venous blood (lithium heparin, EDTA)",
        "",
        "BIOCHEMISTRY",
        "-" * 68,
        f"{'Test':<20}{'Result':<10}{'Units':<13}{'Reference Range':<19}{'Flag'}",
        "-" * 68,
    ]
    biochem_keys = ["crp", "urea", "creatinine", "egfr", "sodium", "potassium", "pct", "lactate"]
    display_names = {
        "crp": "C-reactive protein", "urea": "Urea", "creatinine": "Creatinine",
        "egfr": "eGFR (CKD-EPI)", "sodium": "Sodium", "potassium": "Potassium",
        "pct": "Procalcitonin", "lactate": "Lactate",
    }
    for key in biochem_keys:
        if key not in labs:
            continue
        entry = labs[key]
        flag = "H" if entry.get("abnormal") and entry.get("flag", "H") == "H" else ("L" if entry.get("abnormal") else "")
        lines.append(f"{display_names.get(key, key):<20}{entry['value']:<10}{entry['unit']:<13}{entry['ref']:<19}{flag}")

    lines.extend(["", "HAEMATOLOGY", "-" * 68,
                   f"{'Test':<20}{'Result':<10}{'Units':<13}{'Reference Range':<19}{'Flag'}",
                   "-" * 68])
    haem_keys = ["wcc", "neutrophils", "hb", "platelets"]
    display_names_h = {
        "wcc": "White cell count", "neutrophils": "Neutrophils",
        "hb": "Haemoglobin", "platelets": "Platelets",
    }
    for key in haem_keys:
        if key not in labs:
            continue
        entry = labs[key]
        flag = "H" if entry.get("abnormal") and entry.get("flag", "H") == "H" else ("L" if entry.get("abnormal") else "")
        lines.append(f"{display_names_h.get(key, key):<20}{entry['value']:<10}{entry['unit']:<13}{entry['ref']:<19}{flag}")

    lines.extend(["", f"Authorised by: Dr S. Khan (Consultant Biochemist) {collected_date.split()[0]} 16:10", "=" * 68, ""])
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Clinical narratives — GP referral letters
# ---------------------------------------------------------------------------

_GP_REFERRAL_MARGARET = """\
URGENT GP REFERRAL LETTER

Dr J. Whitfield, Riverside Surgery
To: Acute Medical Unit, City General Hospital
Date: 18/02/2026

Re: Margaret THORNTON, DOB 03/05/1975, NHS 412 553 8901

Dear Colleagues,

I am referring this 50-year-old lady with a 4-day history of worsening \
cough productive of green sputum, fevers and malaise. She has a background \
of well-controlled asthma (Clenil 200mcg BD, salbutamol PRN) and \
hypertension (amlodipine 5mg OD).

In surgery today: Temp 37.9C, HR 88, BP 128/78, RR 16, SpO2 97% on \
room air. Chest auscultation: scattered crackles left base. No wheeze.

CRP point-of-care: 120 mg/L. She is systemically well, eating and \
drinking normally. I would appreciate assessment and consideration of \
outpatient vs inpatient management.

Kind regards,
Dr J. Whitfield
"""

_GP_REFERRAL_HAROLD = """\
URGENT GP REFERRAL LETTER

Dr M. Patel, Oaklands Medical Centre
To: Acute Medical Unit, City General Hospital
Date: 18/02/2026

Re: Harold PEMBERTON, DOB 10/09/1960, NHS 523 441 7632

Dear Colleagues,

I am referring this 65-year-old gentleman with known heart failure \
(EF 38%, last echo 6 months ago), atrial fibrillation (on apixaban + \
bisoprolol) and type 2 diabetes (metformin + gliclazide). He presents \
with 3-day history of increasing breathlessness, productive cough, and \
rigors.

In surgery: Temp 38.6C, HR 102 irregularly irregular, BP 118/72, \
RR 24, SpO2 92% on room air. Bilateral basal crackles — difficult to \
distinguish new from his baseline HF. Fine bilateral crepitations. \
Peripheral oedema unchanged from baseline.

Given cardiac comorbidity and bilateral signs, please assess urgently.

Kind regards,
Dr M. Patel
"""

_GP_REFERRAL_SUSAN = """\
URGENT GP REFERRAL LETTER

Dr A. Brooks, Elm Tree Practice
To: Acute Medical Unit, City General Hospital
Date: 18/02/2026

Re: Susan CLARKE, DOB 22/11/1975, NHS 634 772 1098

Dear Colleagues,

I am referring this 50-year-old lady with a 5-day history of dry cough, \
low-grade fevers (up to 37.8C), and left-sided pleuritic chest pain. \
She has a background of anxiety disorder (sertraline 50mg OD) and GORD \
(omeprazole 20mg OD).

Of note, she was seen in respiratory outpatient clinic 3 months ago for \
investigation of a left-sided pleural effusion found incidentally on CT \
chest — this was drained and cytology was benign.

In surgery: Temp 37.5C, HR 80, BP 124/76, RR 16, SpO2 98% on room air. \
Chest clear to auscultation. CRP point-of-care: 180 mg/L — unexpectedly \
high given relatively well appearance.

Given raised inflammatory markers and history of prior effusion, I \
would appreciate CXR and further workup.

Kind regards,
Dr A. Brooks
"""

_GP_REFERRAL_DAVID = """\
URGENT GP REFERRAL LETTER

Dr K. Osei, Greenfield Surgery
To: Acute Medical Unit, City General Hospital
Date: 18/02/2026

Re: David OKONKWO, DOB 15/07/1975, NHS 745 883 2019

Dear Colleagues,

I am referring this 50-year-old gentleman, previously fit and well with \
no significant past medical history. He presents with a 2-day history of \
fever (39.0C), dry cough, and myalgia. No rigors or haemoptysis.

In surgery: Temp 38.2C, HR 86, BP 132/80, RR 18, SpO2 97% on room air. \
Chest auscultation: subtle crackles right mid-zone, otherwise clear.

CRP point-of-care: 160 mg/L. He is otherwise well, eating and drinking \
normally. Given raised CRP, please review and consider CXR.

Kind regards,
Dr K. Osei
"""

_GP_REFERRAL_PATRICIA = """\
URGENT GP REFERRAL LETTER

Dr S. Macmillan, St Andrews Surgery
To: Acute Medical Unit, City General Hospital
Date: 18/02/2026

Re: Patricia HENNESSY, DOB 28/03/1960, NHS 856 994 3120

Dear Colleagues,

I am referring this 65-year-old lady with rheumatoid arthritis (on \
methotrexate 15mg weekly + folic acid, under rheumatology) and \
hypothyroidism (levothyroxine 100mcg OD). She presents with 5-day \
history of productive cough, fevers, and increasing breathlessness.

She is immunosuppressed on methotrexate. Last FBC 2 weeks ago showed \
WCC 5.2 (normal range).

In surgery: Temp 38.5C, HR 96, BP 110/68, RR 22, SpO2 93% on room air. \
Left basal crackles and dullness to percussion left base.

Given immunosuppression and clinical findings, please assess urgently.

Kind regards,
Dr S. Macmillan
"""

# ---------------------------------------------------------------------------
# Clinical narratives — Admission clerking notes
# ---------------------------------------------------------------------------

_CLERKING_MARGARET = """\
ACUTE MEDICAL UNIT — ADMISSION CLERKING NOTE

Patient: Margaret THORNTON  DOB: 03/05/1975  NHS: 412 553 8901  MRN: PT-2026-1001
Date: 18/02/2026 16:00  Clerked by: Dr R. Chen (FY2)

PC: 50yo lady referred by GP with 4-day productive cough and fevers.

HPC: Initially dry cough progressing to productive green sputum. Low-grade \
fevers and malaise. No rigors or sweats. Mild left-sided pleuritic chest \
pain. No haemoptysis. Good oral intake throughout.

PMH: Asthma (well-controlled, no exacerbations in 2 years), Hypertension.
DH: Clenil Modulite 200mcg BD, Salbutamol 100mcg PRN, Amlodipine 5mg OD.
Allergies: NKDA

SH: Non-smoker, lives with partner, works as a teacher. Fully independent \
ADLs. No recent travel. Not pregnant. Tolerates oral medications and food.

O/E:
General: Alert, orientated, looks well. AMT 10/10.
Obs: RR 16, SpO2 97% on room air, HR 88, BP 128/78, Temp 37.9C
Resp: Scattered crackles left base. No wheeze. Good air entry bilaterally.
CVS: HS I+II+0, no murmurs. No oedema.
Abdo: Soft, non-tender.
Neuro: GCS 15.

Impression: Likely community-acquired pneumonia, low severity. CXR and \
bloods for severity assessment. Consider outpatient management if CURB65 low.

Plan: CXR, bloods (FBC, U+E, CRP, LFT), CURB65 scoring, empirical \
antibiotics per CAP protocol.
"""

_CLERKING_HAROLD = """\
ACUTE MEDICAL UNIT — ADMISSION CLERKING NOTE

Patient: Harold PEMBERTON  DOB: 10/09/1960  NHS: 523 441 7632  MRN: PT-2026-1002
Date: 18/02/2026 17:30  Clerked by: Dr L. Williams (FY2)

PC: 65yo gentleman with known HF, AF and T2DM, referred with 3-day \
worsening breathlessness, productive cough and rigors.

HPC: Increasing breathlessness over 3 days, now at rest. Productive \
cough with yellow sputum. Rigors x2 at home. Orthopnoea unchanged from \
baseline (2 pillows). Ankle swelling unchanged. Poor oral intake.

PMH: Heart failure (EF 38%, diagnosed 2020), Atrial fibrillation \
(rate-controlled), Type 2 diabetes mellitus, Former smoker (20 pack-years, \
quit 2015).
DH: Bisoprolol 5mg OD, Ramipril 5mg OD, Apixaban 5mg BD, Furosemide 40mg \
OD, Metformin 1g BD, Gliclazide 80mg BD.
Allergies: NKDA

SH: Lives with wife, retired electrician. Baseline: independent with \
stick for mobility. No recent travel. Tolerates oral medications.

O/E:
General: Alert, orientated, looks unwell, tachypnoeic at rest. AMT 8/10 \
(failed date and recall).
Obs: RR 24, SpO2 92% on room air, HR 102 irregularly irregular, BP 118/72, \
Temp 38.6C
Resp: Bilateral basal crackles, more prominent on right. Reduced air \
entry both bases. Dullness to percussion right base.
CVS: AF, no new murmurs. Mild bilateral ankle oedema (baseline).
Abdo: Soft, non-tender.
Neuro: AMT 8/10. GCS 15.

Impression: Community-acquired pneumonia on background of heart failure. \
CURB65 = 2 (confusion + age ≥65). Moderate severity — admit. Need to \
distinguish infective crackles from HF baseline. Bilateral findings \
concerning — consider atypical vs aspiration.

Plan: CXR (compare with prior), bloods, blood cultures x2, start \
empirical antibiotics. Discuss with cardiology if HF decompensation \
suspected. Review fluid balance carefully.
"""

_CLERKING_SUSAN = """\
ACUTE MEDICAL UNIT — ADMISSION CLERKING NOTE

Patient: Susan CLARKE  DOB: 22/11/1975  NHS: 634 772 1098  MRN: PT-2026-1003
Date: 18/02/2026 15:00  Clerked by: Dr P. Singh (FY2)

PC: 50yo lady with 5-day dry cough, low-grade fevers and left-sided \
pleuritic pain. Known prior left pleural effusion (drained 3 months ago).

HPC: Dry cough for 5 days, low-grade fevers (up to 37.8C at home). \
Left-sided pleuritic chest pain, sharp, worse on inspiration. No \
haemoptysis or sputum production. No weight loss. Good appetite, \
eating normally.

PMH: Anxiety disorder, GORD. Previous left-sided pleural effusion (Nov \
2025, drained, cytology benign — under respiratory follow-up).
DH: Sertraline 50mg OD, Omeprazole 20mg OD.
Allergies: NKDA

SH: Non-smoker, lives alone, works as accountant. Fully independent \
ADLs. No recent travel. Not pregnant. Tolerates oral medications.

O/E:
General: Alert, orientated, looks well despite symptoms. AMT 10/10.
Obs: RR 16, SpO2 98% on room air, HR 80, BP 124/76, Temp 37.5C
Resp: Chest clear on auscultation. No crackles, wheeze or focal signs.
CVS: HS I+II+0, regular. No oedema.
Abdo: Soft, non-tender.

Impression: CRP 180 (GP) is discordant with clinical examination — \
patient looks well with clear chest. Previous effusion history raises \
concern for recurrence. CXR essential. Consider: atypical infection vs \
effusion recurrence vs non-respiratory source.

Plan: CXR (comparison with prior CT/CXR), bloods, atypical screen if \
CXR normal. Review respiratory outpatient letters.
"""

_CLERKING_DAVID = """\
ACUTE MEDICAL UNIT — ADMISSION CLERKING NOTE

Patient: David OKONKWO  DOB: 15/07/1975  NHS: 745 883 2019  MRN: PT-2026-1004
Date: 18/02/2026 14:00  Clerked by: Dr A. Hussain (FY2)

PC: 50yo previously fit man with 2-day fever, dry cough and myalgia.

HPC: Acute onset fever (up to 39.0C) 2 days ago. Dry cough, generalised \
myalgia, headache. No rigors, sweats or haemoptysis. No sputum production. \
Eating and drinking normally.

PMH: Nil significant.
DH: None regular.
Allergies: NKDA

SH: Non-smoker, lives with family, IT consultant. Fully independent. \
No recent travel abroad. No sick contacts. Not immunosuppressed.

O/E:
General: Alert, orientated, well-appearing. AMT 10/10.
Obs: RR 18, SpO2 97% on room air, HR 86, BP 132/80, Temp 38.2C
Resp: Subtle crackles right mid-zone, otherwise clear. Good air entry.
CVS: HS I+II+0, regular. No oedema.
Abdo: Soft, non-tender.

Impression: CRP 160 (GP) suggests significant inflammatory response. \
Subtle right mid-zone crackles may represent early consolidation. \
CXR required to confirm. Likely low severity if no consolidation.

Plan: CXR, bloods, CURB65 scoring. Likely suitable for outpatient \
management if CXR confirms mild/subtle disease.
"""

_CLERKING_PATRICIA = """\
ACUTE MEDICAL UNIT — ADMISSION CLERKING NOTE

Patient: Patricia HENNESSY  DOB: 28/03/1960  NHS: 856 994 3120  MRN: PT-2026-1005
Date: 18/02/2026 18:00  Clerked by: Dr M. Ahmed (FY2)

PC: 65yo immunosuppressed lady (methotrexate for RA) with 5-day \
productive cough, fevers and increasing breathlessness.

HPC: Productive cough with green-brown sputum for 5 days. Fevers (up \
to 38.5C), sweats and rigors x1. Progressive breathlessness — now \
dyspnoeic on minimal exertion. Left-sided pleuritic pain. Poor appetite, \
managing fluids only.

PMH: Rheumatoid arthritis (seropositive, on methotrexate 15mg weekly + \
folic acid 5mg weekly), Hypothyroidism.
DH: Methotrexate 15mg PO weekly, Folic acid 5mg weekly (day after MTX), \
Levothyroxine 100mcg OD, Naproxen 250mg BD PRN.
Allergies: NKDA

SH: Non-smoker, lives with husband, retired nurse. Independent ADLs \
baseline. No recent travel. Not pregnant. Currently managing fluids but \
poor solid intake.

O/E:
General: Alert, orientated, looks unwell, flushed. AMT 8/10 (failed \
date and recall).
Obs: RR 22, SpO2 93% on room air, HR 96, BP 110/68, Temp 38.5C
Resp: Left basal crackles. Dullness to percussion left base. Reduced \
air entry left base. Right lung clear.
CVS: HS I+II+0, regular. No oedema.
Abdo: Soft, non-tender.
Neuro: AMT 8/10. GCS 15.

Impression: Community-acquired pneumonia, left lower lobe. \
CURB65 = 2 (confusion + age ≥65). Moderate severity. \
Immunosuppressed on methotrexate — consider opportunistic infection. \
Left basal signs with dullness suggest consolidation ± effusion.

Plan: CXR, bloods (FBC urgent — MTX), blood cultures, sputum, \
atypical screen. Start empirical antibiotics. Hold methotrexate. \
Discuss with rheumatology re MTX hold.
"""

# ---------------------------------------------------------------------------
# Historical documents
# ---------------------------------------------------------------------------

_HF_DISCHARGE_HAROLD = """\
DISCHARGE SUMMARY — CARDIOLOGY

City General Hospital NHS Foundation Trust
Patient: Harold PEMBERTON  DOB: 10/09/1960  NHS: 523 441 7632
Admission: 15/08/2025  Discharge: 22/08/2025
Consultant: Dr R. Shah, Consultant Cardiologist

DIAGNOSIS: Acute decompensation of chronic heart failure (HFrEF, EF 38%)

PRESENTATION: 65yo male admitted with 2-week history of increasing \
breathlessness, orthopnoea and bilateral ankle swelling. Known HFrEF \
diagnosed 2020 following MI. On optimal medical therapy.

INVESTIGATIONS:
- Echo (17/08/2025): EF 38% (unchanged from 2024). Moderate MR. \
No significant valvular disease. LV dilatation.
- CXR: Cardiomegaly, bilateral pleural effusions, upper lobe diversion.
- BNP: 1240 pg/mL (ref <100).
- Renal function: Creatinine 105, eGFR 58.

MANAGEMENT: IV furosemide 80mg BD with fluid restriction. Stepped down \
to oral after 3 days. Weight loss 4.2kg. Uptitrated ramipril to 5mg.

DISCHARGE MEDICATIONS:
Bisoprolol 5mg OD, Ramipril 5mg OD, Apixaban 5mg BD, Furosemide 40mg OD, \
Metformin 1g BD, Gliclazide 80mg BD.

FOLLOW-UP: Heart failure nurse clinic 2 weeks. Cardiology outpatient 6 weeks.
"""

_RESPIRATORY_OPD_SUSAN = """\
RESPIRATORY OUTPATIENT CLINIC LETTER

City General Hospital NHS Foundation Trust
Patient: Susan CLARKE  DOB: 22/11/1975  NHS: 634 772 1098
Date: 20/11/2025
Consultant: Dr H. Brennan, Consultant Respiratory Medicine

Re: Follow-up — Left-sided pleural effusion

Dear Dr Brooks,

Thank you for referring Susan who I saw today in clinic. As you know, \
she was found to have a moderate left-sided pleural effusion incidentally \
on CT chest performed for investigation of persistent cough in October.

She underwent therapeutic and diagnostic thoracentesis on 05/11/2025. \
1.2L of straw-coloured fluid was drained. Cytology: benign mesothelial \
cells, no malignant cells. Protein 28 g/L — transudative. Culture: \
no growth. Glucose normal. LDH within normal limits.

CT chest (02/10/2025): Moderate left-sided pleural effusion. No \
underlying parenchymal abnormality. No mediastinal lymphadenopathy.

She is now asymptomatic. Chest examination today: clear bilaterally, \
no residual signs of effusion. CXR today shows complete resolution.

Plan: Discharge from respiratory clinic. If symptoms recur, please \
re-refer for repeat imaging.

Kind regards,
Dr H. Brennan
"""

_RHEUMATOLOGY_OPD_PATRICIA = """\
RHEUMATOLOGY OUTPATIENT CLINIC LETTER

City General Hospital NHS Foundation Trust
Patient: Patricia HENNESSY  DOB: 28/03/1960  NHS: 856 994 3120
Date: 01/02/2026
Consultant: Dr F. O'Brien, Consultant Rheumatologist

Re: Methotrexate monitoring review

Dear Dr Macmillan,

Patricia attended today for routine methotrexate monitoring. She reports \
good disease control with minimal joint stiffness (15 minutes morning \
stiffness). She has had no infections in the past 6 months. No mouth \
ulcers, nausea or hair loss.

Blood results (01/02/2026):
- FBC: Hb 132, WCC 5.2, Plt 230 — all within normal limits
- LFTs: ALT 22, AST 18, ALP 65 — normal
- Creatinine: 78, eGFR >90
- CRP: 8 mg/L (low-level inflammation, baseline for her)

DAS28-CRP: 2.8 (low disease activity)

Current medications unchanged:
- Methotrexate 15mg PO weekly (Fridays)
- Folic acid 5mg weekly (Saturdays)
- Levothyroxine 100mcg OD
- Naproxen 250mg BD PRN

Plan: Continue current regimen. Repeat bloods in 3 months. If she \
develops any infection, please advise to hold methotrexate and contact \
the rheumatology advice line.

Kind regards,
Dr F. O'Brien
"""

# ---------------------------------------------------------------------------
# Lab data definitions per case
# ---------------------------------------------------------------------------

def _margaret_labs():
    return {
        "crp": {"value": 120, "unit": "mg/L", "ref": "<5", "abnormal": True},
        "urea": {"value": 5.0, "unit": "mmol/L", "ref": "2.5-7.8", "abnormal": False},
        "creatinine": {"value": 68, "unit": "umol/L", "ref": "45-84", "abnormal": False},
        "egfr": {"value": 90, "unit": "mL/min/1.73m2", "ref": ">90", "abnormal": False},
        "sodium": {"value": 139, "unit": "mmol/L", "ref": "133-146", "abnormal": False},
        "potassium": {"value": 4.0, "unit": "mmol/L", "ref": "3.5-5.3", "abnormal": False},
        "pct": {"value": 0.3, "unit": "ng/mL", "ref": "<0.1", "abnormal": True},
        "lactate": {"value": 1.0, "unit": "mmol/L", "ref": "<2.0", "abnormal": False},
        "wcc": {"value": 12.1, "unit": "x10^9/L", "ref": "4.0-11.0", "abnormal": True},
        "neutrophils": {"value": 9.5, "unit": "x10^9/L", "ref": "2.0-7.5", "abnormal": True},
        "hb": {"value": 132, "unit": "g/L", "ref": "115-165", "abnormal": False},
        "platelets": {"value": 260, "unit": "x10^9/L", "ref": "150-400", "abnormal": False},
    }


def _harold_labs():
    return {
        "crp": {"value": 210, "unit": "mg/L", "ref": "<5", "abnormal": True},
        "urea": {"value": 7.0, "unit": "mmol/L", "ref": "2.5-7.8", "abnormal": False},
        "creatinine": {"value": 118, "unit": "umol/L", "ref": "62-106", "abnormal": True},
        "egfr": {"value": 52, "unit": "mL/min/1.73m2", "ref": ">90", "abnormal": True, "flag": "L"},
        "sodium": {"value": 133, "unit": "mmol/L", "ref": "133-146", "abnormal": False},
        "potassium": {"value": 4.8, "unit": "mmol/L", "ref": "3.5-5.3", "abnormal": False},
        "pct": {"value": 1.2, "unit": "ng/mL", "ref": "<0.1", "abnormal": True},
        "lactate": {"value": 1.8, "unit": "mmol/L", "ref": "<2.0", "abnormal": False},
        "wcc": {"value": 18.5, "unit": "x10^9/L", "ref": "4.0-11.0", "abnormal": True},
        "neutrophils": {"value": 15.2, "unit": "x10^9/L", "ref": "2.0-7.5", "abnormal": True},
        "hb": {"value": 128, "unit": "g/L", "ref": "130-170", "abnormal": True, "flag": "L"},
        "platelets": {"value": 310, "unit": "x10^9/L", "ref": "150-400", "abnormal": False},
    }


def _susan_labs():
    return {
        "crp": {"value": 180, "unit": "mg/L", "ref": "<5", "abnormal": True},
        "urea": {"value": 4.5, "unit": "mmol/L", "ref": "2.5-7.8", "abnormal": False},
        "creatinine": {"value": 62, "unit": "umol/L", "ref": "45-84", "abnormal": False},
        "egfr": {"value": 95, "unit": "mL/min/1.73m2", "ref": ">90", "abnormal": False},
        "sodium": {"value": 140, "unit": "mmol/L", "ref": "133-146", "abnormal": False},
        "potassium": {"value": 3.9, "unit": "mmol/L", "ref": "3.5-5.3", "abnormal": False},
        "pct": {"value": 0.15, "unit": "ng/mL", "ref": "<0.1", "abnormal": True},
        "lactate": {"value": 0.9, "unit": "mmol/L", "ref": "<2.0", "abnormal": False},
        "wcc": {"value": 10.8, "unit": "x10^9/L", "ref": "4.0-11.0", "abnormal": False},
        "neutrophils": {"value": 7.2, "unit": "x10^9/L", "ref": "2.0-7.5", "abnormal": False},
        "hb": {"value": 138, "unit": "g/L", "ref": "115-165", "abnormal": False},
        "platelets": {"value": 245, "unit": "x10^9/L", "ref": "150-400", "abnormal": False},
    }


def _david_labs():
    return {
        "crp": {"value": 160, "unit": "mg/L", "ref": "<5", "abnormal": True},
        "urea": {"value": 5.5, "unit": "mmol/L", "ref": "2.5-7.8", "abnormal": False},
        "creatinine": {"value": 85, "unit": "umol/L", "ref": "62-106", "abnormal": False},
        "egfr": {"value": 88, "unit": "mL/min/1.73m2", "ref": ">90", "abnormal": True, "flag": "L"},
        "sodium": {"value": 138, "unit": "mmol/L", "ref": "133-146", "abnormal": False},
        "potassium": {"value": 4.2, "unit": "mmol/L", "ref": "3.5-5.3", "abnormal": False},
        "pct": {"value": 0.5, "unit": "ng/mL", "ref": "<0.1", "abnormal": True},
        "lactate": {"value": 1.1, "unit": "mmol/L", "ref": "<2.0", "abnormal": False},
        "wcc": {"value": 13.0, "unit": "x10^9/L", "ref": "4.0-11.0", "abnormal": True},
        "neutrophils": {"value": 10.0, "unit": "x10^9/L", "ref": "2.0-7.5", "abnormal": True},
        "hb": {"value": 145, "unit": "g/L", "ref": "130-170", "abnormal": False},
        "platelets": {"value": 220, "unit": "x10^9/L", "ref": "150-400", "abnormal": False},
    }


def _patricia_labs():
    return {
        "crp": {"value": 195, "unit": "mg/L", "ref": "<5", "abnormal": True},
        "urea": {"value": 7.0, "unit": "mmol/L", "ref": "2.5-7.8", "abnormal": False},
        "creatinine": {"value": 82, "unit": "umol/L", "ref": "45-84", "abnormal": False},
        "egfr": {"value": 68, "unit": "mL/min/1.73m2", "ref": ">90", "abnormal": True, "flag": "L"},
        "sodium": {"value": 134, "unit": "mmol/L", "ref": "133-146", "abnormal": False},
        "potassium": {"value": 4.4, "unit": "mmol/L", "ref": "3.5-5.3", "abnormal": False},
        "pct": {"value": 0.9, "unit": "ng/mL", "ref": "<0.1", "abnormal": True},
        "lactate": {"value": 1.6, "unit": "mmol/L", "ref": "<2.0", "abnormal": False},
        "wcc": {"value": 4.8, "unit": "x10^9/L", "ref": "4.0-11.0", "abnormal": False},
        "neutrophils": {"value": 3.5, "unit": "x10^9/L", "ref": "2.0-7.5", "abnormal": False},
        "hb": {"value": 118, "unit": "g/L", "ref": "115-165", "abnormal": False},
        "platelets": {"value": 198, "unit": "x10^9/L", "ref": "150-400", "abnormal": False},
    }


# ---------------------------------------------------------------------------
# Helper: flat lab_results dict for case data (mock extraction compat)
# ---------------------------------------------------------------------------

def _flat_labs(labs_dict):
    """Convert rich lab dict to flat lab_results format for case data."""
    key_map = {"pct": "procalcitonin", "hb": "haemoglobin"}
    out = {}
    for k, v in labs_dict.items():
        flat_key = key_map.get(k, k)
        out[flat_key] = {
            "value": v["value"],
            "unit": v["unit"],
            "reference_range": v["ref"],
            "abnormal": v["abnormal"],
        }
    return out


# ---------------------------------------------------------------------------
# 5 case builder functions
# ---------------------------------------------------------------------------

def get_cxr_clear_case() -> dict:
    """Case 1: Margaret Thornton — 50F, clear pneumonia CXR, CURB65=0, low severity."""
    dt = "2026-02-18T16:00:00Z"
    labs = _margaret_labs()
    vitals = {"rr": 16, "sbp": 128, "dbp": 78, "hr": 88, "spo2": 97, "temp": 37.9}

    bundle = {"resourceType": "Bundle", "type": "collection", "entry": [
        _build_patient_resource("pt-001", "Thornton", "Margaret", "female", "1975-05-03", "4125538901"),
        _build_condition_resource("cond-asthma", "195967001", "Asthma", "Asthma"),
        _build_condition_resource("cond-htn", "38341003", "Hypertension", "Hypertension"),
        _build_nkda_resource(),
        *_build_standard_observations(vitals, {
            "urea": labs["urea"]["value"], "crp": labs["crp"]["value"],
            "creatinine": labs["creatinine"]["value"], "egfr": labs["egfr"]["value"],
            "sodium": labs["sodium"]["value"], "potassium": labs["potassium"]["value"],
            "wcc": labs["wcc"]["value"], "neutrophils": labs["neutrophils"]["value"],
            "hb": labs["hb"]["value"], "platelets": labs["platelets"]["value"],
            "pct": labs["pct"]["value"], "lactate": labs["lactate"]["value"],
        }, dt),
        _build_eating_observation("obs-eating", "Eating and drinking normally", dt),
        _build_medication_resource("med-clenil", "Clenil Modulite 200mcg", "Twice daily"),
        _build_medication_resource("med-salbutamol", "Salbutamol 100mcg inhaler", "PRN"),
        _build_medication_resource("med-amlodipine", "Amlodipine 5mg", "Once daily"),
        _build_document_resource("doc-gp-referral", "GP referral letter", _GP_REFERRAL_MARGARET),
        _build_document_resource("doc-clerking", "Admission clerking note", _CLERKING_MARGARET),
        _build_encounter_resource("enc-001", "AMB", "2026-02-18T15:30:00Z", "Community-acquired pneumonia"),
    ]}

    lab_report = _build_lab_report(
        "Margaret THORNTON", "03/05/1975", "412 553 8901", "PT-2026-1001",
        labs, "18/02/2026 16:30", "Dr R. Chen (FY2)",
    )

    return {
        "case_id": "cxr_clear",
        "patient_id": "PT-2026-1001",
        "demographics": {"age": 50, "sex": "Female", "weight_kg": 65},
        "presenting_complaint": "4-day history of productive cough, fevers and malaise",
        "clinical_exam": {
            "respiratory_exam": {
                "crackles": True, "crackles_location": "left base",
                "bronchial_breathing": False, "bronchial_breathing_location": None,
                "dullness_to_percussion": False, "dullness_location": None,
                "reduced_air_entry": False,
            },
            "observations": {
                "respiratory_rate": 16, "systolic_bp": 128, "diastolic_bp": 78,
                "heart_rate": 88, "spo2": 97, "temperature": 37.9,
                "supplemental_o2": "room air",
            },
            "confusion_assessment": {"amt_score": 10, "amt_total": 10, "confused": False},
        },
        "lab_results": _flat_labs(labs),
        "cxr": {
            "findings": {
                "consolidation": {"present": True, "confidence": "moderate", "location": "left lower lobe",
                                  "description": "Left basal air-space opacification with adjacent pleural fluid"},
                "pleural_effusion": {"present": True, "confidence": "moderate",
                                     "location": "left", "description": "Small left-sided pleural effusion"},
                "cardiomegaly": {"present": False, "confidence": "high"},
                "edema": {"present": False, "confidence": "high"},
                "atelectasis": {"present": False, "confidence": "moderate"},
            },
            "image_quality": {"projection": "PA", "rotation": "minimal", "penetration": "adequate"},
            "image_path": _rsna_image("effusion_001.png"),
            "prior_image_path": _rsna_image("normal_001.png"),
        },
        "past_medical_history": {
            "comorbidities": ["Asthma", "Hypertension"],
            "medications": ["Clenil Modulite 200mcg BD", "Salbutamol 100mcg PRN", "Amlodipine 5mg OD"],
            "allergies": [],
            "recent_antibiotics": [],
        },
        "social_history": {
            "pregnancy": False, "oral_tolerance": True, "eating_independently": True,
            "travel_history": [], "immunosuppression": False, "smoking_status": "never",
        },
        "fhir_bundle": bundle,
        "lab_report": {"format": "text", "content": lab_report, "source": "city_general_pathology"},
        "micro_results": [
            {"test_type": "blood_culture", "organism": "Streptococcus pneumoniae", "status": "positive",
             "antibiogram": {"amoxicillin": "S", "co_amoxiclav": "S", "clarithromycin": "S", "doxycycline": "S", "levofloxacin": "S", "penicillin": "S"}},
            {"test_type": "sputum_culture", "organism": "Streptococcus pneumoniae", "status": "positive",
             "antibiogram": {"amoxicillin": "S", "co_amoxiclav": "S", "clarithromycin": "S", "doxycycline": "S", "levofloxacin": "S", "penicillin": "S"}},
            {"test_type": "urinary_antigen", "organism": "Pneumococcal antigen", "status": "positive"},
            {"test_type": "urinary_antigen", "organism": "Legionella antigen", "status": "negative"},
        ],
    }


def get_cxr_bilateral_case() -> dict:
    """Case 2: Harold Pemberton — 65M, bilateral CXR, CURB65=2, moderate severity."""
    dt = "2026-02-18T17:30:00Z"
    labs = _harold_labs()
    vitals = {"rr": 24, "sbp": 118, "dbp": 72, "hr": 102, "spo2": 92, "temp": 38.6}

    bundle = {"resourceType": "Bundle", "type": "collection", "entry": [
        _build_patient_resource("pt-001", "Pemberton", "Harold", "male", "1960-09-10", "5234417632"),
        _build_condition_resource("cond-hf", "84114007", "Heart failure", "Heart failure (EF 38%)", severity="moderate"),
        _build_condition_resource("cond-af", "49436004", "Atrial fibrillation", "Atrial fibrillation"),
        _build_condition_resource("cond-t2dm", "44054006", "Type 2 diabetes mellitus", "Type 2 diabetes mellitus"),
        _build_nkda_resource(),
        *_build_standard_observations(vitals, {
            "urea": labs["urea"]["value"], "crp": labs["crp"]["value"],
            "creatinine": labs["creatinine"]["value"], "egfr": labs["egfr"]["value"],
            "sodium": labs["sodium"]["value"], "potassium": labs["potassium"]["value"],
            "wcc": labs["wcc"]["value"], "neutrophils": labs["neutrophils"]["value"],
            "hb": labs["hb"]["value"], "platelets": labs["platelets"]["value"],
            "pct": labs["pct"]["value"], "lactate": labs["lactate"]["value"],
        }, dt),
        _build_eating_observation("obs-eating", "Poor oral intake, managing fluids", dt),
        _build_medication_resource("med-bisoprolol", "Bisoprolol 5mg", "Once daily"),
        _build_medication_resource("med-ramipril", "Ramipril 5mg", "Once daily"),
        _build_medication_resource("med-apixaban", "Apixaban 5mg", "Twice daily"),
        _build_medication_resource("med-furosemide", "Furosemide 40mg", "Once daily"),
        _build_medication_resource("med-metformin", "Metformin 1g", "Twice daily"),
        _build_medication_resource("med-gliclazide", "Gliclazide 80mg", "Twice daily"),
        _build_document_resource("doc-gp-referral", "GP referral letter", _GP_REFERRAL_HAROLD),
        _build_document_resource("doc-hf-discharge", "HF discharge summary (Aug 2025)", _HF_DISCHARGE_HAROLD),
        _build_document_resource("doc-clerking", "Admission clerking note", _CLERKING_HAROLD),
        _build_encounter_resource("enc-001", "AMB", "2026-02-18T17:00:00Z", "Community-acquired pneumonia"),
    ]}

    lab_report = _build_lab_report(
        "Harold PEMBERTON", "10/09/1960", "523 441 7632", "PT-2026-1002",
        labs, "18/02/2026 18:00", "Dr L. Williams (FY2)",
    )

    return {
        "case_id": "cxr_bilateral",
        "patient_id": "PT-2026-1002",
        "demographics": {"age": 65, "sex": "Male", "weight_kg": 85},
        "presenting_complaint": "3-day worsening breathlessness, productive cough and rigors",
        "clinical_exam": {
            "respiratory_exam": {
                "crackles": True, "crackles_location": "bilateral bases",
                "bronchial_breathing": False, "bronchial_breathing_location": None,
                "dullness_to_percussion": True, "dullness_location": "right base",
                "reduced_air_entry": True,
            },
            "observations": {
                "respiratory_rate": 24, "systolic_bp": 118, "diastolic_bp": 72,
                "heart_rate": 102, "spo2": 92, "temperature": 38.6,
                "supplemental_o2": "room air",
            },
            "confusion_assessment": {"amt_score": 8, "amt_total": 10, "confused": True},
        },
        "lab_results": _flat_labs(labs),
        "cxr": {
            "findings": {
                "consolidation": {"present": True, "confidence": "high", "location": "bilateral lower lobes",
                                  "description": "Bilateral basal consolidation, right > left"},
                "pleural_effusion": {"present": False, "confidence": "moderate"},
                "cardiomegaly": {"present": True, "confidence": "moderate",
                                 "description": "Cardiomegaly consistent with known HF"},
                "edema": {"present": False, "confidence": "moderate"},
                "atelectasis": {"present": False, "confidence": "moderate"},
            },
            "image_quality": {"projection": "AP", "rotation": "minimal", "penetration": "adequate"},
            "image_path": _rsna_image("bilateral_002.png"),
            "prior_image_path": _rsna_image("normal_002.png"),
        },
        "past_medical_history": {
            "comorbidities": ["Heart failure (EF 38%)", "Atrial fibrillation", "Type 2 diabetes mellitus"],
            "medications": ["Bisoprolol 5mg OD", "Ramipril 5mg OD", "Apixaban 5mg BD",
                            "Furosemide 40mg OD", "Metformin 1g BD", "Gliclazide 80mg BD"],
            "allergies": [],
            "recent_antibiotics": [],
        },
        "social_history": {
            "pregnancy": False, "oral_tolerance": True, "eating_independently": False,
            "travel_history": [], "immunosuppression": False, "smoking_status": "former",
        },
        "fhir_bundle": bundle,
        "lab_report": {"format": "text", "content": lab_report, "source": "city_general_pathology"},
        "micro_results": [
            {"test_type": "blood_culture", "organism": "Streptococcus pneumoniae", "status": "positive",
             "antibiogram": {"amoxicillin": "S", "co_amoxiclav": "S", "clarithromycin": "S", "doxycycline": "S", "levofloxacin": "S", "penicillin": "S"}},
            {"test_type": "sputum_culture", "organism": "Streptococcus pneumoniae + Haemophilus influenzae", "status": "positive",
             "antibiogram": {"amoxicillin": "S", "co_amoxiclav": "S", "clarithromycin": "I", "doxycycline": "S", "levofloxacin": "S", "ceftriaxone": "S"}},
            {"test_type": "urinary_antigen", "organism": "Pneumococcal antigen", "status": "positive"},
            {"test_type": "urinary_antigen", "organism": "Legionella antigen", "status": "negative"},
        ],
    }


def get_cxr_normal_case() -> dict:
    """Case 3: Susan Clarke — 50F, normal CXR, CURB65=0, contradictions CR-1/CR-2."""
    dt = "2026-02-18T15:00:00Z"
    labs = _susan_labs()
    vitals = {"rr": 16, "sbp": 124, "dbp": 76, "hr": 80, "spo2": 98, "temp": 37.5}

    bundle = {"resourceType": "Bundle", "type": "collection", "entry": [
        _build_patient_resource("pt-001", "Clarke", "Susan", "female", "1975-11-22", "6347721098"),
        _build_condition_resource("cond-anxiety", "197480006", "Anxiety disorder", "Anxiety disorder"),
        _build_condition_resource("cond-gord", "235595009", "GORD", "Gastro-oesophageal reflux disease"),
        _build_nkda_resource(),
        *_build_standard_observations(vitals, {
            "urea": labs["urea"]["value"], "crp": labs["crp"]["value"],
            "creatinine": labs["creatinine"]["value"], "egfr": labs["egfr"]["value"],
            "sodium": labs["sodium"]["value"], "potassium": labs["potassium"]["value"],
            "wcc": labs["wcc"]["value"], "neutrophils": labs["neutrophils"]["value"],
            "hb": labs["hb"]["value"], "platelets": labs["platelets"]["value"],
            "pct": labs["pct"]["value"], "lactate": labs["lactate"]["value"],
        }, dt),
        _build_eating_observation("obs-eating", "Eating and drinking normally", dt),
        _build_medication_resource("med-sertraline", "Sertraline 50mg", "Once daily"),
        _build_medication_resource("med-omeprazole", "Omeprazole 20mg", "Once daily"),
        _build_document_resource("doc-gp-referral", "GP referral letter", _GP_REFERRAL_SUSAN),
        _build_document_resource("doc-resp-opd", "Respiratory outpatient letter (Nov 2025)", _RESPIRATORY_OPD_SUSAN),
        _build_document_resource("doc-clerking", "Admission clerking note", _CLERKING_SUSAN),
        _build_encounter_resource("enc-001", "AMB", "2026-02-18T14:30:00Z", "Raised inflammatory markers, prior effusion history"),
    ]}

    lab_report = _build_lab_report(
        "Susan CLARKE", "22/11/1975", "634 772 1098", "PT-2026-1003",
        labs, "18/02/2026 15:30", "Dr P. Singh (FY2)",
    )

    return {
        "case_id": "cxr_normal",
        "patient_id": "PT-2026-1003",
        "demographics": {"age": 50, "sex": "Female", "weight_kg": 62},
        "presenting_complaint": "5-day dry cough, low-grade fevers and left-sided pleuritic pain",
        "clinical_exam": {
            "respiratory_exam": {
                "crackles": False, "crackles_location": None,
                "bronchial_breathing": False, "bronchial_breathing_location": None,
                "dullness_to_percussion": False, "dullness_location": None,
                "reduced_air_entry": False,
            },
            "observations": {
                "respiratory_rate": 16, "systolic_bp": 124, "diastolic_bp": 76,
                "heart_rate": 80, "spo2": 98, "temperature": 37.5,
                "supplemental_o2": "room air",
            },
            "confusion_assessment": {"amt_score": 10, "amt_total": 10, "confused": False},
        },
        "lab_results": _flat_labs(labs),
        "cxr": {
            "findings": {
                "consolidation": {"present": False, "confidence": "high"},
                "pleural_effusion": {"present": False, "confidence": "high"},
                "cardiomegaly": {"present": False, "confidence": "high"},
                "edema": {"present": False, "confidence": "high"},
                "atelectasis": {"present": False, "confidence": "moderate"},
            },
            "image_quality": {"projection": "PA", "rotation": "minimal", "penetration": "adequate"},
            "image_path": _rsna_image("normal_001.png"),
            "prior_image_path": _rsna_image("effusion_001.png"),
        },
        "past_medical_history": {
            "comorbidities": ["Anxiety disorder", "GORD",
                              "Previous left pleural effusion (Nov 2025, drained, benign)"],
            "medications": ["Sertraline 50mg OD", "Omeprazole 20mg OD"],
            "allergies": [],
            "recent_antibiotics": [],
        },
        "social_history": {
            "pregnancy": False, "oral_tolerance": True, "eating_independently": True,
            "travel_history": [], "immunosuppression": False, "smoking_status": "never",
        },
        "fhir_bundle": bundle,
        "lab_report": {"format": "text", "content": lab_report, "source": "city_general_pathology"},
        "micro_results": [
            {"test_type": "blood_culture", "organism": "No growth at 48 hours", "status": "negative"},
            {"test_type": "sputum_culture", "organism": "Normal respiratory flora only", "status": "negative"},
            {"test_type": "urinary_antigen", "organism": "Pneumococcal antigen", "status": "negative"},
            {"test_type": "urinary_antigen", "organism": "Legionella antigen", "status": "negative"},
        ],
    }


def get_cxr_subtle_case() -> dict:
    """Case 4: David Okonkwo — 50M, subtle CXR, CURB65=0, low severity."""
    dt = "2026-02-18T14:00:00Z"
    labs = _david_labs()
    vitals = {"rr": 18, "sbp": 132, "dbp": 80, "hr": 86, "spo2": 97, "temp": 38.2}

    bundle = {"resourceType": "Bundle", "type": "collection", "entry": [
        _build_patient_resource("pt-001", "Okonkwo", "David", "male", "1975-07-15", "7458832019"),
        _build_nkda_resource(),
        *_build_standard_observations(vitals, {
            "urea": labs["urea"]["value"], "crp": labs["crp"]["value"],
            "creatinine": labs["creatinine"]["value"], "egfr": labs["egfr"]["value"],
            "sodium": labs["sodium"]["value"], "potassium": labs["potassium"]["value"],
            "wcc": labs["wcc"]["value"], "neutrophils": labs["neutrophils"]["value"],
            "hb": labs["hb"]["value"], "platelets": labs["platelets"]["value"],
            "pct": labs["pct"]["value"], "lactate": labs["lactate"]["value"],
        }, dt),
        _build_eating_observation("obs-eating", "Eating and drinking normally", dt),
        _build_document_resource("doc-gp-referral", "GP referral letter", _GP_REFERRAL_DAVID),
        _build_document_resource("doc-clerking", "Admission clerking note", _CLERKING_DAVID),
        _build_encounter_resource("enc-001", "AMB", "2026-02-18T13:30:00Z", "Fever with raised inflammatory markers"),
    ]}

    lab_report = _build_lab_report(
        "David OKONKWO", "15/07/1975", "745 883 2019", "PT-2026-1004",
        labs, "18/02/2026 14:30", "Dr A. Hussain (FY2)",
    )

    return {
        "case_id": "cxr_subtle",
        "patient_id": "PT-2026-1004",
        "demographics": {"age": 50, "sex": "Male", "weight_kg": 78},
        "presenting_complaint": "2-day history of fever, dry cough and myalgia",
        "clinical_exam": {
            "respiratory_exam": {
                "crackles": True, "crackles_location": "right mid-zone",
                "bronchial_breathing": False, "bronchial_breathing_location": None,
                "dullness_to_percussion": False, "dullness_location": None,
                "reduced_air_entry": False,
            },
            "observations": {
                "respiratory_rate": 18, "systolic_bp": 132, "diastolic_bp": 80,
                "heart_rate": 86, "spo2": 97, "temperature": 38.2,
                "supplemental_o2": "room air",
            },
            "confusion_assessment": {"amt_score": 10, "amt_total": 10, "confused": False},
        },
        "lab_results": _flat_labs(labs),
        "cxr": {
            "findings": {
                "consolidation": {"present": True, "confidence": "low", "location": "right mid-zone",
                                  "description": "Subtle opacity right mid-zone, possible early consolidation"},
                "pleural_effusion": {"present": False, "confidence": "high"},
                "cardiomegaly": {"present": False, "confidence": "high"},
                "edema": {"present": False, "confidence": "high"},
                "atelectasis": {"present": False, "confidence": "moderate"},
            },
            "image_quality": {"projection": "PA", "rotation": "minimal", "penetration": "adequate"},
            "image_path": _rsna_image("subtle_002.png"),
            "prior_image_path": _rsna_image("normal_003.png"),
        },
        "past_medical_history": {
            "comorbidities": [],
            "medications": [],
            "allergies": [],
            "recent_antibiotics": [],
        },
        "social_history": {
            "pregnancy": False, "oral_tolerance": True, "eating_independently": True,
            "travel_history": [], "immunosuppression": False, "smoking_status": "never",
        },
        "fhir_bundle": bundle,
        "lab_report": {"format": "text", "content": lab_report, "source": "city_general_pathology"},
        "micro_results": [
            {"test_type": "blood_culture", "organism": "No growth at 48 hours", "status": "negative"},
            {"test_type": "sputum_culture", "organism": "Streptococcus pneumoniae", "status": "positive",
             "antibiogram": {"amoxicillin": "S", "co_amoxiclav": "S", "clarithromycin": "S", "doxycycline": "S", "levofloxacin": "S", "penicillin": "S"}},
            {"test_type": "urinary_antigen", "organism": "Pneumococcal antigen", "status": "positive"},
            {"test_type": "urinary_antigen", "organism": "Legionella antigen", "status": "negative"},
        ],
    }


def get_cxr_effusion_case() -> dict:
    """Case 5: Patricia Hennessy — 65F, effusion CXR, CURB65=2, immunosuppressed."""
    dt = "2026-02-18T18:00:00Z"
    labs = _patricia_labs()
    vitals = {"rr": 22, "sbp": 110, "dbp": 68, "hr": 96, "spo2": 93, "temp": 38.5}

    bundle = {"resourceType": "Bundle", "type": "collection", "entry": [
        _build_patient_resource("pt-001", "Hennessy", "Patricia", "female", "1960-03-28", "8569943120"),
        _build_condition_resource("cond-ra", "69896004", "Rheumatoid arthritis", "Rheumatoid arthritis (seropositive, on methotrexate)"),
        _build_condition_resource("cond-hypothyroid", "40930008", "Hypothyroidism", "Hypothyroidism"),
        _build_nkda_resource(),
        *_build_standard_observations(vitals, {
            "urea": labs["urea"]["value"], "crp": labs["crp"]["value"],
            "creatinine": labs["creatinine"]["value"], "egfr": labs["egfr"]["value"],
            "sodium": labs["sodium"]["value"], "potassium": labs["potassium"]["value"],
            "wcc": labs["wcc"]["value"], "neutrophils": labs["neutrophils"]["value"],
            "hb": labs["hb"]["value"], "platelets": labs["platelets"]["value"],
            "pct": labs["pct"]["value"], "lactate": labs["lactate"]["value"],
        }, dt),
        _build_eating_observation("obs-eating", "Managing fluids, poor solid intake", dt),
        _build_medication_resource("med-mtx", "Methotrexate 15mg PO", "Weekly (Fridays)"),
        _build_medication_resource("med-folic", "Folic acid 5mg", "Weekly (day after MTX)"),
        _build_medication_resource("med-levo", "Levothyroxine 100mcg", "Once daily"),
        _build_medication_resource("med-naproxen", "Naproxen 250mg", "Twice daily PRN"),
        _build_document_resource("doc-gp-referral", "GP referral letter", _GP_REFERRAL_PATRICIA),
        _build_document_resource("doc-rheum-opd", "Rheumatology outpatient letter (Feb 2026)", _RHEUMATOLOGY_OPD_PATRICIA),
        _build_document_resource("doc-clerking", "Admission clerking note", _CLERKING_PATRICIA),
        _build_encounter_resource("enc-001", "AMB", "2026-02-18T17:30:00Z", "Community-acquired pneumonia, immunosuppressed"),
    ]}

    lab_report = _build_lab_report(
        "Patricia HENNESSY", "28/03/1960", "856 994 3120", "PT-2026-1005",
        labs, "18/02/2026 18:30", "Dr M. Ahmed (FY2)",
    )

    return {
        "case_id": "cxr_effusion",
        "patient_id": "PT-2026-1005",
        "demographics": {"age": 65, "sex": "Female", "weight_kg": 68},
        "presenting_complaint": "5-day productive cough, fevers, increasing breathlessness. Immunosuppressed on methotrexate.",
        "clinical_exam": {
            "respiratory_exam": {
                "crackles": True, "crackles_location": "left base",
                "bronchial_breathing": False, "bronchial_breathing_location": None,
                "dullness_to_percussion": True, "dullness_location": "left base",
                "reduced_air_entry": True,
            },
            "observations": {
                "respiratory_rate": 22, "systolic_bp": 110, "diastolic_bp": 68,
                "heart_rate": 96, "spo2": 93, "temperature": 38.5,
                "supplemental_o2": "room air",
            },
            "confusion_assessment": {"amt_score": 8, "amt_total": 10, "confused": True},
        },
        "lab_results": _flat_labs(labs),
        "cxr": {
            "findings": {
                "consolidation": {"present": True, "confidence": "moderate", "location": "left lower lobe",
                                  "description": "Left basal consolidation with adjacent pleural effusion"},
                "pleural_effusion": {"present": True, "confidence": "high",
                                     "location": "left", "description": "Moderate left-sided pleural effusion"},
                "cardiomegaly": {"present": False, "confidence": "high"},
                "edema": {"present": False, "confidence": "high"},
                "atelectasis": {"present": False, "confidence": "moderate"},
            },
            "image_quality": {"projection": "AP", "rotation": "minimal", "penetration": "adequate"},
            "image_path": _rsna_image("effusion_001.png"),
            "prior_image_path": None,
        },
        "past_medical_history": {
            "comorbidities": ["Rheumatoid arthritis (on methotrexate)", "Hypothyroidism"],
            "medications": ["Methotrexate 15mg PO weekly", "Folic acid 5mg weekly",
                            "Levothyroxine 100mcg OD", "Naproxen 250mg BD PRN"],
            "allergies": [],
            "recent_antibiotics": [],
        },
        "social_history": {
            "pregnancy": False, "oral_tolerance": True, "eating_independently": False,
            "travel_history": [], "immunosuppression": True, "smoking_status": "never",
        },
        "fhir_bundle": bundle,
        "lab_report": {"format": "text", "content": lab_report, "source": "city_general_pathology"},
        "micro_results": [
            {"test_type": "blood_culture", "organism": "Klebsiella pneumoniae", "status": "positive",
             "antibiogram": {"amoxicillin": "R", "co_amoxiclav": "S", "ceftriaxone": "S", "ciprofloxacin": "S", "meropenem": "S", "gentamicin": "S", "piperacillin_tazobactam": "S"}},
            {"test_type": "sputum_culture", "organism": "Klebsiella pneumoniae", "status": "positive",
             "antibiogram": {"amoxicillin": "R", "co_amoxiclav": "S", "ceftriaxone": "S", "ciprofloxacin": "S", "meropenem": "S", "gentamicin": "S", "piperacillin_tazobactam": "S"}},
            {"test_type": "urinary_antigen", "organism": "Pneumococcal antigen", "status": "negative"},
            {"test_type": "urinary_antigen", "organism": "Legionella antigen", "status": "negative"},
        ],
    }

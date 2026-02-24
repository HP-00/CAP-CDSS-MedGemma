"""CAP Agent state schema — 12 TypedDicts + CAPAgentState."""

import operator
from typing import Annotated, List, Optional, TypedDict, get_type_hints

try:
    from typing import NotRequired
except ImportError:
    from typing_extensions import NotRequired


class CURB65Variables(TypedDict, total=False):
    confusion: Optional[bool]       # AMT <= 8
    urea: Optional[float]           # mmol/L
    respiratory_rate: Optional[int]  # breaths/min
    systolic_bp: Optional[int]      # mmHg
    diastolic_bp: Optional[int]     # mmHg
    age: Optional[int]


class CURB65Score(TypedDict):
    c: int                    # 0 or 1
    u: int                    # 0 or 1
    r: int                    # 0 or 1
    b: int                    # 0 or 1
    age_65: int               # 0 or 1
    crb65: int                # 0-4 (community, no urea)
    curb65: Optional[int]     # 0-5 (hospital, if urea available)
    severity_tier: str        # "low", "moderate", "high"
    missing_variables: list


class LabValues(TypedDict, total=False):
    crp: Optional[dict]
    urea: Optional[dict]
    creatinine: Optional[dict]
    egfr: Optional[dict]
    sodium: Optional[dict]
    potassium: Optional[dict]
    wcc: Optional[dict]
    neutrophils: Optional[dict]
    haemoglobin: Optional[dict]
    platelets: Optional[dict]
    procalcitonin: Optional[dict]
    lactate: Optional[dict]
    bnp: Optional[dict]


class CXRFindings(TypedDict, total=False):
    consolidation: Optional[dict]      # {present, confidence, location, bounding_box?}
    pleural_effusion: Optional[dict]   # {present, confidence, bounding_box?}
    cardiomegaly: Optional[dict]
    edema: Optional[dict]
    atelectasis: Optional[dict]        # {present, confidence, bounding_box?}
    image_quality: Optional[dict]      # {projection, rotation, penetration}
    longitudinal_comparison: Optional[dict]  # {consolidation: {change, description}, ...}


class ClinicalExamFindings(TypedDict, total=False):
    respiratory_exam: Optional[dict]   # {crackles, bronchial_breathing, location}
    observations: Optional[dict]       # {rr, bp, hr, spo2, temp}
    confusion_status: Optional[dict]   # {present, amt_score}


class PatientDemographics(TypedDict, total=False):
    age: Optional[int]
    sex: Optional[str]
    allergies: Optional[list]          # [{drug, reaction_type, severity}]
    comorbidities: Optional[list]
    recent_antibiotics: Optional[list] # [{drug, date, indication}]
    pregnancy: Optional[bool]
    oral_tolerance: Optional[bool]
    eating_independently: Optional[bool]  # Discharge criterion (Halm 1998)
    travel_history: Optional[list]
    smoking_status: Optional[str]      # "current", "former", "never", None


class MicrobiologyResult(TypedDict, total=False):
    organism: Optional[str]            # "Streptococcus pneumoniae"
    susceptibilities: Optional[dict]   # {"amoxicillin": "S", "clarithromycin": "R"}
    test_type: Optional[str]           # "blood_culture", "sputum_culture", "urine_antigen"
    status: Optional[str]              # "positive", "negative", "pending", "not_sent"


class ContradictionAlert(TypedDict, total=False):
    rule_id: str                                    # "CR-1" to "CR-10"
    pattern: str                                    # Human-readable description
    evidence_for: str
    evidence_against: str
    severity: str                                   # clinical importance: "high", "moderate", "low"
    confidence: str                                 # detection certainty: "high", "moderate", "low"
    resolution_strategy: str                        # "A"-"E"
    recommendation: NotRequired[Optional[dict]]     # CR-9 switch data


class AntibioticRecommendation(TypedDict, total=False):
    severity_tier: str
    first_line: str
    dose_route: str
    allergy_adjustment: Optional[str]
    atypical_cover: Optional[str]
    renal_adjustment: Optional[str]
    corticosteroid_recommendation: Optional[str]
    stewardship_notes: list
    evidence_reference: str
    reasoning: str


class InvestigationPlan(TypedDict, total=False):
    blood_cultures: Optional[dict]     # {recommended, reasoning}
    sputum_culture: Optional[dict]
    pneumococcal_antigen: Optional[dict]
    legionella_antigen: Optional[dict]


class MonitoringPlan(TypedDict, total=False):
    crp_repeat_timing: str
    cxr_follow_up: Optional[str]
    discharge_criteria_met: Optional[bool]
    discharge_criteria_details: Optional[dict]
    next_review: str
    treatment_duration: Optional[dict]  # {extend_recommended, criteria_met, reasoning}
    treatment_response: Optional[dict]  # {reassess_needed, actions, reasoning}
    crp_trend: Optional[dict]           # {admission_value, current_value, percent_change, trend, flag_senior_review, reasoning}
    pct_trend: Optional[dict]           # {admission_value, current_value, percent_change, trend, flag_senior_review, reasoning}


class ToolResult(TypedDict):
    tool_name: str
    status: str          # "success", "error", "partial"
    summary: str
    raw_output: dict


class CAPAgentState(TypedDict):
    # Input
    case_id: str
    patient_id: str
    case_data: dict

    # Streaming/UI
    messages: Annotated[List, operator.add]
    thinking_traces: Annotated[List[str], operator.add]
    reasoning_trace: Annotated[List[dict], operator.add]
    current_step: str

    # Extraction outputs
    tool_results: Annotated[List[ToolResult], operator.add]
    clinical_findings: Annotated[List[str], operator.add]
    lab_findings: Annotated[List[str], operator.add]
    cxr_findings: Annotated[List[str], operator.add]

    # Structured extractions
    curb65_variables: Optional[CURB65Variables]
    lab_values: Optional[LabValues]
    cxr_analysis: Optional[CXRFindings]
    clinical_exam: Optional[ClinicalExamFindings]
    patient_demographics: Optional[PatientDemographics]

    # Severity
    curb65_score: Optional[CURB65Score]

    # Contradictions
    contradictions_detected: Annotated[List[ContradictionAlert], operator.add]
    resolution_results: Annotated[List[str], operator.add]

    # Treatment
    antibiotic_recommendation: Optional[AntibioticRecommendation]
    investigation_plan: Optional[InvestigationPlan]

    # Monitoring
    monitoring_plan: Optional[MonitoringPlan]

    # Output
    synthesized_findings: Optional[str]
    clinician_summary: Optional[str]
    structured_output: Optional[dict]

    # Microbiology (T=48h)
    micro_results: Optional[list]      # List[MicrobiologyResult], from case_data at T=48h

    # Tracking
    errors: Annotated[List[str], operator.add]
    data_gaps: Annotated[List[str], operator.add]


def build_initial_state(case: dict) -> dict:
    """Build an initial state dict from a case, introspecting CAPAgentState.

    This is the single source of truth for the notebook's initial_state dict.
    Fields are populated as follows:
      - Accumulator fields (Annotated with operator.add) → []
      - case_id, patient_id → from case dict
      - case_data → the case dict itself
      - current_step → "Initializing..."
      - All other fields → None
    """
    hints = get_type_hints(CAPAgentState, include_extras=True)
    state: dict = {}
    for field, hint in hints.items():
        # Accumulator: Annotated[..., operator.add]
        if hasattr(hint, "__metadata__") and operator.add in hint.__metadata__:
            state[field] = []
        elif field == "case_id":
            state[field] = case.get("case_id", "")
        elif field == "patient_id":
            state[field] = case.get("patient_id", "")
        elif field == "case_data":
            state[field] = case
        elif field == "current_step":
            state[field] = "Initializing..."
        else:
            state[field] = None
    return state

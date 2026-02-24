// Mirror of Python TypedDicts from src/cap_agent/agent/state.py

export interface CURB65Variables {
  confusion?: boolean;
  urea?: number;
  respiratory_rate?: number;
  systolic_bp?: number;
  diastolic_bp?: number;
  age?: number;
}

export interface CURB65Score {
  c: number;
  u: number;
  r: number;
  b: number;
  age_65: number;
  crb65: number;
  curb65: number | null;
  severity_tier: "low" | "moderate" | "high";
  missing_variables: string[];
}

export interface LabValue {
  value: number;
  unit: string;
  reference_range: string;
  abnormal_flag?: boolean;
  abnormal?: boolean;
}

export interface LabValues {
  crp?: LabValue;
  urea?: LabValue;
  creatinine?: LabValue;
  egfr?: LabValue;
  sodium?: LabValue;
  potassium?: LabValue;
  wcc?: LabValue;
  neutrophils?: LabValue;
  haemoglobin?: LabValue;
  platelets?: LabValue;
  procalcitonin?: LabValue;
  lactate?: LabValue;
  bnp?: LabValue;
}

export interface CXRFinding {
  present: boolean;
  confidence: string;
  location?: string;
  description?: string;
  bounding_box?: number[]; // [x1, y1, x2, y2] normalized to 896x896
}

export interface CXRFindings {
  consolidation?: CXRFinding;
  pleural_effusion?: CXRFinding;
  cardiomegaly?: CXRFinding;
  edema?: CXRFinding;
  atelectasis?: CXRFinding;
  image_quality?: {
    projection: string;
    rotation: string;
    penetration: string;
  };
  longitudinal_comparison?: Record<
    string,
    { change: string; description: string }
  >;
}

export interface ClinicalExamFindings {
  respiratory_exam?: {
    crackles: boolean;
    crackles_location?: string;
    bronchial_breathing: boolean;
    bronchial_breathing_location?: string;
  };
  observations?: {
    respiratory_rate: number;
    systolic_bp: number;
    diastolic_bp: number;
    heart_rate: number;
    spo2: number;
    temperature: number;
    supplemental_o2?: string;
  };
  confusion_status?: {
    present: boolean;
    amt_score: number;
  };
}

export interface PatientDemographics {
  age?: number;
  sex?: string;
  allergies?: Array<
    { drug?: string; reaction_type?: string; severity?: string } | string
  >;
  comorbidities?: string[];
  recent_antibiotics?: Array<{
    drug: string;
    date?: string;
    indication?: string;
  }>;
  pregnancy?: boolean;
  oral_tolerance?: boolean;
  eating_independently?: boolean;
  travel_history?: string[];
  smoking_status?: string;
}

export interface ContradictionAlert {
  rule_id: string;
  pattern: string;
  evidence_for: string;
  evidence_against: string;
  severity: "high" | "moderate" | "low";
  confidence: "high" | "moderate" | "low";
  resolution_strategy: string;
  recommendation?: Record<string, unknown>;
}

export interface AntibioticRecommendation {
  severity_tier: string;
  first_line: string;
  dose_route: string;
  allergy_adjustment?: string;
  atypical_cover?: string;
  renal_adjustment?: string;
  corticosteroid_recommendation?: string;
  stewardship_notes: string[];
  evidence_reference: string;
  reasoning: string;
}

export interface MonitoringPlan {
  crp_repeat_timing: string;
  cxr_follow_up?: string;
  discharge_criteria_met?: boolean;
  discharge_criteria_details?: Record<string, boolean>;
  next_review: string;
  treatment_duration?: {
    extend_recommended: boolean;
    criteria_met: number;
    reasoning: string;
  };
  treatment_response?: {
    reassess_needed: boolean;
    actions: string[];
    reasoning: string;
  };
  crp_trend?: {
    admission_value: number;
    current_value: number;
    percent_change: number;
    trend: string;
    flag_senior_review: boolean;
    reasoning: string;
  };
  pct_trend?: {
    admission_value: number;
    current_value: number;
    percent_change: number;
    trend: string;
    flag_senior_review: boolean;
    reasoning: string;
  };
}

export interface InvestigationPlan {
  blood_cultures?: { recommended: boolean; reasoning: string };
  sputum_culture?: { recommended: boolean; reasoning: string };
  pneumococcal_antigen?: { recommended: boolean; reasoning: string };
  legionella_antigen?: { recommended: boolean; reasoning: string };
}

export interface TraceStep {
  step_number: number;
  action: string;
  input_summary: string;
  output_summary: string;
  timestamp: string;
  duration_ms?: number;
  reasoning?: string;
}

export interface StructuredOutput {
  case_id: string;
  patient_id: string;
  generated_at: string;
  ai_disclaimer: string;
  provenance: {
    extraction_pipeline: string;
    data_sources: Record<string, string[]>;
    extraction_tools: Record<string, string>;
  };
  sections: {
    "1_patient": {
      demographics: PatientDemographics;
      source: string;
      data_sources: string[];
    };
    "2_severity": {
      curb65: CURB65Score;
      source: string;
    };
    "3_cxr": {
      findings: CXRFindings;
      source: string;
      data_sources: string[];
    };
    "4_key_bloods": {
      values: LabValues;
      source: string;
      data_sources: string[];
    };
    "5_contradiction_alert": {
      detected: number;
      alerts: ContradictionAlert[];
      informational: ContradictionAlert[];
      resolutions: string[];
      source: string;
    };
    "6_treatment_pathway": {
      antibiotic: AntibioticRecommendation;
      corticosteroid?: string;
      investigations: InvestigationPlan;
      source: string;
    };
    "7_data_gaps": { gaps: string[]; source: string };
    "8_monitoring": { plan: MonitoringPlan; source: string };
  };
  reasoning_trace: TraceStep[];
}

// SSE Event types

export interface SubNodeProgressEvent {
  node: string;
  sub_node: string;
  label: string;
  gpu_call: number;
  total_gpu_calls: number;
}

export interface TokenStreamEvent {
  node: string;
  tokens: Array<{ token: string; is_thinking: boolean }>;
}

export interface NodeCompleteEvent {
  node: string;
  label: string;
  step: number;
  timestamp: number;
  patient_demographics?: PatientDemographics;
  curb65_score?: CURB65Score;
  lab_values?: LabValues;
  cxr_analysis?: CXRFindings;
  clinical_exam?: ClinicalExamFindings;
  contradictions_detected?: ContradictionAlert[];
  resolution_results?: string[];
  antibiotic_recommendation?: AntibioticRecommendation;
  investigation_plan?: InvestigationPlan;
  monitoring_plan?: MonitoringPlan;
  clinician_summary?: string;
  structured_output?: StructuredOutput;
  data_gaps?: string[];
  errors?: string[];
  reasoning_trace?: TraceStep[];
}

export interface PipelineState {
  status: "idle" | "running" | "complete" | "error";
  completedNodes: string[];
  activeNode: string | null;
  totalNodes: number;
  // Accumulated data from SSE events
  patientDemographics: PatientDemographics | null;
  curb65Score: CURB65Score | null;
  labValues: LabValues | null;
  cxrAnalysis: CXRFindings | null;
  clinicalExam: ClinicalExamFindings | null;
  contradictions: ContradictionAlert[];
  resolutionResults: string[];
  antibioticRecommendation: AntibioticRecommendation | null;
  investigationPlan: InvestigationPlan | null;
  monitoringPlan: MonitoringPlan | null;
  clinicianSummary: string | null;
  structuredOutput: StructuredOutput | null;
  dataGaps: string[];
  errors: string[];
  reasoningTrace: TraceStep[];
  mockMode?: boolean;
  // Streaming state
  activeSubNode: string | null;
  subNodeLabel: string | null;
  subNodeProgress: { current: number; total: number } | null;
  streamingText: string;
  streamingThinking: string;
  streamingNode: string | null;
}

export interface DemoCase {
  id: string;
  label: string;
  description: string;
}

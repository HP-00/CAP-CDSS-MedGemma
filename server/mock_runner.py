"""Mock runner for GPU-free local development.

Patches call_medgemma with a prompt-keyword router (same pattern as E2E tests
and benchmark quick mode) and adds artificial delays to simulate real latency.

Mirrors the real SSE event format including node_start, sub_node_progress,
and token_stream events for frontend testing without GPU.

Case-aware: selects appropriate mock parameters for each demo scenario so that
T=48h shows stewardship contradictions, Day 3-4 shows CRP trends, and CR-10
shows allergy safety alerts.
"""

import asyncio
import time
import logging
from unittest.mock import patch

from cap_agent.agent.graph import build_cap_agent_graph
from cap_agent.agent.state import build_initial_state
from server.sse import NODE_ORDER, NODE_LABELS, _sse_event

logger = logging.getLogger(__name__)

# Shared mock responses (also used by tests/test_pipeline_e2e.py)
from server.mock_responses import (
    build_prompt_router,
    _mock_ehr_synthesis,
    _mock_lab_synthesis,
)

# Artificial delays per node (seconds) to simulate GPU inference
NODE_DELAYS = {
    "load_case": 0.3,
    "parallel_extraction": 2.0,
    "severity_scoring": 0.3,
    "check_contradictions": 0.5,
    "contradiction_resolution": 1.0,
    "treatment_selection": 0.5,
    "monitoring_plan": 0.3,
    "output_assembly": 1.5,
}

# Simulated sub-node progress for parallel_extraction
EXTRACTION_SUB_NODES = [
    ("ehr_narrative", "Filtering clinical notes...", 1, 8),
    ("ehr_structured", "Filtering structured data...", 2, 8),
    ("ehr_synthesis", "Synthesizing patient data...", 3, 8),
    ("lab_extraction", "Extracting lab values...", 4, 8),
    ("lab_synthesis", "Synthesizing lab results...", 5, 8),
    ("cxr_classification", "Classifying chest X-ray...", 6, 8),
    ("cxr_localization", "Localizing findings...", 7, 8),
    ("cxr_longitudinal", "Comparing with prior...", 8, 8),
]

# Mock-only delays — tuned to simulate real GPU latency for demo purposes.
# These only apply in mock mode (no CUDA). Real pipeline uses actual
# MedGemma inference which takes 5-30s per call naturally.
SUB_NODE_DELAY = 0.6   # per extraction sub-step (~5s total)
TOKEN_DELAY = 0.06     # per streamed word (~60 WPM readable typewriter)

# Mock thinking text for contradiction resolution
MOCK_THINKING = (
    "Let me analyze the contradiction between the clinical findings and lab results. "
    "The CXR shows consolidation but the lab markers suggest a different pattern. "
    "I need to weigh the evidence from both modalities carefully."
)

# Mock summary for token streaming
MOCK_SUMMARY_WORDS = (
    "This 72-year-old male presents with community-acquired pneumonia. "
    "CURB65 score indicates moderate severity requiring hospital admission. "
    "Chest X-ray confirms right lower lobe consolidation. "
    "Recommended treatment is amoxicillin with consideration for macrolide cover. "
    "Key contradictions between lab and imaging findings have been resolved. "
    "Monitoring plan includes CRP repeat at 48 hours and clinical review."
).split()


def _build_case_aware_router(case_data: dict):
    """Build a mock router with parameters appropriate for the case scenario.

    Detects case type from case_id and configures mock MedGemma responses
    to match the expected clinical scenario (same parameters as E2E tests).
    """
    case_id = case_data.get("case_id", "")

    if case_id == "cxr_clear":
        # Margaret Thornton: 50F, CURB65=0, low severity
        ehr_json = _mock_ehr_synthesis(
            urea=5.0, confusion=False, rr=16,
            sbp=128, dbp=78, age=50,
            hr=88, spo2=97, temp=37.9,
            sex="Female", comorbidities=["Asthma", "Hypertension"],
            smoking_status="never",
        )
        lab_json = _mock_lab_synthesis(crp=120, urea=5.0)

    elif case_id == "cxr_bilateral":
        # Harold Pemberton: 65M, CURB65=2, moderate severity
        ehr_json = _mock_ehr_synthesis(
            urea=7.0, confusion=True, rr=24,
            sbp=118, dbp=72, age=65,
            hr=102, spo2=92, temp=38.6,
            sex="Male",
            comorbidities=["Heart failure (EF 38%)", "Atrial fibrillation", "Type 2 diabetes mellitus"],
            smoking_status="former",
        )
        lab_json = _mock_lab_synthesis(crp=210, urea=7.0)

    elif case_id == "cxr_normal":
        # Susan Clarke: 50F, CURB65=0, low severity, CR-1/CR-2 expected
        ehr_json = _mock_ehr_synthesis(
            urea=4.5, confusion=False, rr=16,
            sbp=124, dbp=76, age=50,
            hr=80, spo2=98, temp=37.5,
            sex="Female", comorbidities=["Anxiety disorder", "GORD"],
            smoking_status="never",
        )
        lab_json = _mock_lab_synthesis(crp=180, urea=4.5)

    elif case_id == "cxr_subtle":
        # David Okonkwo: 50M, CURB65=0, low severity
        ehr_json = _mock_ehr_synthesis(
            urea=5.5, confusion=False, rr=18,
            sbp=132, dbp=80, age=50,
            hr=86, spo2=97, temp=38.2,
            sex="Male", comorbidities=[],
            smoking_status="never",
        )
        lab_json = _mock_lab_synthesis(crp=160, urea=5.5)

    elif case_id == "cxr_effusion":
        # Patricia Hennessy: 65F, CURB65=2, moderate severity, CR-6 expected
        ehr_json = _mock_ehr_synthesis(
            urea=7.0, confusion=True, rr=22,
            sbp=110, dbp=68, age=65,
            hr=96, spo2=93, temp=38.5,
            sex="Female",
            comorbidities=["Rheumatoid arthritis (on methotrexate)", "Hypothyroidism"],
            smoking_status="never",
        )
        lab_json = _mock_lab_synthesis(crp=195, urea=7.0)

    elif "48H" in case_id.upper() or "48h" in case_id:
        # T=48h Stewardship: improving vitals, lower CRP, urea normalizing
        ehr_json = _mock_ehr_synthesis(
            urea=6.8, confusion=False, rr=18,
            sbp=115, dbp=70, age=72,
            hr=82, spo2=96, temp=37.0,
        )
        lab_json = _mock_lab_synthesis(crp=95, urea=6.8)

    elif "DAY" in case_id.upper() or "day3" in case_id.lower():
        # Day 3-4: CRP only partially improved, treatment reassessment
        ehr_json = _mock_ehr_synthesis(
            urea=7.0, confusion=False, rr=20,
            sbp=110, dbp=68, age=72,
            hr=92, spo2=95, temp=37.8,
        )
        lab_json = _mock_lab_synthesis(crp=110, urea=7.0)

    else:
        # T=0 and CR-10 (CR-10 uses mock extraction, so router params
        # are only hit by pipeline-level nodes like clinician summary)
        ehr_json = _mock_ehr_synthesis(
            urea=8.2, confusion=False, rr=22,
            sbp=105, dbp=65, age=72,
        )
        lab_json = _mock_lab_synthesis(crp=186, urea=8.2)

    return build_prompt_router(ehr_json, lab_json)


STATE_KEYS = [
    "patient_demographics", "curb65_score",
    "lab_values", "cxr_analysis", "clinical_exam",
    "contradictions_detected", "resolution_results",
    "antibiotic_recommendation", "investigation_plan",
    "monitoring_plan", "clinician_summary", "structured_output",
    "data_gaps", "errors", "reasoning_trace",
]


def stream_pipeline_mock(case_data: dict, cxr_path: str | None = None):
    """Stream pipeline with mocked MedGemma for local development.

    Mirrors the real stream_pipeline() SSE event format including:
      - node_start before each node
      - sub_node_progress during parallel_extraction
      - token_stream for output_assembly and contradiction_resolution
      - node_complete after each node
    """
    # LangGraph requires an event loop; create one if running in a worker thread
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())

    if cxr_path:
        if "cxr" not in case_data:
            case_data["cxr"] = {}
        case_data["cxr"]["image_path"] = cxr_path

    router = _build_case_aware_router(case_data)
    graph = build_cap_agent_graph()
    initial_state = build_initial_state(case_data)

    yield _sse_event("pipeline_start", {
        "total_nodes": len(NODE_LABELS),
        "node_labels": NODE_LABELS,
        "mock_mode": True,
    })

    # Emit initial node_start
    yield _sse_event("node_start", {
        "node": NODE_ORDER[0],
        "label": NODE_LABELS[NODE_ORDER[0]],
        "step": 1,
    })

    step = 0
    with patch("cap_agent.models.medgemma.call_medgemma", side_effect=router):
        try:
            for chunk in graph.stream(initial_state, stream_mode="updates"):
                for node_name, node_output in chunk.items():
                    step += 1

                    # Pre-node simulated events
                    if node_name == "parallel_extraction":
                        # Emit sub-node progress with simulated delays
                        for sub_node, label, gpu_call, total in EXTRACTION_SUB_NODES:
                            yield _sse_event("sub_node_progress", {
                                "node": "parallel_extraction",
                                "sub_node": sub_node,
                                "label": label,
                                "gpu_call": gpu_call,
                                "total_gpu_calls": total,
                            })
                            time.sleep(SUB_NODE_DELAY)

                    elif node_name == "contradiction_resolution":
                        # Stream thinking tokens
                        for word in MOCK_THINKING.split():
                            yield _sse_event("token_stream", {
                                "node": "contradiction_resolution",
                                "tokens": [{"token": word + " ", "is_thinking": True}],
                            })
                            time.sleep(TOKEN_DELAY)
                        # Stream resolution text
                        resolution_text = " ".join(node_output.get("resolution_results", ["Contradiction resolved."]))
                        for word in resolution_text.split()[:30]:
                            yield _sse_event("token_stream", {
                                "node": "contradiction_resolution",
                                "tokens": [{"token": word + " ", "is_thinking": False}],
                            })
                            time.sleep(TOKEN_DELAY)

                    elif node_name == "output_assembly":
                        # Stream summary tokens word by word
                        summary = node_output.get("clinician_summary", "")
                        words = summary.split() if summary else MOCK_SUMMARY_WORDS
                        for word in words:
                            yield _sse_event("token_stream", {
                                "node": "output_assembly",
                                "tokens": [{"token": word + " ", "is_thinking": False}],
                            })
                            time.sleep(TOKEN_DELAY)
                    else:
                        # Standard delay for other nodes
                        delay = NODE_DELAYS.get(node_name, 0.5)
                        time.sleep(delay)

                    # Emit node_complete
                    event_data = {
                        "node": node_name,
                        "label": NODE_LABELS.get(node_name, node_name),
                        "step": step,
                        "timestamp": time.time(),
                    }
                    for key in STATE_KEYS:
                        if key in node_output:
                            event_data[key] = node_output[key]
                    yield _sse_event("node_complete", event_data)

                    # Emit node_start for next node
                    # Smart routing: skip contradiction_resolution when no contradictions
                    if node_name == "check_contradictions":
                        has_contradictions = bool(node_output.get("contradictions_detected"))
                        next_node = "contradiction_resolution" if has_contradictions else "treatment_selection"
                        yield _sse_event("node_start", {
                            "node": next_node,
                            "label": NODE_LABELS.get(next_node, next_node),
                            "step": step + 1,
                        })
                    else:
                        try:
                            idx = NODE_ORDER.index(node_name)
                            if idx + 1 < len(NODE_ORDER):
                                next_node = NODE_ORDER[idx + 1]
                                yield _sse_event("node_start", {
                                    "node": next_node,
                                    "label": NODE_LABELS.get(next_node, next_node),
                                    "step": step + 1,
                                })
                        except ValueError:
                            pass

            yield _sse_event("pipeline_complete", {"step": step, "status": "success"})

        except Exception as e:
            logger.exception("Mock pipeline error")
            yield _sse_event("pipeline_error", {"error": str(e), "step": step})

"""SSE generator wrapping LangGraph graph.stream() with token-level streaming.

Uses a queue bridge between the graph execution thread and the SSE generator:
  - Graph thread pushes events (node_start, node_complete, sub_node_progress,
    token_stream) to a shared queue
  - SSE generator drains the queue and yields formatted SSE events
  - Token batching: accumulates tokens for up to 50ms before flushing
  - Heartbeat: sends keepalive comment every 15s during long operations
"""

import asyncio
import json
import logging
import queue
import threading
import time
from collections.abc import Generator

from cap_agent.agent.graph import build_cap_agent_graph
from cap_agent.agent.nodes import set_streaming_callbacks, clear_streaming_callbacks
from cap_agent.agent.state import build_initial_state

logger = logging.getLogger(__name__)

# Node display names and order for progress tracking
NODE_ORDER = [
    "load_case",
    "parallel_extraction",
    "severity_scoring",
    "check_contradictions",
    "contradiction_resolution",
    "treatment_selection",
    "monitoring_plan",
    "output_assembly",
]

NODE_LABELS = {
    "load_case": "Load Case",
    "parallel_extraction": "Extract Data",
    "severity_scoring": "Score Severity",
    "check_contradictions": "Check Contradictions",
    "contradiction_resolution": "Resolve Contradictions",
    "treatment_selection": "Select Treatment",
    "monitoring_plan": "Monitoring Plan",
    "output_assembly": "Assemble Output",
}

STATE_KEYS = [
    "patient_demographics", "curb65_score",
    "lab_values", "cxr_analysis", "clinical_exam",
    "contradictions_detected", "resolution_results",
    "antibiotic_recommendation", "investigation_plan",
    "monitoring_plan", "clinician_summary", "structured_output",
    "data_gaps", "errors", "reasoning_trace",
]

_SENTINEL = object()  # Signals graph thread completion
_TOKEN_BATCH_MS = 50  # Flush token batches every 50ms
_HEARTBEAT_INTERVAL = 15  # SSE keepalive every 15s


def _sse_event(event_type: str, data: dict) -> str:
    """Format an SSE event string."""
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"


def stream_pipeline(case_data: dict, cxr_path: str | None = None) -> Generator[str, None, None]:
    """Stream pipeline execution as SSE events with token-level streaming.

    Architecture: queue bridge between graph thread and SSE generator.
    The graph thread runs graph.stream() and pushes events to a shared queue.
    Streaming callbacks push sub_node_progress and token_stream events.
    The SSE generator drains the queue with token batching and heartbeats.

    Events emitted:
      - pipeline_start: total nodes and labels
      - node_start: before each node begins
      - sub_node_progress: before each GPU call during extraction
      - token_stream: batched tokens during generation (contradiction/summary)
      - node_complete: when a node finishes with state updates
      - pipeline_complete: final event
      - pipeline_error: on error
      - SSE comment (: keepalive) every 15s

    Args:
        case_data: Built case dict from demo_cases.build_case()
        cxr_path: Optional path to uploaded CXR image
    """
    if cxr_path:
        if "cxr" not in case_data:
            case_data["cxr"] = {}
        case_data["cxr"]["image_path"] = cxr_path

    bridge: queue.Queue = queue.Queue()

    # --- Callbacks that push to the queue ---
    def progress_callback(sub_node: str, label: str, gpu_call: int, total: int):
        bridge.put(("sub_node_progress", {
            "sub_node": sub_node,
            "label": label,
            "gpu_call": gpu_call,
            "total_gpu_calls": total,
        }))

    def token_callback(token_text: str, is_thinking: bool):
        bridge.put(("token", {
            "token": token_text,
            "is_thinking": is_thinking,
        }))

    # --- Graph execution thread ---
    def _run_graph():
        # LangGraph internals require an event loop in the current thread
        try:
            asyncio.get_event_loop()
        except RuntimeError:
            asyncio.set_event_loop(asyncio.new_event_loop())

        set_streaming_callbacks(progress_cb=progress_callback, token_cb=token_callback)
        try:
            graph = build_cap_agent_graph()
            initial_state = build_initial_state(case_data)

            step = 0
            for chunk in graph.stream(initial_state, stream_mode="updates"):
                for node_name, node_output in chunk.items():
                    step += 1
                    logger.info("Node complete: %s (step %d)", node_name, step)

                    event_data = {
                        "node": node_name,
                        "label": NODE_LABELS.get(node_name, node_name),
                        "step": step,
                        "timestamp": time.time(),
                    }
                    for key in STATE_KEYS:
                        if key in node_output:
                            event_data[key] = node_output[key]

                    bridge.put(("node_complete", event_data))

            bridge.put(("pipeline_complete", {"step": step, "status": "success"}))
        except Exception as e:
            logger.exception("Pipeline error in graph thread")
            bridge.put(("pipeline_error", {"error": str(e)}))
        finally:
            clear_streaming_callbacks()
            bridge.put((_SENTINEL, None))

    # --- Emit pipeline_start + first node_start ---
    yield _sse_event("pipeline_start", {
        "total_nodes": len(NODE_ORDER),
        "node_labels": NODE_LABELS,
    })
    current_node = NODE_ORDER[0]
    yield _sse_event("node_start", {
        "node": current_node,
        "label": NODE_LABELS[current_node],
        "step": 1,
    })

    # Start graph thread
    graph_thread = threading.Thread(target=_run_graph, daemon=True)
    graph_thread.start()

    # --- SSE generator: drain queue with token batching and heartbeat ---
    last_heartbeat = time.time()
    token_batch: list[dict] = []
    last_token_flush = time.time()

    while True:
        try:
            msg_type, msg_data = bridge.get(timeout=0.05)
        except queue.Empty:
            # Flush any pending token batch
            now = time.time()
            if token_batch and (now - last_token_flush) >= _TOKEN_BATCH_MS / 1000:
                yield _sse_event("token_stream", {
                    "node": current_node,
                    "tokens": token_batch,
                })
                token_batch = []
                last_token_flush = now

            # Heartbeat
            if (now - last_heartbeat) >= _HEARTBEAT_INTERVAL:
                yield ": keepalive\n\n"
                last_heartbeat = now
            continue

        if msg_type is _SENTINEL:
            # Flush remaining tokens
            if token_batch:
                yield _sse_event("token_stream", {
                    "node": current_node,
                    "tokens": token_batch,
                })
                token_batch = []
            break

        if msg_type == "token":
            token_batch.append(msg_data)
            now = time.time()
            if (now - last_token_flush) >= _TOKEN_BATCH_MS / 1000:
                yield _sse_event("token_stream", {
                    "node": current_node,
                    "tokens": token_batch,
                })
                token_batch = []
                last_token_flush = now

        elif msg_type == "sub_node_progress":
            # Flush pending tokens before sub-node change
            if token_batch:
                yield _sse_event("token_stream", {
                    "node": current_node,
                    "tokens": token_batch,
                })
                token_batch = []
                last_token_flush = time.time()
            msg_data["node"] = current_node or "parallel_extraction"
            yield _sse_event("sub_node_progress", msg_data)

        elif msg_type == "node_complete":
            # Flush pending tokens before node transition
            if token_batch:
                yield _sse_event("token_stream", {
                    "node": current_node,
                    "tokens": token_batch,
                })
                token_batch = []
                last_token_flush = time.time()

            node_name = msg_data["node"]
            yield _sse_event("node_complete", msg_data)

            # Emit node_start for the next node
            # Smart routing: skip contradiction_resolution when no contradictions
            if node_name == "check_contradictions":
                has_contradictions = bool(msg_data.get("contradictions_detected"))
                next_node = "contradiction_resolution" if has_contradictions else "treatment_selection"
                current_node = next_node
                yield _sse_event("node_start", {
                    "node": next_node,
                    "label": NODE_LABELS.get(next_node, next_node),
                    "step": msg_data["step"] + 1,
                })
            else:
                try:
                    idx = NODE_ORDER.index(node_name)
                    if idx + 1 < len(NODE_ORDER):
                        next_node = NODE_ORDER[idx + 1]
                        current_node = next_node
                        yield _sse_event("node_start", {
                            "node": next_node,
                            "label": NODE_LABELS.get(next_node, next_node),
                            "step": msg_data["step"] + 1,
                        })
                except ValueError:
                    pass

        elif msg_type == "pipeline_complete":
            yield _sse_event("pipeline_complete", msg_data)

        elif msg_type == "pipeline_error":
            yield _sse_event("pipeline_error", msg_data)

        # Update heartbeat timestamp
        last_heartbeat = time.time()

    graph_thread.join(timeout=5.0)

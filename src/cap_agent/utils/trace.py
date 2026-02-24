"""Reasoning trace infrastructure for pipeline step logging."""

import time
from datetime import datetime


def create_trace_step(step_number: int, action: str, input_summary: str, reasoning: str) -> dict:
    """Create a reasoning trace step with timestamp."""
    return {
        "step_number": step_number,
        "action": action,
        "input_summary": input_summary,
        "output_summary": None,
        "reasoning": reasoning,
        "timestamp": datetime.now().isoformat(),
        "duration_ms": None,
        "_start_time": time.time(),
    }


def complete_trace_step(step: dict, output_summary: str) -> dict:
    """Complete a trace step with output and duration."""
    step["output_summary"] = output_summary
    step["duration_ms"] = int((time.time() - step.pop("_start_time")) * 1000)
    return step

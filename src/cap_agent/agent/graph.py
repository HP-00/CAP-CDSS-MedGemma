"""LangGraph state graph construction for the CAP CDSS agent."""

from langgraph.graph import StateGraph, END
from langgraph.types import CachePolicy
from langgraph.cache.memory import InMemoryCache

from cap_agent.agent.state import CAPAgentState
from cap_agent.agent.nodes import (
    load_case_node,
    parallel_extraction_node,
    severity_scoring_node,
    check_contradictions_node,
    should_resolve_contradictions,
    contradiction_resolution_node,
    treatment_selection_node,
    monitoring_plan_node,
    output_assembly_node,
)


def build_cap_agent_graph(checkpointer=None):
    """Build the 8-node LangGraph workflow for CAP clinical decision support.

    Args:
        checkpointer: Optional LangGraph checkpointer for fault tolerance.
                      Pass InMemorySaver() for in-memory checkpointing (requires
                      thread_id in invoke config). Default None = no checkpointing.

    Note: Using InMemorySaver as checkpointer causes accumulated state
        to differ across invocations, which silently prevents cache hits on
        GPU nodes (LangGraph Issue #5980). For reliable caching, omit the
        checkpointer or implement a custom key_func for CachePolicy.

    Graph topology:
        load_case -> parallel_extraction -> severity_scoring -> check_contradictions
            -> [contradiction_resolution | treatment_selection]
            -> monitoring_plan -> output_assembly -> END

    Caching:
        InMemoryCache is always enabled. GPU nodes (parallel_extraction,
        contradiction_resolution, output_assembly) have CachePolicy with TTL,
        so re-running the same case skips GPU calls entirely.
    """
    workflow = StateGraph(CAPAgentState)

    # Add 8 nodes — GPU nodes get CachePolicy for automatic memoization
    workflow.add_node("load_case", load_case_node)
    workflow.add_node("parallel_extraction", parallel_extraction_node,
                      cache_policy=CachePolicy(ttl=600))
    workflow.add_node("severity_scoring", severity_scoring_node)
    workflow.add_node("check_contradictions", check_contradictions_node)
    workflow.add_node("contradiction_resolution", contradiction_resolution_node,
                      cache_policy=CachePolicy(ttl=300))
    workflow.add_node("treatment_selection", treatment_selection_node)
    workflow.add_node("monitoring_plan", monitoring_plan_node)
    workflow.add_node("output_assembly", output_assembly_node,
                      cache_policy=CachePolicy(ttl=300))

    # Entry point
    workflow.set_entry_point("load_case")

    # Linear edges
    workflow.add_edge("load_case", "parallel_extraction")
    workflow.add_edge("parallel_extraction", "severity_scoring")
    workflow.add_edge("severity_scoring", "check_contradictions")

    # Conditional: contradictions detected -> resolve, else -> treatment
    workflow.add_conditional_edges(
        "check_contradictions",
        should_resolve_contradictions,
        {
            "contradiction_resolution": "contradiction_resolution",
            "treatment_selection": "treatment_selection",
        }
    )

    workflow.add_edge("contradiction_resolution", "treatment_selection")
    workflow.add_edge("treatment_selection", "monitoring_plan")
    workflow.add_edge("monitoring_plan", "output_assembly")
    workflow.add_edge("output_assembly", END)

    return workflow.compile(cache=InMemoryCache(), checkpointer=checkpointer)

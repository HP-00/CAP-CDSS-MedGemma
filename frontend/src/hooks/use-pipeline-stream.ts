import { useCallback, useReducer } from "react";
import type {
  PipelineState,
  NodeCompleteEvent,
  SubNodeProgressEvent,
  TokenStreamEvent,
  ContradictionAlert,
  TraceStep,
} from "@/types/pipeline";

const INITIAL_STATE: PipelineState = {
  status: "idle",
  completedNodes: [],
  activeNode: null,
  totalNodes: 8,
  patientDemographics: null,
  curb65Score: null,
  labValues: null,
  cxrAnalysis: null,
  clinicalExam: null,
  contradictions: [],
  resolutionResults: [],
  antibioticRecommendation: null,
  investigationPlan: null,
  monitoringPlan: null,
  clinicianSummary: null,
  structuredOutput: null,
  dataGaps: [],
  errors: [],
  reasoningTrace: [],
  // Streaming state
  activeSubNode: null,
  subNodeLabel: null,
  subNodeProgress: null,
  streamingText: "",
  streamingThinking: "",
  streamingNode: null,
};

type Action =
  | { type: "RESET" }
  | { type: "SET_STATUS"; status: PipelineState["status"] }
  | { type: "PIPELINE_START"; totalNodes: number; mockMode?: boolean }
  | { type: "NODE_START"; node: string }
  | { type: "NODE_COMPLETE"; event: NodeCompleteEvent }
  | { type: "SUB_NODE_PROGRESS"; event: SubNodeProgressEvent }
  | { type: "TOKEN_STREAM"; event: TokenStreamEvent }
  | { type: "PIPELINE_COMPLETE" }
  | { type: "ERROR"; error: string };

function reducer(state: PipelineState, action: Action): PipelineState {
  switch (action.type) {
    case "RESET":
      return INITIAL_STATE;

    case "SET_STATUS":
      return { ...state, status: action.status };

    case "PIPELINE_START":
      return {
        ...INITIAL_STATE,
        status: "running",
        totalNodes: action.totalNodes,
        mockMode: action.mockMode,
      };

    case "NODE_START":
      return {
        ...state,
        activeNode: action.node,
        // Clear sub-node state when entering a new node
        activeSubNode: null,
        subNodeLabel: null,
        subNodeProgress: null,
        // Clear streaming state for the new node
        streamingText: "",
        streamingThinking: "",
        streamingNode: action.node,
      };

    case "SUB_NODE_PROGRESS":
      return {
        ...state,
        activeSubNode: action.event.sub_node,
        subNodeLabel: action.event.label,
        subNodeProgress: {
          current: action.event.gpu_call,
          total: action.event.total_gpu_calls,
        },
      };

    case "TOKEN_STREAM": {
      let newText = state.streamingText;
      let newThinking = state.streamingThinking;
      for (const t of action.event.tokens) {
        if (t.is_thinking) {
          newThinking += t.token;
        } else {
          newText += t.token;
        }
      }
      return {
        ...state,
        streamingText: newText,
        streamingThinking: newThinking,
        streamingNode: action.event.node,
      };
    }

    case "NODE_COMPLETE": {
      const e = action.event;
      const newState: PipelineState = {
        ...state,
        completedNodes: [...state.completedNodes, e.node],
        activeNode: null,
        // Clear sub-node state
        activeSubNode: null,
        subNodeLabel: null,
        subNodeProgress: null,
        patientDemographics: e.patient_demographics ?? state.patientDemographics,
        curb65Score: e.curb65_score ?? state.curb65Score,
        labValues: e.lab_values ?? state.labValues,
        cxrAnalysis: e.cxr_analysis ?? state.cxrAnalysis,
        clinicalExam: e.clinical_exam ?? state.clinicalExam,
        contradictions: [
          ...state.contradictions,
          ...(e.contradictions_detected ?? []) as ContradictionAlert[],
        ],
        resolutionResults: [
          ...state.resolutionResults,
          ...(e.resolution_results ?? []),
        ],
        antibioticRecommendation: e.antibiotic_recommendation ?? state.antibioticRecommendation,
        investigationPlan: e.investigation_plan ?? state.investigationPlan,
        monitoringPlan: e.monitoring_plan ?? state.monitoringPlan,
        clinicianSummary: e.clinician_summary ?? state.clinicianSummary,
        structuredOutput: e.structured_output ?? state.structuredOutput,
        dataGaps: [...state.dataGaps, ...(e.data_gaps ?? [])],
        errors: [...state.errors, ...(e.errors ?? [])],
        reasoningTrace: [
          ...state.reasoningTrace,
          ...(e.reasoning_trace ?? []) as TraceStep[],
        ],
      };

      // When output_assembly completes, use streamed text as summary if available
      // (the clinician_summary from node_complete is the authoritative final version)
      if (e.node === "output_assembly") {
        newState.streamingText = "";
        newState.streamingThinking = "";
        newState.streamingNode = null;
      }

      // When contradiction_resolution completes, clear streaming state
      if (e.node === "contradiction_resolution") {
        newState.streamingText = "";
        newState.streamingThinking = "";
        newState.streamingNode = null;
      }

      return newState;
    }

    case "PIPELINE_COMPLETE":
      return {
        ...state,
        status: "complete",
        activeNode: null,
        activeSubNode: null,
        subNodeLabel: null,
        subNodeProgress: null,
        streamingText: "",
        streamingThinking: "",
        streamingNode: null,
      };

    case "ERROR":
      return { ...state, status: "error", errors: [...state.errors, action.error] };

    default:
      return state;
  }
}

export function usePipelineStream() {
  const [state, dispatch] = useReducer(reducer, INITIAL_STATE);

  const runPipeline = useCallback(async (caseId: string, forceMock?: boolean) => {
    dispatch({ type: "RESET" });

    try {
      const url = `/api/run/${caseId}${forceMock ? "?force_mock=true" : ""}`;
      const response = await fetch(url, { method: "POST" });

      if (!response.ok) {
        dispatch({ type: "ERROR", error: `HTTP ${response.status}: ${response.statusText}` });
        return;
      }

      const reader = response.body?.getReader();
      if (!reader) {
        dispatch({ type: "ERROR", error: "No response body" });
        return;
      }

      const decoder = new TextDecoder();
      let buffer = "";
      let eventType = "";
      let dataStr = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (line.startsWith("event: ")) {
            eventType = line.slice(7).trim();
          } else if (line.startsWith("data: ")) {
            dataStr = line.slice(6);
          } else if (line === "" && eventType && dataStr) {
            try {
              const data = JSON.parse(dataStr);
              switch (eventType) {
                case "pipeline_start":
                  dispatch({
                    type: "PIPELINE_START",
                    totalNodes: data.total_nodes ?? 8,
                    mockMode: data.mock_mode,
                  });
                  break;
                case "node_start":
                  dispatch({ type: "NODE_START", node: data.node });
                  break;
                case "sub_node_progress":
                  dispatch({ type: "SUB_NODE_PROGRESS", event: data as SubNodeProgressEvent });
                  break;
                case "token_stream":
                  dispatch({ type: "TOKEN_STREAM", event: data as TokenStreamEvent });
                  break;
                case "node_complete":
                  dispatch({ type: "NODE_COMPLETE", event: data as NodeCompleteEvent });
                  break;
                case "pipeline_complete":
                  dispatch({ type: "PIPELINE_COMPLETE" });
                  break;
                case "pipeline_error":
                  dispatch({ type: "ERROR", error: data.error ?? "Pipeline error" });
                  break;
              }
            } catch {
              // Skip malformed JSON
            }
            eventType = "";
            dataStr = "";
          }
        }
      }

      // If we haven't received a pipeline_complete event, mark complete
      if (state.status === "running") {
        dispatch({ type: "PIPELINE_COMPLETE" });
      }
    } catch (err) {
      dispatch({
        type: "ERROR",
        error: err instanceof Error ? err.message : "Connection failed",
      });
    }
  }, [state.status]);

  const reset = useCallback(() => dispatch({ type: "RESET" }), []);

  return { state, runPipeline, reset };
}

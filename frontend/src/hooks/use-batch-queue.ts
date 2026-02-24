import { useCallback, useRef, useState } from "react";
import type { PipelineState, NodeCompleteEvent, SubNodeProgressEvent, TokenStreamEvent, ContradictionAlert, TraceStep } from "@/types/pipeline";

const INITIAL_PIPELINE_STATE: PipelineState = {
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
  activeSubNode: null,
  subNodeLabel: null,
  subNodeProgress: null,
  streamingText: "",
  streamingThinking: "",
  streamingNode: null,
};

function applyNodeComplete(state: PipelineState, e: NodeCompleteEvent): PipelineState {
  return {
    ...state,
    completedNodes: [...state.completedNodes, e.node],
    activeNode: null,
    activeSubNode: null,
    subNodeLabel: null,
    subNodeProgress: null,
    streamingText: "",
    streamingThinking: "",
    streamingNode: null,
    patientDemographics: e.patient_demographics ?? state.patientDemographics,
    curb65Score: e.curb65_score ?? state.curb65Score,
    labValues: e.lab_values ?? state.labValues,
    cxrAnalysis: e.cxr_analysis ?? state.cxrAnalysis,
    clinicalExam: e.clinical_exam ?? state.clinicalExam,
    contradictions: [
      ...state.contradictions,
      ...((e.contradictions_detected ?? []) as ContradictionAlert[]),
    ],
    resolutionResults: [...state.resolutionResults, ...(e.resolution_results ?? [])],
    antibioticRecommendation: e.antibiotic_recommendation ?? state.antibioticRecommendation,
    investigationPlan: e.investigation_plan ?? state.investigationPlan,
    monitoringPlan: e.monitoring_plan ?? state.monitoringPlan,
    clinicianSummary: e.clinician_summary ?? state.clinicianSummary,
    structuredOutput: e.structured_output ?? state.structuredOutput,
    dataGaps: [...state.dataGaps, ...(e.data_gaps ?? [])],
    errors: [...state.errors, ...(e.errors ?? [])],
    reasoningTrace: [...state.reasoningTrace, ...((e.reasoning_trace ?? []) as TraceStep[])],
  };
}

function applyNodeStart(state: PipelineState, node: string): PipelineState {
  return {
    ...state,
    activeNode: node,
    activeSubNode: null,
    subNodeLabel: null,
    subNodeProgress: null,
    streamingText: "",
    streamingThinking: "",
    streamingNode: node,
  };
}

function applySubNodeProgress(state: PipelineState, e: SubNodeProgressEvent): PipelineState {
  return {
    ...state,
    activeSubNode: e.sub_node,
    subNodeLabel: e.label,
    subNodeProgress: { current: e.gpu_call, total: e.total_gpu_calls },
  };
}

function applyTokenStream(state: PipelineState, e: TokenStreamEvent): PipelineState {
  let newText = state.streamingText;
  let newThinking = state.streamingThinking;
  for (const t of e.tokens) {
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
    streamingNode: e.node,
  };
}

export interface BatchQueueState {
  queue: string[];
  currentIndex: number;
  results: Map<string, PipelineState>;
  status: "idle" | "running" | "complete";
}

export function useBatchQueue() {
  const [batchState, setBatchState] = useState<BatchQueueState>({
    queue: [],
    currentIndex: -1,
    results: new Map(),
    status: "idle",
  });

  const abortRef = useRef<AbortController | null>(null);

  const runSingleCase = useCallback(
    async (caseId: string, results: Map<string, PipelineState>, forceMock?: boolean): Promise<PipelineState> => {
      let state: PipelineState = { ...INITIAL_PIPELINE_STATE, status: "running" };

      // Update results map with running state
      const newResults = new Map(results);
      newResults.set(caseId, state);
      setBatchState((prev) => ({ ...prev, results: newResults }));

      try {
        const controller = new AbortController();
        abortRef.current = controller;

        const url = `/api/run/${caseId}${forceMock ? "?force_mock=true" : ""}`;
        const response = await fetch(url, {
          method: "POST",
          signal: controller.signal,
        });

        if (!response.ok) {
          state = { ...state, status: "error", errors: [`HTTP ${response.status}`] };
          return state;
        }

        const reader = response.body?.getReader();
        if (!reader) {
          state = { ...state, status: "error", errors: ["No response body"] };
          return state;
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
                    state = {
                      ...INITIAL_PIPELINE_STATE,
                      status: "running",
                      totalNodes: data.total_nodes ?? 8,
                      mockMode: data.mock_mode,
                    };
                    break;
                  case "node_start":
                    state = applyNodeStart(state, data.node);
                    break;
                  case "sub_node_progress":
                    state = applySubNodeProgress(state, data as SubNodeProgressEvent);
                    break;
                  case "token_stream":
                    state = applyTokenStream(state, data as TokenStreamEvent);
                    break;
                  case "node_complete":
                    state = applyNodeComplete(state, data as NodeCompleteEvent);
                    break;
                  case "pipeline_complete":
                    state = { ...state, status: "complete", activeNode: null };
                    break;
                  case "pipeline_error":
                    state = {
                      ...state,
                      status: "error",
                      errors: [...state.errors, data.error ?? "Pipeline error"],
                    };
                    break;
                }
              } catch {
                // Skip malformed JSON
              }

              // Update results map with latest state on each event
              const updated = new Map(results);
              updated.set(caseId, state);
              setBatchState((prev) => ({ ...prev, results: updated }));

              eventType = "";
              dataStr = "";
            }
          }
        }

        // Ensure we mark complete if stream ended without explicit event
        if (state.status === "running") {
          state = { ...state, status: "complete", activeNode: null };
        }
      } catch (err) {
        if ((err as Error).name === "AbortError") {
          state = { ...state, status: "error", errors: ["Aborted"] };
        } else {
          state = {
            ...state,
            status: "error",
            errors: [...state.errors, err instanceof Error ? err.message : "Connection failed"],
          };
        }
      }

      return state;
    },
    [],
  );

  const startBatch = useCallback(
    async (ids: string[], forceMock?: boolean) => {
      if (ids.length === 0) return;

      const results = new Map<string, PipelineState>();
      // Initialize all as idle
      for (const id of ids) {
        results.set(id, { ...INITIAL_PIPELINE_STATE });
      }

      setBatchState({
        queue: ids,
        currentIndex: 0,
        results,
        status: "running",
      });

      let currentResults = results;

      for (let i = 0; i < ids.length; i++) {
        setBatchState((prev) => ({ ...prev, currentIndex: i }));
        const result = await runSingleCase(ids[i], currentResults, forceMock);

        currentResults = new Map(currentResults);
        currentResults.set(ids[i], result);
        setBatchState((prev) => ({
          ...prev,
          results: currentResults,
          currentIndex: i,
        }));
      }

      setBatchState((prev) => ({
        ...prev,
        status: "complete",
        currentIndex: -1,
      }));
    },
    [runSingleCase],
  );

  const currentCaseId =
    batchState.status === "running" && batchState.currentIndex >= 0
      ? batchState.queue[batchState.currentIndex] ?? null
      : null;

  return {
    batch: batchState,
    startBatch,
    currentCaseId,
    getResult: useCallback(
      (caseId: string) => batchState.results.get(caseId),
      [batchState.results],
    ),
  };
}

import type { PipelineState } from "@/types/pipeline";
import { PatientBanner } from "@/components/dashboard/patient-banner";
import { SeverityCard } from "@/components/dashboard/severity-card";
import { CXRViewer } from "@/components/dashboard/cxr-viewer";
import { LabPanel } from "@/components/dashboard/lab-panel";
import { ContradictionAlerts } from "@/components/dashboard/contradiction-alerts";
import { TreatmentCard } from "@/components/dashboard/treatment-card";
import { MonitoringCard } from "@/components/dashboard/monitoring-card";
import { ClinicianSummary } from "@/components/dashboard/clinician-summary";
import { DataGapsCard } from "@/components/dashboard/data-gaps-card";
import { ReasoningTrace } from "@/components/dashboard/reasoning-trace";

interface DashboardProps {
  state: PipelineState;
  cxrUrl: string | null;
}

export function Dashboard({ state, cxrUrl }: DashboardProps) {
  const isRunning = state.status === "running";
  const hasData = state.status === "complete" || state.completedNodes.length > 0;

  // Determine loading states for each card based on which nodes have completed
  const extractionDone = state.completedNodes.includes("parallel_extraction");
  const scoringDone = state.completedNodes.includes("severity_scoring");
  const contradictionsDone = state.completedNodes.includes("check_contradictions")
    || state.completedNodes.includes("contradiction_resolution");
  const treatmentDone = state.completedNodes.includes("treatment_selection");
  const monitoringDone = state.completedNodes.includes("monitoring_plan");
  const outputDone = state.completedNodes.includes("output_assembly");

  if (state.status === "idle") {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center max-w-md">
          <div className="h-16 w-16 rounded-2xl bg-clinical-cyan/10 border border-clinical-cyan/20 flex items-center justify-center mx-auto mb-4">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-clinical-cyan">
              <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
            </svg>
          </div>
          <h2 className="text-lg font-semibold text-foreground mb-2">CAP Clinical Decision Support</h2>
          <p className="text-sm text-muted-foreground leading-relaxed">
            Select a clinical scenario from the sidebar and click <strong>Run Pipeline</strong> to begin the 8-node agentic analysis workflow.
          </p>
          <div className="mt-6 flex justify-center gap-4 text-[11px] text-muted-foreground/60 font-mono">
            <span>MedGemma 4B</span>
            <span>·</span>
            <span>LangGraph</span>
            <span>·</span>
            <span>8 nodes</span>
          </div>
        </div>
      </div>
    );
  }

  if (state.status === "error" && state.completedNodes.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center max-w-md p-6 rounded-lg bg-severity-high/5 border border-severity-high/20">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-severity-high mx-auto mb-3">
            <circle cx="12" cy="12" r="10" />
            <line x1="15" y1="9" x2="9" y2="15" />
            <line x1="9" y1="9" x2="15" y2="15" />
          </svg>
          <h3 className="text-sm font-semibold text-severity-high mb-2">Pipeline Error</h3>
          <p className="text-xs text-muted-foreground">
            {state.errors[state.errors.length - 1] ?? "An unexpected error occurred"}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 p-6 space-y-4 overflow-y-auto">
      {/* Patient banner — full width */}
      <PatientBanner
        demographics={state.patientDemographics}
        clinicalExam={state.clinicalExam}
        curb65Score={state.curb65Score}
        loading={isRunning && !extractionDone}
        dataGaps={state.dataGaps}
      />

      {/* Row 1: 3-column clinical data */}
      {hasData && (
        <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
          <SeverityCard
            score={state.curb65Score}
            loading={isRunning && !scoringDone}
            dataGaps={state.dataGaps}
          />
          <LabPanel
            labs={state.labValues}
            loading={isRunning && !extractionDone}
            dataGaps={state.dataGaps}
          />
          <CXRViewer
            findings={state.cxrAnalysis}
            imageUrl={cxrUrl}
            loading={isRunning && !extractionDone}
            dataGaps={state.dataGaps}
          />
        </div>
      )}

      {/* Row 2: 3-column actions */}
      {hasData && (
        <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
          <ContradictionAlerts
            contradictions={state.contradictions}
            resolutions={state.resolutionResults}
            loading={isRunning && !contradictionsDone}
            streamingThinking={state.streamingNode === "contradiction_resolution" ? state.streamingThinking : undefined}
            streamingResolution={state.streamingNode === "contradiction_resolution" ? state.streamingText : undefined}
            isStreaming={isRunning && state.streamingNode === "contradiction_resolution"}
          />
          {(treatmentDone || (isRunning && scoringDone)) && (
            <TreatmentCard
              recommendation={state.antibioticRecommendation}
              investigations={state.investigationPlan}
              loading={isRunning && !treatmentDone}
            />
          )}
          {(monitoringDone || (isRunning && treatmentDone)) && (
            <MonitoringCard
              plan={state.monitoringPlan}
              loading={isRunning && !monitoringDone}
            />
          )}
        </div>
      )}

      {/* Row 3: full-width summary */}
      {(outputDone || (isRunning && monitoringDone)) && (
        <ClinicianSummary
          summary={state.clinicianSummary}
          loading={isRunning && !outputDone}
          streamingText={state.streamingNode === "output_assembly" ? state.streamingText : undefined}
          isStreaming={isRunning && state.streamingNode === "output_assembly"}
          dataGaps={state.dataGaps}
        />
      )}

      {/* Footer: collapsed by default */}
      {state.status === "complete" && (
        <div className="space-y-2 pt-2">
          <DataGapsCard gaps={state.dataGaps} />
          <ReasoningTrace trace={state.reasoningTrace} />
        </div>
      )}
    </div>
  );
}

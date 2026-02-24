import { useBatchContext } from "@/stores/batch-store";
import { BatchProgressTable } from "@/components/batch/batch-progress-table";
import { BatchNodeCards } from "@/components/batch/batch-node-cards";
import { PageTransition } from "@/components/layout/page-transition";
import { Progress } from "@/components/ui/progress";

export function AnalysisPage() {
  const { batch, patients, currentCaseId, getResult } = useBatchContext();
  const { queue, status } = batch;

  const completedCount = queue.filter((id) => {
    const r = getResult(id);
    return r?.status === "complete" || r?.status === "error";
  }).length;

  const progressPct = queue.length > 0 ? (completedCount / queue.length) * 100 : 0;
  const currentPatient = patients.find((p) => p.caseId === currentCaseId);
  const currentResult = currentCaseId ? getResult(currentCaseId) : undefined;

  return (
    <PageTransition className="flex-1 flex flex-col min-h-0">
      {/* Header */}
      <div className="shrink-0 border-b border-border/50 px-6 py-3 bg-background/50 backdrop-blur-sm">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold tracking-tight">Batch Analysis</h1>
            <p className="text-xs text-muted-foreground mt-0.5">
              {status === "running"
                ? `Analysing patient ${batch.currentIndex + 1} of ${queue.length}...`
                : status === "complete"
                  ? `${completedCount} of ${queue.length} patients analysed`
                  : "No analysis in progress"}
            </p>
          </div>
        </div>
        {status === "running" && (
          <div className="mt-3">
            <Progress value={progressPct} className="h-1.5" />
          </div>
        )}
      </div>

      {/* Main content */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-6">
        {/* Live node cards for currently-running patient */}
        {status === "running" && currentPatient && currentResult && (
          <div className="bg-card/50 border border-border/30 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-3">
              <div className="h-2 w-2 rounded-full bg-severity-moderate animate-pulse" />
              <span className="text-sm font-medium">
                Running: {currentPatient.name}
              </span>
              <span className="text-xs text-muted-foreground">({currentPatient.bed})</span>
            </div>
            <BatchNodeCards state={currentResult} />

            {/* Sub-node progress label */}
            {currentResult.subNodeLabel && (
              <div className="mt-3 flex items-center gap-2 text-xs text-muted-foreground animate-in fade-in duration-300">
                <div className="h-1.5 w-1.5 rounded-full bg-clinical-cyan animate-pulse" />
                <span>
                  {currentResult.subNodeLabel}
                  {currentResult.subNodeProgress && (
                    <span className="text-muted-foreground/60 font-mono ml-1">
                      ({currentResult.subNodeProgress.current}/{currentResult.subNodeProgress.total})
                    </span>
                  )}
                </span>
              </div>
            )}

            {/* Inference activity indicator — concise status, not raw text */}
            {currentResult.streamingNode && (currentResult.streamingText || currentResult.streamingThinking) && (
              <div className="mt-3 border-t border-border/20 pt-3 animate-in fade-in duration-300">
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <div className="h-1.5 w-1.5 rounded-full bg-clinical-cyan animate-pulse" />
                  <span>
                    {currentResult.streamingNode === "contradiction_resolution"
                      ? currentResult.streamingThinking && !currentResult.streamingText
                        ? "Weighing evidence across clinical modalities..."
                        : "Formulating contradiction resolution..."
                      : currentResult.streamingNode === "output_assembly"
                        ? "Composing clinician summary..."
                        : "Running MedGemma inference..."}
                  </span>
                  <span className="text-[11px] font-mono text-muted-foreground/60 ml-auto">
                    {currentResult.streamingText.split(/\s+/).filter(Boolean).length} words
                  </span>
                </div>
                <div className="mt-2 h-1 rounded-full animate-shimmer" />
              </div>
            )}
          </div>
        )}

        {/* Progress table */}
        <BatchProgressTable />
      </div>
    </PageTransition>
  );
}

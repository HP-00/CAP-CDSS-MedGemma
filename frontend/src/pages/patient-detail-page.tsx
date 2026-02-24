import { useCallback } from "react";
import { useParams, useNavigate, useSearchParams } from "react-router-dom";
import { useBatchContext } from "@/stores/batch-store";
import { useModeContext } from "@/stores/mode-store";
import { usePipelineStream } from "@/hooks/use-pipeline-stream";
import { Dashboard } from "@/pages/dashboard";
import { CompactView } from "@/components/detail/compact-view";
import { GraphicalView } from "@/components/detail/graphical-view";
import { PageTransition } from "@/components/layout/page-transition";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { getSeverityConfig } from "@/lib/severity-colors";

export function PatientDetailPage() {
  const { caseId } = useParams<{ caseId: string }>();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { patients, getResult } = useBatchContext();
  const { demoMode } = useModeContext();

  // Standalone pipeline for running analysis from detail page
  const { state: standaloneState, runPipeline } = usePipelineStream();

  const batchResult = caseId ? getResult(caseId) : undefined;
  const patient = patients.find((p) => p.caseId === caseId);

  // Use batch result if available, otherwise standalone
  const pipelineState = batchResult?.status === "complete" || batchResult?.status === "running"
    ? batchResult
    : standaloneState;

  const activeTab = searchParams.get("tab") ?? "full";
  const setActiveTab = (tab: string) => setSearchParams({ tab });

  const handleRunAnalysis = useCallback(() => {
    if (caseId) {
      runPipeline(caseId, demoMode);
    }
  }, [caseId, demoMode, runPipeline]);

  const severityConfig = pipelineState.curb65Score
    ? getSeverityConfig(pipelineState.curb65Score.severity_tier)
    : null;

  const hasNoResult = pipelineState.status === "idle";

  return (
    <PageTransition className="flex-1 flex flex-col min-h-0">
      {/* Breadcrumb + patient info bar */}
      <div className="shrink-0 border-b border-border/50 px-6 py-3 bg-background/50 backdrop-blur-sm">
        <div className="flex items-center gap-2 text-xs text-muted-foreground mb-2">
          <button onClick={() => navigate("/")} className="hover:text-foreground transition-colors">
            Dashboard
          </button>
          <span>/</span>
          <button onClick={() => navigate("/analysis")} className="hover:text-foreground transition-colors">
            Analysis
          </button>
          <span>/</span>
          <span className="text-foreground font-medium">{patient?.name ?? caseId}</span>
        </div>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h1 className="text-lg font-semibold tracking-tight">{patient?.name ?? "Patient"}</h1>
            {patient && (
              <span className="text-sm text-muted-foreground">
                {patient.age}{patient.sex?.[0]} &middot; {patient.bed}
              </span>
            )}
            {severityConfig && (
              <Badge className={severityConfig.badge}>{severityConfig.label}</Badge>
            )}
          </div>
          <div className="flex items-center gap-2">
            {hasNoResult && (
              <Button onClick={handleRunAnalysis} className="bg-clinical-cyan hover:bg-clinical-cyan/90 text-white">
                Run Analysis
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* Tab content */}
      {hasNoResult ? (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center max-w-md">
            <div className="h-16 w-16 rounded-2xl bg-clinical-cyan/10 border border-clinical-cyan/20 flex items-center justify-center mx-auto mb-4">
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-clinical-cyan">
                <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
              </svg>
            </div>
            <h2 className="text-lg font-semibold mb-2">No Analysis Available</h2>
            <p className="text-sm text-muted-foreground">
              Click <strong>Run Analysis</strong> above to run the CAP pipeline for this patient, or go back and run a batch analysis.
            </p>
          </div>
        </div>
      ) : (
        <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col min-h-0">
          <div className="shrink-0 px-6 py-2">
            <TabsList className="bg-muted/30 h-9 p-1 gap-1 rounded-lg">
              <TabsTrigger
                value="full"
                className="rounded-md px-3 py-1.5 text-sm font-medium transition-all focus-visible:outline-none focus-visible:ring-0 data-[state=active]:bg-clinical-cyan/15 data-[state=active]:text-clinical-cyan data-[state=active]:shadow-sm data-[state=inactive]:text-muted-foreground data-[state=inactive]:hover:text-foreground after:hidden"
              >
                Full View
              </TabsTrigger>
              <TabsTrigger
                value="compact"
                className="rounded-md px-3 py-1.5 text-sm font-medium transition-all focus-visible:outline-none focus-visible:ring-0 data-[state=active]:bg-clinical-cyan/15 data-[state=active]:text-clinical-cyan data-[state=active]:shadow-sm data-[state=inactive]:text-muted-foreground data-[state=inactive]:hover:text-foreground after:hidden"
              >
                Compact
              </TabsTrigger>
              <TabsTrigger
                value="graphical"
                className="rounded-md px-3 py-1.5 text-sm font-medium transition-all focus-visible:outline-none focus-visible:ring-0 data-[state=active]:bg-clinical-cyan/15 data-[state=active]:text-clinical-cyan data-[state=active]:shadow-sm data-[state=inactive]:text-muted-foreground data-[state=inactive]:hover:text-foreground after:hidden"
              >
                Graphical
              </TabsTrigger>
            </TabsList>
          </div>
          <TabsContent value="full" className="flex-1 m-0 overflow-y-auto">
            <Dashboard state={pipelineState} cxrUrl={caseId ? `/api/case/${caseId}/cxr-image` : null} />
          </TabsContent>
          <TabsContent value="compact" className="flex-1 m-0 overflow-y-auto">
            <CompactView state={pipelineState} patient={patient ?? null} />
          </TabsContent>
          <TabsContent value="graphical" className="flex-1 m-0 overflow-y-auto">
            <GraphicalView state={pipelineState} />
          </TabsContent>
        </Tabs>
      )}
    </PageTransition>
  );
}

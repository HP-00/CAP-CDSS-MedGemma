import type { PipelineState } from "@/types/pipeline";

const NODES = [
  { id: "load_case", label: "Load", icon: "M5 8l4 4 4-4" },
  { id: "parallel_extraction", label: "Extract", icon: "M12 3v18M3 12h18" },
  { id: "severity_scoring", label: "Score", icon: "M13 2L3 14h9l-1 8 10-12h-9l1-8" },
  { id: "check_contradictions", label: "Check", icon: "M9 12l2 2 4-4" },
  { id: "contradiction_resolution", label: "Resolve", icon: "M4 4h16v16H4z" },
  { id: "treatment_selection", label: "Treat", icon: "M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0016.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 002 8.5c0 2.3 1.5 4.05 3 5.5l7 7 7-7z" },
  { id: "monitoring_plan", label: "Monitor", icon: "M22 12h-4l-3 9L9 3l-3 9H2" },
  { id: "output_assembly", label: "Output", icon: "M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2" },
];

interface PipelineProgressProps {
  state: PipelineState;
}

export function PipelineProgress({ state }: PipelineProgressProps) {
  const { completedNodes, status, subNodeLabel, subNodeProgress } = state;

  // Find the next node to be active (first non-completed)
  const activeIndex = status === "running"
    ? NODES.findIndex((n) => !completedNodes.includes(n.id))
    : -1;

  return (
    <div className="w-full">
      <div className="flex items-center justify-between px-2">
        {NODES.map((node, i) => {
          const isCompleted = completedNodes.includes(node.id);
          const isActive = i === activeIndex;
          const isSkipped = status === "complete" && !isCompleted;

          return (
            <div key={node.id} className="flex items-center flex-1 last:flex-initial">
              {/* Node dot */}
              <div className="flex flex-col items-center gap-1.5">
                <div
                  className={`
                    h-9 w-9 rounded-lg border flex items-center justify-center transition-all duration-500
                    ${isCompleted
                      ? "bg-severity-low/20 border-severity-low/40 text-severity-low"
                      : isActive
                        ? "bg-severity-moderate/20 border-severity-moderate/40 text-severity-moderate animate-pulse-glow"
                        : isSkipped
                          ? "bg-muted/30 border-border/30 text-muted-foreground/50"
                          : "bg-secondary/50 border-border/30 text-muted-foreground/60"
                    }
                  `}
                >
                  {isCompleted ? (
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                      <polyline points="20 6 9 17 4 12" />
                    </svg>
                  ) : isSkipped ? (
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <line x1="5" y1="12" x2="19" y2="12" />
                    </svg>
                  ) : (
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d={node.icon} />
                    </svg>
                  )}
                </div>
                <span className={`text-[10px] font-medium tracking-wider uppercase ${
                  isCompleted
                    ? "text-severity-low"
                    : isActive
                      ? "text-severity-moderate"
                      : "text-muted-foreground/50"
                }`}>
                  {node.label}
                </span>
              </div>

              {/* Connector line */}
              {i < NODES.length - 1 && (
                <div className="flex-1 mx-1.5 h-px mt-[-16px]">
                  <div
                    className={`h-full transition-all duration-700 ${
                      isCompleted ? "bg-severity-low/40" : "bg-border/30"
                    }`}
                  />
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Sub-node progress indicator */}
      {status === "running" && subNodeLabel && (
        <div className="mt-3 flex items-center justify-center gap-2 text-xs text-muted-foreground animate-in fade-in duration-300">
          <div className="h-1.5 w-1.5 rounded-full bg-clinical-cyan animate-pulse" />
          <span>
            {subNodeLabel}
            {subNodeProgress && (
              <span className="text-muted-foreground/60 font-mono ml-1">
                ({subNodeProgress.current}/{subNodeProgress.total})
              </span>
            )}
          </span>
        </div>
      )}
    </div>
  );
}

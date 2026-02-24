import type { PipelineState } from "@/types/pipeline";

const NODES = [
  { id: "load_case", label: "Load" },
  { id: "parallel_extraction", label: "Extract" },
  { id: "severity_scoring", label: "Score" },
  { id: "check_contradictions", label: "Check" },
  { id: "contradiction_resolution", label: "Resolve" },
  { id: "treatment_selection", label: "Treat" },
  { id: "monitoring_plan", label: "Monitor" },
  { id: "output_assembly", label: "Output" },
];

interface BatchNodeCardsProps {
  state: PipelineState;
}

export function BatchNodeCards({ state }: BatchNodeCardsProps) {
  const { completedNodes, status } = state;
  const activeIndex =
    status === "running"
      ? NODES.findIndex((n) => !completedNodes.includes(n.id))
      : -1;

  return (
    <div className="flex items-center gap-1.5">
      {NODES.map((node, i) => {
        const isCompleted = completedNodes.includes(node.id);
        const isActive = i === activeIndex;
        const isSkipped = status === "complete" && !isCompleted;

        return (
          <div key={node.id} className="flex items-center gap-1.5">
            <div
              className={`
                flex items-center gap-1 px-2 py-1 rounded text-[10px] font-mono uppercase tracking-wider border transition-all
                ${
                  isCompleted
                    ? "bg-severity-low/10 border-severity-low/30 text-severity-low"
                    : isActive
                      ? "bg-severity-moderate/10 border-severity-moderate/30 text-severity-moderate animate-pulse"
                      : isSkipped
                        ? "bg-muted/20 border-border/20 text-muted-foreground/40"
                        : "bg-muted/10 border-border/20 text-muted-foreground/40"
                }
              `}
            >
              {isCompleted ? (
                <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
              ) : isActive ? (
                <div className="h-1.5 w-1.5 rounded-full bg-severity-moderate" />
              ) : null}
              {node.label}
            </div>
            {i < NODES.length - 1 && (
              <div className={`w-2 h-px ${isCompleted ? "bg-severity-low/40" : "bg-border/30"}`} />
            )}
          </div>
        );
      })}
    </div>
  );
}

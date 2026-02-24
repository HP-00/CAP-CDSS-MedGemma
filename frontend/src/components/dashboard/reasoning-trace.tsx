import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { useState } from "react";
import type { TraceStep } from "@/types/pipeline";
import { formatDuration } from "@/lib/format";

interface ReasoningTraceProps {
  trace: TraceStep[];
}

export function ReasoningTrace({ trace }: ReasoningTraceProps) {
  const [open, setOpen] = useState(false);

  if (trace.length === 0) return null;

  const totalDuration = trace.reduce((sum, t) => sum + ((t.duration_ms ?? 0) / 1000), 0);

  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <CollapsibleTrigger className="flex items-center gap-2 text-xs text-muted-foreground hover:text-foreground transition-colors px-2 py-1 w-full">
        <svg
          width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
          className={`transition-transform ${open ? "rotate-90" : ""}`}
        >
          <polyline points="9 18 15 12 9 6" />
        </svg>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="12" cy="12" r="10" />
          <polyline points="12 6 12 12 16 14" />
        </svg>
        Reasoning trace — {trace.length} steps, {formatDuration(totalDuration)} total
      </CollapsibleTrigger>
      <CollapsibleContent>
        <Card className="border-border/30 bg-card/50 mt-2">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Pipeline Trace</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-0">
              {trace.map((step, i) => (
                <div key={i} className="flex items-start gap-3 py-2 border-b border-border/10 last:border-0">
                  {/* Timeline dot */}
                  <div className="flex flex-col items-center pt-1">
                    <div className="h-2 w-2 rounded-full bg-clinical-cyan/60" />
                    {i < trace.length - 1 && <div className="w-px flex-1 bg-border/20 mt-1" />}
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono font-medium text-foreground">
                        {step.action}
                      </span>
                      {step.duration_ms != null && (
                        <span className="text-[10px] font-mono text-muted-foreground">
                          {formatDuration(step.duration_ms / 1000)}
                        </span>
                      )}
                    </div>
                    <div className="text-[11px] text-muted-foreground mt-0.5 truncate">
                      {step.output_summary}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </CollapsibleContent>
    </Collapsible>
  );
}

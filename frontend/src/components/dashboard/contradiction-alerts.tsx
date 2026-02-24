import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { useState } from "react";
import type { ContradictionAlert } from "@/types/pipeline";
import { getConfidenceColor } from "@/lib/severity-colors";
import ReactMarkdown from "react-markdown";

interface ContradictionAlertsProps {
  contradictions: ContradictionAlert[];
  resolutions: string[];
  loading?: boolean;
  streamingThinking?: string;
  streamingResolution?: string;
  isStreaming?: boolean;
}

export function ContradictionAlerts({
  contradictions,
  resolutions,
  loading,
  streamingThinking,
  streamingResolution,
  isStreaming,
}: ContradictionAlertsProps) {
  const [expandedInfo, setExpandedInfo] = useState(false);
  const [expandedAlerts, setExpandedAlerts] = useState<Set<string>>(new Set());

  const toggleAlert = (id: string) => {
    setExpandedAlerts((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  if (loading && !isStreaming) {
    return (
      <Card className="border-border/30 bg-card/50">
        <CardHeader className="pb-3">
          <Skeleton className="h-5 w-40" />
        </CardHeader>
        <CardContent className="space-y-2">
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
        </CardContent>
      </Card>
    );
  }

  if (contradictions.length === 0 && !isStreaming) return null;

  const alerts = contradictions.filter((c) => c.confidence !== "low");
  const informational = contradictions.filter((c) => c.confidence === "low");

  return (
    <Card className="border-border/30 bg-card/50 animate-slide-up stagger-3">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
          Contradiction Analysis
          <Badge variant="outline" className="text-[10px] font-mono border-severity-high/30 text-severity-high">
            {alerts.length} alert{alerts.length !== 1 ? "s" : ""}
          </Badge>
          {informational.length > 0 && (
            <Badge variant="outline" className="text-[10px] font-mono border-border/30 text-muted-foreground">
              {informational.length} informational
            </Badge>
          )}
          {isStreaming && (
            <span className="text-[10px] font-mono text-clinical-cyan/60 animate-pulse">resolving</span>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-1.5">
        {/* High/moderate confidence alerts — single-line expandable */}
        {alerts.map((c, i) => {
          const alertId = `${c.rule_id}-${i}`;
          const isOpen = expandedAlerts.has(alertId);
          return (
            <Collapsible key={alertId} open={isOpen} onOpenChange={() => toggleAlert(alertId)}>
              <CollapsibleTrigger
                className={`flex items-center gap-2 w-full px-2 py-1.5 rounded-md text-xs transition-colors ${
                  c.severity === "high"
                    ? "bg-severity-high/5 hover:bg-severity-high/10"
                    : "bg-severity-moderate/5 hover:bg-severity-moderate/10"
                }`}
              >
                <Badge className={`text-[10px] font-mono shrink-0 ${
                  c.severity === "high"
                    ? "bg-severity-high/20 text-severity-high border border-severity-high/30"
                    : "bg-severity-moderate/20 text-severity-moderate border border-severity-moderate/30"
                }`}>
                  {c.rule_id}
                </Badge>
                <span className="truncate text-left font-medium">{c.pattern}</span>
                <Badge variant="outline" className={`text-[9px] font-mono shrink-0 ml-auto ${getConfidenceColor(c.confidence)}`}>
                  {c.confidence}
                </Badge>
                <svg
                  width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
                  className={`shrink-0 transition-transform text-muted-foreground ${isOpen ? "rotate-90" : ""}`}
                >
                  <polyline points="9 18 15 12 9 6" />
                </svg>
              </CollapsibleTrigger>
              <CollapsibleContent>
                <div className="p-2 mt-1 rounded-md border border-border/10 bg-secondary/10">
                  <div className="flex gap-1 mb-1.5">
                    <Badge variant="outline" className="text-[9px] font-mono border-border/30 text-muted-foreground">
                      Strategy {c.resolution_strategy}
                    </Badge>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-[11px]">
                    <div>
                      <span className="text-severity-low font-medium">For: </span>
                      <span className="text-muted-foreground">{c.evidence_for}</span>
                    </div>
                    <div>
                      <span className="text-severity-high font-medium">Against: </span>
                      <span className="text-muted-foreground">{c.evidence_against}</span>
                    </div>
                  </div>
                </div>
              </CollapsibleContent>
            </Collapsible>
          );
        })}

        {/* Streaming thinking block — compact, capped height with gradient */}
        {isStreaming && streamingThinking && (
          <div className="border-t border-border/20 pt-2 mt-2">
            <div className="text-[10px] font-medium text-muted-foreground/60 uppercase tracking-wider mb-1 flex items-center gap-1.5">
              <div className="h-1.5 w-1.5 rounded-full bg-clinical-cyan/40 animate-pulse" />
              Weighing clinical evidence...
            </div>
            <div className="relative max-h-12 overflow-hidden">
              <div className="text-[11px] text-muted-foreground/40 italic pl-2 border-l-2 border-muted/20 py-1">
                {streamingThinking.slice(-150)}
              </div>
              <div className="absolute inset-x-0 bottom-0 h-4 bg-gradient-to-t from-card/90 to-transparent pointer-events-none" />
            </div>
          </div>
        )}

        {/* Streaming resolution text — compact with word count */}
        {isStreaming && streamingResolution && (
          <div className="border-t border-border/20 pt-2 mt-2">
            <div className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider mb-1 flex items-center gap-1.5">
              Resolution
              <span className="text-[11px] font-mono text-muted-foreground/60 ml-auto">
                {streamingResolution.split(/\s+/).filter(Boolean).length} words
              </span>
            </div>
            <div className="relative max-h-16 overflow-hidden">
              <div className="text-xs text-muted-foreground pl-2 border-l-2 border-clinical-cyan/30 py-1 [&_strong]:font-semibold [&_strong]:text-foreground [&_p]:mb-1">
                <ReactMarkdown>{streamingResolution}</ReactMarkdown>
                <span className="inline-block w-[2px] h-[1em] bg-clinical-cyan ml-0.5 align-middle animate-blink" />
              </div>
              <div className="absolute inset-x-0 bottom-0 h-4 bg-gradient-to-t from-card/90 to-transparent pointer-events-none" />
            </div>
          </div>
        )}

        {/* Resolution results — final (non-streaming) */}
        {!isStreaming && resolutions.length > 0 && (
          <div className="border-t border-border/20 pt-2 mt-2">
            <div className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider mb-1">
              Resolutions
            </div>
            {resolutions.map((r, i) => (
              <div key={i} className="text-xs text-muted-foreground pl-2 border-l-2 border-clinical-cyan/30 py-1 [&_strong]:font-semibold [&_strong]:text-foreground [&_p]:mb-1">
                <ReactMarkdown>{r}</ReactMarkdown>
              </div>
            ))}
          </div>
        )}

        {/* Informational (low confidence) — collapsed */}
        {informational.length > 0 && (
          <Collapsible open={expandedInfo} onOpenChange={setExpandedInfo}>
            <CollapsibleTrigger className="flex items-center gap-1.5 text-[11px] text-muted-foreground hover:text-foreground transition-colors w-full pt-2">
              <svg
                width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
                className={`transition-transform ${expandedInfo ? "rotate-90" : ""}`}
              >
                <polyline points="9 18 15 12 9 6" />
              </svg>
              {informational.length} informational item{informational.length !== 1 ? "s" : ""} (low confidence)
            </CollapsibleTrigger>
            <CollapsibleContent className="space-y-1.5 mt-2">
              {informational.map((c, i) => (
                <div
                  key={`info-${c.rule_id}-${i}`}
                  className="p-2 rounded-sm bg-secondary/20 border border-border/10 text-xs text-muted-foreground"
                >
                  <span className="font-mono text-[10px] mr-2">{c.rule_id}</span>
                  {c.pattern}
                </div>
              ))}
            </CollapsibleContent>
          </Collapsible>
        )}
      </CardContent>
    </Card>
  );
}

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { FallbackBadge } from "@/components/ui/fallback-badge";
import { useState } from "react";
import { getCardFallbacks } from "@/lib/fallback-utils";
import ReactMarkdown from "react-markdown";

interface ClinicianSummaryProps {
  summary: string | null;
  loading?: boolean;
  streamingText?: string;
  isStreaming?: boolean;
  dataGaps?: string[];
}

export function ClinicianSummary({ summary, loading, streamingText, isStreaming, dataGaps }: ClinicianSummaryProps) {
  const [expanded, setExpanded] = useState(false);

  if (loading && !isStreaming) {
    return (
      <Card className="border-border/30 bg-card/50">
        <CardHeader className="pb-3">
          <Skeleton className="h-5 w-36" />
        </CardHeader>
        <CardContent className="space-y-2">
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-3/4" />
          <Skeleton className="h-4 w-5/6" />
        </CardContent>
      </Card>
    );
  }

  // During streaming: show accumulated text with cursor + gradient fade
  if (isStreaming && streamingText) {
    return (
      <Card className="border-border/30 bg-card/50 animate-slide-up stagger-6">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
            Clinician Summary
            <FallbackBadge reasons={getCardFallbacks(dataGaps, "summary")} />
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-clinical-cyan">
              <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
            </svg>
            <span className="text-[10px] font-mono text-clinical-cyan/60 animate-pulse">generating</span>
            <span className="text-[11px] font-mono text-muted-foreground/60 ml-auto">
              {streamingText.split(/\s+/).filter(Boolean).length} words
            </span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="relative max-h-32 overflow-hidden">
            <div className="text-sm leading-relaxed text-foreground/90 font-sans [&_strong]:font-semibold [&_strong]:text-foreground [&_ul]:list-disc [&_ul]:pl-4 [&_ol]:list-decimal [&_ol]:pl-4 [&_p]:mb-1.5 [&_li]:mb-0.5">
              <ReactMarkdown>{streamingText}</ReactMarkdown>
              <span className="inline-block w-[2px] h-[1em] bg-clinical-cyan ml-0.5 align-middle animate-blink" />
            </div>
            <div className="absolute inset-x-0 bottom-0 h-8 bg-gradient-to-t from-card/90 to-transparent pointer-events-none" />
          </div>
        </CardContent>
      </Card>
    );
  }

  // Final summary display — capped with "Read more" toggle
  if (!summary) return null;

  return (
    <Card className="border-border/30 bg-card/50 animate-slide-up stagger-6">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
          Clinician Summary
          <FallbackBadge reasons={getCardFallbacks(dataGaps, "summary")} />
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-clinical-cyan">
            <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
          </svg>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className={`relative ${!expanded ? "max-h-48 overflow-hidden" : ""}`}>
          <div className="text-sm leading-relaxed text-foreground/90 font-sans [&_strong]:font-semibold [&_strong]:text-foreground [&_ul]:list-disc [&_ul]:pl-4 [&_ol]:list-decimal [&_ol]:pl-4 [&_p]:mb-1.5 [&_li]:mb-0.5">
            <ReactMarkdown>{summary}</ReactMarkdown>
          </div>
          {!expanded && (
            <div className="absolute inset-x-0 bottom-0 h-12 bg-gradient-to-t from-card to-transparent pointer-events-none" />
          )}
        </div>
        {!expanded && (
          <button
            onClick={() => setExpanded(true)}
            className="text-xs text-clinical-cyan hover:text-clinical-cyan/80 font-medium mt-1 transition-colors"
          >
            Read more
          </button>
        )}
        {expanded && (
          <button
            onClick={() => setExpanded(false)}
            className="text-xs text-clinical-cyan hover:text-clinical-cyan/80 font-medium mt-1 transition-colors"
          >
            Show less
          </button>
        )}
      </CardContent>
    </Card>
  );
}

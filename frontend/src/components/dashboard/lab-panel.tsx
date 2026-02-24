import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { FallbackBadge } from "@/components/ui/fallback-badge";
import { useState } from "react";
import type { LabValues, LabValue } from "@/types/pipeline";
import { formatLabValue, isAbnormal } from "@/lib/format";
import { getCardFallbacks } from "@/lib/fallback-utils";

interface LabPanelProps {
  labs: LabValues | null;
  loading?: boolean;
  dataGaps?: string[];
}

const PRIMARY_LABS: { key: keyof LabValues; label: string }[] = [
  { key: "crp", label: "CRP" },
  { key: "wcc", label: "WCC" },
  { key: "urea", label: "Urea" },
  { key: "creatinine", label: "Creatinine" },
  { key: "haemoglobin", label: "Haemoglobin" },
  { key: "platelets", label: "Platelets" },
];

const SECONDARY_LABS: { key: keyof LabValues; label: string }[] = [
  { key: "neutrophils", label: "Neutrophils" },
  { key: "egfr", label: "eGFR" },
  { key: "sodium", label: "Sodium" },
  { key: "potassium", label: "Potassium" },
  { key: "procalcitonin", label: "Procalcitonin" },
  { key: "lactate", label: "Lactate" },
];

function LabRow({ label, value }: { label: string; value: LabValue }) {
  const abnormal = isAbnormal(value);
  return (
    <div
      className={`grid grid-cols-[1fr_auto_auto] gap-2 px-2 py-1 rounded-sm transition-colors ${
        abnormal ? "bg-severity-high/5" : ""
      }`}
    >
      <span className={`text-xs font-medium ${abnormal ? "text-severity-high" : "text-foreground"}`}>
        {abnormal && <span className="inline-block w-1.5 h-1.5 rounded-full bg-severity-high mr-1.5 align-middle" />}
        {label}
      </span>
      <span className={`text-xs font-mono text-right w-28 ${abnormal ? "text-severity-high font-semibold" : "text-foreground"}`}>
        {formatLabValue(value)}
      </span>
      <span className="text-[11px] font-mono text-muted-foreground/60 text-right w-20">
        {value.reference_range}
      </span>
    </div>
  );
}

export function LabPanel({ labs, loading, dataGaps }: LabPanelProps) {
  const [expanded, setExpanded] = useState(false);

  if (loading) {
    return (
      <Card className="border-border/30 bg-card/50">
        <CardHeader className="pb-3">
          <Skeleton className="h-5 w-24" />
        </CardHeader>
        <CardContent className="space-y-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-6 w-full" />
          ))}
        </CardContent>
      </Card>
    );
  }

  if (!labs) return null;

  const primaryEntries = PRIMARY_LABS
    .filter(({ key }) => labs[key] != null)
    .map(({ key, label }) => ({ key, label, value: labs[key] as LabValue }));

  const secondaryEntries = SECONDARY_LABS
    .filter(({ key }) => labs[key] != null)
    .map(({ key, label }) => ({ key, label, value: labs[key] as LabValue }));

  return (
    <Card className="border-border/30 bg-card/50 animate-slide-up stagger-2">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
          Key Bloods
          <FallbackBadge reasons={getCardFallbacks(dataGaps, "labs")} />
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-0.5">
          {/* Header */}
          <div className="grid grid-cols-[1fr_auto_auto] gap-2 px-2 py-1 text-[10px] font-mono text-muted-foreground/60 uppercase tracking-wider">
            <span>Test</span>
            <span className="text-right w-28">Result</span>
            <span className="text-right w-20">Ref</span>
          </div>

          {/* Primary labs — always visible */}
          {primaryEntries.map(({ key, label, value }) => (
            <LabRow key={key} label={label} value={value} />
          ))}

          {/* Secondary labs — collapsible */}
          {secondaryEntries.length > 0 && (
            <Collapsible open={expanded} onOpenChange={setExpanded}>
              <CollapsibleTrigger className="flex items-center gap-1.5 text-[11px] text-muted-foreground hover:text-foreground transition-colors w-full px-2 pt-1.5">
                <svg
                  width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
                  className={`transition-transform ${expanded ? "rotate-90" : ""}`}
                >
                  <polyline points="9 18 15 12 9 6" />
                </svg>
                {expanded ? "Show less" : `+ ${secondaryEntries.length} more`}
              </CollapsibleTrigger>
              <CollapsibleContent className="space-y-0.5 mt-0.5">
                {secondaryEntries.map(({ key, label, value }) => (
                  <LabRow key={key} label={label} value={value} />
                ))}
              </CollapsibleContent>
            </Collapsible>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

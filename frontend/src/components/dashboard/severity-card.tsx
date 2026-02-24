import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { FallbackBadge } from "@/components/ui/fallback-badge";
import type { CURB65Score } from "@/types/pipeline";
import { getSeverityConfig } from "@/lib/severity-colors";
import { getCardFallbacks } from "@/lib/fallback-utils";

interface SeverityCardProps {
  score: CURB65Score | null;
  loading?: boolean;
  dataGaps?: string[];
}

const CURB_LABELS = [
  { key: "c", label: "C", full: "Confusion" },
  { key: "u", label: "U", full: "Urea > 7" },
  { key: "r", label: "R", full: "RR ≥ 30" },
  { key: "b", label: "B", full: "BP low" },
  { key: "age_65", label: "65", full: "Age ≥ 65" },
] as const;

export function SeverityCard({ score, loading, dataGaps }: SeverityCardProps) {
  if (loading) {
    return (
      <Card className="border-border/30 bg-card/50">
        <CardHeader className="pb-3">
          <Skeleton className="h-5 w-32" />
        </CardHeader>
        <CardContent className="space-y-3">
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-8 w-full" />
        </CardContent>
      </Card>
    );
  }

  if (!score) return null;

  const config = getSeverityConfig(score.severity_tier);
  const totalScore = score.curb65 ?? score.crb65;
  const maxScore = score.curb65 != null ? 5 : 4;
  const scoreLabel = score.curb65 != null ? "CURB-65" : "CRB-65";

  return (
    <Card className={`border-border/30 bg-card/50 animate-slide-up ${config.glow}`}>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium text-muted-foreground flex items-center justify-between">
          <span className="flex items-center gap-2">
            Severity Assessment
            <FallbackBadge reasons={getCardFallbacks(dataGaps, "severity")} />
          </span>
          <Badge className={`text-xs font-mono ${config.badge} border`}>
            {config.label}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {/* Big score */}
        <div className="flex items-center gap-4">
          <div className={`text-4xl font-mono font-bold ${config.text}`}>
            {totalScore}
          </div>
          <div className="text-sm text-muted-foreground">
            <div className="font-medium">{scoreLabel}</div>
            <div className="text-xs">out of {maxScore}</div>
          </div>
        </div>

        {/* CURB-65 boxes */}
        <div className="flex gap-1.5">
          {CURB_LABELS.map(({ key, label, full }) => {
            const val = score[key as keyof CURB65Score] as number;
            const active = val === 1;
            return (
              <div
                key={key}
                title={`${full}: ${active ? "Present" : "Absent"}`}
                className={`flex-1 py-1.5 rounded-md border text-center transition-all ${
                  active
                    ? `${config.bg} ${config.border} ${config.text}`
                    : "bg-secondary/30 border-border/20 text-muted-foreground/40"
                }`}
              >
                <div className="font-mono text-sm font-bold">{label}</div>
                <div className="text-[9px] font-mono mt-0.5">{active ? "1" : "0"}</div>
              </div>
            );
          })}
        </div>

        {/* Missing variables */}
        {score.missing_variables.length > 0 && (
          <div className="text-[11px] text-severity-moderate/80">
            Missing: {score.missing_variables.join(", ")}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

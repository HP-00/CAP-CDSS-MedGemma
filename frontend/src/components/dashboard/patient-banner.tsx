import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { FallbackBadge } from "@/components/ui/fallback-badge";
import type { PatientDemographics, ClinicalExamFindings, CURB65Score } from "@/types/pipeline";
import { formatAge } from "@/lib/format";
import { getSeverityConfig } from "@/lib/severity-colors";
import { getCardFallbacks } from "@/lib/fallback-utils";

interface PatientBannerProps {
  demographics: PatientDemographics | null;
  clinicalExam?: ClinicalExamFindings | null;
  curb65Score?: CURB65Score | null;
  loading?: boolean;
  dataGaps?: string[];
}

function VitalChip({
  label,
  value,
  abnormal,
}: {
  label: string;
  value: string;
  abnormal: boolean;
}) {
  return (
    <span
      className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono ${
        abnormal
          ? "bg-severity-high/15 text-severity-high font-bold"
          : "bg-secondary/50 text-muted-foreground"
      }`}
    >
      <span className="opacity-60">{label}</span>
      {value}
    </span>
  );
}

export function PatientBanner({ demographics, clinicalExam, curb65Score, loading, dataGaps }: PatientBannerProps) {
  if (loading) {
    return (
      <Card className="border-border/30 bg-card/50">
        <CardContent className="py-4 px-6">
          <div className="flex items-center gap-4">
            <Skeleton className="h-10 w-10 rounded-md" />
            <div className="flex-1 space-y-2">
              <Skeleton className="h-5 w-48" />
              <Skeleton className="h-4 w-96" />
            </div>
            <div className="shrink-0 flex items-center gap-1.5">
              <Skeleton className="h-5 w-12" />
              <Skeleton className="h-5 w-12" />
              <Skeleton className="h-5 w-14" />
              <Skeleton className="h-5 w-12" />
              <Skeleton className="h-5 w-12" />
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!demographics) return null;

  const allergies = demographics.allergies ?? [];
  const comorbidities = demographics.comorbidities ?? [];
  const hasAllergies = allergies.length > 0 && !(
    allergies.length === 1 &&
    (allergies[0] === "NKDA" || (typeof allergies[0] === "object" && allergies[0]?.drug === "NKDA"))
  );

  const obs = clinicalExam?.observations;

  return (
    <Card className="border-border/30 bg-card/50 animate-slide-up">
      <CardContent className="py-4 px-6">
        <div className="flex items-start gap-4">
          {/* Patient icon */}
          <div className="h-10 w-10 rounded-md bg-clinical-cyan/10 border border-clinical-cyan/20 flex items-center justify-center shrink-0">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-clinical-cyan">
              <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2" />
              <circle cx="12" cy="7" r="4" />
            </svg>
          </div>

          <div className="flex-1 min-w-0">
            {/* Name + age line */}
            <div className="flex items-center gap-3 flex-wrap">
              <span className="text-base font-semibold">
                {demographics.age != null
                  ? formatAge(demographics.age, demographics.sex ?? undefined)
                  : "—"}
              </span>
              {demographics.smoking_status && (
                <Badge variant="outline" className="text-[10px] font-mono border-border/30">
                  {demographics.smoking_status} smoker
                </Badge>
              )}
              {demographics.pregnancy && (
                <Badge variant="outline" className="text-[10px] font-mono border-severity-moderate/30 text-severity-moderate">
                  Pregnant
                </Badge>
              )}
              {demographics.oral_tolerance === false && (
                <Badge variant="outline" className="text-[10px] font-mono border-severity-high/30 text-severity-high">
                  Oral intolerance
                </Badge>
              )}
              <FallbackBadge reasons={getCardFallbacks(dataGaps, "patient-banner")} />
            </div>

            {/* Tags row */}
            <div className="flex items-center gap-2 mt-2 flex-wrap">
              {/* Allergies */}
              {hasAllergies ? (
                allergies.map((a, i) => {
                  const drug = typeof a === "string" ? a : a.drug ?? "Unknown";
                  const reaction = typeof a === "object" ? a.reaction_type : undefined;
                  return (
                    <Badge key={i} className="text-[10px] font-mono bg-severity-high/15 text-severity-high border border-severity-high/30">
                      ALLERGY: {drug}{reaction ? ` (${reaction})` : ""}
                    </Badge>
                  );
                })
              ) : (
                <Badge variant="outline" className="text-[10px] font-mono border-severity-low/30 text-severity-low">
                  NKDA
                </Badge>
              )}

              {/* Comorbidities */}
              {comorbidities.map((c, i) => (
                <Badge key={i} variant="outline" className="text-[10px] font-mono border-border/30 text-muted-foreground">
                  {c}
                </Badge>
              ))}
            </div>
          </div>

          {/* Right side: vitals + severity */}
          <div className="shrink-0 flex items-center gap-1.5 flex-wrap justify-end">
            {obs && (
              <>
                <VitalChip label="HR" value={`${obs.heart_rate}`} abnormal={obs.heart_rate > 100} />
                <VitalChip label="RR" value={`${obs.respiratory_rate}`} abnormal={obs.respiratory_rate >= 30} />
                <VitalChip label="BP" value={`${obs.systolic_bp}/${obs.diastolic_bp}`} abnormal={obs.systolic_bp < 90 || obs.diastolic_bp <= 60} />
                <VitalChip label="SpO2" value={`${obs.spo2}%`} abnormal={obs.spo2 < 92} />
                <VitalChip label="T" value={`${obs.temperature}\u00b0`} abnormal={obs.temperature > 38.3 || obs.temperature < 36} />
              </>
            )}
            {curb65Score && (
              <Badge className={`${getSeverityConfig(curb65Score.severity_tier).badge} text-[10px] font-mono border`}>
                CURB-65: {curb65Score.curb65 ?? curb65Score.crb65}/5
              </Badge>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

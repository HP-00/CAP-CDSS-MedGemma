import type { ClinicalExamFindings } from "@/types/pipeline";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface VitalSignsCardProps {
  clinicalExam: ClinicalExamFindings | null;
}

interface VitalReadout {
  label: string;
  value: string;
  unit: string;
  abnormal: boolean;
}

function getVitalReadouts(
  obs: NonNullable<ClinicalExamFindings["observations"]>,
): VitalReadout[] {
  return [
    {
      label: "HR",
      value: String(obs.heart_rate),
      unit: "bpm",
      abnormal: obs.heart_rate > 100,
    },
    {
      label: "RR",
      value: String(obs.respiratory_rate),
      unit: "/min",
      abnormal: obs.respiratory_rate >= 30,
    },
    {
      label: "SBP",
      value: String(obs.systolic_bp),
      unit: "mmHg",
      abnormal: obs.systolic_bp < 90,
    },
    {
      label: "DBP",
      value: String(obs.diastolic_bp),
      unit: "mmHg",
      abnormal: obs.diastolic_bp <= 60,
    },
    {
      label: "SpO\u2082",
      value: String(obs.spo2),
      unit: "%",
      abnormal: obs.spo2 < 92,
    },
    {
      label: "Temp",
      value: obs.temperature.toFixed(1),
      unit: "\u00b0C",
      abnormal: obs.temperature > 38.3 || obs.temperature < 36,
    },
  ];
}

export function VitalSignsCard({ clinicalExam }: VitalSignsCardProps) {
  const obs = clinicalExam?.observations;

  if (!obs) {
    return (
      <Card className="border-border/30">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">Vital Signs</CardTitle>
        </CardHeader>
        <CardContent className="flex items-center justify-center h-36 text-xs text-muted-foreground">
          No vital signs data
        </CardContent>
      </Card>
    );
  }

  const readouts = getVitalReadouts(obs);

  return (
    <Card className="border-border/30">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium">Vital Signs</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        <div className="grid grid-cols-3 gap-2">
          {readouts.map((r) => (
            <div
              key={r.label}
              className={`p-2 rounded-md border ${
                r.abnormal
                  ? "bg-severity-high/10 border-severity-high/25"
                  : "bg-secondary/30 border-border/20"
              }`}
            >
              <div className="text-[10px] uppercase font-mono text-muted-foreground">
                {r.label}
              </div>
              <div
                className={`text-sm font-mono ${
                  r.abnormal ? "font-bold text-severity-high" : ""
                }`}
              >
                {r.value}
                <span className="text-[10px] text-muted-foreground ml-0.5">
                  {r.unit}
                </span>
              </div>
            </div>
          ))}
        </div>
        {obs.supplemental_o2 && (
          <Badge
            variant="outline"
            className="text-[10px] font-mono border-clinical-cyan/30 text-clinical-cyan"
          >
            O{"\u2082"}: {obs.supplemental_o2}
          </Badge>
        )}
      </CardContent>
    </Card>
  );
}

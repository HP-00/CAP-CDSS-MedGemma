import type { RawCaseData } from "@/types/case-data";
import { Badge } from "@/components/ui/badge";

interface LabsDrawerProps {
  data: RawCaseData;
}

const ABNORMAL_THRESHOLDS: Record<string, { low?: number; high?: number }> = {
  crp: { high: 10 },
  wcc: { low: 4, high: 11 },
  urea: { high: 7 },
  creatinine: { high: 120 },
  sodium: { low: 135, high: 145 },
  potassium: { low: 3.5, high: 5.0 },
  albumin: { low: 35 },
  haemoglobin: { low: 120 },
  platelets: { low: 150, high: 400 },
  lactate: { high: 2 },
  procalcitonin: { high: 0.25 },
};

function isAbnormal(key: string, value: number): boolean {
  const k = key.toLowerCase().replace(/\s/g, "");
  const threshold = ABNORMAL_THRESHOLDS[k];
  if (!threshold) return false;
  if (threshold.low !== undefined && value < threshold.low) return true;
  if (threshold.high !== undefined && value > threshold.high) return true;
  return false;
}

export function LabsDrawer({ data }: LabsDrawerProps) {
  const rawReport = data.labReport;
  const admissionLabs = data.admissionLabs;

  // labReport can be a string or an object {format, content, source}
  const labReportText: string | null =
    typeof rawReport === "string"
      ? rawReport
      : rawReport && typeof rawReport === "object" && "content" in rawReport
        ? (rawReport as { content: string }).content
        : null;

  if (!labReportText && !admissionLabs) {
    return (
      <div className="flex items-center justify-center h-40 text-sm text-muted-foreground">
        No lab results available for this case.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Structured lab values table */}
      {admissionLabs && Object.keys(admissionLabs).length > 0 && (
        <div>
          <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
            Admission Labs
          </h3>
          <div className="rounded-lg border border-border/50 overflow-hidden">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-border/30 bg-muted/30">
                  <th className="text-left py-1.5 px-3 font-medium text-muted-foreground">Test</th>
                  <th className="text-right py-1.5 px-3 font-medium text-muted-foreground">Value</th>
                  <th className="text-right py-1.5 px-3 font-medium text-muted-foreground">Flag</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(admissionLabs).map(([key, value]) => {
                  const abnormal = isAbnormal(key, value);
                  return (
                    <tr key={key} className="border-b border-border/20 last:border-b-0">
                      <td className="py-1.5 px-3 capitalize">{key.replace(/_/g, " ")}</td>
                      <td className={`py-1.5 px-3 text-right font-mono ${abnormal ? "text-severity-high font-semibold" : ""}`}>
                        {value}
                      </td>
                      <td className="py-1.5 px-3 text-right">
                        {abnormal && (
                          <Badge variant="outline" className="text-[9px] border-severity-high/40 text-severity-high">
                            Abnormal
                          </Badge>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Raw lab report text */}
      {labReportText && (
        <div>
          <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
            Raw Lab Report
          </h3>
          <pre className="text-[11px] leading-relaxed font-mono bg-muted/30 rounded-lg border border-border/50 p-3 whitespace-pre-wrap overflow-x-auto">
            {labReportText}
          </pre>
        </div>
      )}
    </div>
  );
}

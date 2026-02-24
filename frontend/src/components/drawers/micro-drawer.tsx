import type { RawCaseData, MicroResult } from "@/types/case-data";
import { Badge } from "@/components/ui/badge";

interface MicroDrawerProps {
  data: RawCaseData;
}

const SUSCEPTIBILITY_COLORS: Record<string, string> = {
  S: "bg-green-500/10 text-green-600 border-green-500/30",
  I: "bg-amber-500/10 text-amber-600 border-amber-500/30",
  R: "bg-red-500/10 text-red-600 border-red-500/30",
};

function renderAntibiogram(antibiogram: Record<string, string>) {
  const entries = Object.entries(antibiogram);
  if (entries.length === 0) return null;

  return (
    <div className="mt-2">
      <div className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground mb-1">
        Antibiogram
      </div>
      <div className="rounded border border-border/30 overflow-hidden">
        <table className="w-full text-xs">
          <thead>
            <tr className="bg-muted/30 border-b border-border/30">
              <th className="text-left py-1 px-2 font-medium text-muted-foreground">Antibiotic</th>
              <th className="text-center py-1 px-2 font-medium text-muted-foreground w-16">Result</th>
            </tr>
          </thead>
          <tbody>
            {entries.map(([drug, result]) => (
              <tr key={drug} className="border-b border-border/20 last:border-b-0">
                <td className="py-1 px-2 capitalize">{drug.replace(/_/g, " ")}</td>
                <td className="py-1 px-2 text-center">
                  <Badge
                    variant="outline"
                    className={`text-[9px] font-semibold ${SUSCEPTIBILITY_COLORS[result] ?? "border-border/40 text-muted-foreground"}`}
                  >
                    {result}
                  </Badge>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function MicroDrawer({ data }: MicroDrawerProps) {
  const results = data.microResults;

  if (!results || results.length === 0) {
    return (
      <div className="flex items-center justify-center h-40 text-sm text-muted-foreground">
        No microbiology results available for this case.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {results.map((result: MicroResult, i: number) => (
        <div key={i} className="rounded-lg border border-border/50 p-3">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs font-semibold text-foreground">{result.organism}</span>
            <Badge
              variant="outline"
              className={`text-[9px] ${
                result.status === "positive" || result.status === "final"
                  ? "border-severity-high/40 text-severity-high"
                  : "border-border/40 text-muted-foreground"
              }`}
            >
              {result.status}
            </Badge>
          </div>
          <div className="text-[10px] text-muted-foreground">
            Test: {(result.testType ?? result.test_type)?.replace(/_/g, " ") ?? "Unknown"}
          </div>
          {result.antibiogram && renderAntibiogram(result.antibiogram)}
        </div>
      ))}
    </div>
  );
}

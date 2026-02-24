import { useState } from "react";
import type { RawCaseData } from "@/types/case-data";
import { Badge } from "@/components/ui/badge";

interface CxrDrawerProps {
  data: RawCaseData;
  caseId?: string;
}

export function CxrDrawer({ data, caseId }: CxrDrawerProps) {
  const cxr = data.cxrFindings;
  const [imgError, setImgError] = useState(false);
  const imageUrl = caseId ? `/api/case/${caseId}/cxr-image` : null;

  const entries = cxr ? Object.entries(cxr) : [];

  return (
    <div className="space-y-3">
      {/* CXR image */}
      {imageUrl && !imgError && (
        <div className="rounded-lg border border-border/50 overflow-hidden bg-black/40">
          <img
            src={imageUrl}
            alt="Chest X-Ray"
            className="w-full object-contain max-h-64"
            onError={() => setImgError(true)}
          />
        </div>
      )}

      {entries.map(([key, value]) => (
        <div key={key} className="rounded-lg border border-border/50 p-3">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              {key.replace(/_/g, " ")}
            </span>
            {typeof value === "boolean" && (
              <Badge
                variant="outline"
                className={`text-[10px] ${
                  value
                    ? "border-severity-high/40 text-severity-high"
                    : "border-border/40 text-muted-foreground"
                }`}
              >
                {value ? "Present" : "Absent"}
              </Badge>
            )}
          </div>
          {typeof value === "string" && (
            <p className="text-xs text-foreground leading-relaxed">{value}</p>
          )}
          {typeof value === "object" && value !== null && !Array.isArray(value) && (
            <div className="space-y-1 mt-1">
              {Object.entries(value as Record<string, unknown>).map(([subKey, subVal]) => (
                <div key={subKey} className="flex items-start gap-2 text-xs">
                  <span className="text-muted-foreground min-w-[100px] shrink-0">
                    {subKey.replace(/_/g, " ")}:
                  </span>
                  <span className="text-foreground">{String(subVal)}</span>
                </div>
              ))}
            </div>
          )}
          {Array.isArray(value) && (
            <ul className="space-y-0.5 mt-1">
              {(value as unknown[]).map((item, i) => (
                <li key={i} className="text-xs text-foreground pl-2 border-l-2 border-clinical-cyan/30">
                  {String(item)}
                </li>
              ))}
            </ul>
          )}
        </div>
      ))}
    </div>
  );
}

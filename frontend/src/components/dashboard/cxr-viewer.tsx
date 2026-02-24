import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { FallbackBadge } from "@/components/ui/fallback-badge";
import { useState } from "react";
import type { CXRFindings } from "@/types/pipeline";
import { getCardFallbacks } from "@/lib/fallback-utils";

interface CXRViewerProps {
  findings: CXRFindings | null;
  imageUrl?: string | null;
  loading?: boolean;
  dataGaps?: string[];
}

const FINDING_KEYS = ["consolidation", "pleural_effusion", "cardiomegaly", "edema", "atelectasis"] as const;

function BoundingBoxOverlays({ boxes }: { boxes: { box: number[]; label: string; color: string }[] }) {
  return (
    <>
      {boxes.map((bb, i) => {
        const [x1, y1, x2, y2] = bb.box;
        return (
          <div
            key={i}
            className="absolute border-2 rounded-sm pointer-events-none"
            style={{
              left: `${(x1 / 896) * 100}%`,
              top: `${(y1 / 896) * 100}%`,
              width: `${((x2 - x1) / 896) * 100}%`,
              height: `${((y2 - y1) / 896) * 100}%`,
              borderColor: bb.color,
              boxShadow: `0 0 8px color-mix(in oklch, ${bb.color} 25%, transparent)`,
            }}
          >
            <span
              className="absolute -top-5 left-0 text-[9px] font-mono px-1 rounded-sm"
              style={{ backgroundColor: bb.color, color: "var(--background)" }}
            >
              {bb.label}
            </span>
          </div>
        );
      })}
    </>
  );
}

function BoxToggleButton({ active, onClick, className }: { active: boolean; onClick: () => void; className?: string }) {
  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <button
            onClick={(e) => { e.stopPropagation(); onClick(); }}
            className={`inline-flex items-center justify-center rounded-md p-1 transition-colors ${
              active
                ? "text-blue-400 hover:text-blue-300"
                : "text-muted-foreground/50 hover:text-muted-foreground"
            } ${className ?? ""}`}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="3" width="18" height="18" rx="2" />
              <rect x="7" y="7" width="10" height="10" rx="1" strokeDasharray={active ? "0" : "2 2"} />
            </svg>
          </button>
        </TooltipTrigger>
        <TooltipContent side="bottom">
          {active ? "Hide findings" : "Show findings"}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

export function CXRViewer({ findings, imageUrl, loading, dataGaps }: CXRViewerProps) {
  const [longOpen, setLongOpen] = useState(false);
  const [enlarged, setEnlarged] = useState(false);
  const [showBoxes, setShowBoxes] = useState(false);

  if (loading) {
    return (
      <Card className="border-border/30 bg-card/50">
        <CardHeader className="pb-3">
          <Skeleton className="h-5 w-24" />
        </CardHeader>
        <CardContent>
          <Skeleton className="h-48 w-full rounded-md" />
        </CardContent>
      </Card>
    );
  }

  if (!findings) return null;

  const boundingBoxes: { box: number[]; label: string; color: string }[] = [];

  for (const key of FINDING_KEYS) {
    const f = findings[key];
    if (f && f.present && f.bounding_box) {
      boundingBoxes.push({
        box: f.bounding_box,
        label: key.replace("_", " "),
        color: key === "consolidation" ? "var(--severity-high)" : "var(--severity-moderate)",
      });
    }
  }

  return (
    <Card className="border-border/30 bg-card/50 animate-slide-up stagger-1">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
          Chest X-Ray
          {findings.image_quality && (
            <Badge variant="outline" className="text-[10px] font-mono border-border/30">
              {findings.image_quality.projection}
            </Badge>
          )}
          <FallbackBadge reasons={getCardFallbacks(dataGaps, "cxr")} />
          {boundingBoxes.length > 0 && (
            <BoxToggleButton active={showBoxes} onClick={() => setShowBoxes(!showBoxes)} />
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {imageUrl ? (
          <div
            className="relative h-48 bg-black/40 rounded-md overflow-hidden border border-border/20 cursor-pointer"
            onClick={() => setEnlarged(true)}
            title="Click to enlarge"
          >
            <img
              src={imageUrl}
              alt="Chest X-Ray"
              className="w-full h-full object-contain"
            />
            {showBoxes && boundingBoxes.length > 0 && <BoundingBoxOverlays boxes={boundingBoxes} />}
          </div>
        ) : (
          <div className="h-48 bg-secondary/20 rounded-md flex items-center justify-center border border-border/20">
            <div className="text-center text-muted-foreground/40">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" className="mx-auto mb-2">
                <rect x="3" y="3" width="18" height="18" rx="2" />
                <circle cx="8.5" cy="8.5" r="1.5" />
                <path d="M21 15l-5-5L5 21" />
              </svg>
              <span className="text-xs">No CXR image uploaded</span>
            </div>
          </div>
        )}

        {/* Longitudinal comparison — collapsed by default */}
        {findings.longitudinal_comparison && (
          <Collapsible open={longOpen} onOpenChange={setLongOpen}>
            <CollapsibleTrigger className="flex items-center gap-1.5 text-[11px] text-muted-foreground hover:text-foreground transition-colors w-full">
              <svg
                width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
                className={`transition-transform ${longOpen ? "rotate-90" : ""}`}
              >
                <polyline points="9 18 15 12 9 6" />
              </svg>
              Longitudinal comparison
            </CollapsibleTrigger>
            <CollapsibleContent className="space-y-1 mt-1.5">
              {Object.entries(findings.longitudinal_comparison).map(([key, val]) => (
                <div key={key} className="flex items-center justify-between text-xs">
                  <span className="text-muted-foreground capitalize">{key.replace("_", " ")}</span>
                  <Badge variant="outline" className={`text-[10px] font-mono ${
                    val.change === "new" || val.change === "worsened"
                      ? "text-severity-high border-severity-high/30"
                      : val.change === "improved"
                        ? "text-severity-low border-severity-low/30"
                        : "text-muted-foreground border-border/30"
                  }`}>
                    {val.change}
                  </Badge>
                </div>
              ))}
            </CollapsibleContent>
          </Collapsible>
        )}
      </CardContent>

      {/* Enlarge modal */}
      {imageUrl && (
        <Dialog open={enlarged} onOpenChange={setEnlarged}>
          <DialogContent className="max-w-3xl p-2">
            <DialogTitle className="sr-only">Chest X-Ray — Enlarged View</DialogTitle>
            <div className="relative bg-black/40 rounded-md overflow-hidden" style={{ maxHeight: "80vh" }}>
              {boundingBoxes.length > 0 && (
                <BoxToggleButton
                  active={showBoxes}
                  onClick={() => setShowBoxes(!showBoxes)}
                  className="absolute top-2 right-2 z-10 bg-black/50 backdrop-blur-sm rounded-md"
                />
              )}
              <img
                src={imageUrl}
                alt="Chest X-Ray — Enlarged"
                className="w-full h-full object-contain"
                style={{ maxHeight: "80vh" }}
              />
              {showBoxes && boundingBoxes.length > 0 && <BoundingBoxOverlays boxes={boundingBoxes} />}
            </div>
          </DialogContent>
        </Dialog>
      )}
    </Card>
  );
}

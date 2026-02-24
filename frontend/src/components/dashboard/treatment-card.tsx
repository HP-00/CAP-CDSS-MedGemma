import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { useState } from "react";
import type { AntibioticRecommendation, InvestigationPlan } from "@/types/pipeline";
import { getSeverityConfig } from "@/lib/severity-colors";

interface TreatmentCardProps {
  recommendation: AntibioticRecommendation | null;
  investigations: InvestigationPlan | null;
  loading?: boolean;
}

export function TreatmentCard({ recommendation, investigations, loading }: TreatmentCardProps) {
  const [stewOpen, setStewOpen] = useState(false);
  const [invOpen, setInvOpen] = useState(false);

  if (loading) {
    return (
      <Card className="border-border/30 bg-card/50">
        <CardHeader className="pb-3">
          <Skeleton className="h-5 w-40" />
        </CardHeader>
        <CardContent className="space-y-3">
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-8 w-full" />
        </CardContent>
      </Card>
    );
  }

  if (!recommendation) return null;

  const tierConfig = getSeverityConfig(
    recommendation.severity_tier as "low" | "moderate" | "high"
  );

  const stewardshipCount = recommendation.stewardship_notes?.length ?? 0;
  const investigationEntries = investigations ? Object.entries(investigations) : [];

  return (
    <Card className="border-border/30 bg-card/50 animate-slide-up stagger-4">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
          Treatment Pathway
          <Badge className={`text-[10px] font-mono ${tierConfig.badge} border`}>
            {recommendation.severity_tier}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {/* Primary antibiotic */}
        <div className="p-3 rounded-md bg-clinical-cyan/5 border border-clinical-cyan/20">
          <div className="text-xs text-muted-foreground font-medium mb-1">First-line antibiotic</div>
          <div className="text-base font-semibold text-clinical-cyan">{recommendation.first_line}</div>
          <div className="text-xs font-mono text-muted-foreground mt-1">{recommendation.dose_route}</div>
        </div>

        {/* Conditional adjustment boxes */}
        <div className="grid grid-cols-1 gap-2 text-xs">
          {recommendation.allergy_adjustment && (
            <div className="p-2 rounded-sm bg-severity-high/5 border border-severity-high/10">
              <span className="text-severity-high font-medium">Allergy adjustment: </span>
              <span className="text-muted-foreground">{recommendation.allergy_adjustment}</span>
            </div>
          )}
          {recommendation.atypical_cover && (
            <div className="p-2 rounded-sm bg-secondary/30 border border-border/10">
              <span className="font-medium text-foreground">Atypical cover: </span>
              <span className="text-muted-foreground">{recommendation.atypical_cover}</span>
            </div>
          )}
          {recommendation.renal_adjustment && (
            <div className="p-2 rounded-sm bg-secondary/30 border border-border/10">
              <span className="font-medium text-foreground">Renal: </span>
              <span className="text-muted-foreground">{recommendation.renal_adjustment}</span>
            </div>
          )}
          {recommendation.corticosteroid_recommendation && (
            <div className="p-2 rounded-sm bg-secondary/30 border border-border/10">
              <span className="font-medium text-foreground">Corticosteroid: </span>
              <span className="text-muted-foreground">{recommendation.corticosteroid_recommendation}</span>
            </div>
          )}
        </div>

        {/* Evidence reference */}
        {recommendation.evidence_reference && (
          <Badge variant="outline" className="text-[9px] font-mono border-border/30 text-muted-foreground">
            {recommendation.evidence_reference}
          </Badge>
        )}

        {/* Stewardship notes — collapsed by default */}
        {stewardshipCount > 0 && (
          <Collapsible open={stewOpen} onOpenChange={setStewOpen}>
            <CollapsibleTrigger className="flex items-center gap-1.5 text-[11px] text-muted-foreground hover:text-foreground transition-colors w-full border-t border-border/20 pt-2">
              <svg
                width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
                className={`transition-transform ${stewOpen ? "rotate-90" : ""}`}
              >
                <polyline points="9 18 15 12 9 6" />
              </svg>
              Stewardship ({stewardshipCount})
            </CollapsibleTrigger>
            <CollapsibleContent className="mt-1.5">
              {recommendation.stewardship_notes.map((note, i) => (
                <div key={i} className="text-[11px] text-muted-foreground pl-2 border-l border-clinical-teal/30 py-0.5">
                  {note}
                </div>
              ))}
            </CollapsibleContent>
          </Collapsible>
        )}

        {/* Investigations — collapsed by default */}
        {investigationEntries.length > 0 && (
          <Collapsible open={invOpen} onOpenChange={setInvOpen}>
            <CollapsibleTrigger className="flex items-center gap-1.5 text-[11px] text-muted-foreground hover:text-foreground transition-colors w-full border-t border-border/20 pt-2">
              <svg
                width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
                className={`transition-transform ${invOpen ? "rotate-90" : ""}`}
              >
                <polyline points="9 18 15 12 9 6" />
              </svg>
              Investigations ({investigationEntries.length})
            </CollapsibleTrigger>
            <CollapsibleContent className="mt-1.5">
              <div className="grid grid-cols-2 gap-1.5">
                {investigationEntries.map(([key, val]) => {
                  if (!val) return null;
                  return (
                    <div key={key} className="flex items-center gap-1.5 text-[11px]">
                      <div className={`h-1.5 w-1.5 rounded-full ${val.recommended ? "bg-severity-low" : "bg-muted-foreground/30"}`} />
                      <span className={val.recommended ? "text-foreground" : "text-muted-foreground/50"}>
                        {key.replace(/_/g, " ")}
                      </span>
                    </div>
                  );
                })}
              </div>
            </CollapsibleContent>
          </Collapsible>
        )}
      </CardContent>
    </Card>
  );
}

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { useState } from "react";
import type { MonitoringPlan } from "@/types/pipeline";
import { formatPercentChange } from "@/lib/format";

interface MonitoringCardProps {
  plan: MonitoringPlan | null;
  loading?: boolean;
}

export function MonitoringCard({ plan, loading }: MonitoringCardProps) {
  const [dischargeOpen, setDischargeOpen] = useState(false);

  if (loading) {
    return (
      <Card className="border-border/30 bg-card/50">
        <CardHeader className="pb-3">
          <Skeleton className="h-5 w-32" />
        </CardHeader>
        <CardContent className="space-y-3">
          <Skeleton className="h-8 w-full" />
          <Skeleton className="h-8 w-full" />
        </CardContent>
      </Card>
    );
  }

  if (!plan) return null;

  const dischargeMet = plan.discharge_criteria_met;
  const dischargeDetails = plan.discharge_criteria_details;
  const dischargeMetCount = dischargeDetails
    ? Object.values(dischargeDetails).filter(Boolean).length
    : null;
  const dischargeTotalCount = dischargeDetails
    ? Object.keys(dischargeDetails).length
    : null;

  return (
    <Card className="border-border/30 bg-card/50 animate-slide-up stagger-5">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
          Monitoring & Discharge
          {dischargeMet != null && (
            <Badge className={`text-[10px] font-mono border ${
              dischargeMet
                ? "bg-severity-low/20 text-severity-low border-severity-low/30"
                : "bg-severity-moderate/20 text-severity-moderate border-severity-moderate/30"
            }`}>
              {dischargeMet ? "Discharge criteria met" : "Discharge criteria not met"}
            </Badge>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {/* Key timing info */}
        <div className="grid grid-cols-2 gap-3">
          <div className="p-2 rounded-md bg-secondary/30 border border-border/10">
            <div className="text-[10px] text-muted-foreground font-medium">CRP Repeat</div>
            <div className="text-xs font-mono text-foreground mt-0.5">{plan.crp_repeat_timing}</div>
          </div>
          <div className="p-2 rounded-md bg-secondary/30 border border-border/10">
            <div className="text-[10px] text-muted-foreground font-medium">Next Review</div>
            <div className="text-xs font-mono text-foreground mt-0.5">{plan.next_review}</div>
          </div>
        </div>

        {/* CRP Trend */}
        {plan.crp_trend && (
          <div className="p-2 rounded-md border border-border/20 bg-secondary/10">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">CRP Trend</span>
              <Badge variant="outline" className={`text-[10px] font-mono ${
                plan.crp_trend.trend === "improving"
                  ? "text-severity-low border-severity-low/30"
                  : plan.crp_trend.trend === "worsening"
                    ? "text-severity-high border-severity-high/30"
                    : "text-severity-moderate border-severity-moderate/30"
              }`}>
                {plan.crp_trend.trend}
              </Badge>
            </div>
            <div className="flex items-baseline gap-3 mt-1.5">
              <div className="text-xs">
                <span className="text-muted-foreground">Admission: </span>
                <span className="font-mono">{plan.crp_trend.admission_value}</span>
              </div>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-muted-foreground">
                <path d="M5 12h14M12 5l7 7-7 7" />
              </svg>
              <div className="text-xs">
                <span className="text-muted-foreground">Current: </span>
                <span className="font-mono">{plan.crp_trend.current_value}</span>
              </div>
              <span className={`text-xs font-mono font-semibold ${
                plan.crp_trend.percent_change < 0 ? "text-severity-low" : "text-severity-high"
              }`}>
                {formatPercentChange(plan.crp_trend.percent_change)}
              </span>
            </div>
            {plan.crp_trend.flag_senior_review && (
              <div className="mt-1.5 text-[11px] text-severity-high">
                Senior review recommended
              </div>
            )}
          </div>
        )}

        {/* Treatment response */}
        {plan.treatment_response && (
          <div className={`p-2 rounded-md border ${
            plan.treatment_response.reassess_needed
              ? "bg-severity-moderate/5 border-severity-moderate/20"
              : "bg-severity-low/5 border-severity-low/20"
          }`}>
            <div className="flex items-center gap-2">
              <div className={`h-2 w-2 rounded-full ${
                plan.treatment_response.reassess_needed ? "bg-severity-moderate" : "bg-severity-low"
              }`} />
              <span className="text-xs font-medium">
                {plan.treatment_response.reassess_needed ? "Reassessment needed" : "Responding to treatment"}
              </span>
            </div>
            {plan.treatment_response.actions?.length > 0 && (
              <div className="mt-1.5 pl-4 space-y-0.5">
                {plan.treatment_response.actions.map((a, i) => (
                  <div key={i} className="text-[11px] text-muted-foreground">• {a}</div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Treatment duration */}
        {plan.treatment_duration && (
          <div className="text-xs text-muted-foreground border-t border-border/20 pt-2">
            <span className="font-medium">Duration: </span>
            {plan.treatment_duration.extend_recommended
              ? `Extension recommended (${plan.treatment_duration.criteria_met} criteria met)`
              : "Standard duration"}
          </div>
        )}

        {/* Discharge criteria details — collapsed by default */}
        {dischargeDetails && (
          <Collapsible open={dischargeOpen} onOpenChange={setDischargeOpen}>
            <CollapsibleTrigger className="flex items-center gap-1.5 text-[11px] text-muted-foreground hover:text-foreground transition-colors w-full border-t border-border/20 pt-2">
              <svg
                width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
                className={`transition-transform ${dischargeOpen ? "rotate-90" : ""}`}
              >
                <polyline points="9 18 15 12 9 6" />
              </svg>
              Discharge criteria ({dischargeMetCount}/{dischargeTotalCount} met)
            </CollapsibleTrigger>
            <CollapsibleContent className="mt-1.5">
              <div className="grid grid-cols-2 gap-1">
                {Object.entries(dischargeDetails).map(([key, met]) => (
                  <div key={key} className="flex items-center gap-1.5 text-[11px]">
                    <div className={`h-1.5 w-1.5 rounded-full ${met ? "bg-severity-low" : "bg-severity-high"}`} />
                    <span className={met ? "text-muted-foreground" : "text-severity-high/80"}>
                      {key.replace(/_/g, " ")}
                    </span>
                  </div>
                ))}
              </div>
            </CollapsibleContent>
          </Collapsible>
        )}

        {/* CXR follow-up */}
        {plan.cxr_follow_up && (
          <div className="text-xs text-muted-foreground">
            <span className="font-medium">CXR follow-up: </span>{plan.cxr_follow_up}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { useState } from "react";

interface DataGapsCardProps {
  gaps: string[];
}

export function DataGapsCard({ gaps }: DataGapsCardProps) {
  const [open, setOpen] = useState(false);

  if (gaps.length === 0) {
    return (
      <Collapsible>
        <CollapsibleTrigger className="flex items-center gap-2 text-xs text-severity-low/60 hover:text-severity-low transition-colors px-2 py-1">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M22 11.08V12a10 10 0 11-5.93-9.14" />
            <polyline points="22 4 12 14.01 9 11.01" />
          </svg>
          No data gaps identified
        </CollapsibleTrigger>
      </Collapsible>
    );
  }

  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <CollapsibleTrigger className="flex items-center gap-2 text-xs text-severity-moderate hover:text-severity-moderate/80 transition-colors px-2 py-1 w-full">
        <svg
          width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
          className={`transition-transform ${open ? "rotate-90" : ""}`}
        >
          <polyline points="9 18 15 12 9 6" />
        </svg>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
          <line x1="12" y1="9" x2="12" y2="13" />
          <line x1="12" y1="17" x2="12.01" y2="17" />
        </svg>
        {gaps.length} data gap{gaps.length !== 1 ? "s" : ""} identified
      </CollapsibleTrigger>
      <CollapsibleContent>
        <Card className="border-border/30 bg-card/50 mt-2">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-severity-moderate">Data Gaps</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-1">
              {gaps.map((gap, i) => (
                <div key={i} className="flex items-start gap-2 text-xs text-muted-foreground">
                  <div className="h-1.5 w-1.5 rounded-full bg-severity-moderate mt-1.5 shrink-0" />
                  {gap}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </CollapsibleContent>
    </Collapsible>
  );
}

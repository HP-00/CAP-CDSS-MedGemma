import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";

interface FallbackBadgeProps {
  reasons: string[];
}

export function FallbackBadge({ reasons }: FallbackBadgeProps) {
  if (reasons.length === 0) return null;

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[10px] font-mono leading-none border bg-amber-500/15 text-amber-500 border-amber-500/30 cursor-default select-none">
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="shrink-0">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            Fallback
          </span>
        </TooltipTrigger>
        <TooltipContent side="bottom" className="max-w-xs">
          <div className="space-y-1">
            {reasons.map((reason, i) => (
              <div key={i} className="text-xs">{reason}</div>
            ))}
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

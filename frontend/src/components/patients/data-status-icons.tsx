import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";

interface DataStatusIconsProps {
  data: {
    cxr: boolean;
    labs: boolean;
    fhir: boolean;
    micro: boolean;
    docs: boolean;
  };
}

const ITEMS = [
  {
    key: "cxr" as const,
    label: "Chest X-ray",
    icon: (
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="3" width="18" height="18" rx="2" />
        <circle cx="12" cy="12" r="3" />
      </svg>
    ),
  },
  {
    key: "labs" as const,
    label: "Lab Results",
    icon: (
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M9 3h6v7l4 8H5l4-8V3z" />
        <path d="M9 3h6" />
      </svg>
    ),
  },
  {
    key: "fhir" as const,
    label: "FHIR Bundle",
    icon: (
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <ellipse cx="12" cy="5" rx="9" ry="3" />
        <path d="M3 5v14a9 3 0 0 0 18 0V5" />
        <path d="M3 12a9 3 0 0 0 18 0" />
      </svg>
    ),
  },
  {
    key: "micro" as const,
    label: "Microbiology",
    icon: (
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="2" />
        <path d="M12 2v4" /><path d="M12 18v4" />
        <path d="m4.93 4.93 2.83 2.83" /><path d="m16.24 16.24 2.83 2.83" />
        <path d="M2 12h4" /><path d="M18 12h4" />
        <path d="m4.93 19.07 2.83-2.83" /><path d="m16.24 7.76 2.83-2.83" />
      </svg>
    ),
  },
  {
    key: "docs" as const,
    label: "Documents",
    icon: (
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z" />
        <path d="M14 2v6h6" />
        <path d="M8 13h8" />
        <path d="M8 17h5" />
      </svg>
    ),
  },
];

export function DataStatusIcons({ data }: DataStatusIconsProps) {
  return (
    <TooltipProvider delayDuration={200}>
      <div className="flex items-center gap-1.5">
        {ITEMS.map((item) => {
          const available = data[item.key];
          return (
            <Tooltip key={item.key}>
              <TooltipTrigger asChild>
                <span
                  className={`inline-flex items-center justify-center h-6 w-6 rounded ${
                    available
                      ? "text-clinical-cyan bg-clinical-cyan/10"
                      : "text-muted-foreground/30"
                  }`}
                >
                  {item.icon}
                </span>
              </TooltipTrigger>
              <TooltipContent side="bottom" className="text-xs">
                {item.label}: {available ? "Available" : "Not available"}
              </TooltipContent>
            </Tooltip>
          );
        })}
      </div>
    </TooltipProvider>
  );
}

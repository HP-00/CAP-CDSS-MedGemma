import { useState, useEffect, useCallback } from "react";
import { NavLink } from "react-router-dom";
import { Badge } from "@/components/ui/badge";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { useBatchContext } from "@/stores/batch-store";
import { useModeContext } from "@/stores/mode-store";
import { useCaseData } from "@/hooks/use-case-data";
import { DataSourceDrawer } from "@/components/drawers/data-source-drawer";
import type { DataSourceType } from "@/types/case-data";

const NAV_ITEMS = [
  {
    to: "/",
    label: "Dashboard",
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="3" width="7" height="7" rx="1" />
        <rect x="14" y="3" width="7" height="7" rx="1" />
        <rect x="3" y="14" width="7" height="7" rx="1" />
        <rect x="14" y="14" width="7" height="7" rx="1" />
      </svg>
    ),
  },
  {
    to: "/analysis",
    label: "Analysis",
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
      </svg>
    ),
  },
];

const DATA_SOURCE_ITEMS: { key: DataSourceType; label: string; icon: React.ReactNode }[] = [
  {
    key: "cxr",
    label: "Chest X-ray",
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="3" width="18" height="18" rx="2" />
        <circle cx="12" cy="12" r="3" />
      </svg>
    ),
  },
  {
    key: "labs",
    label: "Lab Results",
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d="M9 3h6v7l4 8H5l4-8V3z" />
        <path d="M9 3h6" />
      </svg>
    ),
  },
  {
    key: "fhir",
    label: "FHIR Bundle",
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <ellipse cx="12" cy="5" rx="9" ry="3" />
        <path d="M3 5v14a9 3 0 0 0 18 0V5" />
        <path d="M3 12a9 3 0 0 0 18 0" />
      </svg>
    ),
  },
  {
    key: "micro",
    label: "Microbiology",
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="2" />
        <path d="M12 2v4" /><path d="M12 18v4" />
        <path d="m4.93 4.93 2.83 2.83" /><path d="m16.24 16.24 2.83 2.83" />
        <path d="M2 12h4" /><path d="M18 12h4" />
        <path d="m4.93 19.07 2.83-2.83" /><path d="m16.24 7.76 2.83-2.83" />
      </svg>
    ),
  },
  {
    key: "docs",
    label: "Documents",
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z" />
        <path d="M14 2v6h6" />
        <path d="M8 13h8" />
        <path d="M8 17h5" />
      </svg>
    ),
  },
];

export function AppSidebar() {
  const { demoMode, setDemoMode } = useModeContext();
  const { activePatientId, patients } = useBatchContext();
  const { data: caseData, loading: caseLoading, error: caseError, fetchCaseData, clearData } = useCaseData();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [activeSource, setActiveSource] = useState<DataSourceType | null>(null);

  const activePatient = activePatientId
    ? patients.find((p) => p.caseId === activePatientId)
    : null;

  // Clear data when active patient changes
  useEffect(() => {
    if (!activePatientId) {
      clearData();
      setDrawerOpen(false);
    }
  }, [activePatientId, clearData]);

  const handleSourceClick = useCallback(
    (source: DataSourceType) => {
      if (!activePatientId || !activePatient) return;

      // Check if this source is available
      if (!activePatient.dataAvailable[source]) return;

      fetchCaseData(activePatientId);
      setActiveSource(source);
      setDrawerOpen(true);
    },
    [activePatientId, activePatient, fetchCaseData],
  );

  return (
    <TooltipProvider delayDuration={200}>
      <aside className="sidebar-fixed-dark w-14 shrink-0 flex flex-col items-center py-4 gap-2 h-screen sticky top-0 border-r border-white/5">
        {/* Brand mark */}
        <div className="h-9 w-9 rounded-lg bg-clinical-cyan/20 border border-clinical-cyan/30 flex items-center justify-center mb-4">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="oklch(0.72 0.12 220)" strokeWidth="2">
            <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
          </svg>
        </div>

        {/* Nav icons */}
        <nav className="flex flex-col gap-1">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) =>
                `relative h-10 w-10 flex items-center justify-center rounded-lg transition-all ${
                  isActive
                    ? "bg-white/10 text-white before:absolute before:left-0 before:top-1.5 before:bottom-1.5 before:w-[3px] before:rounded-r before:bg-clinical-cyan"
                    : "text-white/40 hover:text-white/70 hover:bg-white/5"
                }`
              }
              title={item.label}
            >
              {item.icon}
            </NavLink>
          ))}
        </nav>

        {/* Data source divider + icons */}
        <div className="w-7 border-t border-white/10 mt-2 mb-1" />

        <nav className="flex flex-col gap-1">
          {DATA_SOURCE_ITEMS.map((item) => {
            const hasPatient = !!activePatient;
            const isAvailable = hasPatient && activePatient.dataAvailable[item.key];

            let colorClass: string;
            if (!hasPatient) {
              colorClass = "text-white/15 cursor-not-allowed";
            } else if (!isAvailable) {
              colorClass = "text-white/25 cursor-not-allowed";
            } else {
              colorClass = "text-clinical-cyan hover:bg-white/5 cursor-pointer";
            }

            return (
              <Tooltip key={item.key}>
                <TooltipTrigger asChild>
                  <button
                    className={`h-9 w-9 flex items-center justify-center rounded-lg transition-all ${colorClass}`}
                    onClick={() => handleSourceClick(item.key)}
                    disabled={!isAvailable}
                    aria-label={item.label}
                  >
                    {item.icon}
                  </button>
                </TooltipTrigger>
                <TooltipContent side="right" className="text-xs">
                  {item.label}
                  {!hasPatient && " (no patient selected)"}
                  {hasPatient && !isAvailable && " (not available)"}
                </TooltipContent>
              </Tooltip>
            );
          })}
        </nav>

        {/* Spacer */}
        <div className="flex-1" />

        {/* Footer: mode toggle + version */}
        <div className="flex flex-col items-center gap-2 pb-1">
          {/* Live mode label */}
          <span
            className={`text-[9px] font-mono uppercase tracking-wider transition-colors duration-200 ${
              demoMode ? "text-amber-400" : "text-green-400"
            }`}
          >
            {demoMode ? "DEMO" : "INFER"}
          </span>

          {/* Toggle switch */}
          <Tooltip>
            <TooltipTrigger asChild>
              <button
                onClick={() => setDemoMode(!demoMode)}
                className={`relative w-[32px] h-[18px] rounded-full border transition-colors duration-200 ${
                  demoMode
                    ? "bg-amber-400/25 border-amber-400/40"
                    : "bg-green-400/25 border-green-400/40"
                }`}
                aria-label={demoMode ? "Demo Mode (Mock)" : "Inference Mode (GPU)"}
              >
                <span
                  className={`absolute top-[1px] w-[14px] h-[14px] rounded-full transition-all duration-200 ${
                    demoMode
                      ? "left-[15px] bg-amber-400"
                      : "left-[1px] bg-green-400"
                  }`}
                />
              </button>
            </TooltipTrigger>
            <TooltipContent side="right" className="text-xs">
              {demoMode ? "Demo Mode (Mock)" : "Inference Mode"}
            </TooltipContent>
          </Tooltip>

          <Badge
            variant="outline"
            className="text-[8px] font-mono border-white/10 text-white/30 px-1 py-0"
          >
            v0.1
          </Badge>
        </div>
      </aside>

      {/* Data source drawer — rendered via portal, not constrained by sidebar */}
      <DataSourceDrawer
        open={drawerOpen}
        onOpenChange={setDrawerOpen}
        sourceType={activeSource}
        data={caseData}
        loading={caseLoading}
        error={caseError}
        caseId={activePatientId ?? undefined}
      />
    </TooltipProvider>
  );
}

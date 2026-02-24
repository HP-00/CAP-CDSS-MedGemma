import type { LabValues, LabValue } from "@/types/pipeline";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { isAbnormal } from "@/lib/format";

interface LabHeatmapProps {
  labValues: LabValues | null;
}

interface LabCell {
  key: keyof LabValues;
  label: string;
  fullName: string;
}

const LAB_CELLS: LabCell[] = [
  { key: "crp", label: "CRP", fullName: "C-Reactive Protein" },
  { key: "wcc", label: "WCC", fullName: "White Cell Count" },
  { key: "neutrophils", label: "Neut", fullName: "Neutrophils" },
  { key: "urea", label: "Urea", fullName: "Urea" },
  { key: "creatinine", label: "Creat", fullName: "Creatinine" },
  { key: "egfr", label: "eGFR", fullName: "Estimated GFR" },
  { key: "sodium", label: "Na+", fullName: "Sodium" },
  { key: "potassium", label: "K+", fullName: "Potassium" },
  { key: "haemoglobin", label: "Hb", fullName: "Haemoglobin" },
  { key: "platelets", label: "Plt", fullName: "Platelets" },
  { key: "procalcitonin", label: "PCT", fullName: "Procalcitonin" },
  { key: "lactate", label: "Lact", fullName: "Lactate" },
  { key: "bnp", label: "BNP", fullName: "B-type Natriuretic Peptide" },
];

function LabCellItem({ lab, cell }: { lab: LabValue; cell: LabCell }) {
  const abnormal = isAbnormal(lab);
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <div
          className={`px-2 py-1.5 rounded border text-center cursor-default min-w-0 ${
            abnormal
              ? "bg-severity-high/10 border-severity-high/20"
              : "bg-severity-low/8 border-severity-low/20"
          }`}
        >
          <div className="text-[10px] uppercase font-mono text-muted-foreground leading-none mb-1">
            {cell.label}
          </div>
          <div
            className={`text-sm font-mono leading-none ${
              abnormal ? "font-bold text-severity-high" : ""
            }`}
          >
            {lab.value}
          </div>
          <div className="text-[9px] text-muted-foreground font-mono mt-0.5 truncate">
            {lab.unit}
          </div>
        </div>
      </TooltipTrigger>
      <TooltipContent>
        <p className="font-mono text-xs">
          {cell.fullName}: {lab.value} {lab.unit}
        </p>
        <p className="text-[10px] text-muted-foreground">
          Ref: {lab.reference_range}
        </p>
      </TooltipContent>
    </Tooltip>
  );
}

export function LabHeatmap({ labValues }: LabHeatmapProps) {
  if (!labValues) {
    return (
      <Card className="border-border/30">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">Lab Values</CardTitle>
        </CardHeader>
        <CardContent className="flex items-center justify-center h-20 text-xs text-muted-foreground">
          No lab data available
        </CardContent>
      </Card>
    );
  }

  const presentCells = LAB_CELLS.filter(
    (c) => labValues[c.key] !== undefined,
  );

  if (presentCells.length === 0) {
    return (
      <Card className="border-border/30">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">Lab Values</CardTitle>
        </CardHeader>
        <CardContent className="flex items-center justify-center h-20 text-xs text-muted-foreground">
          No lab data available
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-border/30">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium flex items-center justify-between">
          Lab Values
          <span className="flex items-center gap-2 text-[10px] font-normal text-muted-foreground">
            <span className="flex items-center gap-1">
              <span className="inline-block h-2 w-2 rounded-full bg-severity-low/60" />
              Normal
            </span>
            <span className="flex items-center gap-1">
              <span className="inline-block h-2 w-2 rounded-full bg-severity-high/60" />
              Abnormal
            </span>
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <TooltipProvider>
          <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 gap-2">
            {presentCells.map((cell) => (
              <LabCellItem
                key={cell.key}
                lab={labValues[cell.key]!}
                cell={cell}
              />
            ))}
          </div>
        </TooltipProvider>
      </CardContent>
    </Card>
  );
}

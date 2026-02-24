import type { PipelineState } from "@/types/pipeline";
import { CURB65Radar } from "./curb65-radar";
import { VitalSignsCard } from "./vital-signs-card";
import { LabHeatmap } from "./lab-heatmap";

interface GraphicalViewProps {
  state: PipelineState;
}

export function GraphicalView({ state }: GraphicalViewProps) {
  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        <LabHeatmap labValues={state.labValues} />
        <CURB65Radar score={state.curb65Score} />
        <VitalSignsCard clinicalExam={state.clinicalExam} />
      </div>
    </div>
  );
}

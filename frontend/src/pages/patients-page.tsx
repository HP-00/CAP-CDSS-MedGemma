import { useNavigate } from "react-router-dom";
import { useBatchContext } from "@/stores/batch-store";
import { useModeContext } from "@/stores/mode-store";
import { PatientTable } from "@/components/patients/patient-table";
import { PageTransition } from "@/components/layout/page-transition";
import { Button } from "@/components/ui/button";

export function PatientsPage() {
  const { patients, patientsLoading, selectedIds, toggleSelection, toggleAll, startBatch, batch, activePatientId, setActivePatient } =
    useBatchContext();
  const { demoMode } = useModeContext();
  const navigate = useNavigate();

  const selectedCount = selectedIds.size;
  const isBatchRunning = batch.status === "running";

  const handleAnalyse = () => {
    const ids = Array.from(selectedIds);
    startBatch(ids, demoMode);
    navigate("/analysis");
  };

  return (
    <PageTransition className="flex-1 flex flex-col min-h-0">
      {/* Toolbar */}
      <div className="shrink-0 border-b border-border/50 px-6 py-3 flex items-center justify-between bg-background/50 backdrop-blur-sm">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">Patient List</h1>
          <p className="text-xs text-muted-foreground mt-0.5">
            {patients.length} patients on ward &middot; Select patients for CAP analysis
          </p>
        </div>
        <div className="flex items-center gap-3">
          {selectedCount > 0 && (
            <Button
              onClick={handleAnalyse}
              disabled={isBatchRunning}
              className="bg-clinical-cyan hover:bg-clinical-cyan/90 text-white font-medium"
            >
              Analyse Selected ({selectedCount})
            </Button>
          )}
        </div>
      </div>

      {/* Table */}
      <div className="flex-1 overflow-y-auto px-6 py-4">
        {patientsLoading ? (
          <div className="flex items-center justify-center h-40 text-sm text-muted-foreground">
            Loading patients...
          </div>
        ) : (
          <PatientTable
            patients={patients}
            selectedIds={selectedIds}
            onToggleSelection={toggleSelection}
            onToggleAll={toggleAll}
            activePatientId={activePatientId}
            onSelectActive={setActivePatient}
          />
        )}
      </div>
    </PageTransition>
  );
}

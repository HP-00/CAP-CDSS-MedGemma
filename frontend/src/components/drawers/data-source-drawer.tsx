import type { RawCaseData, DataSourceType } from "@/types/case-data";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { CxrDrawer } from "./cxr-drawer";
import { LabsDrawer } from "./labs-drawer";
import { FhirDrawer } from "./fhir-drawer";
import { MicroDrawer } from "./micro-drawer";
import { DocsDrawer } from "./docs-drawer";

interface DataSourceDrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  sourceType: DataSourceType | null;
  data: RawCaseData | null;
  loading: boolean;
  error: string | null;
  caseId?: string;
}

const SOURCE_META: Record<DataSourceType, { title: string; description: string }> = {
  cxr: { title: "Chest X-ray", description: "CXR findings and imaging data" },
  labs: { title: "Lab Results", description: "Laboratory values and reports" },
  fhir: { title: "FHIR Bundle", description: "Electronic health record data" },
  micro: { title: "Microbiology", description: "Culture and sensitivity results" },
  docs: { title: "Clinical Documents", description: "Clerking notes and clinical documentation" },
};

export function DataSourceDrawer({
  open,
  onOpenChange,
  sourceType,
  data,
  loading,
  error,
  caseId,
}: DataSourceDrawerProps) {
  const meta = sourceType ? SOURCE_META[sourceType] : null;
  const isDocs = sourceType === "docs";

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader className="px-5 pt-5 pb-3 border-b border-border/50 shrink-0">
          <DialogTitle className="text-sm">{meta?.title ?? "Data Source"}</DialogTitle>
          <DialogDescription className="text-xs">
            {meta?.description ?? ""}
          </DialogDescription>
        </DialogHeader>

        {isDocs ? (
          <div className="flex-1 overflow-y-auto min-h-0">
            {loading && (
              <div className="flex items-center justify-center h-40 text-sm text-muted-foreground">
                <div className="flex items-center gap-2">
                  <div className="h-4 w-4 border-2 border-clinical-cyan/30 border-t-clinical-cyan rounded-full animate-spin" />
                  Loading data...
                </div>
              </div>
            )}
            {error && (
              <div className="flex items-center justify-center h-40 text-sm text-severity-high">
                {error}
              </div>
            )}
            {!loading && !error && data && <DocsDrawer data={data} />}
            {!loading && !error && !data && (
              <div className="flex items-center justify-center h-40 text-sm text-muted-foreground">
                Select a patient to view data.
              </div>
            )}
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto p-5 min-h-0">
            {loading && (
              <div className="flex items-center justify-center h-40 text-sm text-muted-foreground">
                <div className="flex items-center gap-2">
                  <div className="h-4 w-4 border-2 border-clinical-cyan/30 border-t-clinical-cyan rounded-full animate-spin" />
                  Loading data...
                </div>
              </div>
            )}
            {error && (
              <div className="flex items-center justify-center h-40 text-sm text-severity-high">
                {error}
              </div>
            )}
            {!loading && !error && data && sourceType === "cxr" && <CxrDrawer data={data} caseId={caseId} />}
            {!loading && !error && data && sourceType === "labs" && <LabsDrawer data={data} />}
            {!loading && !error && data && sourceType === "fhir" && <FhirDrawer data={data} />}
            {!loading && !error && data && sourceType === "micro" && <MicroDrawer data={data} />}
            {!loading && !error && !data && (
              <div className="flex items-center justify-center h-40 text-sm text-muted-foreground">
                Select a patient to view data.
              </div>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

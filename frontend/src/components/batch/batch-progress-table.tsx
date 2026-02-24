import { useNavigate } from "react-router-dom";
import { useBatchContext } from "@/stores/batch-store";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { BatchNodeCards } from "./batch-node-cards";
import { getSeverityConfig } from "@/lib/severity-colors";

export function BatchProgressTable() {
  const { batch, patients, getResult } = useBatchContext();
  const navigate = useNavigate();

  if (batch.queue.length === 0) {
    return (
      <div className="text-center py-12 text-muted-foreground text-sm">
        No patients queued for analysis. Go back to select patients.
      </div>
    );
  }

  return (
    <div className="patient-table">
      <Table>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead className="emr-label">Patient</TableHead>
            <TableHead className="emr-label">Status</TableHead>
            <TableHead className="emr-label">Progress</TableHead>
            <TableHead className="emr-label">Result</TableHead>
            <TableHead className="emr-label w-24">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {batch.queue.map((caseId, index) => {
            const patient = patients.find((p) => p.caseId === caseId);
            const result = getResult(caseId);
            const isRunning = result?.status === "running";
            const isComplete = result?.status === "complete";
            const isError = result?.status === "error";
            const isQueued = !isRunning && !isComplete && !isError;

            const severityConfig =
              isComplete && result?.curb65Score
                ? getSeverityConfig(result.curb65Score.severity_tier)
                : null;

            return (
              <TableRow key={caseId}>
                <TableCell>
                  <div className="font-medium text-[13px]">
                    {patient?.name ?? caseId}
                  </div>
                  <div className="text-[11px] text-muted-foreground">
                    {patient?.bed}
                  </div>
                </TableCell>
                <TableCell>
                  {isQueued && (
                    <Badge variant="outline" className="text-[10px] text-muted-foreground">
                      Queued ({index + 1})
                    </Badge>
                  )}
                  {isRunning && (
                    <Badge className="text-[10px] bg-severity-moderate/20 text-severity-moderate border border-severity-moderate/30">
                      <span className="inline-block h-1.5 w-1.5 rounded-full bg-severity-moderate animate-pulse mr-1" />
                      Running
                    </Badge>
                  )}
                  {isComplete && (
                    <Badge className="text-[10px] bg-severity-low/20 text-severity-low border border-severity-low/30">
                      Complete
                    </Badge>
                  )}
                  {isError && (
                    <Badge className="text-[10px] bg-severity-high/20 text-severity-high border border-severity-high/30">
                      Error
                    </Badge>
                  )}
                </TableCell>
                <TableCell>
                  {(isRunning || isComplete) && result ? (
                    <BatchNodeCards state={result} />
                  ) : (
                    <span className="text-xs text-muted-foreground/40">—</span>
                  )}
                </TableCell>
                <TableCell>
                  {severityConfig && result?.curb65Score && (
                    <Badge className={`${severityConfig.badge} text-[10px]`}>
                      CURB-65: {result.curb65Score.curb65 ?? result.curb65Score.crb65} &middot; {severityConfig.label}
                    </Badge>
                  )}
                </TableCell>
                <TableCell>
                  {(isComplete || isError) && (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-xs text-clinical-cyan hover:text-clinical-cyan"
                      onClick={() => navigate(`/patient/${caseId}`)}
                    >
                      View Detail &rarr;
                    </Button>
                  )}
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}

import type { PatientRow } from "@/types/patient";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { DataStatusIcons } from "./data-status-icons";
import { getSeverityConfig } from "@/lib/severity-colors";

interface PatientTableProps {
  patients: PatientRow[];
  selectedIds: Set<string>;
  onToggleSelection: (id: string) => void;
  onToggleAll: () => void;
  activePatientId: string | null;
  onSelectActive: (id: string) => void;
}

export function PatientTable({
  patients,
  selectedIds,
  onToggleSelection,
  onToggleAll,
  activePatientId,
  onSelectActive,
}: PatientTableProps) {
  const allSelected = patients.length > 0 && selectedIds.size === patients.length;

  return (
    <div className="patient-table">
      <Table>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead className="w-10">
              <Checkbox
                checked={allSelected}
                onCheckedChange={onToggleAll}
                aria-label="Select all patients"
              />
            </TableHead>
            <TableHead className="emr-label">Patient</TableHead>
            <TableHead className="emr-label">Age / Sex</TableHead>
            <TableHead className="emr-label">Bed</TableHead>
            <TableHead className="emr-label">Admission</TableHead>
            <TableHead className="emr-label">Primary Dx</TableHead>
            <TableHead className="emr-label">Data Available</TableHead>
            <TableHead className="emr-label">Status</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {patients.map((patient) => {
            const isSelected = selectedIds.has(patient.caseId);
            const isActive = activePatientId === patient.caseId;
            const severityConfig = patient.severityTier
              ? getSeverityConfig(patient.severityTier)
              : null;

            return (
              <TableRow
                key={patient.caseId}
                className={`cursor-pointer transition-colors ${
                  isSelected ? "selected bg-clinical-cyan/5 border-l-2 border-l-clinical-cyan" : ""
                } ${isActive && !isSelected ? "bg-clinical-teal/5" : ""}`}
                onClick={() => onSelectActive(patient.caseId)}
              >
                <TableCell onClick={(e) => e.stopPropagation()}>
                  <Checkbox
                    checked={isSelected}
                    onCheckedChange={() => onToggleSelection(patient.caseId)}
                    aria-label={`Select ${patient.name}`}
                  />
                </TableCell>
                <TableCell>
                  <div className={`font-medium text-[13px] ${isActive ? "text-clinical-cyan" : ""}`}>
                    {patient.name}
                  </div>
                </TableCell>
                <TableCell className="font-mono text-[13px]">
                  {patient.age}{patient.sex?.[0]}
                </TableCell>
                <TableCell className="font-mono text-[13px]">
                  {patient.bed}
                </TableCell>
                <TableCell className="text-[12px] text-muted-foreground">
                  {patient.admissionDate}
                </TableCell>
                <TableCell className="text-[11px] leading-snug">
                  {patient.primaryDx}
                </TableCell>
                <TableCell>
                  <DataStatusIcons data={patient.dataAvailable} />
                </TableCell>
                <TableCell>
                  {severityConfig ? (
                    <Badge className={`${severityConfig.badge} text-[10px]`}>
                      CURB-65: {patient.curb65Score} &middot; {severityConfig.label}
                    </Badge>
                  ) : (
                    <Badge variant="outline" className="text-[10px] text-muted-foreground border-border/40">
                      Ready
                    </Badge>
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

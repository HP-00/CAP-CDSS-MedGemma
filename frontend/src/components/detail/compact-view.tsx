import type { PipelineState } from "@/types/pipeline";
import type { PatientRow } from "@/types/patient";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { isAbnormal } from "@/lib/format";
import { getSeverityConfig } from "@/lib/severity-colors";

interface CompactViewProps {
  state: PipelineState;
  patient: PatientRow | null;
}

function VitalCell({ value, unit, abnormal }: { value: number | undefined; unit?: string; abnormal?: boolean }) {
  if (value === undefined) return <TableCell className="text-center text-muted-foreground text-xs">—</TableCell>;
  return (
    <TableCell className={`text-center font-mono text-xs ${abnormal ? "text-severity-high font-bold" : ""}`}>
      {value}{unit ?? ""}
    </TableCell>
  );
}

function LabCell({ value, abnormal }: { value: number | undefined; abnormal?: boolean }) {
  if (value === undefined) return <TableCell className="text-center text-muted-foreground text-xs">—</TableCell>;
  return (
    <TableCell className={`text-center font-mono text-xs ${abnormal ? "text-severity-high font-bold" : ""}`}>
      {value}{abnormal ? "*" : ""}
    </TableCell>
  );
}

export function CompactView({ state, patient }: CompactViewProps) {
  const { curb65Score, labValues, contradictions, antibioticRecommendation, clinicianSummary, clinicalExam, patientDemographics } = state;
  const severityConfig = curb65Score ? getSeverityConfig(curb65Score.severity_tier) : null;

  const obs = clinicalExam?.observations;
  const highAlerts = contradictions.filter((c) => c.confidence !== "low");

  // Vital abnormal checks (CURB-65 thresholds)
  const rrAbn = obs?.respiratory_rate !== undefined && obs.respiratory_rate >= 30;
  const bpAbn = obs !== undefined && (obs.systolic_bp < 90 || obs.diastolic_bp <= 60);
  const hrAbn = obs?.heart_rate !== undefined && obs.heart_rate > 100;
  const spo2Abn = obs?.spo2 !== undefined && obs.spo2 < 92;
  const tempAbn = obs?.temperature !== undefined && (obs.temperature > 38.3 || obs.temperature < 36);

  // Lab abnormal flags
  const crpAbn = labValues?.crp ? isAbnormal(labValues.crp) : false;
  const wccAbn = labValues?.wcc ? isAbnormal(labValues.wcc) : false;
  const ureaAbn = labValues?.urea ? isAbnormal(labValues.urea) : false;

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-4">
      <Table className="border border-border/30 rounded-lg overflow-hidden">
        <TableHeader>
          <TableRow className="patient-table">
            <TableHead className="text-xs font-semibold">Patient</TableHead>
            <TableHead className="text-xs font-semibold text-center">CURB-65</TableHead>
            <TableHead className="text-xs font-semibold text-center">RR</TableHead>
            <TableHead className="text-xs font-semibold text-center">BP</TableHead>
            <TableHead className="text-xs font-semibold text-center">HR</TableHead>
            <TableHead className="text-xs font-semibold text-center">SpO2</TableHead>
            <TableHead className="text-xs font-semibold text-center">Temp</TableHead>
            <TableHead className="text-xs font-semibold text-center">CRP</TableHead>
            <TableHead className="text-xs font-semibold text-center">WCC</TableHead>
            <TableHead className="text-xs font-semibold text-center">Urea</TableHead>
            <TableHead className="text-xs font-semibold">Treatment</TableHead>
            <TableHead className="text-xs font-semibold text-center">Alerts</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow>
            {/* Patient */}
            <TableCell className="text-xs font-medium whitespace-nowrap">
              {patient?.name ?? "—"}
              <span className="text-muted-foreground ml-1.5">
                {patient?.age ?? patientDemographics?.age ?? "—"}{patient?.sex?.[0] ?? patientDemographics?.sex?.[0] ?? ""}
              </span>
              <span className="text-muted-foreground ml-1.5">{patient?.bed ?? ""}</span>
            </TableCell>

            {/* CURB-65 */}
            <TableCell className="text-center">
              {curb65Score ? (
                <Badge className={`${severityConfig?.badge} text-[10px] font-mono`}>
                  {curb65Score.curb65 ?? curb65Score.crb65}/5
                </Badge>
              ) : "—"}
            </TableCell>

            {/* Vitals */}
            <VitalCell value={obs?.respiratory_rate} abnormal={rrAbn} />
            <TableCell className={`text-center font-mono text-xs ${bpAbn ? "text-severity-high font-bold" : ""}`}>
              {obs ? `${obs.systolic_bp}/${obs.diastolic_bp}` : "—"}
            </TableCell>
            <VitalCell value={obs?.heart_rate} abnormal={hrAbn} />
            <VitalCell value={obs?.spo2} unit="%" abnormal={spo2Abn} />
            <VitalCell value={obs?.temperature} unit="°" abnormal={tempAbn} />

            {/* Labs */}
            <LabCell value={labValues?.crp?.value} abnormal={crpAbn} />
            <LabCell value={labValues?.wcc?.value} abnormal={wccAbn} />
            <LabCell value={labValues?.urea?.value} abnormal={ureaAbn} />

            {/* Treatment */}
            <TableCell className="text-xs max-w-[160px] truncate">
              {antibioticRecommendation
                ? `${antibioticRecommendation.first_line} ${antibioticRecommendation.dose_route}`
                : "—"}
            </TableCell>

            {/* Alerts */}
            <TableCell className="text-center">
              {highAlerts.length > 0 ? (
                <Badge variant="destructive" className="text-[10px] font-mono">
                  {highAlerts.length}
                </Badge>
              ) : (
                <span className="text-xs text-muted-foreground">0</span>
              )}
            </TableCell>
          </TableRow>
        </TableBody>
      </Table>

      {/* Active Alerts bar */}
      {highAlerts.length > 0 && (
        <div className="flex items-center gap-2 px-3 py-2 rounded-md bg-severity-high/5 border border-severity-high/20">
          <span className="text-xs font-semibold text-severity-high shrink-0">Active Alerts</span>
          <div className="flex flex-wrap gap-1.5">
            {highAlerts.map((alert, i) => (
              <Badge key={i} variant="outline" className="text-[10px] border-severity-high/30 text-severity-high font-mono">
                {alert.rule_id}: {alert.pattern} ({alert.confidence})
              </Badge>
            ))}
          </div>
        </div>
      )}

      {/* Summary */}
      {clinicianSummary && (
        <div className="px-3 py-2 rounded-md bg-card/50 border border-border/30">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">AI Summary</span>
          <p className="text-xs font-mono leading-relaxed mt-1 text-foreground/80 whitespace-pre-wrap">
            {clinicianSummary.split("\n").slice(0, 3).join("\n")}
          </p>
        </div>
      )}
    </div>
  );
}

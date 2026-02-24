import { useState } from "react";
import type { RawCaseData, FhirResource } from "@/types/case-data";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Badge } from "@/components/ui/badge";

interface FhirDrawerProps {
  data: RawCaseData;
}

function pascalToTitleCase(str: string): string {
  return str.replace(/([a-z])([A-Z])/g, "$1 $2");
}

function groupByResourceType(entries: { resource: FhirResource }[]): Record<string, FhirResource[]> {
  const groups: Record<string, FhirResource[]> = {};
  for (const entry of entries) {
    const type = entry.resource.resourceType;
    if (!groups[type]) groups[type] = [];
    groups[type].push(entry.resource);
  }
  return groups;
}

function renderPatient(resource: FhirResource) {
  const name = (resource.name as { given?: string[]; family?: string }[])?.[0];
  return (
    <div className="space-y-1 text-xs">
      {name && (
        <div><span className="text-muted-foreground">Name:</span> {name.given?.join(" ")} {name.family}</div>
      )}
      {resource.gender ? <div><span className="text-muted-foreground">Gender:</span> {String(resource.gender)}</div> : null}
      {resource.birthDate ? <div><span className="text-muted-foreground">DOB:</span> {String(resource.birthDate)}</div> : null}
    </div>
  );
}

function renderCondition(resource: FhirResource) {
  const coding = (resource.code as { coding?: { display?: string }[] })?.coding?.[0];
  return (
    <div className="text-xs">
      <span className="text-foreground">{coding?.display ?? "Unknown condition"}</span>
      {resource.clinicalStatus ? (
        <Badge variant="outline" className="ml-2 text-[9px]">
          {String((resource.clinicalStatus as { coding?: { code?: string }[] })?.coding?.[0]?.code ?? "")}
        </Badge>
      ) : null}
    </div>
  );
}

function renderAllergy(resource: FhirResource) {
  const coding = (resource.code as { coding?: { display?: string }[] })?.coding?.[0];
  const criticality = resource.criticality as string | undefined;
  return (
    <div className="text-xs flex items-center gap-2">
      <span className="text-foreground">{coding?.display ?? "Unknown allergy"}</span>
      {criticality && (
        <Badge
          variant="outline"
          className={`text-[9px] ${
            criticality === "high"
              ? "border-severity-high/40 text-severity-high"
              : "border-border/40 text-muted-foreground"
          }`}
        >
          {criticality}
        </Badge>
      )}
    </div>
  );
}

function renderObservation(resource: FhirResource) {
  const coding = (resource.code as { coding?: { display?: string }[] })?.coding?.[0];
  const valueQty = resource.valueQuantity as { value?: number; unit?: string } | undefined;
  const valueStr = resource.valueString as string | undefined;
  return (
    <div className="text-xs flex items-center justify-between">
      <span className="text-muted-foreground">{coding?.display ?? "Observation"}</span>
      <span className="font-mono">
        {valueQty ? `${valueQty.value} ${valueQty.unit ?? ""}` : valueStr ?? "\u2014"}
      </span>
    </div>
  );
}

function renderMedicationRequest(resource: FhirResource) {
  const medText = (resource.medicationCodeableConcept as { text?: string })?.text;
  const medCoding = (resource.medicationCodeableConcept as { coding?: { display?: string }[] })?.coding?.[0]?.display;
  const dosage = (resource.dosageInstruction as { text?: string }[])?.[0]?.text;
  const status = resource.status as string | undefined;
  return (
    <div className="text-xs space-y-1">
      <div className="flex items-center gap-2">
        <span className="text-foreground font-medium">{medText ?? medCoding ?? "Unknown medication"}</span>
        {status && (
          <Badge variant="outline" className="text-[9px] border-border/40 text-muted-foreground">
            {status}
          </Badge>
        )}
      </div>
      {dosage && (
        <div className="text-muted-foreground">{dosage}</div>
      )}
    </div>
  );
}

function renderEncounter(resource: FhirResource) {
  const classInfo = resource.class as { display?: string; code?: string } | undefined;
  const period = resource.period as { start?: string; end?: string } | undefined;
  const reason = (resource.reasonCode as { coding?: { display?: string }[] }[])?.[0]?.coding?.[0]?.display;
  const status = resource.status as string | undefined;
  return (
    <div className="text-xs space-y-1">
      <div className="flex items-center gap-2">
        {classInfo && (
          <span className="text-foreground font-medium">{classInfo.display ?? classInfo.code ?? "Encounter"}</span>
        )}
        {status && (
          <Badge variant="outline" className="text-[9px] border-border/40 text-muted-foreground">
            {status}
          </Badge>
        )}
      </div>
      {period && (
        <div className="text-muted-foreground">
          {period.start && <span>From: {period.start}</span>}
          {period.end && <span className="ml-2">To: {period.end}</span>}
        </div>
      )}
      {reason && (
        <div className="text-muted-foreground">Reason: {reason}</div>
      )}
    </div>
  );
}

function renderGeneric(resource: FhirResource) {
  const { resourceType, ...rest } = resource;
  return (
    <pre className="text-[10px] font-mono bg-muted/20 rounded p-2 overflow-x-auto whitespace-pre-wrap max-h-40">
      {JSON.stringify(rest, null, 2)}
    </pre>
  );
}

const RENDERERS: Record<string, (r: FhirResource) => React.ReactNode> = {
  Patient: renderPatient,
  Condition: renderCondition,
  AllergyIntolerance: renderAllergy,
  Observation: renderObservation,
  MedicationRequest: renderMedicationRequest,
  Encounter: renderEncounter,
};

const SECTION_ORDER = ["Patient", "Condition", "AllergyIntolerance", "Observation", "MedicationRequest", "Encounter"];

export function FhirDrawer({ data }: FhirDrawerProps) {
  const bundle = data.fhirBundle;
  const [openSections, setOpenSections] = useState<Set<string>>(new Set(["Patient"]));

  if (!bundle?.entry?.length) {
    return (
      <div className="flex items-center justify-center h-40 text-sm text-muted-foreground">
        No FHIR bundle available for this case.
      </div>
    );
  }

  const grouped = groupByResourceType(bundle.entry);
  // Remove DocumentReference — handled by docs-drawer
  delete grouped["DocumentReference"];

  const sortedTypes = [
    ...SECTION_ORDER.filter((t) => grouped[t]),
    ...Object.keys(grouped).filter((t) => !SECTION_ORDER.includes(t)),
  ];

  const toggle = (type: string) => {
    setOpenSections((prev) => {
      const next = new Set(prev);
      if (next.has(type)) next.delete(type);
      else next.add(type);
      return next;
    });
  };

  return (
    <div className="space-y-2">
      <div className="text-[10px] text-muted-foreground mb-2">
        {bundle.entry.length} resources &middot; {sortedTypes.length} types
      </div>
      {sortedTypes.map((type) => {
        const resources = grouped[type];
        const renderer = RENDERERS[type] ?? renderGeneric;
        const isOpen = openSections.has(type);

        return (
          <Collapsible key={type} open={isOpen} onOpenChange={() => toggle(type)}>
            <CollapsibleTrigger className="flex items-center justify-between w-full rounded-lg border border-border/50 px-3 py-2 hover:bg-accent/50 transition-colors">
              <div className="flex items-center gap-2">
                <svg
                  width="12"
                  height="12"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.5"
                  className={`text-muted-foreground transition-transform ${isOpen ? "rotate-90" : ""}`}
                >
                  <path d="m9 18 6-6-6-6" />
                </svg>
                <span className="text-xs font-medium">{pascalToTitleCase(type)}</span>
              </div>
              <Badge variant="outline" className="text-[9px] border-border/40 text-muted-foreground">
                {resources.length}
              </Badge>
            </CollapsibleTrigger>
            <CollapsibleContent>
              <div className="mt-1 space-y-1.5 pl-3 border-l-2 border-border/30 ml-3">
                {resources.map((resource, i) => (
                  <div key={i} className="rounded border border-border/30 p-2">
                    {renderer(resource)}
                  </div>
                ))}
              </div>
            </CollapsibleContent>
          </Collapsible>
        );
      })}
    </div>
  );
}

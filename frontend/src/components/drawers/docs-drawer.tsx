import { useState } from "react";
import type { RawCaseData, FhirResource } from "@/types/case-data";

interface DocsDrawerProps {
  data: RawCaseData;
}

interface DocumentItem {
  id: string;
  title: string;
  content: string;
}

function extractDocuments(data: RawCaseData): DocumentItem[] {
  const docs: DocumentItem[] = [];
  const entries = data.fhirBundle?.entry ?? [];

  for (const entry of entries) {
    const resource: FhirResource = entry.resource;
    if (resource.resourceType !== "DocumentReference") continue;

    const contentArr = resource.content as { attachment?: { data?: string; contentType?: string } }[] | undefined;
    const base64 = contentArr?.[0]?.attachment?.data;
    if (!base64) continue;

    let decoded = "";
    try {
      decoded = atob(base64);
    } catch {
      decoded = "(unable to decode)";
    }

    const title = (resource.description as string) ?? `Document ${docs.length + 1}`;
    docs.push({ id: `doc-${docs.length}`, title, content: decoded });
  }

  return docs;
}

export function DocsDrawer({ data }: DocsDrawerProps) {
  const documents = extractDocuments(data);
  const [selectedId, setSelectedId] = useState<string | null>(documents[0]?.id ?? null);

  if (documents.length === 0) {
    return (
      <div className="flex items-center justify-center h-40 text-sm text-muted-foreground">
        No clinical documents available for this case.
      </div>
    );
  }

  const selected = documents.find((d) => d.id === selectedId) ?? documents[0];

  return (
    <div className="flex h-full">
      {/* Left sidebar — document list */}
      <div className="w-[200px] shrink-0 border-r border-border/50 overflow-y-auto">
        <div className="p-3 space-y-1">
          <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-2 px-2">
            Documents ({documents.length})
          </div>
          {documents.map((doc) => (
            <button
              key={doc.id}
              onClick={() => setSelectedId(doc.id)}
              className={`w-full text-left px-3 py-2 rounded-md text-xs transition-colors ${
                doc.id === selected.id
                  ? "bg-clinical-cyan/10 text-clinical-cyan border border-clinical-cyan/20"
                  : "text-muted-foreground hover:bg-accent/50 hover:text-foreground"
              }`}
            >
              <div className="flex items-center gap-2">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="shrink-0">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z" />
                  <path d="M14 2v6h6" />
                </svg>
                <span className="truncate">{doc.title}</span>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Right content area */}
      <div className="flex-1 overflow-y-auto p-5 min-h-0">
        <div className="mb-3">
          <h3 className="text-sm font-medium text-foreground">{selected.title}</h3>
        </div>
        <pre className="text-[11px] leading-relaxed font-mono bg-muted/30 rounded border border-border/30 p-4 whitespace-pre-wrap">
          {selected.content}
        </pre>
      </div>
    </div>
  );
}

# Frontend Architecture

> **Stack:** Vite 7 + React 19 + TypeScript 5.9 + Tailwind CSS 4 + shadcn/ui (New York)
> **Entry:** `frontend/src/main.tsx` → `App.tsx` → React Router (`/`, `/analysis`, `/patient/:caseId`)
> **Build:** `cd frontend && npm run build` → `frontend/dist/` (static SPA)
> **Dev:** `cd frontend && npx vite --port 5173` (proxies `/api` → `localhost:8000`)

---

## Directory Structure

```
frontend/
├── index.html                     # SPA entry (lung emoji favicon)
├── package.json                   # Dependencies (React 19, shadcn, Tailwind 4)
├── vite.config.ts                 # Vite config: React plugin, Tailwind plugin, /api proxy
├── components.json                # shadcn/ui config (New York style, no RSC)
├── tsconfig.json                  # Path alias: @/* → src/*
├── tsconfig.app.json              # App-level TS config (baseUrl + paths)
├── tsconfig.node.json             # Node-level TS config (Vite config files)
└── src/
    ├── main.tsx                   # ReactDOM root mount
    ├── App.tsx                    # Root layout: Sidebar + Header + Dashboard
    ├── index.css                  # Dark clinical theme, animations, custom fonts
    ├── types/
    │   ├── pipeline.ts            # 18 TS interfaces mirroring Python TypedDicts
    │   ├── patient.ts             # PatientRow, BatchState, BatchContextValue
    │   └── case-data.ts           # RawCaseData, FhirBundle, MicroResult, DataSourceType
    ├── hooks/
    │   ├── use-pipeline-stream.ts # SSE connection + useReducer state machine
    │   ├── use-demo-cases.ts      # Fetches /api/cases
    │   ├── use-batch-queue.ts     # Batch analysis queue management
    │   └── use-case-data.ts       # Fetches /api/case/{id}/data for drawer inspection
    ├── stores/
    │   └── batch-store.tsx        # BatchProvider context: patients, selection, active patient
    ├── lib/
    │   ├── utils.ts               # cn() helper (clsx + tailwind-merge)
    │   ├── severity-colors.ts     # Traffic-light mapping: low→green, moderate→amber, high→red
    │   └── format.ts              # Clinical value formatters (lab values, age, timestamps)
    ├── components/
    │   ├── ui/                    # shadcn primitives (auto-installed)
    │   │   ├── alert.tsx
    │   │   ├── avatar.tsx
    │   │   ├── badge.tsx
    │   │   ├── button.tsx
    │   │   ├── card.tsx
    │   │   ├── checkbox.tsx
    │   │   ├── collapsible.tsx
    │   │   ├── dialog.tsx         # Radix Dialog — used by header profile modal
    │   │   ├── dropdown-menu.tsx
    │   │   ├── progress.tsx
    │   │   ├── scroll-area.tsx
    │   │   ├── separator.tsx
    │   │   ├── sheet.tsx
    │   │   ├── skeleton.tsx
    │   │   ├── table.tsx
    │   │   ├── tabs.tsx
    │   │   └── tooltip.tsx
    │   ├── layout/
    │   │   ├── header.tsx         # Top bar: ward selector, MedGemma badge, active patient indicator, inbox dropdown (5 messages), profile modal (staff card + stats)
    │   │   ├── app-sidebar.tsx    # Nav icons, data source icons (CXR/Labs/FHIR/Micro), GPU status, DataSourceDrawer
    │   │   └── page-transition.tsx # Route transition wrapper
    │   ├── drawers/               # Data source slide-out panels
    │   │   ├── data-source-drawer.tsx  # Sheet wrapper, routes by DataSourceType
    │   │   ├── cxr-drawer.tsx          # CXR findings cards
    │   │   ├── docs-drawer.tsx         # DocumentReference viewer (FHIR documents, base64 decode)
    │   │   ├── labs-drawer.tsx         # Lab table + raw report
    │   │   ├── fhir-drawer.tsx         # FHIR resources grouped by type, collapsible
    │   │   └── micro-drawer.tsx        # Microbiology + antibiogram table
    │   ├── patients/              # Patient list components
    │   │   ├── patient-table.tsx  # Ward list table with active selection
    │   │   └── data-status-icons.tsx  # CXR/Labs/FHIR/Micro availability icons
    │   ├── batch/                 # Batch analysis components
    │   │   ├── batch-node-cards.tsx
    │   │   └── batch-progress-table.tsx
    │   ├── detail/                # Patient detail visualisations
    │   │   ├── compact-view.tsx        # Tabular/compact display mode
    │   │   ├── crp-trend-chart.tsx     # CRP over time line chart
    │   │   ├── curb65-radar.tsx        # CURB65 component radar chart
    │   │   ├── graphical-view.tsx      # Entry point composing detail charts
    │   │   ├── lab-heatmap.tsx         # Lab values heatmap with abnormal ranges
    │   │   └── vital-signs-card.tsx    # 3-column vital signs grid with abnormal flags
    │   └── dashboard/             # 11 clinical data cards
    │       ├── pipeline-progress.tsx    # 8-node horizontal stepper with icons
    │       ├── patient-banner.tsx       # Demographics, allergy/comorbidity badges
    │       ├── severity-card.tsx        # CURB-65 score + [C][U][R][B][65] breakdown
    │       ├── cxr-viewer.tsx           # CXR image + bounding box overlays + findings
    │       ├── lab-panel.tsx            # Lab table with abnormal value highlighting
    │       ├── contradiction-alerts.tsx # Tiered alert cards (high/moderate/low)
    │       ├── treatment-card.tsx       # Antibiotic recommendation + evidence refs
    │       ├── monitoring-card.tsx      # Discharge criteria, CRP trend, treatment response
    │       ├── clinician-summary.tsx    # Real-time token streaming with cursor + word count
    │       ├── data-gaps-card.tsx       # Missing data warnings (collapsible)
    │       └── reasoning-trace.tsx      # Step-by-step pipeline trace (collapsible)
    └── pages/
        ├── patients-page.tsx     # Landing page: patient list + toolbar
        ├── analysis-page.tsx     # Batch analysis runner
        ├── patient-detail-page.tsx # Single patient detail
        └── dashboard.tsx         # Composes all dashboard cards in grid
```

---

## Component Tree

```
App (BatchProvider wraps everything)
├── AppSidebar                ← nav icons, data source icons, GPU status, DataSourceDrawer (portal)
│   ├── useBatchContext()     ← reads activePatientId, patients
│   ├── useCaseData()         ← fetches case data on demand
│   └── DataSourceDrawer      ← Sheet (right, 480px), routes to 4 drawer components
│       ├── CxrDrawer         ← CXR findings cards (consolidation, effusion, etc.)
│       ├── LabsDrawer        ← Admission labs table + raw lab report
│       ├── FhirDrawer        ← FHIR Bundle grouped by resourceType, collapsible
│       └── MicroDrawer       ← Microbiology results + antibiogram (S/I/R)
├── Header                    ← ward selector, MedGemma badge, active patient indicator, inbox dropdown, profile modal
│   ├── useBatchContext()     ← reads activePatientId, patients, setActivePatient
│   ├── Inbox dropdown        ← 5 hardcoded messages, mark-all-as-read, unread badge
│   └── Profile modal         ← staff card (name, GMC, bleep), Today's Stats (9 humorous rows)
├── Routes
│   ├── / → PatientsPage
│   │   └── PatientTable      ← row click sets active patient (not navigate)
│   ├── /analysis → AnalysisPage
│   └── /patient/:caseId → PatientDetailPage
└── (Dashboard — accessed from patient detail)
    ├── PipelineProgress      ← 8-node stepper
    ├── PatientBanner         ← demographics, allergy badges
    ├── [grid: 2-col on xl]
    │   ├── SeverityCard, CXRViewer, LabPanel, ContradictionAlerts
    ├── TreatmentCard, MonitoringCard, ClinicianSummary
    └── [collapsible] DataGapsCard, ReasoningTrace
```

---

## Active Patient & Data Source Drawers

### Active Patient State

`BatchContextValue` (in `stores/batch-store.tsx`) holds `activePatientId: string | null` and `setActivePatient()`. The active patient is purely frontend state — it does NOT flow through SSE or the pipeline.

- `PatientTable` row click calls `onSelectActive(caseId)` instead of navigating to a detail page
- Active row: `bg-clinical-teal/5` background, patient name in `text-clinical-cyan`
- `Header` reads `activePatientId` from context and shows a pulsing teal dot + name + age/sex/bed + X dismiss button

### Data Source Drawers

The sidebar shows 4 data source icons below the navigation (CXR, Labs, FHIR, Micro). Each icon has 3 visual states:

| State | Style | Condition |
|-------|-------|-----------|
| Disabled | `text-white/15` | No patient selected |
| Unavailable | `text-white/25` | Patient selected but source missing |
| Active | `text-clinical-cyan` | Clickable — source available |

Clicking an active icon fetches case data via the `useCaseData()` hook (`GET /api/case/{id}/data`) and opens a `DataSourceDrawer` (shadcn Sheet, right side, 480px). The drawer routes by `DataSourceType` to one of 4 content components:

| Component | Renders |
|-----------|---------|
| `CxrDrawer` | CXR findings cards (consolidation, effusion, etc.) |
| `LabsDrawer` | Admission labs table + raw lab report text |
| `FhirDrawer` | FHIR Bundle grouped by resourceType, collapsible sections |
| `MicroDrawer` | Microbiology results + antibiogram table (S/I/R) |

### Types (`types/case-data.ts`)

| Type | Fields |
|------|--------|
| `RawCaseData` | caseId, patientId, fhirBundle, labReport, cxrFindings, microResults, admissionLabs, treatmentStatus, allergies |
| `DataSourceType` | `"cxr" \| "labs" \| "fhir" \| "micro"` |
| `FhirBundle` | resourceType, type, entry (array of `FhirEntry`) |
| `FhirResource` | resourceType + arbitrary keys |
| `MicroResult` | test_type, organism, status, antibiogram? |
| `AllergyDetail` | substance, reaction_type, criticality? |

### `useCaseData()` Hook

Fetches `GET /api/case/{caseId}/data`, caches by caseId (ref-based), and transforms snake_case keys to camelCase. Returns `{ data, loading, error, fetchCaseData, clearData }`.

---

## State Management — `usePipelineStream` Hook

The core hook (`hooks/use-pipeline-stream.ts`) uses `useReducer` to accumulate state from SSE events streamed by the backend.

### State Shape (`PipelineState`)

| Field | Type | Populated by |
|-------|------|-------------|
| `status` | `"idle" \| "running" \| "complete" \| "error"` | Lifecycle events |
| `completedNodes` | `string[]` | `NODE_COMPLETE` events |
| `activeNode` | `string \| null` | Set between events |
| `totalNodes` | `number` (default 8) | `PIPELINE_START` event |
| `mockMode` | `boolean?` | `PIPELINE_START` event |
| `patientDemographics` | `PatientDemographics \| null` | `parallel_extraction` node |
| `curb65Score` | `CURB65Score \| null` | `severity_scoring` node |
| `placeOfCare` | `Record<string, unknown> \| null` | `severity_scoring` node |
| `labValues` | `LabValues \| null` | `parallel_extraction` node |
| `cxrAnalysis` | `CXRFindings \| null` | `parallel_extraction` node |
| `clinicalExam` | `ClinicalExamFindings \| null` | `parallel_extraction` node |
| `contradictions` | `ContradictionAlert[]` | `check_contradictions` + `treatment_selection` |
| `resolutionResults` | `string[]` | `contradiction_resolution` |
| `antibioticRecommendation` | `AntibioticRecommendation \| null` | `treatment_selection` |
| `investigationPlan` | `InvestigationPlan \| null` | `treatment_selection` |
| `monitoringPlan` | `MonitoringPlan \| null` | `monitoring_plan` |
| `clinicianSummary` | `string \| null` | `output_assembly` |
| `structuredOutput` | `StructuredOutput \| null` | `output_assembly` |
| `dataGaps` | `string[]` | Various nodes |
| `errors` | `string[]` | Various nodes |
| `reasoningTrace` | `TraceStep[]` | All nodes |
| `activeSubNode` | `string \| null` | `SUB_NODE_PROGRESS` events (frontend-only) |
| `subNodeLabel` | `string \| null` | `SUB_NODE_PROGRESS` events (frontend-only) |
| `subNodeProgress` | `{current, total} \| null` | `SUB_NODE_PROGRESS` events (frontend-only) |
| `streamingText` | `string` | `TOKEN_STREAM` events — accumulated response tokens (frontend-only) |
| `streamingThinking` | `string` | `TOKEN_STREAM` events — accumulated thinking tokens (frontend-only) |
| `streamingNode` | `string \| null` | `TOKEN_STREAM` events — which node is streaming (frontend-only) |

### Reducer Actions

| Action | Trigger | Effect |
|--------|---------|--------|
| `RESET` | User clicks Reset | Returns to `INITIAL_STATE` |
| `SET_STATUS` | Internal | Updates `status` field only |
| `PIPELINE_START` | SSE `pipeline_start` event | Resets state, sets `status: "running"` |
| `NODE_START` | SSE `node_start` event | Clears sub-node state, sets `activeNode` |
| `SUB_NODE_PROGRESS` | SSE `sub_node_progress` event | Updates `activeSubNode`, `subNodeLabel`, `subNodeProgress` |
| `TOKEN_STREAM` | SSE `token_stream` event | Accumulates tokens into `streamingText` or `streamingThinking` based on `is_thinking` flag |
| `NODE_COMPLETE` | SSE `node_complete` event | Appends to `completedNodes`, merges node data. For `output_assembly`/`contradiction_resolution`, flushes streaming state. |
| `PIPELINE_COMPLETE` | SSE `pipeline_complete` event | Sets `status: "complete"` |
| `ERROR` | SSE `pipeline_error` or fetch error | Sets `status: "error"`, appends error |

### SSE Connection Pattern

The hook uses `fetch()` + `ReadableStream` instead of `EventSource` because `EventSource` doesn't support POST requests. The SSE text stream is parsed manually:

```
event: node_complete
data: {"node": "load_case", "step": 1, ...}

event: node_complete
data: {"node": "parallel_extraction", "step": 2, "patient_demographics": {...}, ...}
```

The reducer accumulates state progressively — list fields (`contradictions`, `errors`, `dataGaps`, `reasoningTrace`) append, scalar fields overwrite with latest non-null value.

---

## TypeScript Types (`types/pipeline.ts`)

All 18 interfaces mirror Python TypedDicts from `src/cap_agent/agent/state.py`. This is the contract between backend SSE events and frontend rendering:

| Interface | Mirrors Python | Used by component |
|-----------|---------------|-------------------|
| `CURB65Score` | `state.py:CURB65Score` | `SeverityCard` |
| `LabValues` / `LabValue` | `state.py:LabValues` | `LabPanel` |
| `CXRFindings` / `CXRFinding` | `state.py:CXRFindings` | `CXRViewer` |
| `PatientDemographics` | `state.py:PatientDemographics` | `PatientBanner` |
| `ContradictionAlert` | `state.py:ContradictionAlert` | `ContradictionAlerts` |
| `AntibioticRecommendation` | `state.py:AntibioticRecommendation` | `TreatmentCard` |
| `MonitoringPlan` | `state.py:MonitoringPlan` | `MonitoringCard` |
| `InvestigationPlan` | `state.py:InvestigationPlan` | `TreatmentCard` |
| `ClinicalExamFindings` | `state.py:ClinicalExamFindings` | (available, not yet rendered) |
| `TraceStep` | `state.py` trace entries | `ReasoningTrace` |
| `StructuredOutput` | `output_assembly` result | (stored, available for export) |
| `NodeCompleteEvent` | SSE event payload | `usePipelineStream` reducer |
| `SubNodeProgressEvent` | SSE `sub_node_progress` payload | `usePipelineStream` reducer |
| `TokenStreamEvent` | SSE `token_stream` payload | `usePipelineStream` reducer |
| `PipelineState` | Accumulated frontend state (incl. streaming fields) | All dashboard components |
| `DemoCase` | `/api/cases` response | `AppSidebar` |

**Critical convention:** Python uses `snake_case`, TypeScript interfaces use `snake_case` for field names to match SSE JSON directly (no camelCase conversion in the reducer — fields like `patient_demographics` pass through as-is).

---

## Theming & Visual System

### CSS Variables (`index.css`)

The dark "Clinical Mission Control" theme uses oklch colors:

| Variable | Purpose | Value |
|----------|---------|-------|
| `--background` | Page background | `oklch(0.11 0.015 260)` — near-black navy |
| `--foreground` | Primary text | `oklch(0.93 0.01 250)` — cool white |
| `--card` | Card backgrounds | `oklch(0.14 0.015 260)` — dark navy |
| `--primary` | Interactive elements | `oklch(0.72 0.12 220)` — clinical cyan |
| `--severity-low` | Green (CURB65 0-1) | `oklch(0.72 0.19 142)` |
| `--severity-moderate` | Amber (CURB65 2) | `oklch(0.75 0.18 75)` |
| `--severity-high` | Red (CURB65 3-5) | `oklch(0.63 0.24 25)` |
| `--clinical-cyan` | Primary accent | `oklch(0.72 0.12 220)` |
| `--clinical-teal` | Secondary accent | `oklch(0.65 0.13 180)` |

### Fonts

| Font | Usage | Weight range |
|------|-------|-------------|
| DM Sans | UI text (`--font-sans`) | 300-700 |
| JetBrains Mono | Clinical data, code (`--font-mono`) | 300-600 |

### Animations

| Class | Purpose | Duration |
|-------|---------|----------|
| `.animate-pulse-glow` | Active pipeline node indicator | 2s infinite |
| `.animate-blink` | Typewriter cursor | 0.8s step-end |
| `.animate-slide-up` | Card entrance animation | 0.4s ease-out |
| `.stagger-1` to `.stagger-6` | Staggered entrance delays | 0.05-0.3s |
| `.scanline-overlay` | CXR viewer retro effect | Static |

### Background

Body has a subtle 40px grid pattern overlaid on the dark background for depth.

---

## Dashboard Layout Logic (`pages/dashboard.tsx`)

Cards render progressively based on which pipeline nodes have completed:

```
Pipeline Node Completed     → Cards Unlocked
─────────────────────────────────────────────
(any node started)          → PipelineProgress (shows sub-node label + progress during extraction)
parallel_extraction         → PatientBanner, SeverityCard (loading), CXRViewer, LabPanel
severity_scoring            → SeverityCard (data), TreatmentCard (loading)
check_contradictions        → ContradictionAlerts
contradiction_resolution    → ContradictionAlerts (streaming thinking block + resolution text in real-time)
treatment_selection         → TreatmentCard (data), MonitoringCard (loading)
monitoring_plan             → MonitoringCard (data), ClinicianSummary (loading)
output_assembly             → ClinicianSummary (real-time token streaming), DataGapsCard, ReasoningTrace
```

Loading states use shadcn `Skeleton` components. The `isRunning && !nodeDone` pattern controls loading.

**Streaming rendering:** During `output_assembly`, `clinician-summary.tsx` renders `streamingText` in real-time with a blinking cursor and word count (replaces old typewriter effect). During `contradiction_resolution`, `contradiction-alerts.tsx` shows a dimmed thinking block (last 150 chars of `streamingThinking`) and accumulating resolution text. `pipeline-progress.tsx` shows the current sub-node label and GPU call counter (e.g., "Extracting clinical findings (2/3)") during extraction.

---

## How To: Add a New Dashboard Card

### Step 1: Identify the data source

Check if your data already exists in `PipelineState` (from an SSE event field). If not, you need to propagate it from the backend (see `docs/frontend/data-flow-and-extensibility.md`).

### Step 2: Create the component

```bash
# Create new component file
touch frontend/src/components/dashboard/my-new-card.tsx
```

Follow the established pattern:

```tsx
import type { MyDataType } from "@/types/pipeline";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

interface MyNewCardProps {
  data: MyDataType | null;
  loading?: boolean;
}

export function MyNewCard({ data, loading }: MyNewCardProps) {
  if (loading || !data) {
    return (
      <Card className="border-border/30 bg-card/50">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            My Card Title
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-20 w-full" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-border/30 bg-card/50 animate-slide-up">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          My Card Title
        </CardTitle>
      </CardHeader>
      <CardContent>
        {/* Render your data here */}
      </CardContent>
    </Card>
  );
}
```

### Step 3: Wire into Dashboard

Edit `pages/dashboard.tsx`:

1. Import the component
2. Add it to the JSX at the appropriate position
3. Connect it to the `state` prop with the correct loading condition

```tsx
import { MyNewCard } from "@/components/dashboard/my-new-card";

// In the JSX, after the relevant node check:
{(someNodeDone || (isRunning && previousNodeDone)) && (
  <MyNewCard
    data={state.myDataField}
    loading={isRunning && !someNodeDone}
  />
)}
```

### Step 4: Add shadcn components if needed

```bash
cd frontend && npx shadcn@latest add [component-name]
```

---

## How To: Add a New shadcn Component

```bash
cd frontend
npx shadcn@latest add [component-name]
```

Available components: https://ui.shadcn.com/docs/components

Config is in `components.json` (New York style, Lucide icons, no RSC).

---

## How To: Modify the Theme

Edit `frontend/src/index.css`:

- **Colors:** Change oklch values in the `:root` block
- **Severity palette:** Change `--color-severity-*` in `@theme inline`
- **Fonts:** Update `@import url(...)` and `--font-sans`/`--font-mono` in `@theme inline`
- **Animations:** Add/modify `@keyframes` blocks and utility classes

All theme changes propagate through CSS variables — components use Tailwind classes like `bg-severity-high/10` that reference the variables automatically.

---

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `react` / `react-dom` | 19.2 | UI framework |
| `vite` | 7.3 | Build tool + dev server |
| `tailwindcss` | 4.2 | Utility-first CSS |
| `@tailwindcss/vite` | 4.2 | Tailwind Vite plugin |
| `shadcn` | 3.8 | Component CLI (dev) |
| `radix-ui` | 1.4 | Headless UI primitives |
| `class-variance-authority` | 0.7 | Variant management |
| `clsx` + `tailwind-merge` | Latest | Class name utilities |
| `lucide-react` | 0.575 | Icons |
| `tw-animate-css` | 1.4 | Animation utilities |
| `typescript` | 5.9 | Type checking |

---

## Build & Verification

```bash
# Dev mode (with backend proxy)
cd frontend && npx vite --port 5173

# Type check
cd frontend && npx tsc -b

# Build for production
cd frontend && npm run build
# → frontend/dist/ (static files, ~277kB JS + ~49kB CSS)

# Lint
cd frontend && npm run lint
```

Production build output is served by FastAPI's `StaticFiles` mount (see server docs).

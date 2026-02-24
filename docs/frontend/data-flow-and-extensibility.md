# Data Flow & Extensibility Guide

> End-to-end data flow from LangGraph pipeline to React dashboard, with step-by-step recipes for common modifications.

---

## End-to-End Data Flow

```
User clicks "Run Pipeline" (React)
       │
       ▼
POST /api/run/{case_id}  (FastAPI)
       │
       ├── build_case(case_id)  →  demo_cases.py  →  synthetic.py builder
       │
       ├── GPU?  ─── Yes ──→  sse.stream_pipeline()  (queue bridge + real graph)
       │         └── No  ──→  mock_runner.stream_pipeline_mock()  (simulated streaming)
       │
       ▼
SSE bridge sets up callbacks:
       ├── set_streaming_callbacks(progress_cb, token_cb)  →  thread-local in nodes.py
       ├── progress_cb → pushed to queue as ("sub_node_progress", {...})
       ├── token_cb → pushed to queue as ("token", {token, is_thinking})
       │
       ▼
build_initial_state(case_data)  →  state.py:build_initial_state()
       │
       ▼
graph.stream(initial_state, stream_mode="updates")  — runs in background thread
       │
       ├── Yields: {node_name: node_output_dict}  ×8 nodes
       ├── Extraction nodes call progress_cb before each GPU call
       ├── contradiction_resolution + output_assembly call call_medgemma_streaming(token_callback=token_cb)
       │
       ▼
SSE Generator (queue bridge): drains queue.Queue
       │
       ├── node_start events → before each node
       ├── sub_node_progress events → before each GPU call in extraction
       ├── token_stream events → batched tokens every 50ms during generation
       ├── node_complete events → after each node, with state fields
       ├── `: keepalive` comment → every 15s heartbeat
       │
       ▼
StreamingResponse  →  HTTP SSE stream  →  Browser
       │
       ▼
usePipelineStream hook (React)
       │
       ├── ReadableStream reader parses SSE text
       ├── JSON.parse each data payload
       ├── dispatch(NODE_START | SUB_NODE_PROGRESS | TOKEN_STREAM | NODE_COMPLETE, event)
       │
       ▼
useReducer accumulates state
       │
       ├── Scalars: overwrite with latest non-null
       ├── Lists: append (contradictions, errors, traces)
       ├── Streaming: TOKEN_STREAM → streamingText or streamingThinking
       ├── Progress: SUB_NODE_PROGRESS → activeSubNode, subNodeLabel, subNodeProgress
       │
       ▼
Dashboard re-renders
       │
       ├── Checks completedNodes[] to show/hide cards
       ├── Each card receives its data slice as props
       ├── ClinicianSummary renders streamingText in real-time during output_assembly
       ├── ContradictionAlerts shows streaming thinking + resolution during contradiction_resolution
       ├── PipelineProgress shows sub-node label + progress counter during extraction
       └── Loading skeletons show for pending nodes
```

---

## The 5 Touchpoints for Any Data Field

Every piece of clinical data passes through exactly 5 files:

| Layer | File | What happens |
|-------|------|-------------|
| 1. Python state | `src/cap_agent/agent/state.py` | Field declared in `CAPAgentState` TypedDict |
| 2. Node logic | `src/cap_agent/agent/nodes.py` | Node function populates the field |
| 3. SSE forwarding | `server/sse.py` + `server/mock_runner.py` | Field name in forwarding list |
| 4. TypeScript types | `frontend/src/types/pipeline.ts` | Interface + `NodeCompleteEvent` + `PipelineState` |
| 5. React component | `frontend/src/components/dashboard/*.tsx` | Renders the data |

**The reducer** (`hooks/use-pipeline-stream.ts`) is the bridge between layers 3 and 5.

---

## Recipe: Add a New Data Field End-to-End

**Example:** Adding a `sepsis_screen` field that contains early warning scores.

### Step 1: Python State (`src/cap_agent/agent/state.py`)

Add the TypedDict and field:

```python
class SepsisScreen(TypedDict):
    score: int
    components: dict
    alert_level: str

class CAPAgentState(TypedDict):
    # ... existing fields ...
    sepsis_screen: Optional[SepsisScreen]
```

### Step 2: Node Logic (`src/cap_agent/agent/nodes.py`)

Populate in the relevant node (likely `severity_scoring`):

```python
def severity_scoring_node(state: CAPAgentState) -> dict:
    # ... existing scoring logic ...
    return {
        "curb65_score": score,
        "place_of_care": place,
        "sepsis_screen": {"score": 3, "components": {...}, "alert_level": "moderate"},
        # ... rest ...
    }
```

### Step 3: SSE Forwarding

Add `"sepsis_screen"` to the key list in **both** files:

**`server/sse.py`** (line ~84):
```python
for key in [
    "patient_demographics", "curb65_score", "place_of_care",
    # ... existing keys ...
    "sepsis_screen",  # ← add here
]:
```

**`server/mock_runner.py`** (`STATE_KEYS` list):
```python
STATE_KEYS = [
    "patient_demographics", "curb65_score", "place_of_care",
    # ... existing keys ...
    "sepsis_screen",  # ← add here
]
```

### Step 4: TypeScript Types (`frontend/src/types/pipeline.ts`)

Add the interface and wire it through:

```typescript
// New interface
export interface SepsisScreen {
  score: number;
  components: Record<string, unknown>;
  alert_level: "low" | "moderate" | "high";
}

// Add to NodeCompleteEvent
export interface NodeCompleteEvent {
  // ... existing fields ...
  sepsis_screen?: SepsisScreen;
}

// Add to PipelineState
export interface PipelineState {
  // ... existing fields ...
  sepsisScreen: SepsisScreen | null;
}
```

### Step 5: Reducer (`hooks/use-pipeline-stream.ts`)

Add to `INITIAL_STATE`:
```typescript
const INITIAL_STATE: PipelineState = {
  // ... existing ...
  sepsisScreen: null,
};
```

Add to `NODE_COMPLETE` case in reducer:
```typescript
case "NODE_COMPLETE": {
  const e = action.event;
  return {
    ...state,
    // ... existing ...
    sepsisScreen: e.sepsis_screen ?? state.sepsisScreen,
  };
}
```

### Step 6: Dashboard Component

Create `frontend/src/components/dashboard/sepsis-card.tsx` and wire it into `pages/dashboard.tsx`.

---

## Recipe: Add a New Demo Case

**Example:** Adding a readmission case.

### Step 1: Build the case data (`src/cap_agent/data/synthetic.py`)

```python
def get_synthetic_readmission_case():
    """72yo male readmitted within 30 days of discharge."""
    case = copy.deepcopy(SYNTHETIC_CAP_CASE)
    case["case_id"] = "READMIT-001"
    # Modify FHIR bundle, labs, clinical notes as needed
    return case
```

### Step 2: Register in demo cases (`server/demo_cases.py`)

```python
from cap_agent.data.synthetic import get_synthetic_readmission_case

DEMO_CASES = {
    # ... existing ...
    "readmit": {
        "id": "readmit",
        "label": "30-Day Readmission",
        "description": "Patient readmitted with recurrent symptoms after initial discharge.",
        "builder": get_synthetic_readmission_case,
    },
}
```

### Step 3: (Optional) Add mock router config (`server/mock_runner.py`)

If the case needs specific mock parameters:

```python
def _build_case_aware_router(case_data: dict):
    case_id = case_data.get("case_id", "")

    if "READMIT" in case_id.upper():
        ehr_json = _mock_ehr_synthesis(urea=9.0, ...)
        lab_json = _mock_lab_synthesis(crp=220, ...)
    # ... rest of existing logic ...
```

The sidebar auto-discovers new cases via `/api/cases` — no frontend changes needed.

---

## Recipe: Add a New API Endpoint

**Example:** Adding a `/api/export` endpoint that returns the structured output as downloadable JSON.

### Step 1: Add endpoint in `server/main.py`

```python
from fastapi.responses import JSONResponse

@app.get("/api/export/{case_id}")
def export_result(case_id: str):
    """Export the last pipeline result as JSON."""
    # Implementation depends on whether you cache results
    return JSONResponse(content={"error": "not implemented"})
```

**Critical:** Add this BEFORE the `StaticFiles` mount (which must be the last route).

### Step 2: Call from frontend

```typescript
const res = await fetch(`/api/export/${caseId}`);
const data = await res.json();
```

The Vite dev proxy already forwards all `/api/*` routes to `localhost:8000`.

---

## Recipe: Add a New Dashboard Card

See detailed instructions in `docs/frontend/frontend-architecture.md` under "How To: Add a New Dashboard Card".

Summary:
1. Check if data exists in `PipelineState` (or add it via the "Add a New Data Field" recipe)
2. Create component in `frontend/src/components/dashboard/`
3. Follow the Card + Skeleton loading pattern
4. Wire into `pages/dashboard.tsx` with the `(nodeDone || (isRunning && previousNodeDone))` guard

---

## Recipe: Add Streaming Support to a New Extraction Tool

1. Add optional `progress_callback` parameter to the extraction function signature
2. Call `progress_callback(sub_node, label, gpu_call, total)` before each GPU call
3. Wire in `parallel_extraction_node` (nodes.py) — read from thread-local context via `getattr(_streaming_context, "progress_callback", None)` and pass to the extraction function
4. Mock function should accept but ignore the `progress_callback` parameter

---

## Recipe: Add Token Streaming to a New GPU Node

1. In the node function, check for `token_cb` from thread-local context: `token_cb = getattr(_streaming_context, "token_callback", None)`
2. If present, use `call_medgemma_streaming(prompt, token_callback=token_cb)` instead of `call_medgemma()`
3. If absent, fall back to batch `call_medgemma()` (backward-compatible)
4. Update `server/mock_runner.py` to emit simulated tokens for this node (split text into words, emit with `TOKEN_DELAY`)

---

## Architecture Constraints & Conventions

### Convention: snake_case in SSE, camelCase in components

- SSE JSON uses `snake_case` (e.g., `patient_demographics`, `curb65_score`)
- `NodeCompleteEvent` interface preserves `snake_case` (matches SSE directly)
- `PipelineState` uses `camelCase` (e.g., `patientDemographics`, `curb65Score`)
- The reducer maps between them: `patientDemographics: e.patient_demographics ?? state.patientDemographics`

### Convention: List fields append, scalar fields overwrite

In the reducer:
- **List fields** (`contradictions`, `errors`, `dataGaps`, `reasoningTrace`, `resolutionResults`) use spread + append: `[...state.contradictions, ...(e.contradictions_detected ?? [])]`
- **Scalar fields** use nullish coalescing: `e.curb65_score ?? state.curb65Score` (keeps existing value if new is null/undefined)

This matches the Python side where `Annotated[List, operator.add]` fields accumulate across nodes.

### Convention: Progressive rendering via `completedNodes`

Cards check `state.completedNodes.includes("node_name")` to determine visibility and loading state. The dashboard doesn't wait for the full pipeline — cards appear as their data arrives.

### Convention: StaticFiles mount last

The `app.mount("/", StaticFiles(...))` catch-all **must** be the last route registered. Any API endpoint defined after it would be unreachable.

### Convention: Mock runner reuses E2E test fixtures

`server/mock_runner.py` imports `build_prompt_router`, `_mock_ehr_synthesis`, `_mock_lab_synthesis` from `tests/test_pipeline_e2e.py`. This ensures mock behavior matches test expectations. If you change test fixtures, mock runner behavior changes too.

### Constraint: Single-worker uvicorn

The Dockerfile uses `--workers 1` because MedGemma 4B consumes ~8GB VRAM. Multiple workers would OOM the L4 GPU (24GB). Pipeline requests are sequential.

### Constraint: CXR upload is transient

Uploaded CXR images are stored in a `tempfile` directory (`CXR_DIR`). They don't persist across container restarts. This is acceptable for demos.

### Convention: Active patient is UI-only state

`activePatientId` lives in `BatchProvider` React context — it's purely frontend state for sidebar/header UX. It does NOT flow through SSE or the pipeline. Data source drawers fetch raw case data on-demand via the `useCaseData()` hook, which calls `GET /api/case/{case_id}/data`. The hook caches by caseId and transforms snake_case to camelCase.

### Convention: Drawer content components are pure

Each drawer (`CxrDrawer`, `LabsDrawer`, `FhirDrawer`, `MicroDrawer`) receives `RawCaseData` and renders it. They don't fetch — `DataSourceDrawer` handles loading/error states. To add a new drawer: create the component, add it to `DataSourceDrawer`'s routing, add an icon entry in `app-sidebar.tsx`.

---

## File Cross-Reference: "I want to..."

| I want to... | Edit | Also update |
|--------------|------|------------|
| Add a dashboard card | `frontend/src/components/dashboard/new.tsx` | `pages/dashboard.tsx` imports |
| Add a new data field (full stack) | See "Add a New Data Field" recipe | 5 files across Python + TS |
| Add a demo case | `synthetic.py` + `demo_cases.py` | Optional: `mock_runner.py` |
| Add an API endpoint | `server/main.py` | (before static mount) |
| Add token streaming to a node | `agent/nodes.py` + `models/medgemma.py` | `server/mock_runner.py` (simulated tokens) |
| Add sub-node progress to extraction | `data/extraction.py` + `agent/nodes.py` | `server/mock_runner.py` (simulated sub-nodes) |
| Change SSE event format | `server/sse.py` | `server/mock_runner.py`, `hooks/use-pipeline-stream.ts`, `types/pipeline.ts` |
| Change theme colors | `frontend/src/index.css` | — |
| Add a shadcn component | `npx shadcn@latest add [name]` | Import in your component |
| Change mock delays | `server/mock_runner.py` (`NODE_DELAYS`) | — |
| Change deployment config | `deploy.sh` | `Dockerfile` (if image changes) |
| Add server Python deps | `pyproject.toml` `[server]` group | `pip install -e ".[server]"` |
| Add frontend npm deps | `cd frontend && npm install [pkg]` | — |
| Change pipeline node order | `server/sse.py` (`NODE_ORDER`/`NODE_LABELS`) | `pipeline-progress.tsx` |
| Change active patient behavior | `stores/batch-store.tsx` | `patient-table.tsx`, `header.tsx` |
| Add a data source drawer | `components/drawers/new-drawer.tsx` | `data-source-drawer.tsx` route, `app-sidebar.tsx` icon |
| Change case data fetching | `hooks/use-case-data.ts` | `types/case-data.ts` |
| Change drawer content/layout | `components/drawers/*.tsx` | `types/case-data.ts` (if schema changes) |
| Change CXR upload behavior | `server/main.py` (`upload_cxr`) | `App.tsx` (`handleCxrUpload`) |

---

## Testing After Changes

| Change type | Test command |
|-------------|-------------|
| Python pipeline/state | `pytest -v --tb=short` (468 tests) |
| Frontend TypeScript | `cd frontend && npx tsc -b` |
| Frontend build | `cd frontend && npm run build` |
| SSE integration | Start server + `curl -X POST http://localhost:8000/api/run/t0` |
| Full stack | `./dev.sh` → open browser → run all 4 cases |
| Docker | `docker build -t cap-cdss . && docker run -p 8080:8080 cap-cdss` |

# Server & Deployment Architecture

> **Server:** FastAPI 0.115+ serving REST API + static Vite SPA
> **Deployment:** Single NVIDIA CUDA container on Cloud Run GPU (L4)
> **Local dev:** `./dev.sh` runs backend (port 8000) + frontend (port 5173) in parallel

---

## Server Directory

```
server/
├── __init__.py          # Package marker
├── main.py       (132L) # FastAPI app: API endpoints + static mount
├── demo_cases.py  (51L) # Maps case IDs → synthetic case builders
├── sse.py        (260L) # Queue bridge SSE generator: token batching, heartbeat, streaming events
└── mock_runner.py (239L) # GPU-free mock: case-aware prompt router, simulated streaming
```

---

## FastAPI Endpoints (`server/main.py`)

| Method | Path | Handler | Purpose |
|--------|------|---------|---------|
| `GET` | `/api/health` | `health()` | Returns `{"status": "ok", "gpu": bool}` |
| `GET` | `/api/cases` | `list_cases()` | Returns list of 4 demo cases (id, label, description) |
| `POST` | `/api/run/{case_id}` | `run_pipeline()` | Starts pipeline, returns SSE stream |
| `POST` | `/api/upload-cxr` | `upload_cxr()` | Upload CXR image for analysis |
| `GET` | `/api/case/{case_id}/data` | `get_case_data()` | Returns sanitized case data for drawer inspection |
| `GET` | `/api/cxr/{filename}` | `serve_cxr()` | Serve uploaded CXR image |
| `GET` | `/*` | StaticFiles mount | Serves Vite SPA (`html=True` for client-side routing) |

### Route Order (Critical)

The `StaticFiles` mount at `"/"` **must be the last route** because it's a catch-all. FastAPI matches routes top-to-bottom — if the static mount were first, it would intercept `/api/*` requests. The code guards this with a conditional check:

```python
STATIC_DIR = Path(__file__).parent / "static"
if STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="spa")
```

The `html=True` parameter enables SPA routing — any path that doesn't match a physical file returns `index.html`, letting React Router handle the route.

### GPU Auto-Detection

```python
try:
    import torch
    GPU_AVAILABLE = torch.cuda.is_available()
except ImportError:
    GPU_AVAILABLE = False
```

When `GPU_AVAILABLE=True`: uses `server.sse.stream_pipeline()` (real MedGemma inference).
When `GPU_AVAILABLE=False`: uses `server.mock_runner.stream_pipeline_mock()` (patched MedGemma with keyword router).

---

## Demo Cases (`server/demo_cases.py`)

Maps 4 case IDs to synthetic case builders from `src/cap_agent/data/synthetic.py`:

| Case ID | Label | Builder function | Scenario |
|---------|-------|-----------------|----------|
| `t0` | T=0 Initial Assessment | `get_synthetic_fhir_case()` | Full FHIR + labs + CXR |
| `t48h` | T=48h Stewardship Review | `get_synthetic_48h_case()` | 48h follow-up, IV-to-oral switch |
| `day34` | Day 3-4 Treatment Monitoring | `get_synthetic_day34_case()` | CRP trend, treatment response |
| `cr10` | CR-10 Safety Demo | `get_synthetic_cr10_case()` | Penicillin allergy detection |

### How To: Add a New Demo Case

1. Create the case builder in `src/cap_agent/data/synthetic.py` (follow existing patterns)
2. Import it in `server/demo_cases.py`
3. Add entry to the `DEMO_CASES` dict:

```python
DEMO_CASES = {
    # ... existing cases ...
    "my_case": {
        "id": "my_case",
        "label": "My New Case",
        "description": "Description for sidebar display.",
        "builder": get_my_new_case,
    },
}
```

The sidebar fetches `/api/cases` on mount, so new cases appear automatically.

---

## SSE Streaming (`server/sse.py`)

### Queue Bridge Architecture

The SSE generator uses a **queue bridge** to decouple the LangGraph execution thread from the HTTP response stream:

```
Graph thread (background)                 SSE Generator (main)
─────────────────────────                 ────────────────────
graph.stream() yields chunks              queue.get(timeout=0.05)
    ↓                                         ↓
set_streaming_callbacks()                 Drain queue events
    ↓                                         ↓
Node functions push events:              Batch tokens (50ms window)
  ("node_start", {...})                       ↓
  ("sub_node_progress", {...})            Yield SSE event strings
  ("token", {...})                            ↓
  ("node_complete", {...})                Inject heartbeat (15s)
    ↓                                         ↓
_SENTINEL → signals completion            StreamingResponse → Browser
```

- `_SENTINEL = object()` — Pushed to queue when graph thread completes (success or error)
- `_TOKEN_BATCH_MS = 50` — Accumulate tokens for 50ms before flushing as single SSE event
- `_HEARTBEAT_INTERVAL = 15` — SSE comment (`: keepalive`) every 15s to prevent Cloud Run proxy timeout

### SSE Event Protocol

| Event | Payload | When |
|-------|---------|------|
| `pipeline_start` | `{case_id}` | Before graph starts |
| `node_start` | `{node, label, step}` | Before each node begins |
| `sub_node_progress` | `{node, sub_node, label, gpu_call, total_gpu_calls}` | Before each GPU call in extraction |
| `token_stream` | `{node, tokens: [{token, is_thinking}]}` | Batched every 50ms during generation |
| `node_complete` | `{node, label, step, ...state_keys}` | After node finishes |
| `pipeline_complete` | `{...full_state}` | After graph completes |
| `pipeline_error` | `{error}` | On failure |
| (comment) | `: keepalive` | Every 15s heartbeat |

### Which GPU Calls Stream Tokens

| Node | Token streaming | Thinking tokens | Sub-node progress |
|------|----------------|-----------------|-------------------|
| `parallel_extraction` | No | No | Yes (8 sub-steps) |
| `contradiction_resolution` | Yes | Yes (`enable_thinking=True`) | No |
| `output_assembly` | Yes | No (`enable_thinking=False`) | No |

### Node Order (8 nodes)

```python
NODE_ORDER = [
    "load_case",              # 1. Load patient data
    "parallel_extraction",    # 2. Extract from EHR + labs + CXR (GPU)
    "severity_scoring",       # 3. Calculate CURB-65
    "check_contradictions",   # 4. Detect cross-modal contradictions
    "contradiction_resolution", # 5. Resolve contradictions (GPU, may be skipped)
    "treatment_selection",    # 6. Select antibiotics
    "monitoring_plan",        # 7. Build monitoring plan
    "output_assembly",        # 8. Generate clinician summary (GPU)
]
```

### State Fields Forwarded to Frontend

These keys are extracted from each `node_output` and included in `node_complete` events:

```python
STATE_KEYS = [
    "patient_demographics", "curb65_score", "place_of_care",
    "lab_values", "cxr_analysis", "clinical_exam",
    "contradictions_detected", "resolution_results",
    "antibiotic_recommendation", "investigation_plan",
    "monitoring_plan", "clinician_summary", "structured_output",
    "data_gaps", "errors", "reasoning_trace",
]
```

### SSE Headers

```python
StreamingResponse(generator, media_type="text/event-stream", headers={
    "Cache-Control": "no-cache",      # Prevent caching
    "Connection": "keep-alive",        # Keep SSE connection open
    "X-Accel-Buffering": "no",        # Disable nginx/Cloud Run buffering
})
```

The `X-Accel-Buffering: no` header is critical for Cloud Run — without it, the reverse proxy buffers the entire response and delivers it as one chunk, defeating streaming.

---

## Mock Runner (`server/mock_runner.py`)

### Purpose

Enables GPU-free local development. Patches `call_medgemma` with a prompt-keyword router (same pattern as E2E tests and benchmark quick mode). Now emits the full streaming event protocol (`node_start`, `sub_node_progress`, `token_stream`) with simulated delays.

### Case-Aware Mocking

The mock runner detects case type from `case_id` and configures appropriate mock parameters:

| Case pattern | Mock CRP | Mock Urea | Mock RR | Clinical scenario |
|-------------|---------|----------|--------|-------------------|
| `*48h*` or `*48H*` | 95 | 6.8 | 18 | Improving vitals, stewardship |
| `*day*` or `*DAY*` | 110 | 7.0 | 20 | Partial CRP improvement |
| Default (T=0, CR-10) | 186 | 8.2 | 22 | Acute presentation |

### Artificial Delays

Each node has a simulated delay to mimic GPU inference latency:

| Node | Delay (s) | Rationale |
|------|-----------|-----------|
| `load_case` | 0.3 | Fast (no GPU) |
| `parallel_extraction` | 2.0 | Multiple GPU calls in real mode |
| `severity_scoring` | 0.3 | Deterministic |
| `check_contradictions` | 0.5 | Deterministic |
| `contradiction_resolution` | 1.0 | GPU call (if not Strategy E) |
| `treatment_selection` | 0.5 | Deterministic |
| `monitoring_plan` | 0.3 | Deterministic |
| `output_assembly` | 1.5 | GPU call (clinician summary) |

Total mock pipeline: ~6.4 seconds. Real GPU pipeline: ~30-60 seconds.

### Mock Streaming Simulation

The mock runner simulates the same streaming events as the real pipeline:

| Node | Mock streaming behavior |
|------|------------------------|
| `parallel_extraction` | Emits 8 `sub_node_progress` events with `SUB_NODE_DELAY` (0.6s) between each |
| `contradiction_resolution` | Emits fake thinking tokens (`is_thinking: True`) from `MOCK_THINKING`, then resolution text (`is_thinking: False`) |
| `output_assembly` | Splits mock summary into words, emits each as a `token_stream` event with `TOKEN_DELAY` (0.06s, ~60 WPM) |

Constants:
- `SUB_NODE_DELAY = 0.6` — Delay per extraction sub-step
- `TOKEN_DELAY = 0.06` — Delay per streamed word (~60 WPM)
- `EXTRACTION_SUB_NODES` — 8 extraction sub-steps with labels (e.g., "Filtering narrative observations", "Synthesizing clinical data")

---

## Docker Build (`Dockerfile`)

Multi-stage build: Node builds SPA → Python GPU runtime serves everything.

### Stage 1: Frontend Build

```dockerfile
FROM node:22-slim AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build
```

### Stage 2: Python GPU Runtime

```dockerfile
FROM nvidia/cuda:12.4.0-runtime-ubuntu22.04
# Install Python 3.11 + system deps
# Copy cap_agent source + server + tests + benchmark_data
# pip install torch (CUDA 12.4) + cap_agent[server]
COPY --from=frontend-builder /app/frontend/dist /app/server/static/
CMD ["python3", "-m", "uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
```

### Key Design Decisions

| Decision | Why |
|----------|-----|
| `nvidia/cuda:12.4.0-runtime` | Matches PyTorch CUDA 12.4 wheel index |
| `python3.11` | LangGraph + FastAPI compatibility |
| `--workers 1` | MedGemma 4B uses full GPU memory — can't share |
| Port 8080 | Cloud Run default |
| `npm ci` (not `npm install`) | Reproducible builds from lockfile |
| Frontend dist → `server/static/` | FastAPI serves it via `StaticFiles` mount |

### .dockerignore

Excludes `.git`, `node_modules`, `.venv`, model artifacts (`*.safetensors`, `*.bin`), notebooks, secrets, and docs to keep image small.

---

## Cloud Run Deployment (`deploy.sh`)

### What It Does

```bash
./deploy.sh                    # Deploy with defaults
HF_TOKEN=hf_xxx ./deploy.sh   # Deploy with explicit HF token
```

1. Enables required GCP APIs (Cloud Run, Artifact Registry, Cloud Build)
2. Builds container with Cloud Build (`gcloud builds submit`)
3. Deploys to Cloud Run with GPU settings
4. Prints the service URL

### Cloud Run Configuration

| Setting | Value | Why |
|---------|-------|-----|
| GPU | 1x NVIDIA L4 | MedGemma 4B (~8GB bfloat16) fits in 24GB VRAM |
| CPU | 8 vCPU | Sufficient for FastAPI + data processing |
| Memory | 32 GiB | Model loading + pipeline state |
| Min instances | 1 | No cold starts during demos |
| Max instances | 1 | Single-GPU; no horizontal scaling needed |
| Port | 8080 | Cloud Run default |
| Timeout | 300s | Pipeline takes ~60s; 5x safety margin |
| `--no-cpu-throttling` | Enabled | Keep CPU active for background model loading |
| `--allow-unauthenticated` | Enabled | Demo access without auth |

### Environment Variables

| Variable | Purpose |
|----------|---------|
| `HF_TOKEN` | Hugging Face token for MedGemma gated model access |
| `GCP_PROJECT_ID` | Override default project (default: `medgemma-cap-cdss`) |
| `GCP_REGION` | Override default region (default: `us-central1`) |

---

## Local Development (`dev.sh`)

```bash
./dev.sh
# → Backend: http://localhost:8000 (uvicorn + auto-reload)
# → Frontend: http://localhost:5173 (Vite dev server, proxies /api)
# → Ctrl+C stops both
```

### How It Works

1. Starts uvicorn (backend) on port 8000 with `--reload`
2. Starts Vite (frontend) on port 5173
3. Vite's proxy forwards `/api/*` requests to `localhost:8000`
4. `trap cleanup EXIT` kills both processes on Ctrl+C

### Without GPU

The server auto-detects `GPU_AVAILABLE=False` and uses the mock runner. The frontend shows a "Demo Mode" badge in the header.

---

## How To: Add a New API Endpoint

1. Add the endpoint in `server/main.py` **before** the `StaticFiles` mount:

```python
@app.get("/api/my-endpoint")
def my_endpoint():
    return {"data": "..."}

# ... existing endpoints ...

# Static mount MUST remain last
if STATIC_DIR.exists():
    app.mount("/", StaticFiles(...))
```

2. If the endpoint needs SSE streaming, follow the pattern in `server/sse.py`
3. Install any new Python deps by adding to `pyproject.toml`'s `[project.optional-dependencies] server` list
4. The Vite dev proxy already forwards all `/api/*` routes — no config changes needed

---

## How To: Add a New Pipeline State Field to SSE

To propagate a new field from the LangGraph pipeline to the frontend:

1. **Python state:** Add the field to `CAPAgentState` in `src/cap_agent/agent/state.py`
2. **Node output:** Set the field in the relevant node function in `src/cap_agent/agent/nodes.py`
3. **SSE forwarding:** Add the key to the forwarding list in both files:
   - `server/sse.py` line 84-91 (the `for key in [...]` loop)
   - `server/mock_runner.py` line 79-86 (`STATE_KEYS` list)
4. **TypeScript types:** Add the field to `NodeCompleteEvent` in `frontend/src/types/pipeline.ts`
5. **React state:** Add the field to `PipelineState` and update the reducer in `hooks/use-pipeline-stream.ts`
6. **Dashboard component:** Create or modify a component to render the data

See `docs/frontend/data-flow-and-extensibility.md` for the complete walkthrough.

---

## Deployment Verification Checklist

```bash
# 1. Existing tests pass (no regressions)
pytest -v --tb=short

# 2. Frontend builds
cd frontend && npm run build

# 3. Type check
cd frontend && npx tsc -b

# 4. Server starts locally
cd /project/root && .venv/bin/uvicorn server.main:app --port 8000

# 5. SSE works
curl -X POST http://localhost:8000/api/run/t0

# 6. Docker builds (if Docker available)
docker build -t cap-cdss .

# 7. Deploy to Cloud Run
./deploy.sh

# 8. Test deployed URL
curl https://[service-url]/api/health
curl -X POST https://[service-url]/api/run/t0
```

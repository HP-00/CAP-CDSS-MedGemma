# Cloud Run GPU Deployment & Debugging Playbook

> **Note:** Replace placeholder values (`your-project-id`, `your-project-number`, `your-service-url`) with your GCP project details.

> Complete operational guide for building, deploying, monitoring, and debugging the CAP CDSS on Cloud Run with NVIDIA L4 GPU. Written from real deployment sessions — every command has been battle-tested.

---

## Table of Contents

1. [Service Overview](#1-service-overview)
2. [Prerequisites](#2-prerequisites)
3. [Building and Deploying](#3-building-and-deploying)
4. [Post-Deploy Verification](#4-post-deploy-verification)
5. [Monitoring a Live Pipeline Run](#5-monitoring-a-live-pipeline-run)
6. [Getting Logs](#6-getting-logs)
7. [Debugging Common Issues](#7-debugging-common-issues)
8. [Quota Management](#8-quota-management)
9. [Updating Without Full Redeploy](#9-updating-without-full-redeploy)
10. [Pipeline Lifecycle and Cold Starts](#10-pipeline-lifecycle-and-cold-starts)
11. [SSE Stream Debugging](#11-sse-stream-debugging)
12. [Concurrency and Scaling](#12-concurrency-and-scaling)
13. [Cost Management](#13-cost-management)
14. [Known Issues and Workarounds](#14-known-issues-and-workarounds)
15. [Quick Reference Commands](#15-quick-reference-commands)

---

## 1. Service Overview

| Key | Value |
|-----|-------|
| **Service name** | `cap-cdss` |
| **Project** | `your-project-id` (project number `your-project-number`) |
| **Region** | `us-east4` |
| **GPU** | 1x NVIDIA L4 (24 GB VRAM), no zonal redundancy |
| **CPU / Memory** | 8 vCPU / 32 GiB per instance |
| **Concurrency** | 1 (one request per instance at a time) |
| **Max instances** | 1 (limited by memory quota; see [Quota Management](#8-quota-management)) |
| **Min instances** | 0 (scales to zero when idle) |
| **Container port** | 8080 |
| **Image** | `gcr.io/your-project-id/cap-cdss` |
| **Model** | `google/medgemma-1.5-4b-it` (~8 GB bfloat16, downloaded from HuggingFace at startup) |
| **Service URL** | `https://your-service-url` |

### Architecture in Production

```
Browser → Cloud Run reverse proxy → uvicorn (1 worker, port 8080)
                                       ├── FastAPI serves /api/* endpoints
                                       ├── StaticFiles serves Vite SPA (/)
                                       └── /api/run/{case_id} → SSE stream
                                             ├── Graph thread (LangGraph pipeline)
                                             ├── Queue bridge (thread → SSE)
                                             └── MedGemma GPU inference (up to 9 calls)
```

---

## 2. Prerequisites

### GCP Setup

```bash
# Authenticate
gcloud auth login
gcloud config set project your-project-id

# Verify project
gcloud projects describe your-project-id

# Check billing is enabled (required for GPU)
gcloud billing projects describe your-project-id
```

### Required APIs

These are auto-enabled by `deploy.sh`, but if you need to do it manually:

```bash
gcloud services enable \
    run.googleapis.com \
    artifactregistry.googleapis.com \
    cloudbuild.googleapis.com \
    --project=your-project-id \
    --quiet
```

### Required Environment Variables

| Variable | Purpose | Where to set |
|----------|---------|-------------|
| `HF_TOKEN` | HuggingFace token for gated MedGemma model access | `deploy.sh` default or `HF_TOKEN=hf_xxx ./deploy.sh` |
| `GCP_PROJECT_ID` | GCP project ID (default: `medgemma-cap-cdss` in deploy.sh) | Shell env or `deploy.sh` |
| `GCP_REGION` | Override region (default: `us-east4`) | Shell env or `deploy.sh` |

### Local Tools

- `gcloud` CLI (authenticated)
- `curl` (for SSE testing)
- `python3` with `json` module (for parsing SSE output)

---

## 3. Building and Deploying

### One-Command Deploy

```bash
./deploy.sh
```

This runs three steps automatically:
1. **Enable APIs** — `gcloud services enable` (idempotent, fast)
2. **Build container** — `gcloud builds submit` (uploads source, builds on Cloud Build)
3. **Deploy to Cloud Run** — `gcloud run deploy` with GPU settings

### Step-by-Step Manual Deploy

If `deploy.sh` fails partway through, you can run each step individually:

#### Step 1: Build the Container Image

```bash
gcloud builds submit \
    --tag gcr.io/your-project-id/cap-cdss \
    --project=your-project-id \
    --timeout=1800
```

**Expected duration:** ~10 minutes
**What happens:** Cloud Build uploads your source (~2.5 MiB), runs the multi-stage Dockerfile (Node frontend build → CUDA Python runtime), pushes image to GCR.

**Monitor build progress:**

```bash
# Get build ID from the submit output, then:
gcloud builds log BUILD_ID --project=your-project-id 2>&1 | tail -20

# Or check build status:
gcloud builds describe BUILD_ID --project=your-project-id --format="value(status)"
# Possible values: QUEUED, WORKING, SUCCESS, FAILURE
```

**Key Dockerfile stages to watch for:**

| Step | What | Duration |
|------|------|----------|
| 4/22 | `npm ci` (frontend deps) | ~15s |
| 6/22 | `npm run build` (TypeScript check + Vite) | ~10s |
| 11/22 | System deps (Python 3.11, git, curl) | ~30s |
| 18/22 | `pip install torch` + `cap_agent[server]` | ~3-5 min (PyTorch is ~2 GB) |
| Image push | Push ~4 GB image layers to GCR | ~2-3 min |

#### Step 2: Deploy to Cloud Run

```bash
gcloud run deploy cap-cdss \
    --image gcr.io/your-project-id/cap-cdss \
    --region us-east4 \
    --project=your-project-id \
    --gpu 1 \
    --gpu-type nvidia-l4 \
    --no-gpu-zonal-redundancy \
    --cpu 8 \
    --memory 32Gi \
    --min-instances 0 \
    --max-instances 1 \
    --concurrency 1 \
    --port 8080 \
    --set-env-vars "HF_TOKEN=${HF_TOKEN}" \
    --allow-unauthenticated \
    --timeout=3600 \
    --no-cpu-throttling \
    --cpu-boost
```

**Expected duration:** ~2-5 minutes (pulling image, provisioning GPU, starting container)

**What the flags mean:**

| Flag | Purpose |
|------|---------|
| `--gpu 1 --gpu-type nvidia-l4` | Allocate 1x L4 GPU (24 GB VRAM) |
| `--no-gpu-zonal-redundancy` | Use cheaper non-redundant GPU quota pool (~36% savings) |
| `--concurrency 1` | One request per instance (MedGemma uses full GPU) |
| `--no-cpu-throttling` | Keep CPU active even when not handling requests (needed for model loading) |
| `--cpu-boost` | Extra CPU during container startup (helps model download) |
| `--timeout=3600` | 1 hour request timeout (pipeline + model download on cold start) |

---

## 4. Post-Deploy Verification

After deployment completes, run these checks in order:

### 4.1 Health Check

```bash
curl -s https://your-service-url/api/health
```

**Expected (GPU instance warm):**
```json
{"status": "ok", "gpu": true}
```

**If cold start:** The first request triggers instance provisioning. Health check may take 30-60 seconds to respond. This is normal.

### 4.2 List Demo Cases

```bash
curl -s https://your-service-url/api/cases | python3 -m json.tool
```

**Expected:** JSON array with 4 cases (`t0`, `t48h`, `day34`, `cr10`).

### 4.3 Run a Pipeline (SSE Stream Test)

```bash
# Stream to file (pipeline takes 3-10 min depending on cold/warm start)
curl -s -N -X POST https://your-service-url/api/run/t0 > /tmp/sse_output.txt &
echo "PID: $!"

# Watch the file grow
tail -f /tmp/sse_output.txt
```

**Expected SSE event sequence:**
```
event: pipeline_start
event: node_start        (load_case)
event: node_complete     (load_case)
event: node_start        (parallel_extraction)
event: sub_node_progress (ehr_narrative, 1/3)
event: sub_node_progress (ehr_structured, 2/3)
event: sub_node_progress (ehr_synthesis, 3/3)
event: sub_node_progress (lab_extraction, 1/2)
event: sub_node_progress (lab_synthesis, 2/2)
event: node_complete     (parallel_extraction)
event: node_start        (severity_scoring)
event: node_complete     (severity_scoring)
event: node_start        (check_contradictions)
event: node_complete     (check_contradictions)
event: node_start        (contradiction_resolution)
event: token_stream      (multiple — thinking + resolution tokens)
event: node_complete     (contradiction_resolution)
event: node_start        (treatment_selection)
event: node_complete     (treatment_selection)
event: node_start        (monitoring_plan)
event: node_complete     (monitoring_plan)
event: node_start        (output_assembly)
event: token_stream      (multiple — clinician summary tokens)
event: node_complete     (output_assembly)
event: pipeline_complete
```

### 4.4 Verify Clinician Summary in SSE Output

After the pipeline completes, verify all data made it through:

```bash
python3 -c "
import json
with open('/tmp/sse_output.txt') as f:
    content = f.read()
lines = content.split('\n')
for i, line in enumerate(lines):
    if line.startswith('event: node_complete') and i+1 < len(lines):
        data_line = lines[i+1]
        if data_line.startswith('data: '):
            data = json.loads(data_line[6:])
            node = data.get('node', '?')
            has_summary = 'clinician_summary' in data
            summary_len = len(data['clinician_summary']) if has_summary and data['clinician_summary'] else 0
            print(f'{node}: has_summary={has_summary}, len={summary_len}')
"
```

**Expected:** `output_assembly` should show `has_summary=True` with a non-zero length (typically 800-1200 chars).

---

## 5. Monitoring a Live Pipeline Run

### Watch Node Completions in Real Time

```bash
# Stream Cloud Run logs filtered to node completions
gcloud logging read \
    'resource.type="cloud_run_revision" AND resource.labels.service_name="cap-cdss" AND textPayload=~"Node complete"' \
    --project=your-project-id \
    --limit=20 \
    --format="value(timestamp,textPayload)" \
    --freshness=10m
```

**Example output:**
```
2026-02-22T04:21:07.962629Z  INFO:server.sse:Node complete: output_assembly (step 8)
2026-02-22T04:20:43.280834Z  INFO:server.sse:Node complete: monitoring_plan (step 7)
2026-02-22T04:20:43.280061Z  INFO:server.sse:Node complete: treatment_selection (step 6)
2026-02-22T04:20:43.279255Z  INFO:server.sse:Node complete: contradiction_resolution (step 5)
2026-02-22T04:18:56.568089Z  INFO:server.sse:Node complete: check_contradictions (step 4)
2026-02-22T04:18:56.567037Z  INFO:server.sse:Node complete: severity_scoring (step 3)
2026-02-22T04:18:56.566450Z  INFO:server.sse:Node complete: parallel_extraction (step 2)
2026-02-22T04:11:26.729404Z  INFO:server.sse:Node complete: load_case (step 1)
```

### Watch Model Loading (Cold Start)

```bash
gcloud logging read \
    'resource.type="cloud_run_revision" AND resource.labels.service_name="cap-cdss" AND textPayload=~"Warm-up|Fetching|safetensors"' \
    --project=your-project-id \
    --limit=10 \
    --format="value(timestamp,textPayload)" \
    --freshness=10m
```

**Key milestones to look for:**
1. `Fetching 2 files:` — Model download from HuggingFace started
2. `Warm-up: text-only forward pass...` — Model loaded, CUDA kernel compilation
3. `Warm-up: image+text forward pass...` — Vision encoder compilation
4. `Warm-up complete.` — Ready for inference

### Watch for Errors

```bash
gcloud logging read \
    'resource.type="cloud_run_revision" AND resource.labels.service_name="cap-cdss" AND (severity="ERROR" OR textPayload=~"Pipeline error|Exception|Traceback")' \
    --project=your-project-id \
    --limit=10 \
    --format="value(timestamp,textPayload)" \
    --freshness=15m
```

---

## 6. Getting Logs

### Recent Logs (All)

```bash
gcloud logging read \
    'resource.type="cloud_run_revision" AND resource.labels.service_name="cap-cdss"' \
    --project=your-project-id \
    --limit=50 \
    --format="value(timestamp,textPayload)" \
    --freshness=15m
```

### Filter by Time Window

```bash
# Logs from a specific time range
gcloud logging read \
    'resource.type="cloud_run_revision" AND resource.labels.service_name="cap-cdss" AND timestamp>="2026-02-22T04:00:00Z" AND timestamp<="2026-02-22T05:00:00Z"' \
    --project=your-project-id \
    --limit=100 \
    --format="value(timestamp,textPayload)"
```

### HTTP Request Logs

```bash
gcloud logging read \
    'resource.type="cloud_run_revision" AND resource.labels.service_name="cap-cdss" AND httpRequest.requestUrl!=""' \
    --project=your-project-id \
    --limit=20 \
    --format="value(timestamp,httpRequest.requestUrl,httpRequest.status,httpRequest.latency)"
```

### GPU Call Timing

```bash
gcloud logging read \
    'resource.type="cloud_run_revision" AND resource.labels.service_name="cap-cdss" AND textPayload=~"pad_token_id|Setting"' \
    --project=your-project-id \
    --limit=20 \
    --format="value(timestamp,textPayload)" \
    --freshness=15m
```

Each `Setting pad_token_id to eos_token_id:1` line marks a MedGemma GPU call. Count them and diff timestamps to measure per-call latency.

### Export Full Logs to File

```bash
gcloud logging read \
    'resource.type="cloud_run_revision" AND resource.labels.service_name="cap-cdss"' \
    --project=your-project-id \
    --limit=500 \
    --format=json \
    --freshness=30m > /tmp/cloudrun_logs.json
```

---

## 7. Debugging Common Issues

### 7.1 Cold Start Timeout

**Symptom:** First request after scale-to-zero takes 5-10 minutes or times out.

**Cause:** Model download from HuggingFace Hub (~8 GB) on every cold start.

**Timeline of a cold start:**
| Phase | Duration | What happens |
|-------|----------|--------------|
| Instance provisioning | ~10-15s | Cloud Run allocates GPU + container |
| Container startup | ~5-10s | Python + uvicorn starts |
| Model download | ~15-30s | 2 safetensor files from HuggingFace |
| Model warm-up | ~5s | 2 forward passes (text + image) to compile CUDA kernels |
| **Total** | **~35-60s** | First request served after this |

**Fixes:**
- Pre-warm before demo: `curl https://your-service-url/api/health`
- Set `--min-instances 1` in deploy.sh to keep one instance always warm ($1.65/hr always-on cost)
- Future: bake model weights into Docker image (Google recommends this for <10 GB models)

**Debug:**
```bash
# Check if model download is happening
gcloud logging read \
    'resource.type="cloud_run_revision" AND resource.labels.service_name="cap-cdss" AND textPayload=~"Fetching|safetensors|Warm-up"' \
    --project=your-project-id --limit=10 \
    --format="value(timestamp,textPayload)" --freshness=10m
```

### 7.2 Pipeline Hangs (No Node Completions)

**Symptom:** `node_start` emitted but no `node_complete` for minutes.

**Likely cause:** GPU inference running (especially `parallel_extraction` with 8 calls).

**Debug:**
```bash
# Check what the last completed node was
gcloud logging read \
    'resource.type="cloud_run_revision" AND resource.labels.service_name="cap-cdss" AND textPayload=~"Node complete"' \
    --project=your-project-id --limit=5 \
    --format="value(timestamp,textPayload)" --freshness=15m
```

**Normal durations (warm instance):**
| Node | Expected Duration |
|------|-------------------|
| load_case | <1s |
| parallel_extraction | 2-5 min (8 GPU calls) |
| severity_scoring | <1s |
| check_contradictions | <1s |
| contradiction_resolution | 30s-2 min (1 GPU call) |
| treatment_selection | <1s |
| monitoring_plan | <1s |
| output_assembly | 20-30s (1 GPU call) |

### 7.3 Instance Busy / Can't Access Website

**Symptom:** Browser hangs or gets no response from the service URL.

**Cause:** With `--concurrency 1`, only one request is handled at a time. If a pipeline is running (including orphaned runs from closed browser tabs), all other requests queue.

**Debug:**
```bash
# Check if a pipeline is actively running
gcloud logging read \
    'resource.type="cloud_run_revision" AND resource.labels.service_name="cap-cdss" AND textPayload=~"Node complete"' \
    --project=your-project-id --limit=3 \
    --format="value(timestamp,textPayload)" --freshness=5m
```

If nodes are still completing, the instance is busy. Wait for `output_assembly (step 8)` to appear.

**Workaround:** Increase `--max-instances` to allow a second instance to serve static files. See [Quota Management](#8-quota-management) — this requires sufficient CPU/memory quota.

**Important:** Closing the browser does NOT cancel a running pipeline. The graph thread is a daemon thread that runs to completion regardless of client disconnection. There is no cancellation mechanism.

### 7.4 Build Fails

**Symptom:** `gcloud builds submit` returns FAILURE.

**Debug:**
```bash
# Get the build ID from the error output, then:
gcloud builds log BUILD_ID --project=your-project-id 2>&1 | tail -50
```

**Common build failures:**

| Error | Cause | Fix |
|-------|-------|-----|
| `npm run build` fails | TypeScript error in frontend | Run `cd frontend && npm run build` locally first |
| `pip install torch` timeout | Cloud Build network issue | Retry (transient) |
| `pip install -e ".[server]"` fails | Missing dependency in pyproject.toml | Check `[project.optional-dependencies] server` |
| Image push timeout | Large image (~4 GB) | Retry or increase `--timeout` |

### 7.5 Deploy Fails with Quota Error

**Symptom:** `gcloud run deploy` fails with `Quota violated`.

**Debug:**
```bash
# Check which quota was exceeded
# The error message tells you exactly which quota and the values
# e.g.: CpuAllocPerProjectRegion requested: 24000 allowed: 20000
```

See [Quota Management](#8-quota-management) for how to check and request increases.

### 7.6 SSE Stream Drops / Buffering

**Symptom:** Frontend gets all data at once instead of streaming, or connection drops mid-pipeline.

**Cause:** Missing `X-Accel-Buffering: no` header, or proxy timeout.

**Verify headers are set** (in `server/main.py`):
```python
return StreamingResponse(generator, media_type="text/event-stream", headers={
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",  # Critical for Cloud Run
})
```

**Verify heartbeats are working** (should see `: keepalive` every 15s in raw SSE):
```bash
curl -s -N -X POST https://your-service-url/api/run/t0 | head -100
```

### 7.7 HuggingFace Token Error

**Symptom:** Logs show `401 Unauthorized` or `HF_TOKEN not set`.

**Debug:**
```bash
# Check if HF_TOKEN is set in the Cloud Run service
gcloud run services describe cap-cdss \
    --region=us-east4 \
    --project=your-project-id \
    --format="value(spec.template.spec.containers[0].env)"
```

**Fix:** Redeploy with correct token:
```bash
HF_TOKEN=hf_your_correct_token ./deploy.sh
```

---

## 8. Quota Management

### Check Current Quotas

```bash
# GPU quota (L4 GPUs, no zonal redundancy)
gcloud beta quotas info list \
    --service=run.googleapis.com \
    --project=your-project-id \
    --filter="quotaId:GpuAllocNzPerProjectRegion" \
    --format=json 2>&1 | python3 -c "
import sys, json
data = json.load(sys.stdin)
for item in data:
    for dim in item.get('dimensionsInfos', []):
        region = dim.get('dimensions', {}).get('region', '?')
        value = dim.get('details', {}).get('value', '0')
        if int(value) > 0:
            print(f'{region}: {value} L4 GPUs')
"
```

**Current quotas (as of 2026-02-22):**

| Quota | Value | Limit for |
|-------|-------|-----------|
| GPU (L4, no zonal redundancy) in us-east4 | 3 | Up to 3 GPU instances |
| CPU per region | 24,000m | 3 instances × 8 vCPU (recently approved from 20,000m) |
| Memory per region | 40 GiB | Only 1 instance × 32 GiB (increase pending) |

### Request Quota Increase via CLI

```bash
# CPU quota increase
gcloud beta quotas preferences create \
    --service=run.googleapis.com \
    --project=your-project-id \
    --quota-id=CpuAllocPerProjectRegion \
    --preferred-value=24000 \
    --dimensions=region=us-east4 \
    --justification="Need N GPU instances with 8 vCPU each" \
    --email=your-email@example.com

# Memory quota increase
gcloud beta quotas preferences create \
    --service=run.googleapis.com \
    --project=your-project-id \
    --quota-id=MemAllocPerProjectRegion \
    --preferred-value=107374182400 \
    --dimensions=region=us-east4 \
    --justification="Need N GPU instances with 32GiB each" \
    --email=your-email@example.com
```

### Check Quota Request Status

```bash
# Get the preference ID from the create output, then:
gcloud beta quotas preferences describe PREFERENCE_ID \
    --project=your-project-id \
    --format="value(quotaId,quotaConfig.preferredValue,quotaConfig.grantedValue,reconciling)"
```

- `reconciling=True` → Still pending review
- `reconciling` absent + `grantedValue` matches `preferredValue` → Approved
- `grantedValue` < `preferredValue` → Partially approved or denied

### Quota Console UI

View and manage quotas in the browser:
- **All quotas:** `https://console.cloud.google.com/iam-admin/quotas?project=your-project-id`
- **Increase requests:** `https://console.cloud.google.com/iam-admin/quotas/qirs?project=your-project-id`

Filter by: Service = `Cloud Run Admin API`, Region = `us-east4`

### Quota Math for Multi-Instance

| Instances | GPU (L4) | CPU | Memory |
|-----------|----------|-----|--------|
| 1 | 1 | 8,000m | 32 GiB (34,359,738,368 bytes) |
| 2 | 2 | 16,000m | 64 GiB (68,719,476,736 bytes) |
| 3 | 3 | 24,000m | 96 GiB (103,079,215,104 bytes) |

---

## 9. Updating Without Full Redeploy

### Change Cloud Run Settings Only (No Rebuild)

For settings-only changes (scaling, env vars, timeouts), skip the build step:

```bash
# Example: change max-instances
gcloud run services update cap-cdss \
    --max-instances 2 \
    --region us-east4 \
    --project your-project-id

# Example: update env vars
gcloud run services update cap-cdss \
    --set-env-vars "HF_TOKEN=hf_new_token" \
    --region us-east4 \
    --project your-project-id
```

### Check Current Service Configuration

```bash
# Full service description
gcloud run services describe cap-cdss \
    --region=us-east4 \
    --project=your-project-id

# Just the URL
gcloud run services describe cap-cdss \
    --region=us-east4 \
    --project=your-project-id \
    --format='value(status.url)'

# Current revision
gcloud run revisions list \
    --service=cap-cdss \
    --region=us-east4 \
    --project=your-project-id \
    --format="table(name,spec.containerConcurrency,status.conditions[0].status)"
```

### Check Existing Service State

```bash
gcloud run services list \
    --project=your-project-id \
    --region=us-east4 \
    --format="table(name,status.url)"
```

---

## 10. Pipeline Lifecycle and Cold Starts

### What Happens on First Request (Cold Start)

```
t=0s    Cloud Run receives request
t=10s   GPU instance provisioned, container starting
t=15s   uvicorn running, FastAPI app loaded
t=15s   /api/run/t0 received → load_case node runs
t=16s   parallel_extraction starts → triggers get_model_and_processor()
t=16s   Model download begins (2 safetensor shards from HuggingFace Hub)
t=45s   Model loaded to GPU (bfloat16, SDPA attention)
t=46s   Warm-up: text-only forward pass (CUDA kernel compile)
t=48s   Warm-up: image+text forward pass (SigLIP vision encoder compile)
t=50s   Warm-up complete → first real GPU call begins
t=50s+  8 extraction GPU calls run sequentially (each 5-30s)
...     Pipeline continues through 8 nodes
t=~5min Pipeline complete
```

### What Happens on Subsequent Requests (Warm Instance)

```
t=0s    Request received (instance already warm)
t=0s    load_case: instant
t=0s    parallel_extraction: 8 GPU calls (model already in memory)
t=~3min Pipeline complete (no download, no warm-up)
```

### Instance Idle Timeout

- Cloud Run GPU instances have a **~10 minute idle timeout**
- After 10 minutes with no requests, the instance scales to zero
- Next request triggers a cold start
- **Tip:** Before a demo, send a curl to `/api/health` 1-2 minutes ahead to wake the instance

---

## 11. SSE Stream Debugging

### Capture Raw SSE Stream

```bash
# Full capture (wait for pipeline_complete)
curl -s -N -X POST https://your-service-url/api/run/t0 > /tmp/sse_raw.txt

# Watch in real time
curl -s -N -X POST https://your-service-url/api/run/t0
```

### Parse SSE Events from Captured Output

```bash
# Count events by type
grep "^event:" /tmp/sse_raw.txt | sort | uniq -c | sort -rn

# Extract all node_complete events
python3 -c "
import json
with open('/tmp/sse_raw.txt') as f:
    content = f.read()
lines = content.split('\n')
for i, line in enumerate(lines):
    if line.startswith('event: node_complete') and i+1 < len(lines):
        data_line = lines[i+1]
        if data_line.startswith('data: '):
            data = json.loads(data_line[6:])
            print(f\"Step {data['step']}: {data['node']} ({data['label']})\")
"
```

### Verify a Specific Field Exists in SSE

```bash
# Check if clinician_summary is in output_assembly event
python3 -c "
import json
with open('/tmp/sse_raw.txt') as f:
    content = f.read()
lines = content.split('\n')
for i, line in enumerate(lines):
    if line.startswith('event: node_complete') and i+1 < len(lines):
        data_line = lines[i+1]
        if 'output_assembly' in data_line:
            data = json.loads(data_line[6:])
            for key in ['clinician_summary', 'structured_output']:
                present = key in data
                val_len = len(str(data.get(key, '')))
                print(f'{key}: present={present}, length={val_len}')
"
```

### Count Token Stream Events

```bash
# How many token batches were sent
grep -c "token_stream" /tmp/sse_raw.txt

# Count keepalive heartbeats
grep -c "keepalive" /tmp/sse_raw.txt
```

---

## 12. Concurrency and Scaling

### Current Setup: Single Instance, Single Concurrency

- `--max-instances 1` + `--concurrency 1` = one pipeline at a time
- If a pipeline is running, all other requests (including static file serving) **queue**
- Closing the browser does NOT cancel a running pipeline (no cancellation mechanism)

### Why concurrency=1

Cloud Run GPU has a **known autoscaling bug** with `concurrency > 1`:
- Autoscaling uses request concurrency as the scaling signal
- With concurrency > 1, the scheduler may route multiple requests to the same GPU instance
- MedGemma 4B uses full GPU memory — concurrent inference causes OOM

### Scaling to Multiple Instances

To support concurrent users (e.g., multiple judges testing simultaneously):

1. Increase `--max-instances` (e.g., 3)
2. Ensure sufficient quota (see [Quota Management](#8-quota-management)):
   - GPU: N L4 GPUs
   - CPU: N × 8,000m
   - Memory: N × 32 GiB (in bytes)
3. Cost: ~$1.65/hr per active instance, $0 when scaled to zero

```bash
gcloud run services update cap-cdss \
    --max-instances 3 \
    --region us-east4 \
    --project your-project-id
```

### Session Affinity (Optional)

For SSE reconnections, add `--session-affinity` to route the same client to the same instance:

```bash
gcloud run services update cap-cdss \
    --session-affinity \
    --region us-east4 \
    --project your-project-id
```

---

## 13. Cost Management

### Billing Model

Cloud Run GPU uses **instance-based billing** (not request-based):
- Billed for the full lifecycle of each instance (startup → idle timeout)
- GPU idle timeout: ~10 minutes after last request
- No charge when scaled to zero

### Cost Breakdown (us-east4, no zonal redundancy)

| Resource | Rate | Per instance |
|----------|------|-------------|
| NVIDIA L4 GPU | ~$0.70/hr | $0.70/hr |
| 8 vCPU | ~$0.70/hr | $0.70/hr |
| 32 GiB RAM | ~$0.25/hr | $0.25/hr |
| **Total** | | **~$1.65/hr** |

### Cost Scenarios

| Scenario | Monthly Cost |
|----------|-------------|
| Demo only (2 hrs/day, 5 days/week) | ~$33 |
| Always-on (min-instances=1) | ~$1,200 |
| Burst (3 instances, 1 hr/day) | ~$100 |
| Zero traffic | $0 |

### Monitor Spending

```bash
# Check current billing
gcloud billing accounts list
# Then view in console: https://console.cloud.google.com/billing?project=your-project-id
```

---

## 14. Known Issues and Workarounds

### Orphaned Pipeline Runs

**Issue:** Closing browser tab doesn't cancel running pipeline. Graph thread completes to the end.

**Impact:** Instance is blocked for 2-5 minutes. New requests queue.

**Workaround:** Wait for pipeline to finish. Monitor with node completion logs.

**Future fix needed:** Add `threading.Event` cancellation token to graph thread, check between GPU calls.

### Memory Quota Blocks Multi-Instance

**Issue:** Default memory quota (40 GiB) only supports 1 instance at 32 GiB.

**Status:** Quota increase request submitted (107 GiB requested, pending review).

**Workaround:** Could reduce per-instance memory to 16 GiB (MedGemma 4B uses ~12 GiB total: 8 GB VRAM + 4 GB host RAM), allowing 2 instances within 40 GiB quota.

### Model Download on Every Cold Start

**Issue:** ~8 GB model downloaded from HuggingFace on every cold start.

**Impact:** 15-30s added to first request.

**Future fix:** Bake model into Docker image (Google recommends for <10 GB models). Would increase image size to ~12 GB but eliminate download latency.

### No Startup Probe

**Issue:** `/api/health` returns `{"status": "ok"}` immediately on container start, before model is loaded. Traffic may be routed to instance that isn't ready for inference.

**Impact:** First pipeline request triggers model download mid-request (works, but slow).

**Future fix:** Gate `/api/health` on model readiness:
```python
@app.get("/api/health")
def health():
    if GPU_AVAILABLE:
        from cap_agent.models.medgemma import _model
        if _model is None:
            return JSONResponse({"status": "loading", "gpu": True}, status_code=503)
    return {"status": "ok", "gpu": GPU_AVAILABLE}
```

Then add startup probe to deploy.sh:
```bash
--startup-probe httpGet.path=/api/health,httpGet.port=8080,initialDelaySeconds=0,failureThreshold=20,timeoutSeconds=5,periodSeconds=10
```

---

## 15. Quick Reference Commands

### Deployment

```bash
# Full deploy (build + push + deploy)
./deploy.sh

# Build only (no deploy)
gcloud builds submit --tag gcr.io/your-project-id/cap-cdss --project=your-project-id --timeout=1800

# Deploy only (reuse existing image)
gcloud run deploy cap-cdss --image gcr.io/your-project-id/cap-cdss --region us-east4 --project=your-project-id [flags...]

# Update settings only (no rebuild)
gcloud run services update cap-cdss --max-instances 2 --region us-east4 --project your-project-id
```

### Health and Testing

```bash
# Health check
curl -s https://your-service-url/api/health

# List cases
curl -s https://your-service-url/api/cases | python3 -m json.tool

# Run pipeline (capture full SSE output)
curl -s -N -X POST https://your-service-url/api/run/t0 > /tmp/sse_output.txt
```

### Logs

```bash
# All recent logs
gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="cap-cdss"' --project=your-project-id --limit=50 --format="value(timestamp,textPayload)" --freshness=15m

# Node completions only
gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="cap-cdss" AND textPayload=~"Node complete"' --project=your-project-id --limit=10 --format="value(timestamp,textPayload)" --freshness=15m

# Errors only
gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="cap-cdss" AND severity="ERROR"' --project=your-project-id --limit=10 --format="value(timestamp,textPayload)" --freshness=30m

# Model loading progress
gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="cap-cdss" AND textPayload=~"Warm-up|Fetching|safetensors"' --project=your-project-id --limit=10 --format="value(timestamp,textPayload)" --freshness=10m

# HTTP requests
gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="cap-cdss" AND httpRequest.requestUrl!=""' --project=your-project-id --limit=20 --format="value(timestamp,httpRequest.requestUrl,httpRequest.status)"
```

### Quota

```bash
# Check GPU quota
gcloud beta quotas info list --service=run.googleapis.com --project=your-project-id --filter="quotaId:GpuAllocNzPerProjectRegion" --format=json

# Check CPU/memory quota
gcloud beta quotas info list --service=run.googleapis.com --project=your-project-id --filter="quotaId:CpuAllocPerProjectRegion OR quotaId:MemAllocPerProjectRegion" --format=json

# Check quota request status
gcloud beta quotas preferences describe PREFERENCE_ID --project=your-project-id --format="value(quotaId,quotaConfig.preferredValue,quotaConfig.grantedValue,reconciling)"
```

### Service Info

```bash
# Service URL
gcloud run services describe cap-cdss --region=us-east4 --project=your-project-id --format='value(status.url)'

# Current revision
gcloud run revisions list --service=cap-cdss --region=us-east4 --project=your-project-id --format="table(name,status.conditions[0].status)"

# List all services
gcloud run services list --project=your-project-id --region=us-east4 --format="table(name,status.url)"
```

### Build

```bash
# Check build status
gcloud builds describe BUILD_ID --project=your-project-id --format="value(status)"

# Build logs
gcloud builds log BUILD_ID --project=your-project-id 2>&1 | tail -30

# List recent builds
gcloud builds list --project=your-project-id --limit=5
```

---

## Appendix: Observed Pipeline Timings

From production runs on 2026-02-22 (warm instance, no CXR image):

| Run | parallel_extraction | contradiction_resolution | output_assembly | Total |
|-----|--------------------|-----------------------|----------------|-------|
| First (cold + model download) | ~7.5 min | ~1:47 | ~24s | ~9.5 min |
| Second (warm) | ~3:57 | ~1:41 | ~26s | ~6.5 min |
| Third (warm, cached) | ~3:38 | ~1:14 | ~25s | ~5.5 min |

Load_case, severity_scoring, check_contradictions, treatment_selection, and monitoring_plan are all <1s (deterministic, no GPU).

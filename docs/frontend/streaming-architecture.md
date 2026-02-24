# Streaming Architecture

> Token-level SSE streaming from MedGemma inference to React dashboard.

---

## Design Rationale

GPU calls take 2-7 seconds each. Without streaming, the UI shows nothing during inference — the user stares at a skeleton for the entire duration of `contradiction_resolution` and `output_assembly`. Token streaming fills this gap by pushing generated tokens to the frontend as they're produced, giving the clinician real-time visibility into the model's reasoning.

Sub-node progress serves a similar purpose for `parallel_extraction`, where 8 sequential GPU calls execute without any intermediate node completion events. Progress callbacks report which extraction step is active (e.g., "Synthesizing clinical data (2/3)").

---

## Queue Bridge Pattern

The streaming architecture uses a **queue bridge** to decouple the LangGraph execution thread from the SSE HTTP response generator.

### Why Separate Threads?

LangGraph's `graph.stream()` is a blocking generator. Streaming tokens from `TextIteratorStreamer` requires draining a separate thread's output. The SSE generator must also inject heartbeats and batch tokens on a timer. A queue bridge solves all three:

```
Graph Thread (background)              SSE Generator (main thread)
──────────────────────                 ─────────────────────────
graph.stream() blocks                  queue.get(timeout=0.05)
    ↓                                      ↓
Node functions execute                 Drain all available events
    ↓                                      ↓
Callbacks push to queue:               Batch tokens (50ms window)
  ("node_start", {...})                    ↓
  ("sub_node_progress", {...})         Yield SSE event strings
  ("token", {token, is_thinking})          ↓
  ("node_complete", {...})             Inject heartbeat (15s)
    ↓                                      ↓
_SENTINEL pushed on completion         Break on _SENTINEL
```

### Queue Event Types

| Event tuple | Pushed by | Consumed as |
|-------------|-----------|-------------|
| `("node_start", {node, label, step})` | `stream_pipeline` loop | SSE `node_start` |
| `("sub_node_progress", {node, sub_node, label, gpu_call, total})` | `progress_callback` | SSE `sub_node_progress` |
| `("token", {token, is_thinking})` | `token_callback` | Batched into SSE `token_stream` |
| `("node_complete", {node, label, step, ...state})` | `stream_pipeline` loop | SSE `node_complete` |
| `_SENTINEL` | Graph thread on exit | Terminates generator |

### Sentinel Termination

`_SENTINEL = object()` is a module-level singleton. The graph thread pushes it to the queue on both success and error paths (via `finally` block). The SSE generator breaks its drain loop when it encounters the sentinel.

---

## Token Batching

### Problem

Emitting one SSE event per token creates excessive TCP overhead — each event is a separate HTTP chunk with headers. At ~30 tokens/second, this means 30 HTTP chunks/second.

### Solution

`_TOKEN_BATCH_MS = 50` — The SSE generator accumulates tokens in a `token_batch: list[dict]` and flushes them as a single `token_stream` SSE event every 50ms:

```python
# Flush condition
if token_batch and (now - last_token_flush) >= _TOKEN_BATCH_MS / 1000:
    yield _sse_event("token_stream", {"node": current_node, "tokens": token_batch})
    token_batch = []
    last_token_flush = now
```

This reduces SSE events from ~30/s to ~20/s while keeping perceived latency under 50ms.

Token batches are also flushed immediately before `sub_node_progress` and `node_complete` events to prevent tokens from appearing after their containing node completes.

---

## Heartbeat

`_HEARTBEAT_INTERVAL = 15` — Every 15 seconds of inactivity, the SSE generator yields a comment:

```
: keepalive
```

### Why 15 Seconds?

Cloud Run's reverse proxy buffers responses by default. The `X-Accel-Buffering: no` header disables this, but some proxy layers (nginx, load balancers) may still timeout idle connections after 30-60 seconds. A 15-second heartbeat provides a 2x safety margin.

SSE comments (lines starting with `:`) are silently ignored by the browser's `EventSource` API and by our manual `ReadableStream` parser. They serve purely as keepalive signals.

---

## Thinking Tokens

MedGemma uses `<unused94>` and `<unused95>` as thinking token delimiters. These survive `skip_special_tokens=True` in the tokenizer.

### Detection in Stream

`call_medgemma_streaming()` tracks an `in_thinking` boolean:

```python
if "<unused94>" in token_text:
    in_thinking = True
    token_text = token_text.replace("<unused94>", "")
elif "<unused95>" in token_text:
    in_thinking = False
    token_text = token_text.replace("<unused95>", "")

if token_text.strip() and token_callback:
    token_callback(token_text, in_thinking)
```

### Frontend Rendering

The `usePipelineStream` reducer routes tokens to separate buffers:

- `is_thinking: true` → `streamingThinking` (dimmed, italic text in `contradiction-alerts.tsx`)
- `is_thinking: false` → `streamingText` (normal text in `clinician-summary.tsx` or `contradiction-alerts.tsx`)

Only the last 150 characters of `streamingThinking` are displayed (with gradient fade) to avoid overwhelming the UI with internal reasoning.

---

## Which Nodes Stream

| Node | Token streaming | Thinking | Sub-node progress | Rationale |
|------|----------------|----------|-------------------|-----------|
| `parallel_extraction` | No | No | Yes (8 sub-steps) | Multiple short GPU calls; progress is more useful than tokens |
| `contradiction_resolution` | Yes | Yes | No | Single long GPU call; thinking reveals clinical reasoning |
| `output_assembly` | Yes | No | No | Single long GPU call; tokens show summary being written |

Other nodes (load_case, severity_scoring, check_contradictions, treatment_selection, monitoring_plan) are deterministic CPU operations — they complete in <100ms and don't benefit from streaming.

### Why Not Stream Extraction Tokens?

Extraction calls use `enable_thinking=False` and produce structured JSON. Streaming JSON tokens would be meaningless to clinicians. Sub-node progress ("Extracting lab values (2/3)") provides better UX for these calls.

---

## Frontend Rendering

### Two-Buffer Pattern

The frontend maintains two separate text buffers for streaming:

| Buffer | State field | Populated by | Rendered in |
|--------|-------------|-------------|-------------|
| Response | `streamingText` | `TOKEN_STREAM` with `is_thinking: false` | `clinician-summary.tsx`, `contradiction-alerts.tsx` |
| Thinking | `streamingThinking` | `TOKEN_STREAM` with `is_thinking: true` | `contradiction-alerts.tsx` (dimmed) |

Both buffers are cleared when their source node emits `NODE_COMPLETE`.

### Visual Elements

- **Blinking cursor:** Appended to `streamingText` during active streaming
- **Word count:** Displayed during streaming to show progress
- **Gradient fade:** Bottom fade on capped-height containers (`max-h-48`) during streaming
- **Sub-node label:** Shown in `pipeline-progress.tsx` with pulsing cyan dot and GPU call counter

---

## Testing

### Local Verification with `./dev.sh`

1. Start the full stack: `./dev.sh`
2. The backend auto-detects `GPU_AVAILABLE=False` and uses the mock runner
3. Open `http://localhost:5173` in browser
4. Click any demo case in the sidebar

### What to Look For in Mock Mode

| Phase | Expected behavior |
|-------|-------------------|
| Extraction (node 2) | Sub-node label appears below pipeline progress, cycles through 8 steps with 0.6s delay each |
| Contradiction resolution (node 5) | Thinking text appears in dimmed italic, followed by resolution text |
| Output assembly (node 8) | Summary text streams word-by-word with blinking cursor |
| Between nodes | Node start/complete transitions, no streaming |

### Verifying SSE Events

```bash
# Watch raw SSE events
curl -X POST http://localhost:8000/api/run/t0 -N
```

Expected event sequence:
```
event: pipeline_start
event: node_start        (load_case)
event: node_complete     (load_case)
event: node_start        (parallel_extraction)
event: sub_node_progress (8 times)
event: node_complete     (parallel_extraction)
...
event: node_start        (output_assembly)
event: token_stream      (multiple, batched)
event: node_complete     (output_assembly)
event: pipeline_complete
```

---

## Constants Reference

| Constant | Value | File | Purpose |
|----------|-------|------|---------|
| `_SENTINEL` | `object()` | `server/sse.py` | Graph thread completion signal |
| `_TOKEN_BATCH_MS` | `50` | `server/sse.py` | Token flush interval (ms) |
| `_HEARTBEAT_INTERVAL` | `15` | `server/sse.py` | SSE keepalive interval (s) |
| `SUB_NODE_DELAY` | `0.6` | `server/mock_runner.py` | Mock extraction step delay (s) |
| `TOKEN_DELAY` | `0.06` | `server/mock_runner.py` | Mock token emission delay (s, ~60 WPM) |
| `EXTRACTION_SUB_NODES` | 8 entries | `server/mock_runner.py` | Mock extraction sub-step labels |

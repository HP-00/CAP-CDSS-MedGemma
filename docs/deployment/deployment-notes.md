# Deployment Notes

Quick reference for deployment constraints. For the full playbook, see [cloud-run-deployment-and-debugging-playbook.md](cloud-run-deployment-and-debugging-playbook.md).

## Cloud Run L4 GPU Constraints

- **Single worker only:** `--workers 1` in Dockerfile. MedGemma 4B fills GPU memory; multiple workers would OOM.
- **Concurrency 1:** Each pipeline run uses the full GPU. Concurrent requests queue.
- **Cold start ~60s:** Model loading (4B params + SDPA compilation + SigLIP vision encoder warm-up).
- **GPU type:** NVIDIA L4 (24GB VRAM). Sufficient for MedGemma 4B in bfloat16.
- **Memory:** 32Gi RAM required alongside GPU for model loading and FHIR parsing.

## SSE Streaming Requirements

- **`X-Accel-Buffering: no` header is critical:** Without it, Cloud Run's reverse proxy buffers the entire response, defeating token-level streaming. Set in `server/sse.py`.
- **Heartbeat every 15s:** SSE comment (`: keepalive`) prevents proxy timeout. Cloud Run has a 60s idle timeout.
- **Token batching (50ms):** Reduces TCP overhead while maintaining perceived real-time streaming.

## Token Management

- **Never hardcode tokens.** `deploy.sh` uses `${HF_TOKEN:?...}` to require the caller to set it.
- **HF_TOKEN** is passed as a Cloud Run environment variable via `--set-env-vars`.
- The token grants access to `google/medgemma-1.5-4b-it` (gated model).

## Known Limitations

| Issue | Impact | Mitigation |
|-------|--------|------------|
| Single concurrent request | Queue forms under load | Scale horizontally with multiple services (cost trade-off) |
| Cold start ~60s | First request after idle is slow | `--min-instances 1` keeps one instance warm (but costs ~$5/day) |
| No persistent storage | Pipeline results are ephemeral | Results returned in SSE stream; client renders and caches |
| Cloud Build timeout | Large Docker image (~8GB) | `--timeout=1800` in deploy.sh |

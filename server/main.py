"""FastAPI server — serves API endpoints + built Vite SPA."""

import logging
import os
import tempfile
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from server.demo_cases import get_case_list, build_case

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="CAP CDSS", version="0.1.0")

# CXR upload directory
CXR_DIR = Path(tempfile.mkdtemp(prefix="cap_cxr_"))

# Detect GPU availability
try:
    import torch
    GPU_AVAILABLE = torch.cuda.is_available()
except ImportError:
    GPU_AVAILABLE = False

logger.info("GPU available: %s", GPU_AVAILABLE)


# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health():
    return {"status": "ok", "gpu": GPU_AVAILABLE}


@app.get("/api/cases")
def list_cases():
    return get_case_list()


@app.post("/api/run/{case_id}")
def run_pipeline(case_id: str, force_mock: bool = Query(False)):
    """Run pipeline for a demo case, streaming SSE events."""
    try:
        case_data = build_case(case_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # Check for uploaded CXR
    cxr_files = list(CXR_DIR.glob("*.png")) + list(CXR_DIR.glob("*.jpg"))
    cxr_path = str(cxr_files[0]) if cxr_files else None

    # Select real or mock runner (force_mock overrides GPU detection)
    if GPU_AVAILABLE and not force_mock:
        from server.sse import stream_pipeline
        generator = stream_pipeline(case_data, cxr_path)
    else:
        from server.mock_runner import stream_pipeline_mock
        generator = stream_pipeline_mock(case_data, cxr_path)

    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/upload-cxr")
async def upload_cxr(file: UploadFile = File(...)):
    """Upload a CXR image for pipeline analysis."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in (".png", ".jpg", ".jpeg", ".dcm"):
        raise HTTPException(status_code=400, detail="Unsupported file type")

    dest = CXR_DIR / f"cxr_upload{suffix}"
    content = await file.read()
    dest.write_bytes(content)

    return {"filename": dest.name, "path": str(dest), "size": len(content)}


@app.get("/api/case/{case_id}/data")
def get_case_data(case_id: str):
    """Return raw case data for data source inspection."""
    try:
        case_data = build_case(case_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # Sanitize: remove filesystem paths, keep clinically relevant data
    sanitized = {
        "case_id": case_data.get("case_id", case_id),
        "patient_id": case_data.get("patient_id"),
        "fhir_bundle": case_data.get("fhir_bundle"),
        "lab_report": case_data.get("lab_report"),
        "cxr_findings": None,
        "micro_results": case_data.get("micro_results"),
        "admission_labs": case_data.get("admission_labs"),
        "treatment_status": case_data.get("treatment_status"),
        "allergies": case_data.get("allergies"),
    }
    return sanitized


@app.get("/api/cxr/{filename}")
def serve_cxr(filename: str):
    """Serve an uploaded CXR image."""
    path = CXR_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="CXR not found")
    return FileResponse(path)


@app.get("/api/case/{case_id}/cxr-image")
def get_case_cxr_image(case_id: str):
    """Serve the CXR image for a demo case."""
    try:
        case_data = build_case(case_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    image_path = case_data.get("cxr", {}).get("image_path")
    if not image_path or not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail="No CXR image")
    return FileResponse(image_path, media_type="image/png")


# ---------------------------------------------------------------------------
# Static file serving (Vite build output) — MUST be last
# ---------------------------------------------------------------------------

STATIC_DIR = Path(__file__).parent / "static"
if STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="spa")

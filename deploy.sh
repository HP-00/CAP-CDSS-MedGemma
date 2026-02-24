#!/usr/bin/env bash
# =============================================================================
# CAP CDSS — Cloud Run GPU Deployment Script
#
# Prerequisites:
#   1. gcloud CLI installed and authenticated
#   2. GCP project with billing enabled
#   3. HF_TOKEN for MedGemma access
#
# Usage:
#   ./deploy.sh                    # Deploy with defaults
#   HF_TOKEN=hf_xxx ./deploy.sh   # Deploy with explicit token
# =============================================================================

set -euo pipefail

# Configuration — edit these for your setup
PROJECT_ID="${GCP_PROJECT_ID:-medgemma-cap-cdss}"
REGION="${GCP_REGION:-us-east4}"
HF_TOKEN="${HF_TOKEN:?Error: HF_TOKEN environment variable must be set. Usage: HF_TOKEN=hf_xxx ./deploy.sh}"
SERVICE_NAME="cap-cdss"
IMAGE="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "=== CAP CDSS Cloud Run Deployment ==="
echo "Project:  ${PROJECT_ID}"
echo "Region:   ${REGION}"
echo "Image:    ${IMAGE}"
echo ""

# Step 1: Ensure required APIs are enabled
echo "--- Enabling APIs ---"
gcloud services enable \
    run.googleapis.com \
    artifactregistry.googleapis.com \
    cloudbuild.googleapis.com \
    --project="${PROJECT_ID}" \
    --quiet

# Step 2: Build container with Cloud Build
echo "--- Building container ---"
gcloud builds submit \
    --tag "${IMAGE}" \
    --project="${PROJECT_ID}" \
    --timeout=1800

# Step 3: Deploy to Cloud Run with GPU
echo "--- Deploying to Cloud Run ---"
gcloud run deploy "${SERVICE_NAME}" \
    --image "${IMAGE}" \
    --region "${REGION}" \
    --project="${PROJECT_ID}" \
    --gpu 1 \
    --gpu-type nvidia-l4 \
    --no-gpu-zonal-redundancy \
    --cpu 8 \
    --memory 32Gi \
    --min-instances 0 \
    --max-instances 1 \
    --concurrency 1 \
    --port 8080 \
    --set-env-vars "HF_TOKEN=${HF_TOKEN:-}" \
    --allow-unauthenticated \
    --timeout=3600 \
    --no-cpu-throttling \
    --cpu-boost

# Step 4: Get the URL
echo ""
echo "=== Deployment complete ==="
URL=$(gcloud run services describe "${SERVICE_NAME}" \
    --region="${REGION}" \
    --project="${PROJECT_ID}" \
    --format='value(status.url)')
echo "Service URL: ${URL}"
echo ""
echo "Test with:"
echo "  curl ${URL}/api/health"
echo "  curl ${URL}/api/cases"

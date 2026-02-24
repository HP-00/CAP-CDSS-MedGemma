"""Model constants and configuration for MedGemma 1.5 4B."""

MODEL_ID = "google/medgemma-1.5-4b-it"

MODEL_KWARGS = {
    "attn_implementation": "sdpa",
    "dtype": "bfloat16",  # Resolved to torch.bfloat16 at load time
    "device_map": "auto",
}

# Centralised max_new_tokens budgets for every MedGemma call site.
# See AGENTS.md §4 "Token Budget Guidance" for rationale per entry.
TOKEN_BUDGETS = {
    "lab_extraction": 1000,
    "lab_synthesis": 3500,
    "ehr_narrative_filter": 1000,
    "ehr_structured_filter": 1000,
    "ehr_synthesis": 2000,
    "cxr_classification": 2000,
    "cxr_localization": 1000,
    "cxr_longitudinal": 1200,
    "contradiction_resolution": 800,
    "clinician_summary": 1500,
}

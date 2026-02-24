"""Demo case registry — maps case IDs to rich CXR-powered case builders."""

from cap_agent.data.demo_cases import (
    get_cxr_clear_case,
    get_cxr_bilateral_case,
    get_cxr_normal_case,
    get_cxr_subtle_case,
    get_cxr_effusion_case,
)

DEMO_CASES = {
    "cxr_clear": {
        "id": "cxr_clear",
        "label": "Margaret Thornton — Consolidation with Effusion",
        "description": "50F, asthma + HTN. 4-day productive cough, fever, pleuritic chest pain.",
        "builder": get_cxr_clear_case,
    },
    "cxr_bilateral": {
        "id": "cxr_bilateral",
        "label": "Harold Pemberton — Bilateral Pneumonia",
        "description": "65M, HF + AF + T2DM. Worsening dyspnoea, productive cough, confusion.",
        "builder": get_cxr_bilateral_case,
    },
    "cxr_normal": {
        "id": "cxr_normal",
        "label": "Susan Clarke — Normal CXR",
        "description": "50F, prior effusion history. Acute cough, fever, raised inflammatory markers.",
        "builder": get_cxr_normal_case,
    },
    "cxr_subtle": {
        "id": "cxr_subtle",
        "label": "David Okonkwo — Subtle Findings",
        "description": "50M, previously well. 3-day cough, low-grade fever, mild dyspnoea.",
        "builder": get_cxr_subtle_case,
    },
    "cxr_effusion": {
        "id": "cxr_effusion",
        "label": "Patricia Hennessy — Pleural Effusion",
        "description": "65F, RA on methotrexate. Progressive dyspnoea, pleuritic pain, fever.",
        "builder": get_cxr_effusion_case,
    },
}


def get_case_list() -> list[dict]:
    """Return list of demo cases (without builder functions)."""
    return [
        {"id": c["id"], "label": c["label"], "description": c["description"]}
        for c in DEMO_CASES.values()
    ]


def build_case(case_id: str) -> dict:
    """Build a case from a demo case ID."""
    entry = DEMO_CASES.get(case_id)
    if entry is None:
        raise ValueError(f"Unknown case ID: {case_id}. Available: {list(DEMO_CASES.keys())}")
    return entry["builder"]()

"""Track 1: ~12 RSNA CXR case definitions with placeholder image paths.

5 categories: clear pneumonia, bilateral pneumonia, subtle pneumonia,
normal CXR, and abnormal non-pneumonia. Each has paired FHIR-style clinical
data designed to test specific contradiction rules when combined with real
CXR model output.

Ground truth includes cxr_ground_truth for CXR-specific evaluation.
"""

from benchmark_data.cases.helpers import make_case

# ============================================================================
# Category 1: Clear pneumonia (3 cases) — CXR concordant with clinical data
# ============================================================================

T1_CLEAR_01 = make_case(
    "T1-CLEAR-01",
    cxr_consolidation=True,
    cxr_consolidation_location="right lower lobe",
    crackles=True,
    crackles_location="right lower zone",
    bronchial_breathing=True,
    bronchial_breathing_location="right lower zone",
    crp=120,
)
T1_CLEAR_01["cxr"]["image_path"] = "benchmark_data/rsna/images/clear_pneumonia_001.png"
T1_CLEAR_01["cxr"]["prior_image_path"] = "benchmark_data/rsna/images/normal_001.png"
T1_CLEAR_01["ground_truth"]["cxr_ground_truth"] = {
    "consolidation_present": True,
    "cxr_category": "clear_pneumonia",
    "rsna_patient_id": "097788d4-cb88-4457-8e71-0ca7a3da2216",
    "bboxes_normalized": [[185, 221, 871, 736]],
}

T1_CLEAR_02 = make_case(
    "T1-CLEAR-02",
    cxr_consolidation=True,
    cxr_consolidation_location="left lower lobe",
    crackles=True,
    crackles_location="left lower zone",
    crp=95,
    age=72,
    urea=8.0,
)
T1_CLEAR_02["cxr"]["image_path"] = "benchmark_data/rsna/images/clear_pneumonia_002.png"
T1_CLEAR_02["ground_truth"]["cxr_ground_truth"] = {
    "consolidation_present": True,
    "cxr_category": "clear_pneumonia",
    "rsna_patient_id": "aa47c55a-7cf7-4105-9132-de080664f052",
    "bboxes_normalized": [[101, 513, 885, 879]],
}

T1_CLEAR_03 = make_case(
    "T1-CLEAR-03",
    cxr_consolidation=True,
    cxr_consolidation_location="right middle lobe",
    crackles=True,
    crackles_location="right mid zone",
    bronchial_breathing=True,
    bronchial_breathing_location="right mid zone",
    crp=200,
    age=68,
)
T1_CLEAR_03["cxr"]["image_path"] = "benchmark_data/rsna/images/clear_pneumonia_003.png"
T1_CLEAR_03["ground_truth"]["cxr_ground_truth"] = {
    "consolidation_present": True,
    "cxr_category": "clear_pneumonia",
    "rsna_patient_id": "a3ac5fe9-431c-4c10-8691-d0d26e6a0edd",
    "bboxes_normalized": [[21, 176, 852, 503]],
}

# ============================================================================
# Category 2: Bilateral pneumonia (2 cases) — paired with unilateral crackles → CR-5
# ============================================================================

T1_BILATERAL_01 = make_case(
    "T1-BILATERAL-01",
    cxr_consolidation=True,
    cxr_consolidation_location="bilateral lower lobes",
    crackles=True,
    crackles_location="right lower zone",
    age=65,
    urea=7.1,  # moderate severity to avoid CR-4
    expected_contradictions=["CR-5"],
)
T1_BILATERAL_01["cxr"]["image_path"] = "benchmark_data/rsna/images/bilateral_001.png"
T1_BILATERAL_01["cxr"]["prior_image_path"] = "benchmark_data/rsna/images/normal_002.png"
T1_BILATERAL_01["ground_truth"]["cxr_ground_truth"] = {
    "consolidation_present": True,
    "cxr_category": "bilateral_pneumonia",
    "rsna_patient_id": "8dc8e54b-5b05-4dac-80b9-fa48878621e2",
    "bboxes_normalized": [
        [159, 274, 406, 471],
        [185, 588, 523, 827],
        [480, 194, 922, 455],
        [535, 672, 712, 854],
    ],
}

T1_BILATERAL_02 = make_case(
    "T1-BILATERAL-02",
    cxr_consolidation=True,
    cxr_consolidation_location="bilateral mid and lower zones",
    crackles=True,
    crackles_location="left lower zone",
    age=65,
    urea=7.1,
    expected_contradictions=["CR-5"],
)
T1_BILATERAL_02["cxr"]["image_path"] = "benchmark_data/rsna/images/bilateral_002.png"
T1_BILATERAL_02["ground_truth"]["cxr_ground_truth"] = {
    "consolidation_present": True,
    "cxr_category": "bilateral_pneumonia",
    "rsna_patient_id": "32408669-c137-4e8d-bd62-fe8345b40e73",
    "bboxes_normalized": [
        [358, 293, 771, 514],
        [352, 689, 584, 916],
        [782, 686, 923, 929],
        [836, 267, 935, 495],
    ],
}

# ============================================================================
# Category 3: Subtle pneumonia (2 cases) — borderline CXR, high CRP
# ============================================================================

T1_SUBTLE_01 = make_case(
    "T1-SUBTLE-01",
    cxr_consolidation=True,
    crackles=True,
    crackles_location="right lower zone",
    crp=160,
)
T1_SUBTLE_01["cxr"]["image_path"] = "benchmark_data/rsna/images/subtle_001.png"
T1_SUBTLE_01["cxr"]["prior_image_path"] = "benchmark_data/rsna/images/normal_003.png"
T1_SUBTLE_01["cxr"]["findings"]["consolidation"]["confidence"] = "low"
T1_SUBTLE_01["ground_truth"]["cxr_ground_truth"] = {
    "consolidation_present": True,
    "cxr_category": "subtle_pneumonia",
    "rsna_patient_id": "567f81ac-7be3-4663-9a3b-826319bcd6ba",
    "bboxes_normalized": [[676, 772, 729, 828]],
}

T1_SUBTLE_02 = make_case(
    "T1-SUBTLE-02",
    cxr_consolidation=True,
    crackles=True,
    crackles_location="left mid zone",
    bronchial_breathing=True,
    bronchial_breathing_location="left mid zone",
    crp=110,
)
T1_SUBTLE_02["cxr"]["image_path"] = "benchmark_data/rsna/images/subtle_002.png"
T1_SUBTLE_02["cxr"]["findings"]["consolidation"]["confidence"] = "low"
T1_SUBTLE_02["ground_truth"]["cxr_ground_truth"] = {
    "consolidation_present": True,
    "cxr_category": "subtle_pneumonia",
    "rsna_patient_id": "e77e8d88-11e5-4d15-8dfb-abcd5c09c9f0",
    "bboxes_normalized": [[551, 694, 611, 743]],
}

# ============================================================================
# Category 4: Normal CXR (3 cases) — focal crackles + high CRP → CR-1, CR-2
# ============================================================================

T1_NORMAL_01 = make_case(
    "T1-NORMAL-01",
    cxr_consolidation=False,
    crackles=True,
    crackles_location="right lower zone",
    bronchial_breathing=True,
    bronchial_breathing_location="right lower zone",
    crp=180,
    expected_contradictions=["CR-1", "CR-2"],
)
T1_NORMAL_01["cxr"]["image_path"] = "benchmark_data/rsna/images/normal_001.png"
T1_NORMAL_01["cxr"]["prior_image_path"] = "benchmark_data/rsna/images/effusion_001.png"
T1_NORMAL_01["ground_truth"]["cxr_ground_truth"] = {
    "consolidation_present": False,
    "cxr_category": "normal",
    "rsna_patient_id": "0004cfab-14fd-4e49-80ba-63a80b6bddd6",
    "bboxes_normalized": [],
}

T1_NORMAL_02 = make_case(
    "T1-NORMAL-02",
    cxr_consolidation=False,
    crackles=True,
    crackles_location="left lower zone",
    crp=130,
    expected_contradictions=["CR-1", "CR-2"],
)
T1_NORMAL_02["cxr"]["image_path"] = "benchmark_data/rsna/images/normal_002.png"
T1_NORMAL_02["ground_truth"]["cxr_ground_truth"] = {
    "consolidation_present": False,
    "cxr_category": "normal",
    "rsna_patient_id": "00313ee0-9eaa-42f4-b0ab-c148ed3241cd",
    "bboxes_normalized": [],
}

T1_NORMAL_03 = make_case(
    "T1-NORMAL-03",
    cxr_consolidation=False,
    crackles=True,
    crackles_location="right mid zone",
    bronchial_breathing=True,
    bronchial_breathing_location="right mid zone",
    crp=40,  # CRP < 100 → only CR-1, not CR-2
    expected_contradictions=["CR-1"],
)
T1_NORMAL_03["cxr"]["image_path"] = "benchmark_data/rsna/images/normal_003.png"
T1_NORMAL_03["ground_truth"]["cxr_ground_truth"] = {
    "consolidation_present": False,
    "cxr_category": "normal",
    "rsna_patient_id": "00322d4d-1c29-4943-afc9-b6754be640eb",
    "bboxes_normalized": [],
}

# ============================================================================
# Category 5: Abnormal non-pneumonia (2 cases) — effusion → CR-6
# ============================================================================

T1_EFFUSION_01 = make_case(
    "T1-EFFUSION-01",
    cxr_consolidation=False,
    cxr_effusion=True,
    crackles=False,
    bronchial_breathing=False,
    age=65,
    urea=7.1,  # moderate to avoid CR-4
    expected_contradictions=["CR-6"],
)
T1_EFFUSION_01["cxr"]["image_path"] = "benchmark_data/rsna/images/effusion_001.png"
T1_EFFUSION_01["ground_truth"]["cxr_ground_truth"] = {
    "consolidation_present": False,
    "cxr_category": "abnormal_non_pneumonia",
    "rsna_patient_id": "c1edf42b-5958-47ff-a1e7-4f23d99583ba",
    "bboxes_normalized": [],
}

T1_EFFUSION_02 = make_case(
    "T1-EFFUSION-02",
    cxr_consolidation=False,
    cxr_effusion=True,
    crackles=False,
    bronchial_breathing=False,
    age=65,
    urea=7.1,
    crp=25,
    expected_contradictions=["CR-6"],
)
T1_EFFUSION_02["cxr"]["image_path"] = "benchmark_data/rsna/images/effusion_002.png"
T1_EFFUSION_02["ground_truth"]["cxr_ground_truth"] = {
    "consolidation_present": False,
    "cxr_category": "abnormal_non_pneumonia",
    "rsna_patient_id": "c1f6b555-2eb1-4231-98f6-50a963976431",
    "bboxes_normalized": [],
}


TRACK1_CASES: list[dict] = [
    T1_CLEAR_01,
    T1_CLEAR_02,
    T1_CLEAR_03,
    T1_BILATERAL_01,
    T1_BILATERAL_02,
    T1_SUBTLE_01,
    T1_SUBTLE_02,
    T1_NORMAL_01,
    T1_NORMAL_02,
    T1_NORMAL_03,
    T1_EFFUSION_01,
    T1_EFFUSION_02,
]

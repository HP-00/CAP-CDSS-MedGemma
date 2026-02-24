"""Group B: 8 cross-modal contradiction cases (CR-1 through CR-6).

Each case is designed to trigger specific contradiction rules.
Note: CR-2 requires no consolidation + CRP>100 + clinical features, which means
CR-1 also fires (same prerequisites minus CRP). Expected contradictions include both.
"""

from benchmark_data.cases.helpers import make_case

# --- CR-1: CXR no consolidation + focal crackles/bronchial breathing ---

# High confidence: both crackles AND bronchial breathing
CR1_HIGH = make_case(
    "CR1-HIGH",
    cxr_consolidation=False,
    crackles=True,
    crackles_location="right lower zone",
    bronchial_breathing=True,
    bronchial_breathing_location="right lower zone",
    expected_contradictions=["CR-1"],
)

# Moderate confidence: crackles only
CR1_MOD = make_case(
    "CR1-MOD",
    cxr_consolidation=False,
    crackles=True,
    crackles_location="right lower zone",
    bronchial_breathing=False,
    expected_contradictions=["CR-1"],
)

# --- CR-2: CXR no consolidation + CRP > 100 + clinical features ---
# Note: CR-1 also fires (same no-consolidation + clinical features prerequisite)

# High confidence: CRP > 200
CR2_HIGH = make_case(
    "CR2-HIGH",
    cxr_consolidation=False,
    crp=210,
    crackles=True,
    crackles_location="right lower zone",
    bronchial_breathing=True,
    bronchial_breathing_location="right lower zone",
    expected_contradictions=["CR-1", "CR-2"],
)

# Moderate confidence: CRP 100-200
CR2_MOD = make_case(
    "CR2-MOD",
    cxr_consolidation=False,
    crp=150,
    crackles=True,
    crackles_location="right lower zone",
    bronchial_breathing=False,
    expected_contradictions=["CR-1", "CR-2"],
)

# --- CR-3: CXR consolidation + CRP < 20 + no clinical signs ---

# High confidence: CRP < 10
CR3_HIGH = make_case(
    "CR3-HIGH",
    cxr_consolidation=True,
    crp=8,
    crackles=False,
    bronchial_breathing=False,
    expected_contradictions=["CR-3"],
)

# --- CR-4: CURB65 low + immunosuppression + bilateral consolidation ---
# Crackles set to bilateral to avoid also triggering CR-5 (bilateral CXR + unilateral exam)

CR4_HIGH = make_case(
    "CR4-HIGH",
    immunosuppression=True,
    cxr_consolidation=True,
    cxr_consolidation_location="bilateral lower lobes",
    crackles=True,
    crackles_location="bilateral lower zones",
    expected_contradictions=["CR-4"],
)

# --- CR-5: CXR bilateral + unilateral clinical signs ---
# Moderate severity (age=65, urea=7.1 → CURB65=2) avoids CR-4 (low severity only)

CR5 = make_case(
    "CR5",
    age=65,
    urea=7.1,
    cxr_consolidation=True,
    cxr_consolidation_location="bilateral lower lobes",
    crackles=True,
    crackles_location="right lower zone",
    bronchial_breathing=False,
    expected_contradictions=["CR-5"],
)

# --- CR-6: CXR effusion + no consolidation ---
# Must avoid CR-1: set crackles=False and bronchial_breathing=False
# Moderate severity (age=65, urea=7.1) avoids CR-4 (low severity + effusion trigger)

CR6 = make_case(
    "CR6",
    age=65,
    urea=7.1,
    cxr_consolidation=False,
    cxr_effusion=True,
    crackles=False,
    bronchial_breathing=False,
    expected_contradictions=["CR-6"],
)


GROUP_B_CASES: list[dict] = [
    CR1_HIGH,
    CR1_MOD,
    CR2_HIGH,
    CR2_MOD,
    CR3_HIGH,
    CR4_HIGH,
    CR5,
    CR6,
]

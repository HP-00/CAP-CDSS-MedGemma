"""Group A: 15 CURB65 boundary test cases.

12 single-variable boundary cases (all other CURB65 vars at zero-scoring baseline)
+ 3 composite severity tier cases.

All cases have CXR consolidation present + crackles + CRP=50, so no cross-modal
contradiction rules fire.
"""

from benchmark_data.cases.helpers import make_case

# --- 12 single-variable boundary cases ---

# Urea: strictly > 7.0 for U=1
CURB65_U_BELOW = make_case("CURB65-U-BELOW", urea=7.0)
CURB65_U_ABOVE = make_case("CURB65-U-ABOVE", urea=7.1)

# RR: >= 30 for R=1
CURB65_R_BELOW = make_case("CURB65-R-BELOW", rr=29)
CURB65_R_ABOVE = make_case("CURB65-R-ABOVE", rr=30)

# SBP: strictly < 90 for B=1 (from SBP)
CURB65_SBP_BELOW = make_case("CURB65-SBP-BELOW", sbp=90)
CURB65_SBP_ABOVE = make_case("CURB65-SBP-ABOVE", sbp=89)

# DBP: <= 60 for B=1 (from DBP)
CURB65_DBP_BELOW = make_case("CURB65-DBP-BELOW", dbp=61)
CURB65_DBP_ABOVE = make_case("CURB65-DBP-ABOVE", dbp=60)

# Age: >= 65 for Age=1
CURB65_AGE_BELOW = make_case("CURB65-AGE-BELOW", age=64)
CURB65_AGE_ABOVE = make_case("CURB65-AGE-ABOVE", age=65)

# AMT: <= 8 means confused (C=1)
CURB65_AMT_BELOW = make_case("CURB65-AMT-BELOW", amt=9)
CURB65_AMT_ABOVE = make_case("CURB65-AMT-ABOVE", amt=8)

# --- 3 composite severity tier cases ---

CURB65_COMPOSITE_LOW = make_case("CURB65-COMPOSITE-LOW")  # all baseline → CURB65=0
CURB65_COMPOSITE_MOD = make_case("CURB65-COMPOSITE-MOD", age=65, urea=7.1)  # CURB65=2
CURB65_COMPOSITE_HIGH = make_case(
    "CURB65-COMPOSITE-HIGH", age=65, urea=7.1, rr=30, amt=8,
)  # CURB65=4


GROUP_A_CASES: list[dict] = [
    CURB65_U_BELOW,
    CURB65_U_ABOVE,
    CURB65_R_BELOW,
    CURB65_R_ABOVE,
    CURB65_SBP_BELOW,
    CURB65_SBP_ABOVE,
    CURB65_DBP_BELOW,
    CURB65_DBP_ABOVE,
    CURB65_AGE_BELOW,
    CURB65_AGE_ABOVE,
    CURB65_AMT_BELOW,
    CURB65_AMT_ABOVE,
    CURB65_COMPOSITE_LOW,
    CURB65_COMPOSITE_MOD,
    CURB65_COMPOSITE_HIGH,
]

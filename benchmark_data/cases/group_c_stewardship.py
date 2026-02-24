"""Group C: 10 stewardship contradiction cases (CR-7 through CR-11).

These cases require micro_results and/or prior_antibiotic_recommendation.
CR-10 is special: detected in treatment_selection_node via detect_cr10(),
not in detect_contradictions().
"""

from cap_agent.agent.clinical_logic import select_antibiotic

from benchmark_data.cases.helpers import make_case

# --- CR-7: Antibiotic doesn't cover identified organism ---

# Lab susceptibility: S.pneumoniae resistant to amoxicillin
CR7_LAB_R = make_case(
    "CR7-LAB-R",
    # Low severity → amoxicillin prescribed
    micro_results=[
        {
            "test_type": "sputum culture",
            "status": "positive",
            "organism": "Streptococcus pneumoniae",
            "susceptibilities": {"amoxicillin": "R", "co-amoxiclav": "S"},
        },
    ],
    # Need prior_antibiotic_recommendation since detect_contradictions uses it
    prior_antibiotic_recommendation=select_antibiotic(severity="low"),
    expected_contradictions=["CR-7"],
)

# Population-level resistance: Legionella → amoxicillin R in coverage map
CR7_POP_R = make_case(
    "CR7-POP-R",
    micro_results=[
        {
            "test_type": "urinary antigen",
            "status": "positive",
            "organism": "Legionella pneumophila",
        },
    ],
    prior_antibiotic_recommendation=select_antibiotic(severity="low"),
    expected_contradictions=["CR-7"],
)

# --- CR-8: Macrolide prescribed, no atypical pathogen on micro ---

# Fires: moderate severity (macrolide in atypical_cover), S.pneumo positive,
# 2 completed tests, no atypical
CR8_FIRE = make_case(
    "CR8-FIRE",
    age=65,
    urea=7.1,  # CURB65=2 → moderate
    micro_results=[
        {
            "test_type": "sputum culture",
            "status": "positive",
            "organism": "Streptococcus pneumoniae",
        },
        {
            "test_type": "urinary legionella antigen",
            "status": "negative",
            "organism": None,
        },
    ],
    prior_antibiotic_recommendation=select_antibiotic(severity="moderate"),
    expected_contradictions=["CR-8"],
)

# Exempt: high severity (clarithromycin is standard dual therapy)
CR8_EXEMPT = make_case(
    "CR8-EXEMPT",
    age=65,
    urea=7.1,
    rr=30,  # CURB65=3 → high
    micro_results=[
        {
            "test_type": "sputum culture",
            "status": "positive",
            "organism": "Streptococcus pneumoniae",
        },
        {
            "test_type": "urinary legionella antigen",
            "status": "negative",
            "organism": None,
        },
    ],
    prior_antibiotic_recommendation=select_antibiotic(severity="high"),
    expected_contradictions=[],
)

# --- CR-9: IV >48h but oral tolerance + improving ---

# Fires: IV 52h, all stability markers normal, oral tolerant
# Use dbp=60 (B=1) for high severity — RR>=24 and confusion are unstable for CR-9
# CURB65 = age(1) + urea(1) + B(1) = 3 → high. Stable: no confusion, RR<24, temp<37.5
CR9_MET = make_case(
    "CR9-MET",
    age=65,
    urea=7.1,
    dbp=60,  # B=1
    rr=20,
    temperature=37.0,
    heart_rate=80,
    spo2=96,
    sbp=120,
    treatment_status={
        "current_route": "IV",
        "hours_on_iv": 52,
        "iv_antibiotics": ["Co-amoxiclav 1.2g TDS IV"],
    },
    prior_antibiotic_recommendation=select_antibiotic(severity="high"),
    expected_contradictions=["CR-9"],
)

# Does not fire: IV 52h but temperature 38.2 (unstable)
CR9_NOT = make_case(
    "CR9-NOT",
    age=65,
    urea=7.1,
    dbp=60,
    rr=20,
    temperature=38.2,
    heart_rate=80,
    spo2=96,
    sbp=120,
    treatment_status={
        "current_route": "IV",
        "hours_on_iv": 52,
        "iv_antibiotics": ["Co-amoxiclav 1.2g TDS IV"],
    },
    prior_antibiotic_recommendation=select_antibiotic(severity="high"),
    expected_contradictions=[],
)

# --- CR-10: Fluoroquinolone + penicillin intolerance (not true allergy) ---

# Fires: high severity + pen allergy (GI upset = intolerance) → levofloxacin
CR10_FIRE = make_case(
    "CR10-FIRE",
    age=65,
    urea=7.1,
    rr=30,  # high severity
    allergies=[{"drug": "penicillin", "reaction_type": "gi upset", "severity": "mild"}],
    expected_contradictions=["CR-10"],
)

# Does not fire: high severity + pen allergy (anaphylaxis = true allergy) → levofloxacin
CR10_TRUE = make_case(
    "CR10-TRUE",
    age=65,
    urea=7.1,
    rr=30,
    allergies=[{"drug": "penicillin", "reaction_type": "anaphylaxis", "severity": "severe"}],
    expected_contradictions=[],
)

# --- CR-11: Pneumococcal + broad-spectrum → de-escalate ---

# Fires: pneumococcal antigen positive + co-amoxiclav (broad-spectrum)
CR11_FIRE = make_case(
    "CR11-FIRE",
    age=65,
    urea=7.1,
    rr=30,  # high severity → co-amoxiclav
    micro_results=[
        {
            "test_type": "pneumococcal urinary antigen",
            "status": "positive",
            "organism": "Streptococcus pneumoniae",
        },
    ],
    prior_antibiotic_recommendation=select_antibiotic(severity="high"),
    expected_contradictions=["CR-11"],
)

# Fires with susceptibility data → high confidence
CR11_SUSC = make_case(
    "CR11-SUSC",
    age=65,
    urea=7.1,
    rr=30,
    micro_results=[
        {
            "test_type": "pneumococcal urinary antigen",
            "status": "positive",
            "organism": "Streptococcus pneumoniae",
            "susceptibilities": {"amoxicillin": "S", "co-amoxiclav": "S"},
        },
    ],
    prior_antibiotic_recommendation=select_antibiotic(severity="high"),
    expected_contradictions=["CR-11"],
)


GROUP_C_CASES: list[dict] = [
    CR7_LAB_R,
    CR7_POP_R,
    CR8_FIRE,
    CR8_EXEMPT,
    CR9_MET,
    CR9_NOT,
    CR10_FIRE,
    CR10_TRUE,
    CR11_FIRE,
    CR11_SUSC,
]

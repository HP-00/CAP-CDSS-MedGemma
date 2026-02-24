# Contradiction Rules -- Cross-Modal Safety System

The CAP-CDSS implements 11 contradiction rules that detect inconsistencies across CXR imaging, lab results, and clinical examination findings. These rules fire automatically during pipeline execution and generate confidence-weighted alerts for clinician review.

## Overview Table

| Rule | Category | Pattern | Strategy | Confidence |
|------|----------|---------|----------|------------|
| CR-1 | Cross-Modal | CXR negative + clinical signs positive | A (Zone Re-Analysis) | High / Moderate |
| CR-2 | Cross-Modal | CXR negative + CRP > 100 | B (Temporal Context) | High / Moderate |
| CR-3 | Cross-Modal | CXR consolidation + CRP < 20 | C (Differential Diagnosis) | High / Moderate |
| CR-4 | Cross-Modal | Low CURB65 + high-risk features | D (Severity Override) | High / Moderate |
| CR-5 | Cross-Modal | Bilateral CXR + unilateral clinical signs | A (Zone Re-Analysis) | Moderate |
| CR-6 | Cross-Modal | Pleural effusion without consolidation | C (Differential Diagnosis) | Moderate |
| CR-7 | Stewardship | Organism-antibiotic mismatch | E (Deterministic) | High / Moderate |
| CR-8 | Stewardship | Unnecessary macrolide | E (Deterministic) | High / Moderate |
| CR-9 | Stewardship | IV-to-oral switch opportunity | E (Deterministic) | High |
| CR-10 | Stewardship | Unnecessary fluoroquinolone | E (Deterministic) | High |
| CR-11 | Stewardship | Pneumococcal de-escalation opportunity | E (Deterministic) | High / Moderate |

## Cross-Modal Rules (CR-1 to CR-6)

These require MedGemma (GPU) for resolution via Strategies A-D.

### CR-1: CXR-Clinical Discordance

- **Trigger:** CXR shows no consolidation BUT clinical exam reveals focal crackles or bronchial breathing
- **Clinical rationale:** CXR can miss early consolidation (12-24h lag), or subtle findings obscured by image quality. Physical examination signs are highly specific for pneumonia.
- **Resolution Strategy A -- Zone Re-Analysis:** MedGemma re-examines the specific lung zone corresponding to the clinical findings, with enhanced focus on subtle opacities and image quality assessment.
- **Confidence:** High (if both crackles AND bronchial breathing present), Moderate (single finding)
- **Evidence:** EVIDENCE.md sections on CXR sensitivity

### CR-2: CXR-Lab Discordance (Negative CXR + High CRP)

- **Trigger:** CXR shows no consolidation BUT CRP > 100 mg/L with clinical features
- **Clinical rationale:** CRP is very sensitive for bacterial infection. A CRP > 100 with clinical signs strongly suggests pneumonia even with a negative CXR (early pneumonia, dehydrated patient with reduced opacification, or viral/atypical pathogen).
- **Resolution Strategy B -- Temporal Context:** MedGemma evaluates whether CXR lag (12-24h behind clinical presentation) or patient factors (dehydration) could explain the discordance.
- **Confidence:** High (CRP > 200), Moderate (CRP 100-200)

### CR-3: CXR-Lab Discordance (Consolidation + Low CRP)

- **Trigger:** CXR shows consolidation BUT CRP < 20 mg/L with no clinical signs
- **Clinical rationale:** Low CRP with radiographic consolidation raises alternative diagnoses: lung cancer, organizing pneumonia, old scarring, or atelectasis.
- **Resolution Strategy C -- Differential Diagnosis:** MedGemma screens for alternative diagnoses (malignancy features, old films comparison, clinical context).
- **Confidence:** High (CRP < 10), Moderate (CRP 10-20)

### CR-4: Severity Discordance (Low CURB65 + High-Risk Features)

- **Trigger:** CURB65 classifies as "low" severity BUT patient has: immunosuppression, multilobar disease, frailty, severe lung disease, hypoxia (SpO2 < 90%), pleural effusion, significant comorbidities, or pregnancy
- **Clinical rationale:** CURB65 underestimates severity in certain populations. A score of 0-1 with high-risk features may warrant hospital admission or more aggressive treatment.
- **Resolution Strategy D -- Severity Override:** MedGemma reasons about whether override triggers justify escalating treatment despite low CURB65.
- **Confidence:** High (2+ triggers), Moderate (1 trigger)

### CR-5: CXR-Clinical Laterality Mismatch

- **Trigger:** CXR shows bilateral disease BUT clinical exam reveals unilateral signs only
- **Clinical rationale:** Bilateral CXR changes with unilateral clinical signs may indicate one side is old/chronic (e.g., previous TB scarring) or image quality issues.
- **Resolution Strategy A -- Zone Re-Analysis:** Targeted re-examination of bilateral findings.
- **Confidence:** Moderate (always)

### CR-6: Effusion Without Consolidation

- **Trigger:** CXR shows pleural effusion BUT no consolidation visible
- **Clinical rationale:** Isolated effusion without consolidation raises alternative diagnoses: heart failure, malignancy, empyema, TB.
- **Resolution Strategy C -- Differential Diagnosis:** MedGemma screens for alternative diagnoses.
- **Confidence:** Moderate (always)

## Stewardship Rules (CR-7 to CR-11)

These are deterministic (no GPU needed) -- Strategy E. They enforce antibiotic stewardship principles.

### CR-7: Organism-Antibiotic Mismatch

- **Trigger:** Prescribed antibiotic does not cover the identified organism from microbiology results
- **Resolution:** Alert to switch to organism-specific therapy based on susceptibility data
- **Confidence:** High (lab susceptibility), Moderate (population antibiogram)

### CR-8: Unnecessary Macrolide

- **Trigger:** Macrolide (clarithromycin) prescribed but no atypical pathogen detected on microbiology
- **Note:** EXEMPT when severity is "high" -- dual therapy (beta-lactam + macrolide) is standard for severe CAP per BTS guidelines
- **Resolution:** Consider de-escalation to monotherapy
- **Confidence:** High (2 or more atypical tests negative), Moderate (1 test)

### CR-9: IV-to-Oral Switch Opportunity

- **Trigger:** Patient on IV antibiotics for >48 hours, clinically improving, tolerating oral medication
- **Resolution:** Recommend switch to oral equivalent to reduce infection risk and length of stay
- **Confidence:** High (always -- deterministic criteria)

### CR-10: Unnecessary Fluoroquinolone

- **Trigger:** Fluoroquinolone prescribed but penicillin "allergy" is actually intolerance only (GI upset, nausea)
- **Resolution:** Suggest standard beta-lactam therapy (fluoroquinolones have serious side effects: tendon rupture, aortic dissection)
- **Confidence:** High (always -- clear keyword matching)

### CR-11: Pneumococcal De-escalation

- **Trigger:** Pneumococcal urinary antigen positive but broad-spectrum antibiotic prescribed
- **Resolution:** Recommend de-escalation to amoxicillin (narrow-spectrum, first-line for pneumococcal CAP)
- **Confidence:** High (lab susceptibility confirms amoxicillin S), Moderate (population data)

## Confidence Tiering

All contradiction alerts are assigned confidence levels:

| Level | Action | Display |
|-------|--------|---------|
| **High** | Requires clinician review | Alert banner |
| **Moderate** | Recommended for review | Alert banner |
| **Low** | For awareness only | Informational note |

Alerts are NEVER suppressed -- only de-emphasized at low confidence. This ensures clinical safety while reducing alert fatigue.

## Resolution Strategy Summary

| Strategy | Rules | Method | GPU |
|----------|-------|--------|-----|
| A | CR-1, CR-5 | Zone-specific CXR re-analysis | Yes |
| B | CR-2 | Temporal context evaluation | Yes |
| C | CR-3, CR-6 | Differential diagnosis screening | Yes |
| D | CR-4 | Severity override reasoning | Yes |
| E | CR-7 -- CR-11 | Deterministic stewardship rules | No |

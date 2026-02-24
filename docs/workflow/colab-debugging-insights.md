# Session Learnings

Historical Colab validation notes and debugging insights accumulated during development.

> **Note:** GPU call counts below are historical snapshots — the pipeline evolved from
> 10 → 12 → 9 calls as nodes were added then eliminated. See `AGENTS.md` Section 1
> for current specs.

1. **Token truncation is the #1 CXR failure mode** — MedGemma produces correct JSON structure but gets cut off. Manifests as flat dict (first inner object captured) instead of nested multi-finding dict.
2. **Colab caching is aggressive** — `pip install` within the same runtime session may skip rebuild even when repo changes. MUST restart runtime.
3. **MedGemma CXR findings are clinically coherent** — correctly identified consolidation (bilateral, lower lung zones) on Google's example CXR with high confidence.
4. **Contradiction rules adapt to real data** — with mock CXR (no consolidation), CR-1/CR-2 fired. With real CXR (consolidation present), CR-5 fired instead. Validates the rule engine.
5. **EHR QA extraction works end-to-end** — 4-step pipeline on FHIR Bundle + freetext clerking note. 13/13 verification checks passed on A100.
6. **Age from FHIR birthDate vs clerking note** — `fhir_utils.py` computes age from birthDate (71), clerking note says 72 (birthday not yet passed). MedGemma preferred structured data per priority rule. Does not affect CURB65 (>=65 either way).
7. **Fact-filter pattern more reliable than direct JSON extraction** — having MedGemma produce English facts in Steps 2-3, then JSON only in Step 4, avoids multi-step JSON parsing failures.
8. **10 MedGemma calls per full pipeline** — 4 EHR + 3 CXR + 1 contradiction + 1 synthesis + 1 summary = 343s on A100.
9. **CR-5 fires with real bilateral CXR + unilateral exam** — validates that contradiction rules adapt dynamically to extraction output.
10. **Lab extraction works end-to-end** — 2-step pipeline on NHS pathology report + FHIR Observations: 12/12 labs extracted, 0 data gaps, 14/14 verification checks on A100.
11. **Thinking tokens can consume entire budget** — Lab synthesis at 2000 max_new_tokens failed because MedGemma restated the JSON schema in its thinking trace. Bumped to 3500 to give room for both thinking and output.
12. **Dual-source merge validated** — FHIR render (0 GPU calls) + plaintext extraction (1 GPU call) produce redundant facts; synthesis correctly reconciles them into a single JSON.
13. **All 3 extraction tools now real** — no more mocks in the full pipeline when FHIR bundle + lab_report + CXR image are present (EHR, CXR, Lab all use MedGemma).
14. **Full pipeline: 12 GPU calls, ~473s on A100** — 4 EHR + 2 Lab + 3 CXR + 1 contradiction + 1 synthesis + 1 summary. Up from 10 calls / ~343s.
15. **Lab susceptibility is authoritative over coverage map** — CR-7 must `continue` on any non-empty lab value, not just "R". Without this, a lab "S" result falls through to the population map which might show "R".
16. **CR-10 allergy data flows through two paths** — `get_synthetic_cr10_case()` must set allergy in BOTH `demographics.allergies` AND `past_medical_history.allergies` because mock extraction reads from PMH.
17. **Unknown penicillin reaction = conservative** — `classify_penicillin_allergy()` treats unknown reaction type as possible true allergy (not intolerance), so CR-10 won't fire. This is by design for patient safety.
18. **T=48h pipeline: ~297s on A100 (~8 GPU calls)** — faster than T=0 because CXR uses mock (0 GPU) and fewer contradictions need resolution.
19. **CR-10 pipeline: ~195s on A100 (~4 GPU calls)** — all mock extraction (0 GPU), only synthesis + summary use MedGemma.
20. **27/27 Colab verification checks pass** — T=0 (14/14) + T=48h (8/8) + CR-10 (5/5).
21. **Strategy E adds 0 latency** — all 4 stewardship rules are deterministic, contradiction_resolution_node short-circuits them with pure Python.
22. **Same 9-node topology handles all 4 demos** — T=0, T=48h, CR-10, and Day 3-4 use identical graph; only case_data changes. Zero graph topology modifications needed.
23. **Day 3-4 pipeline: ~303s on A100 (~8 GPU calls)** — similar to 48h (no CXR image), but demonstrates treatment failure pathway.
24. **CRP trend analysis works end-to-end** — 40.9% decrease (186→110), slow_response category, flag_senior_review=True (day ≥ 3).
25. **Day 3-4 has 0 contradictions** — clinically correct; patient is on appropriate antibiotics, just not responding. The CRP trend + treatment_response surface the concern without a contradiction.
26. **34/34 Colab verification checks pass** — T=0 (14) + T=48h (8) + CR-10 (5) + Day 3-4 (7). All 4 demos verified.
27. **Discharge criteria override needed** — vitals alone insufficient when treatment failing (37.8°C is only 1/7 criteria failed, but patient needs reassessment not discharge).
28. **48h CRP trend shows 49% decrease** — (186→95) just under 50%, classified as slow_response. Day 2 so no flag yet, demonstrates day-sensitivity of the algorithm.
29. **Confidence-weighted alerts implemented** — each CR-1 to CR-10 now has a `confidence` field ("high"/"moderate"/"low") based on evidence strength. Output assembly splits into `alerts` (high/moderate confidence) and `informational` (low confidence) to combat alert fatigue.
30. **Source attribution via provenance block** — `structured_output` now has `provenance.data_sources` (per-modality: FHIR vs clerking note vs lab report vs synthetic) and `provenance.extraction_tools` (real pipeline vs mock). Per-section `data_sources` arrays trace each output to its input source.
31. **Resolution-phase confidence update** — Strategies A-D prompts now ask MedGemma to rate confidence. `_parse_resolution_confidence()` extracts this and updates the contradiction's detection-phase confidence. Strategy E (deterministic) skips this since confidence is inherent.
32. **Rigid confidence format directive** — Replaced soft "Rate your confidence" (question 5) with a rigid format instruction at end of prompt: "End with... EXACTLY this format — CONFIDENCE: high/moderate/low". Moved after closing instruction so it's the last thing the model sees. Combined with 3-tier regex parser (structured → natural language → reversed order) to catch more response patterns from the 4B model.

# Benchmark Run History

Chronological log of benchmark runs with key findings. Each run's full
metrics.json and report.html are archived in a timestamped directory.

---

## 2026-02-22 — First full 49-case GPU run (`code-simplify` branch)

- **GPU:** A100, Colab
- **Duration:** 86.4 min (105.8s mean per case)
- **Cases:** 4 builtin + 33 Track 2 + 12 Track 1 = 49 total
- **Branch:** `code-simplify` (commit `92b01b8`)
- **Evaluators:** 8 (added `cxr_localization`)

| Metric | Score |
|--------|-------|
| severity_accuracy | 100% |
| antibiotic_concordance | 100% |
| safety_score | 100% |
| completeness | 100% |
| contradiction_recall | 83.67% |
| contradiction_precision | 42.86% |
| cxr_consolidation | 58.33% |
| cxr_localization | 21.42% (mean IoU) |

**Key findings:**
- Deterministic clinical logic (severity, antibiotics, safety, completeness) is 100% correct across all 49 cases.
- CR-1 false positive on all 33 Track 2 cases: `placeholder_cxr.jpg` missing on Colab causes mock CXR to return "absent consolidation", which triggers CR-1 against clinical exam findings (crackles present). This is a test infrastructure issue, not a pipeline bug.
- MedGemma CXR classification: correct on clear pneumonia (3/3) and bilateral (2/2), misses subtle opacities (0/2 with high confidence), hallucinates consolidation on normal CXRs (3/3 false positive).
- CXR localization: best IoU 51.75% (T1-CLEAR-01), model tends to output large/full-image bounding boxes.
- CR-3, CR-5, CR-6 recall failures (Track 2): caused by missing CXR images, not logic bugs.
- Track 1 contradiction recall failures: cascading from CXR misclassification (e.g., normal CXR falsely reports consolidation, preventing CR-1/CR-2 from firing).

**Action items from this run:**
- [x] Fix Track 2 CXR handling: set `image_path=None` in `_BASE_CASE` (helpers.py). Root cause: truthy `"placeholder_cxr.jpg"` triggered real CXR extraction on nonexistent file → empty findings → 23 spurious CR-1s. Quick-mode now 100% precision/recall across all 33 Track 2 cases.
- [x] Document MedGemma CXR limitations (subtle miss, normal false positive, localization, effusion) in AGENTS-limitations.md

**Files:** `2026-02-22_gpu_49/metrics.json`, `2026-02-22_gpu_49/report.html`

---

## 2026-02-22 Run 2 — 49-case GPU run with Track 2 fix + localization prompt (`code-simplify` branch)

- **GPU:** A100, Colab
- **Duration:** 66.3 min (81.2s mean per case) — 23% faster than Run 1
- **Cases:** 4 builtin + 33 Track 2 + 12 Track 1 = 49 total
- **Branch:** `code-simplify` (commit `8a432e0`)
- **Evaluators:** 8
- **Changes since Run 1:** Track 2 `image_path=None` fix, CXR localization prompt with anatomical zones + tightness constraint

| Metric | Run 1 | Run 2 | Delta | Verdict |
|--------|-------|-------|-------|---------|
| severity_accuracy | 100% | 100% | 0 | STABLE |
| antibiotic_concordance | 100% | 100% | 0 | STABLE |
| safety_score | 100% | 100% | 0 | STABLE |
| completeness | 100% | 100% | 0 | STABLE |
| contradiction_recall | 83.67% | 89.80% | +6.13 | IMPROVED |
| contradiction_precision | 42.86% | 89.80% | +46.94 | IMPROVED |
| cxr_consolidation | 58.33% | 58.33% | 0 | STABLE |
| cxr_localization | 21.42% | 18.29% | -3.13 | REGRESSION |

**Key findings:**
- Contradiction precision jumped from 42.86% → 89.80% — the `image_path=None` fix eliminated 33 Track 2 spurious CR-1 false positives. Track 2 cases now all score 100% recall + precision.
- Contradiction recall improved from 83.67% → 89.80% — mock CXR with `image_path=None` returns consistent findings, allowing cross-modal contradiction rules (CR-3, CR-5, CR-6) to fire correctly.
- CXR localization **regressed** from 21.42% → 18.29% mean IoU. The anatomical zones prompt helped 3/5 cases but hurt 2/5 (T1-CLEAR-01: 51.75% → 25.47%, T1-BILATERAL-01: 32.11% → 20.66%). Net negative.
- Pipeline 23% faster: 81.2s vs 105.8s mean per case. Likely from InMemoryCache + optimizations.
- Builtin case contradiction false positives persist: T=48h (66.7%), CR-10 (33.3%), Day 3-4 (0%) precision.

**Action items from this run:**
- [ ] Revert or rework CXR localization prompt — anatomical zones hurt more than they helped. Consider simpler tightness-only constraint, or revert to original
- [ ] Investigate builtin case contradiction false positives (T=48h, CR-10, Day 3-4) — may be ground truth issues or genuine false positives from MedGemma CXR
- [ ] Consider per-case IoU analysis to understand what box coordinates MedGemma actually outputs

**Files:** `2026-02-22_gpu_49_run2/metrics.json`, `2026-02-22_gpu_49_run2/report.html`

---

## 2026-02-17 — Quick-mode baseline (4 builtin cases, mock MedGemma)

- **GPU:** None (mock `call_medgemma` via prompt-keyword router)
- **Duration:** 0.026s total
- **Cases:** 4 builtin (T=0, T=48h, CR-10, Day 3-4)
- **Branch:** `main`
- **Evaluators:** 7

| Metric | Score |
|--------|-------|
| severity_accuracy | 50% |
| antibiotic_concordance | 100% |
| safety_score | 100% |
| completeness | 100% |
| contradiction_recall | 87.5% |
| contradiction_precision | 58.33% |

**Notes:**
- Severity 50% because mock router returns fixed responses that don't perfectly match all case ground truths.
- This baseline reflects mock behavior, not real model performance.

**Files:** `baseline.json`

# RSNA CXR Benchmark Images

12 chest X-ray images used for Track 1 benchmark evaluation. Pre-processed to
896x896 PNG (MedGemma input size).

## Data Source and Attribution

Images sourced from the **NIH Clinical Center ChestX-ray8 dataset**, annotated
by the RSNA Pneumonia Detection Challenge.

> Wang X, Peng Y, Lu L, Lu Z, Bagheri M, Summers RM. *ChestX-ray8:
> Hospital-scale Chest X-ray Database and Benchmarks.* IEEE CVPR, 2017.

> Shih G, et al. *Augmenting the National Institutes of Health Chest
> Radiograph Dataset with Expert Annotations of Possible Pneumonia.*
> Radiology: Artificial Intelligence, 2019.

Original dataset: https://nihcc.app.box.com/v/ChestXray-NIHCC
RSNA Challenge: https://www.rsna.org/rsnai/ai-image-challenge/rsna-pneumonia-detection-challenge-2018

The NIH Clinical Center states there are no restrictions on the use of the
NIH chest x-ray images. Attribution is required per the terms above.

## Image Files

```
benchmark_data/rsna/images/
├── clear_pneumonia_001.png    # Large unilateral consolidation
├── clear_pneumonia_002.png    # Large unilateral consolidation
├── clear_pneumonia_003.png    # Large unilateral consolidation
├── bilateral_001.png          # Bilateral opacities (4 annotated regions)
├── bilateral_002.png          # Bilateral opacities (4 annotated regions)
├── subtle_001.png             # Small opacity (~3k px² bbox)
├── subtle_002.png             # Small opacity (~3k px² bbox)
├── normal_001.png             # True negative (no annotated opacity)
├── normal_002.png             # True negative (no annotated opacity)
├── normal_003.png             # True negative (no annotated opacity)
├── effusion_001.png           # Abnormal non-pneumonia proxy (No Lung Opacity / Not Normal)
└── effusion_002.png           # Abnormal non-pneumonia proxy (No Lung Opacity / Not Normal)
```

## Selection Criteria

Images were selected from the RSNA stage 2 training labels (30,227 entries)
based on bounding box characteristics:

| Category | Criteria | Selected |
|----------|----------|----------|
| Clear pneumonia | Target=1, 1 bbox, area > 150k px² | Top 3 by area |
| Bilateral | Target=1, 2+ bboxes | Top 2 by box count |
| Subtle | Target=1, 1 bbox, area < 30k px² | 2 smallest |
| Normal | Target=0, no bboxes | 3 true negatives |
| Abnormal non-pneumonia | Target=0, diverse pool | 2 negatives |

> **Note:** Effusion cases were selected from the "No Lung Opacity / Not Normal"
> class in `stage_2_detailed_class_info.csv`.

## Patient ID Mapping

Each benchmark case maps to an RSNA patient ID for traceability back to `stage_2_train_labels.csv`.

| Case ID | RSNA Patient ID | Category | Bbox Count |
|---------|----------------|----------|------------|
| T1-CLEAR-01 | `097788d4-cb88-4457-8e71-0ca7a3da2216` | clear_pneumonia | 1 |
| T1-CLEAR-02 | `aa47c55a-7cf7-4105-9132-de080664f052` | clear_pneumonia | 1 |
| T1-CLEAR-03 | `a3ac5fe9-431c-4c10-8691-d0d26e6a0edd` | clear_pneumonia | 1 |
| T1-BILATERAL-01 | `8dc8e54b-5b05-4dac-80b9-fa48878621e2` | bilateral_pneumonia | 4 |
| T1-BILATERAL-02 | `32408669-c137-4e8d-bd62-fe8345b40e73` | bilateral_pneumonia | 4 |
| T1-SUBTLE-01 | `567f81ac-7be3-4663-9a3b-826319bcd6ba` | subtle_pneumonia | 1 |
| T1-SUBTLE-02 | `e77e8d88-11e5-4d15-8dfb-abcd5c09c9f0` | subtle_pneumonia | 1 |
| T1-NORMAL-01 | `0004cfab-14fd-4e49-80ba-63a80b6bddd6` | normal | 0 |
| T1-NORMAL-02 | `00313ee0-9eaa-42f4-b0ab-c148ed3241cd` | normal | 0 |
| T1-NORMAL-03 | `00322d4d-1c29-4943-afc9-b6754be640eb` | normal | 0 |
| T1-EFFUSION-01 | `c1edf42b-5958-47ff-a1e7-4f23d99583ba` | abnormal_non_pneumonia | 0 |
| T1-EFFUSION-02 | `c1f6b555-2eb1-4231-98f6-50a963976431` | abnormal_non_pneumonia | 0 |

## Coordinate Systems

RSNA annotations use `(x, y, width, height)` in pixel coordinates on 1024x1024 images.

The pipeline uses `[y0, x0, y1, x1]` normalized to 0-1000.

Conversion formula:
```
factor = 1000 / 1024
y0 = round(y * factor)
x0 = round(x * factor)
y1 = round((y + height) * factor)
x1 = round((x + width) * factor)
```

Ground truth bboxes in `benchmark_data/cases/track1_cases.py` are pre-converted to pipeline format.

## Longitudinal Pairs

4 constructed benchmark pairs using unrelated RSNA images to simulate prior/current
CXR comparisons (the RSNA dataset does not include longitudinal data).

| Case | Prior Image | Current Image | Expected Change |
|------|------------|---------------|-----------------|
| T1-CLEAR-01 | normal_001.png | clear_pneumonia_001.png | consolidation: new |
| T1-BILATERAL-01 | normal_002.png | bilateral_001.png | consolidation: new |
| T1-SUBTLE-01 | normal_003.png | subtle_001.png | consolidation: new |
| T1-NORMAL-01 | effusion_001.png | normal_001.png | consolidation: unchanged |

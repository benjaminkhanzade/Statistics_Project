# Phase 1 Data Guide

## Source and access

The files are prepared course subsets based on the National Alzheimer’s Coordinating Center (NACC) Uniform Data Set (UDS) and structural MRI summaries. This project does not download or reconstruct the full NACC database. The local receipt date and data collection period are not recorded. The subset-specific construction and preprocessing guide was not supplied.

Reference dictionaries used to interpret variable names and measures include the NACC UDS Researcher’s Data Dictionary and the SCAN MRI Researcher’s Data Dictionary. Consult the official NACC documentation when interpreting special codes or units.

## Files

| File | Dimensions | Level and use |
|---|---:|---|
| `udslong_imputed.csv` | 1,237 × 180 | One row per `NACCID`; demographics, medical history, function, cognition, and diagnostic variables. The filename indicates imputed/processed data, but the method, imputed columns, and pre-imputation missingness mask are unavailable. |
| `mriscanclean.csv` | 1,237 × 126 | One row per `NACCID`; 124 regional structural measures plus `NACCUDSD`. `AVGTH` is interpreted in millimeters and `GVOL` in cubic millimeters. Scan date, processing version, and QC flags are unavailable. |
| `combined_adjacency_matrix.csv` | 62 × 63 in CSV | Row labels plus a binary 62×62 regional adjacency matrix. It has no participant identifier and is not linked to participant-level analyses. The edge provenance and threshold are undocumented. |

## Linkage and analytic sample

UDS and MRI are linked by `NACCID`, which must be unique in each file. The supplied files contain 1,237 shared IDs, no unmatched IDs, and no duplicate IDs. `NACCUDSD` agrees across both files for all linked participants. This establishes ID linkage, not temporal alignment between MRI and UDS. Visit IDs, visit dates, scan dates, and study period are absent; the actual visit count and baseline visit cannot be recovered.

For the Phase 1 question about older adults, the analytic sample is operationally defined as `NACCAGE >= 65`. There are 864 such participants among the 1,237 linked IDs. The single supplied row per participant is retained; it cannot be verified as a true baseline.

The adjacency matrix has no `NACCID` and is not used in participant-level Phase 1 analyses. Analysis code and generated results are in `src/phase1_analysis.py` and `reports/phase1/`.

## Special codes and data quality

- The participant-level CSVs contain no blank cells. This does not rule out original missingness because the UDS file is imputed/processed.
- `EDUC=99` is treated as unknown. Two such values occur in the full linked dataset; one remains in the age-65+ analytic sample.
- `MOCATOTS` is accepted only in the range 0–30. The full linked dataset has nine invalid/out-of-range values, including code 88; valid fractional values are retained because the imputation method is unknown.
- Fractional `CDRSUM` values are not automatically errors. The six component CDR ratings are absent, so the total cannot be reconstructed from the supplied columns.
- Two nonpositive regional volume cells occur in the full MRI dataset. Nonpositive entorhinal volumes are excluded from valid volume summaries. No undocumented upper bound is imposed on MRI measures.
- IDs are not removed or duplicated artificially. Processing decisions are recorded in the results JSON and analysis code.

## Reproduction

From the repository root, run:

```bash
python3 src/phase1_analysis.py
```

This rebuilds the results JSON, CSV tables, and SVG figures. It does not download or transmit participant-level data.

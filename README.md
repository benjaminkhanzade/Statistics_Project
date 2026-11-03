# Statistics Project: NACC UDS + MRI

This repository contains an individual, five-phase statistics project using a prepared multimodal NACC subset. Phase 1 now focuses on the relationship between MoCA (`MOCATOTS`) and entorhinal volume and thickness among older adults (age 65+). The question, unit of analysis, sample rule, and limitations are documented in the [project card](PROJECT_CARD.md).

## Phase 1 files

- English report: `reports/phase1.pdf` and `reports/phase1/report_phase1.pdf`
- Reproducible analysis: `src/phase1_analysis.py` (Python standard library)
- PDF builder: `src/build_phase1_report.py` (ReportLab)
- Analysis notebook: `notebooks/phase1_descriptive_analysis.ipynb`
- Machine-readable results and four CSV tables: `reports/phase1/`
- Eleven standalone SVG figures: `figures/phase1/`
- Submission bundle, excluding participant-level source CSVs: `reports/phase1/phase1_submission.zip`
- Data provenance and processing notes: [data/README.md](data/README.md)

Run the analysis from the repository root:

```bash
python3 src/phase1_analysis.py
```

Build the English PDF with the project’s Python environment:

```bash
python3 src/build_phase1_report.py
```

The commands do not modify source data. Paths are resolved relative to the repository root.

## Data and scope

The two participant-level CSV files each contain 1,237 rows and 1,237 unique IDs, linked one-to-one by `NACCID`. The 62×62 adjacency matrix has no participant ID and is not used in participant-level Phase 1 analyses. Visit IDs and dates, scan dates, collection period, and the subset-specific data guide were not supplied.

The analytic sample includes 864 linked participants aged 65 or older. Phase 1 includes descriptive summaries, missingness, skewness, a scatterplot with an unadjusted linear trend, and a Pearson correlation heatmap. The age- and education-adjusted models are reserved for a later phase. The clinical/research subset is not a probability sample of the general population.

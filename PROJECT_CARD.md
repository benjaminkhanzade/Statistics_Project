# Statistics Project Card

## Working title

MoCA and entorhinal MRI measures in older adults in the NACC UDS + MRI subset

## Dataset and subset

The selected pathway uses the prepared NACC UDS and structural MRI files: `data/udslong_imputed.csv`, `data/mriscanclean.csv`, and `data/combined_adjacency_matrix.csv`. UDS and MRI are linked by `NACCID`. Collection period and local receipt date are not available. For Phase 1, older adults are defined operationally as participants with `NACCAGE >= 65`.

## Statistical question

Among adults aged 65 years or older, what is the linear relationship between MoCA score (`MOCATOTS`) and structural MRI measures, especially entorhinal cortical volume and thickness, after controlling for age (`NACCAGE`) and years of education (`EDUC`)? Phase 1 audits and describes the data and unadjusted relationships. Adjusted estimates are reserved for the modeling phase.

## Unit of analysis and target sample

The unit is one participant identified by unique `NACCID`. Each supplied CSV contains one row per participant, so that row is retained. The files do not include visit IDs or dates; therefore, the row cannot be verified as a true baseline, and the temporal alignment of MRI and UDS cannot be established. Of 1,237 linked participants, 864 are age 65 or older. Conclusions apply to this NACC clinical/research subset, not a probability sample of the general population.

## Variables and measurement scales

| Variable | Source | Scale | Role |
|---|---|---|---|
| `NACCID` | Shared | Nominal identifier | Link key; not an analytic variable |
| `NACCAGE` | UDS | Continuous, years | Age and planned adjustment variable |
| `EDUC` | UDS | Discrete, years of education | Education and planned adjustment variable; code 99 is unknown |
| `MOCATOTS` | UDS | Score, 0–30 | Primary cognitive measure; out-of-range values are invalid |
| `NACCUDSD` | UDS/MRI | Four-level categorical | Descriptive grouping variable |
| `CDRSUM`, `CDRGLOB` | UDS | Numeric score / ordinal category | Clinical description |
| `LH/RH_ENTORHINAL_AVGTH` | MRI | Continuous, mm | Left/right thickness and derived bilateral mean |
| `LH/RH_ENTORHINAL_GVOL` | MRI | Continuous, mm³ | Left/right volume and derived bilateral mean |

The planned adjusted model will be fitted separately for each MRI measure: `MOCATOTS ~ entorhinal measure + NACCAGE + EDUC`. Phase 1 reports descriptive statistics, plots, and unadjusted pairwise correlations only.

## Analysis decisions and limitations

- `MOCATOTS` is summarized only within 0–30. Values are not rounded or clipped.
- `EDUC=99` is treated as unknown. Other special codes are not generalized across variables.
- Bilateral volume and thickness are arithmetic means of left and right values when both are present and positive. Nonpositive volumes are not treated as valid measurements.
- The UDS filename indicates imputed/processed data, but the imputation method and original missingness mask were not supplied.
- There are no visit identifiers, UDS dates, or scan dates, so baseline selection and UDS–MRI timing cannot be verified.
- `NACCUDSD` indicates cognitive status, not an etiologic Alzheimer’s diagnosis. This observational analysis is not causal and does not estimate population prevalence.

# Datasets

The project has one loader per trial. The table below lists, for each trial,
the raw file format, the harmonization clusters implemented for it, and the
main outcome instruments in its harmonized `outcomes` cluster.

The table was compiled from the code in `data_loading/` and `harmonization_*/`.
It describes variables and structure, not data values.

| No. | Study ID               | Raw format        | Clusters      | Main outcome instruments                              |
|-----|------------------------|-------------------|---------------|-------------------------------------------------------|
| 02  | `02_Aragones_2012`     | Stata / CSV       | B · M · O · T | PHQ-9                                                 |
| 03  | `03_Aragones_2019`     | CSV               | B · M · O · T | HSCL (total, suicidal ideation)                       |
| 04  | `04_Bekelman_2018`     | CSV / Excel       | B · M · O · T | PHQ-9, GAD-7                                          |
| 05  | `05_Bekelman_2015`     | CSV               | B · M · O · T | PHQ-9, GAD-7                                          |
| 08  | `08_Coventry_2015`     | Stata             | B · M · O · T | PHQ-9, GAD-7, SDS                                     |
| 09  | `09_Davidson_2013`     | SPSS              | B · M · O · T | BDI                                                   |
| 10  | `10_Fletcher_2021a`    | Stata             | B · M · O · T | PHQ-9, GAD-7, K10                                     |
| 11  | `11_Fletcher_2021b`    | Stata             | B · M · O · T | PHQ-9, GAD-7                                          |
| 12  | `12_Gensichen_2009`    | Stata             | B · M · O · T | PHQ-9, EQ-5D, SF-36 domains                           |
| 13  | `13_Hölzel_2018`       | SPSS              | B · M · O · T | PHQ-9, GAD-7, EQ-5D                                   |
| 14  | `14_Katon_1995`        | SPSS              | B · M · O · T | SCL-20                                                |
| 15  | `15_Katon_1996`        | SPSS              | B · M · O · T | SCL-20                                                |
| 16  | `16_Katon_1999`        | SPSS              | B · O · T     | SCL-20                                                |
| 17  | `17_Katon_2001`        | SPSS              | B · M · O · T | SCL-20                                                |
| 18  | `18_Katon_2004`        | SPSS              | B · O · T     | SCL-20                                                |
| 19  | `19_Katon_2010`        | SPSS              | B · M · O · T | SCL-20                                                |
| 20  | `20_Patel_2010`        | SPSS              | B · M · O · T | CIS-R                                                 |
| 21  | `21_Richards_2008`     | SPSS              | B · M · O · T | PHQ-9                                                 |
| 22  | `22_Richards_2013`     | SPSS              | B · M · O · T | PHQ-9, EQ-5D, SF-36 (items and domains)               |
| 23  | `23_Rollman_2009`      | SPSS / Excel (zip)| B · M · O · T | HRSD-17                                               |
| 24  | `24_Rollman_2016`      | Excel             | B · M · O · T | PHQ-9, SF-36 component summaries                      |
| 25  | `25_Rollman_2017`      | Excel             | B · M · O · T | PHQ-9, PROMIS depression, SF-12 component summaries   |
| 26  | `26_Salisbury_2016`    | CSV               | B · M · O · T | PHQ-9, GAD-7                                          |
| 27  | `27_Simon_2000`        | SPSS              | B · M · O · T | SCL-20                                                |
| 28  | `28_Simon_2004`        | SPSS              | B · O · T     | SCL-20                                                |
| 29  | `29_Simon_2011`        | SPSS              | —             | *loader only, not yet harmonized*                     |
| 30  | `30_Srinivasan_2022`   | SPSS              | B · M · O · T | PHQ-9, GAD-7                                          |
| 31  | `31_Unützer_2002`      | CSV               | B · M · O · T | SCL-20                                                |
| 32  | `32_Wells_2000`        | SPSS (zip)        | B · M · O · T | CES-D                                                 |
| 33  | `33_Zimmerman_2016`    | Stata             | B · M · O · T | PHQ-9                                                 |

**Clusters:** B = baseline, M = medical history, O = outcomes, T = treatment.

!!! note "Gaps"
    - Dataset numbers **01, 06 and 07** have no loader.
    - **29 Simon 2011** has a loader but no harmonization scripts, so it is
      exported but not part of the merged dataset.
    - **16, 18 and 28** have no `medical_history` cluster.

## Outcome instruments

| Instrument       | Harmonized columns                                  | Range / scoring                                   |
|------------------|-----------------------------------------------------|---------------------------------------------------|
| PHQ-9            | `phq9_1` … `phq9_9`, `phq9_total`                   | items 0–3, total 0–27                             |
| GAD-7            | `gad7_1` … `gad7_7`, `gad7_total`                   | items 0–3, total 0–21                             |
| SCL-20           | `scl20_mean`                                        | mean of the 20 SCL-90 depression items, 0–4       |
| HSCL             | `hscl_total`                                        | mean-item score, 0–4                                 |
| BDI              | `bdi1_total` (BDI-II would be `bdi2_*`)             |                                                   |
| CES-D            | `cesd23_total`, `cesd23_percent_of_maximum`         |                                                   |
| K10              | `k10_total`                                         | 10–50                                             |
| HRSD-17          | `hrsd17_total`, `hrsd17_suicide`                    | suicide item 0–4                                  |
| CIS-R            | `cisr_total`                                        | 0–57                                              |
| PROMIS depression| `promis_depression_total`, `promis_depression_tscore` | T-score                                         |
| EQ-5D            | `eq5d_<domain>`, `eq5d_total`                       |                                                   |
| SF-36 / SF-12    | `sf36_<domain>_value`, `sf36/sf12_*_component_summary` |                                                |

The range checks for these instruments are in
`tests/test_depression_instruments.py` (see [Testing](testing.md)).

**PHQ-9 is the primary outcome** of the current analysis. Only studies with
PHQ-9 at baseline and at about 12 months reach the
[analysis dataset](analysis/analysis-dataset.md).

## Annotation files

These small CSVs in `data/raw/annotations/` are the only data files tracked
in git:

| File                                               | Purpose                                                                  |
|----------------------------------------------------|--------------------------------------------------------------------------|
| `dataset_id_conversions.csv`                       | POOL2 `StudyNo_POOL` → project `StudyNo_OURS` ([POOL2](pipeline/merge-and-enrich.md#pool2-demographic-backfill)) |
| `study_level_extra_infos.xlsx - extra_infos.csv`   | Collaborative-care characteristics of each intervention arm ([Enrichment](pipeline/merge-and-enrich.md#enrichment)) |

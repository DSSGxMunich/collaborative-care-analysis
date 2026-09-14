# Data problems found while auditing the loaders and harmonizing the columns

49 entries. Severity is about the effect on a result, not on the code:
`critical` would have changed a published number, `resolved` means the entry
records how something was decoded rather than a defect that remains.

Kept as Markdown rather than CSV because this repository ignores `*.csv` to
keep data files out of version control, and this is documentation.


## critical

| study | column | problem | what was done | found by |
|---|---|---|---|---|
| 12_Gensichen_2009 | `GebJahr` | Two-digit birth year used directly as age in harmonization_baseline; wrong by up to 70 years | Age rederived from gebdatum minus baseline visit date | loader audit |
| 28_Simon_2004 | `Group` | The two intervention arms were swapped; group 1 is care management plus psychotherapy, not care management alone | 1620 rows relabelled | loader audit vs paper |
| 33_Zimmerman_2016 | `Group` | Arm labels inverted relative to the paper (IG n=134, CG n=191) | Swapped back on load; 650 rows change arm | loader audit vs paper |
| 03_Aragones_2019 | `cm_dm` | Comorbidity flags coded 1/blank; reading blank as missing rather than no silently discarded every negative | Explicit one_blank_no coding per study | code review |

## high

| study | column | problem | what was done | found by |
|---|---|---|---|---|
| 22_Richards_2013 | `gad7_total` | Integer values 0-26 against a GAD-7 maximum of 21, at every wave; study ships no items and codebook does not state the scale | Excluded from the pooled gad7_total; PHQ-9 unaffected | instruments range check |
| 15_Katon_1996 | `cds2` | Chronic condition count is 0 for all 65 patients, which cannot be real | Excluded from n_chronic_conditions_reported | comorbidity screen |
| 05_Bekelman_2015 | `CRF_DM` | Comorbidity form re-administered at every visit; 192 of 384 patients give a different answer later | Baseline answer taken and carried forward, not first non-null in row order | comorbidity verification |
| 08_Coventry_2015 | `ltc1-ltc20` | Twenty condition columns whose own codebook marks them 'Unklar'; values 0-5 with no documented meaning | Left unharmonized and recorded as unusable | comorbidity screen |
| 12_Gensichen_2009 | `ICD101-ICD123` | Up to 23 ICD-10 diagnosis codes per patient, never used by any harmonization script | Now the source for 10 comorbidity columns in this study | comorbidity bottom-up screen |
| 15_Katon_1996 | `katon1996.sav` | Loader path lower-case but the file is Katon1996.sav; works only on case-insensitive macOS | Filename corrected | loader audit |
| 23_Rollman_2009 | `zip archive` | Loader extracts from a zip that is no longer in the study folder; worked only because extracted files lingered | Now fails with a clear message | loader audit |
| 32_Wells_2000 | `zip archive` | Same missing-zip problem | Now fails with a clear message | loader audit |
| 13_Hölzel_2018 / 31_Unützer_2002 | `filenames` | Non-ASCII study names decompose to NFD when a filename passes through an archive on macOS; study IDs then silently fail to match and both studies drop out | normalize_study_id added to config; cost 9 points of age coverage when it happened | age coverage diff |
| 24_Rollman_2016 | `phys_comorbid_when` | Timing is a de-duplicated set per patient, not one entry per condition: up to 15 conditions but at most 3 timings, counts agree in only 16% of rows. Per-condition timing is unrecoverable | Patients whose timings are all post-enrollment excluded; the rest kept with the limitation recorded | second-pass review of RELAX metadata |
| 12_Gensichen_2009 | `ATC columns` | N06A antidepressant codes sit at months 6 and 12 (294 and 287 patients) and on only 4 baseline rows; the columns without a T-suffix are not baseline columns | ds_12 excluded from baseline antidepressant use; would have been an outcome used as a covariate | timepoint distribution check |

## medium

| study | column | problem | what was done | found by |
|---|---|---|---|---|
| 26_Salisbury_2016 | `phq9_total` | 2 non-integer PHQ-9 totals; a sum of integer items cannot be fractional and no items ship to recompute | Set missing with a warning | instruments whole-number guard |
| 26_Salisbury_2016 | `gad7_total` | 31 non-integer GAD-7 totals | Set missing with a warning | instruments whole-number guard |
| 02_Aragones_2012 | `CARDIOVASC` | Codebook documents 1/0 but the data holds 1 and 2 and never 0; the 4 twos are undocumented | Those 4 patients recorded as unknown | comorbidity value check |
| 04_Bekelman_2018 | `phqtotal` | Disagrees with the sum of its own items on 3 rows and scores 21 further rows from an incomplete item set | phqtotalv2 used instead; it matches the items exactly | instruments cross-check |
| 10_Fletcher_2021a | `gad_total_impute` | Imputed variant of gad_total, 7 extra rows, unlabelled as imputed | Non-imputed gad_total used | instruments screen |
| 33_Zimmerman_2016 | `ZDepression_severity` | Depression score already standardised within study (mean 0, sd 1) | Not used; instruments stay on native scales | instruments screen |
| 18_Katon_2004 | `LTC_0/LTCsev_0` | Comorbidity data in a study with no medical-history script at all | Identified; not yet harmonized, checklist behind it unidentified | comorbidity screen |
| 09_Davidson_2013 | `MI_Event/UrgRevasc/*_los` | Cardiac events and lengths of stay recorded during follow-up, not at baseline | Excluded from comorbidity; they belong to censoring/outcomes | comorbidity screen |
| 24_Rollman_2016 | `haheart` | Looks like a heart-disease flag; is actually the cardiovascular-symptoms item of the SIGH-A anxiety scale (hamood, hatense, hafear, haheart, habreath...) | Not used as a comorbidity; trap avoided | RELAX Meta Data |
| 10_Fletcher_2021a | `ad_rec` | Reads as antidepressant; the Stata codebook says Anxiety/Depression (EQ-5D-5L yesno). Trusting the name would have invented an 81.6% antidepressant rate | Used as the EQ-5D anxiety dimension instead | codebook log |
| 21_Richards_2008 | `Antidepress_dose` | Reads as antidepressant dose; labelled Knowledge of dose of antidepressants baseline, i.e. what the patient knows | Not used as medication use | value labels |
| 11_Fletcher_2021b | `live_spouse_0` | Asks whether a spouse lives in the household while ds_32 asks whether the patient is married; the two are not the same question | Column renamed has_spouse_or_partner and both wordings recorded | self-audit |
| 24_Rollman_2016 | `roster conditions` | A roster answers only the conditions it lists; ds_24 has no renal category, so has_renal_disease was False for all 1860 rows, claiming the study asked and found nothing | ds_24 now contributes no value; column drops from 5 studies to 4 | diagnostics |
| 12_Gensichen_2009 | `ICD101-ICD123` | The diagnosis list is recorded once on the baseline row; follow-up rows are empty by design and were reading as negative findings | Rows with no codes are now missing rather than negative | diagnostics |
| 10_Fletcher_2021a | `withdraw` | Unix timestamps (2018-07-05 to 2019-03-27) for 78 patients: this is the withdrawal DATE, while withdrawal is the 0/1 flag. Listed as a censoring candidate on the wrong assumption | Corrected in the candidate notes; a magnitude guard now flags any consumed column above 1e6 | large-number scan |
| 11_Fletcher_2021b | `death_t / phq2wk_dead_di_t` | Named as death but labelled Thought-of-death(Priorities) and Thoughts that you would be better off dead: PHQ-9 suicidal-ideation items, not vital status. Previously listed as a death study | Excluded; death coverage is 2 studies not 3 | clinical-events screen |

## low

| study | column | problem | what was done | found by |
|---|---|---|---|---|
| 13_Hölzel_2018 | `GAD7_1` | 2 responses coded 9, outside the 0-3 response range | Set missing with a warning | instruments range check |
| 12_Gensichen_2009 | `DatBefT1` | 2 survey dates land in 2050 and 2066; DDMMYY typos whose two-digit year pivots into the future | Not consumed; noted for anyone parsing visit dates | visit-schedule check |
| 12_Gensichen_2009 | `DatBefT2` | Reports 626 non-null but 100 are empty strings, so it holds 526 real dates | Blanks read as missing, not as values | visit-schedule check |
| 30_Srinivasan_2022 | `HbA1c` | Lab value present but no diabetes diagnosis column | Not thresholded; ds_30 contributes no diabetes flag | comorbidity screen |
| 12_Gensichen_2009 | `GHZ_T2` | EQ-5D VAS recorded only at month 12 despite an untagged name | Kept as a row-level VAS value | timepoint check |
| 32_Wells_2000 | `MARRIED` | Unlabelled 0/1. Direction corroborated by the variable label SCREENER NOW MARRIED, the codebook frequency table (739 vs 617) and the repo existing baseline script mapping 1 to Married; no publication reports a marital breakdown so it stays unvalidated | Direction kept; column renamed has_spouse_or_partner | self-audit |
| 13_Hölzel_2018 | `FIMA_Med*_PZN` | Values up to 9e9 that look like missing encodings but are German drug identifiers (Pharmazentralnummer) | Not consumed by any cluster; recorded so the magnitudes are not re-investigated | large-number scan |
| 20_Patel_2010 | `h9/h9a/h9b/das_h14` | Carry 9999 as a missing code; CISRTot, the only column consumed from this study, is clean (0-48) | No action; consumed columns verified free of out-of-distribution codes | large-number scan |

## resolved

| study | column | problem | what was done | found by |
|---|---|---|---|---|
| 08_Coventry_2015 | `ltc1-ltc20` | Decoded from the paper: Bayliss burden ratings for up to 20 long-term conditions, 0 meaning absent. Counting above zero gives 7.49, and 6.35 after subtracting each patient's diabetes and heart-disease index conditions, reproducing the published 6.2 (SD 3.0) | ds_08 now contributes a validated condition count | paper |
| 04_Bekelman_2018 | `dem_smoke` | Unlabelled 0-3 code; the study codebook gives 1=Current, 0=Never, 2=Quit <1yr, 3=Quit >=1yr | Smoking harmonized | study codebook |
| 05_Bekelman_2015 | `CRF_SMOKE` | Unlabelled 1-4 code; the compiled data dictionary gives 1=Current, 2=Quit <1yr, 3=Quit >=1yr, 4=Never | Smoking harmonized | PCDM data dictionary PDF |
| 30_Srinivasan_2022 | `educ/educ_NPS` | Unlabelled; the Hope codebook gives educ = years of schooling and educ_NPS = 0 none / 1 primary (1-7) / 2 secondary or higher (>7) | Fixes the threshold used for cross-country education | Hope Codebook |
| 10_Fletcher_2021a | `mo/sc/ua/pd/ad` | A complete EQ-5D-5L hidden under two-letter names, missed on the first pass | EQ-5D dimensions extended from 4 studies to 5 | codebook log |
| 11_Fletcher_2021b | `live_alone_0` | Paper reports Live alone 130 (13.9) and 109 (11.7) by arm | Harmonized column gives 12.8%, an exact match | paper validation |
| 09_Davidson_2013 | `ACM_Event` | All-cause mortality adjudicated as yes/no; missed by the first censoring screen | Now a second death study alongside ds_04 | clinical-events screen |
| 04_Bekelman_2018 | `days_until_death` | Paper reports 10 patients died on CASA and 13 on usual care; the column records a death time for exactly 23 patients | Validated exactly | paper validation |
| 10_Fletcher_2021a | `withdrawal` | 0/1 withdrawal flag recorded at months 6, 12 and 18 over 3107 rows; empty on the baseline row, which hid it from a patient-level check | Harmonized as withdrew_from_study, 68 patients | clinical-events screen |

## open

| study | column | problem | what was done | found by |
|---|---|---|---|---|
| 24_Rollman_2016 | `SIGH-A items` | A 14-item Hamilton Anxiety scale present in this study and not harmonized by any cluster | Recorded as a further instrument family | RELAX Meta Data |

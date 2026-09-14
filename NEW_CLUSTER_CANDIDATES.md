# Cluster candidates found by mining the unharmonized columns

Found by grouping the remaining 3,354 columns into blocks of similarly-named
siblings, which surfaces whole instruments rather than stray columns. Named
instruments appear as blocks of 14 to 50 columns in a single study.

## Implemented from this pass

**Baseline antidepressant use** (`medication` cluster, 4 studies). Whether a
patient entered the trial already on an antidepressant, ranging from 22% of
ds_11 to 88% of ds_26. Three studies validated against their own published
baseline tables. This is arguably the most clinically important covariate the
dataset was missing.

**EQ-5D extended** (`functioning`). ds_10 turned out to carry a complete
EQ-5D-5L under two-letter names (`mo`, `sc`, `ua`, `pd`, `ad`), taking the
dimensions from 4 studies to 5. A `eq5d_vas` column was added for the 0 to 100
self-rated health line, which needs no national value set and so pools where
the utility index cannot: 3 studies.

## Worth building next, in order

| candidate | studies | what is there |
|---|---|---|
| health service use | 6 | ds_08's 50-column `fsuq` battery (GP visits, outpatient, hospital), ds_11's visit counts by provider type, ds_26's outpatient counts, ds_09's `counsel_*` by provider |
| self-rated health (SF-36 item 1) | 3+ | ds_11 `health_0`/`health_t`, ds_12 `sf_f1`/`SF361_T3`, all 1 to 5 |
| SF-36 subscales | 2 | `pf_`, `mh_`, `vt_`, `sf_`, `rp_`, `re_`, `gh_trans_score`, standard 0-100 transformed scales |
| patient activation / care quality | 2 | ds_08's 20-column PACIC battery, ds_08 `*patact` |

## Single-study instruments, recorded so nobody hunts for them again

WHOQOL-BREF (ds_08, 26 columns), AQoL (ds_11, 35), Diabetes Quality of Life
(ds_08, 45), heiQ (ds_08, 41), Seattle Angina Questionnaire (ds_08, 19),
SCHFI self-care of heart failure (ds_04, 23), KCCQ (ds_04/ds_05), SIGH-A
Hamilton Anxiety (ds_24, 14 items), WHODAS (ds_19).

None of these appears in more than two studies, so each contributes
within-study information only.

## Deliberately not pursued

**ds_10's withdrawal columns, corrected.** `withdraw` is not a flag: it holds
Unix timestamps from 2018-07-05 to 2019-03-27, so it is the withdrawal *date*
for 78 patients. `withdrawal` is the 0/1 flag over 3,107 rows. Together they
are a usable date-and-flag pair for one study, which is still too thin for a
censoring cluster but is not what the first pass recorded.

**Medication adherence** (5 studies) is a self-report scale in some studies, a
pill count in others, and days-missed-per-month-per-drug in ds_08. The name is
shared; the construct is not.

**ds_12's ATC drug codes.** 351 of 623 patients have an antidepressant code,
but they sit on the 6- and 12-month rows (294 and 287 patients) against 4 at
baseline. They record prescriptions written during the trial, so they are an
outcome. Genuinely interesting for a different question.

## Two near misses this pass caught

* **`ad_rec`** in ds_10 reads like "antidepressant, recoded" and is
  "Anxiety/Depression (EQ-5D-5L yesno)". Taking the name at face value would
  have produced an 81.6% antidepressant rate for that study.
* **`haheart`** in ds_24 reads like a heart-disease flag and is the
  cardiovascular-symptoms item of the SIGH-A anxiety scale.

Both were caught only by opening the study's own codebook rather than trusting
the column name.

# Column-cluster plan: the 17 remaining clusters

Step 2 inventory + Step 3 design proposals, per PROMPT_column_harmonization.md.
Nothing here is implemented. Each cluster still needs your approval before code.

**Evidence base.** Three sources, in descending order of trust:
1. the 29/26/29/29 existing per-study `harmonization_*` scripts, which are
   reviewed raw->construct decisions and the best evidence available;
2. codebook labels via `variable_labels.py` (only 43% of raw columns carry one);
3. column names, which are the weakest signal and are never trusted alone.
Per-study paper/appendix verification happens per cluster at implementation, the
way age and sex were done. Where a plan below rests only on (3), it says so.

Coverage counts are "studies with a usable source", counting both what an
existing script already maps and raw candidates in studies it skipped.

---

## Tier A: ready to design now, high coverage

### A1. Measurement instruments (own cluster, per the prompt)
The largest cluster and the one the whole analysis leans on. Six families, only
two of them multi-study, and those two are disjoint.

| family | studies | follow-up points |
|---|---|---|
| PHQ-9 total | 15 | mostly 0/3/6/12; ds_22 to 36mo; ds_24 seven waves |
| PHQ-9 items 1-9 | 7 | subset of the above |
| GAD-7 total | 9 | 0/3/6/12 |
| GAD-7 items 1-7 | 6 | |
| SCL-20 mean | 9 | ds_14/15 at 1/4/7mo; ds_19 to 24mo |
| HSCL | 1 (ds_03) | 0/3/6/12 |
| BDI | 1 (ds_09) | |
| CES-D | 2 (ds_22, ds_32) | |
| HRSD-17 | 1 (ds_23) | |
| EQ-5D | 6 (ds_08, 10, 13, 21, 22, 26) | |
| SF-12/36 | 4 (ds_09, 12, 22, +) | |
| KCCQ | 2 (ds_04, ds_05) | heart-failure specific |
| WHODAS | 1 (ds_19) | |
| AUDIT | 2 (ds_04, ds_32) | |

Design: one harmonized column per instrument-scale, never a merged
"depression_score". Keep items and totals as separate columns. Recompute a
total from items only where items are complete, and flag rather than impute.

**SETTLED (2026-09-13): instruments are not bridged.** There is no need for one
model spanning all 30 studies, so each instrument keeps its native scale and
analysis proceeds per instrument family. No merged `depression_severity`
column, no cross-walk, no within-study standardisation in harmonization. If a
bridge is ever wanted it belongs in a model script. This also means the six
single-study instruments are not a problem to solve: they simply contribute
within-study information only.

Remaining design notes:
- ds_08's `follow_up_months` is **continuous** (2.9-16.2), a single free-running
  follow-up by design. Storage is already lossless (float64, 102 distinct
  values, full precision preserved end to end). The risk is any future logic
  that aligns visits across studies by grouping on this column.
- SCL-20 is a 0-4 mean, PHQ-9 a 0-27 sum. Never normalise silently.
- ds_32's existing `cesd23_percent_of_maximum` is a per-study artifact of that
  study's own script, not a template to copy.

### A2. Sex (done), A3. Age (done)
Implemented. Listed for completeness.

### A4. Socioeconomic / cultural / ethnic attributes (Iezzoni 9)
Existing scripts are thin: race 6 studies, employment 5, education 4,
marital 2, income 1. Raw candidates recover more.

| variable | script | raw candidates | plausible total |
|---|---|---|---|
| education | 4 | ds_09, 11, 12 (`Schulab`), 13 (`Bildung`), 26, 30 | ~10 |
| employment | 5 | ds_08, 10, 11, 12 (`erwerb`), 13, 26, 32 | ~11 |
| race/ethnicity | 6 | ds_04, 08, 09, 19, 23, 24, 25, 26, 32 | ~12 |
| income | 1 | ds_11, 26, 30 | ~4 |
| marital status | 2 | ds_11 (`live_spouse_0`), 32 (`MARRIED`) | ~4 |

**Judgment calls:** education levels are country-specific and not rankable
across US/UK/German/Indian systems without a decision (German `Schulab` has no
clean US equivalent). Race/ethnicity categories differ by country and census
era; US studies use OMB categories, ds_08 uses UK ones, ds_26 its own.
I would NOT force a common scheme; propose per-country categories plus a
coarse derived flag only if you want one. **Income and marital status are
probably not viable as covariates** at ~4 studies.

---

## Tier B: designable, moderate coverage

### B1. Comorbidity burden (Iezzoni 6)
Best-supported clinical cluster. From the medical_history scripts:
diabetes 12, hypertension 8, cancer 7, `number_of_chronic_conditions` 7,
heart attack 5, arthritis 5, COPD 4, heart failure 4, plus a long tail.
Two studies carry a `chronic_disease_score` (Von Korff/Clark) and one a Duke
severity index.

Design: a small set of `has_<condition>` booleans for the conditions present in
>=5 studies, plus a count. **Judgment call:** whether to build a Charlson-style
index. The studies do not share the inputs for one, and the existing
`chronic_disease_score` is explicitly "not a simple count" (see
`harmonization_medical_history/ds_17`). I propose count + individual flags, no
derived index.

### B2. Principal diagnosis (Iezzoni 4) and B3. Severity of it (Iezzoni 5)
Depression is the principal diagnosis by construction in most studies, so the
informative variables are *type* and *severity*, not presence: major vs minor
depression, dysthymia, recurrence, episode duration.
ds_14/ds_15 export only the major-depression subgroup; ds_20 only the
depression subgroup of a wider CMD trial. Those are cohort facts already
documented in the loaders and belong here.
**This cluster overlaps the eligibility-criteria work you are holding.** Much
of "principal diagnosis" is fixed by each study's entry criterion, not measured
per patient. I would design it after eligibility is settled, not before.

### B4. Physical functional status (Iezzoni 7)
Sources are instrument sub-scales rather than standalone columns: SF-36/SF-12
physical component, EQ-5D mobility/self-care/usual-activities, WHODAS (ds_19).
Overlaps A1 heavily. Proposal: derive this cluster **from** the harmonized
instrument columns rather than from raw, once A1 exists. No independent raw
inventory needed.

### B5. Psychological / cognitive / psychosocial (Iezzoni 8)
GAD-7 and anxiety items (A1), plus smoking (3 scripts + raw), alcohol (AUDIT,
2 studies), social support and self-efficacy batteries in ds_08/ds_11/ds_26.
Cognitive measures are effectively absent: no MMSE/MoCA found in any study,
and several trials exclude cognitive impairment at entry. **Alert:** "cognitive
functioning" cannot be harmonized; it should be recorded as not measured rather
than left looking like missing data.

### B6. Health status and quality of life (Iezzoni 10)
EQ-5D (6 studies), SF-12/36 (4), KCCQ (2, heart failure only), plus
`self_rated_health_status` in one script. Same derive-from-A1 approach as B4.

---

## Tier C: the data does not support these

### C1. Clinical override / censoring events
**This is the one I need you to look at.** The prompt asks for vital status,
hospitalisation during follow-up, and discontinuation reason. What exists:

- **death / censoring: 3 studies.** ds_04 (`days_until_death`,
  `days_until_censoring`), ds_11 (`death_t`), and a ds_32 hit that is a
  false positive (a CES-D *item* about thoughts of death, not vital status).
  So realistically **2 studies**.
- **discontinuation: 1 study.** ds_10 (`withdraw`, `withdrawal`).
- **hospitalisation: 5 studies**, and mostly as service-use questionnaire items
  (ds_08's `fsuq*` battery, 22 columns) rather than a clean event flag.

Consequence: for 28 of 30 studies we cannot tell a missing follow-up caused by
death from one caused by anything else. A cluster built on 2 studies is not a
covariate, and any informative-censoring or competing-risks handling is out of
reach from the IPD as delivered. Options: (a) build it for the 2-5 studies and
label it explicitly as unusable for pooled modelling, (b) go back to the CONSORT
diagrams in the papers, which do report deaths and withdrawals at study level
but not per patient, (c) drop the cluster and record why. **I recommend (c)
plus a note, and would not start it without your call.**

### C2. Acute clinical stability (Iezzoni 3)
Vitals and labs appear in a handful of studies only (BP and pulse in ds_04/05,
HbA1c in ds_30, BMI scattered). Baseline hospitalisation history, which is the
other route in, has the timing-ambiguity problem the prompt flags. Coverage is
too thin to pool.

### C3. Patient attitudes and preferences (Iezzoni 11)
18 candidate pairs across 8 studies, and most are treatment-adherence or
patient-activation items rather than outcome preferences. `medication_adherence`
exists in 2 scripts. Not a viable cross-study covariate; propose recording as
not-measured.

### C4-C8. The five baseline-covariate points
These are not separate clusters in the data sense:
- *baseline measurement of the response* = the A1 instrument at month 0.
- *most recent status* and *trajectory as of time zero* = derived from A1 across
  follow-up, once A1 exists.
- *variables explaining variation in the response* and *subtler predictors* are
  modelling-stage selection criteria, not harmonisation targets.
Propose folding these into A1 as derived columns, and saying so explicitly
rather than leaving five empty cluster slots.

### C9. Study eligibility criteria
On hold at your instruction. Blocks B2/B3 cleanly.

---

## Proposed order

1. **A1 instruments** — largest payoff, unblocks B4 and B6.
2. **B1 comorbidity** — best clinical coverage after instruments.
3. **A4 socioeconomic** — real gaps to recover, but needs your call on
   cross-country categories first.
4. **B4/B6** derived from A1.
5. **B5** minus cognition.
6. B2/B3 after eligibility.
7. C1-C3 only after you decide; my recommendation is to document them as
   not supported rather than build them.

That is 6 implementable clusters, not 17. The honest headline is that the IPD
supports instruments, comorbidity and sociodemographics well, and most of the
remaining Iezzoni dimensions thinly or not at all.

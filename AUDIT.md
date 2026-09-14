# Self-audit of the cluster harmonization

Asked: did I make mistakes, what could have gone wrong, am I using all the
information, can I validate everything against the papers. Honest answers below.

## Mistakes I made

Six, five of which I caught while building and one only during this audit.

1. **Roster catch-all over-counting (caught by this audit).** ds_24's
   comorbidity roster has an entry reading "Other, e.g. chronic sinusitis,
   chronic bronchitis", chosen by 276 patients. My respiratory pattern matched
   the word "bronchitis" inside the *category label*, so 35 patients were
   marked as having a lung condition on the strength of an example in a
   catch-all option. Fixed: ds_24 respiratory went from 77 patients to 42.
   Found only by printing all 49 roster tokens and checking which pattern
   caught each one.
2. **Reading follow-up values as baseline (ds_05).** `broadcast_within_patient`
   takes the first non-null value in row order. ds_05 re-administers its
   comorbidity form at every visit and 192 of 384 patients change answer, so
   the harmonized value was an arbitrary visit. Fixed by taking the month-0
   answer. Caught by 146 disagreements against the existing pipeline.
3. **Nearly using follow-up prescriptions as baseline (ds_12).** Its ATC
   antidepressant codes sit on the 6- and 12-month rows, 294 and 287 patients,
   against 4 at baseline. Caught by checking the timepoint distribution before
   trusting the column names.
4. **A wrong "fix" that made things worse (ds_24 timing).** I assumed
   `phys_comorbid_name` and `phys_comorbid_when` were parallel lists and
   filtered per condition. They are not: up to 15 conditions against at most 3
   timings, agreeing in 16% of rows. The result collapsed ds_24's prevalences
   to about 6%, which is how I noticed.
5. **A near miss on a column name (ds_10 `ad_rec`).** Reads as "antidepressant,
   recoded"; the codebook says "Anxiety/Depression (EQ-5D-5L yesno)". Would
   have produced an 81.6% antidepressant rate.
6. **Reporting numbers from a stale file.** Twice I ran the build with output
   piped away, did not notice it had crashed, and read results from the
   previous CSV. Both times the numbers I quoted were real but out of date.
   This is the process failure that worries me most, because nothing about the
   output looks wrong. Every build now gets its "Wrote harmonized_data.csv"
   line checked.

## What is validated against the papers

| study | construct | paper | computed |
|---|---|---|---|
| ds_23 | hypertension | 131 + 122 | 253 |
| ds_23 | diabetes | 60 + 68 | 128 |
| ds_23 | stroke | 12 + 12 | 24 |
| ds_23 | hyperlipidaemia | 128 + 117 | 245 |
| ds_26 | antidepressant use | 258/288, 251/289 | 88.2% |
| ds_09 | antidepressant use | 27 + 26 of 150 | 35.3% |
| ds_08 | antidepressant use | 59 + 73 | 132 of 360 |
| ds_08 | condition count | 6.2 (SD 3.0) | 6.35 |
| 15 studies | age | Table 1 means | 11 exact, none worse than 0.7y |
| several | sex | Table 1 counts | exact |
| ds_11 | lives alone | 130 (13.9) + 109 (11.7) | 12.8% |

## What is not validated, and why

Most comorbidity prevalences outside ds_23, all of education, employment,
living alone, smoking, EQ-5D, the SF summaries and all of service use.

Two reasons. Some papers simply do not report the quantity: ds_04 and ds_05
never give a smoking percentage in their main text, and ds_31 gives no diabetes
figure. Others report it in a form that cannot be compared without more work,
such as by arm with different denominators, or in a figure rather than a table.

Where a paper reports nothing, the mapping rests on the codebook alone. That is
weaker evidence than a matched aggregate, and the columns concerned are marked
as such in their modules.

## What could still be wrong

* **Unlabelled binary columns read by name.** `lives_alone` and ds_32's `WORK`
  are 0/1 with no value labels. Direction was checked by prevalence
  plausibility, which would not catch an inversion if the true rate were near
  50%. `lives_alone` is now validated (see below); ds_32's `WORK` at 63.2% is
  not.
* **Roster and code-based studies.** ds_24's conditions may include some
  diagnosed after enrollment, since per-condition timing does not exist.
  ds_12's ICD codes are the practice's list of important diagnoses, so absence
  is not proof of absence.
* **Service use reference periods differ** by study and by wave, from one month
  to six. The flags say whether a service was used, never how often, precisely
  because a count would mix those windows. They are still not rates.
* **The 56% of columns with no label at all.** Everything here rests on names
  and on documentation that exists. A column with an opaque name and no
  codebook entry cannot be found by any method I have used, and 414 such
  columns remain.

## The strategy that worked best

Comparing a computed aggregate against a number printed in the paper. It is the
only method here that can confirm a meaning rather than suggest one, and it
decoded ds_08's twenty "unclear" columns outright. Where a paper reports a
baseline table, it should be the first thing consulted, not the last.


## Follow-up: the `is_partnered` direction

Flagged above as the most exposed inference. Investigated, and the conclusion
is that the direction was right but the **name was wrong**.

*Direction.* ds_11's column carries value labels (0 No, 1 Yes), so it was never
in doubt. ds_32's `MARRIED` has none, and three independent lines agree that 1
means married: the variable label is the yes/no phrasing "SCREENER NOW
MARRIED"; the study's own codebook frequency table gives 739 ones against 617
zeros, a plausible 54.5%; and this repo's existing
`harmonization_baseline/ds_32` script, written independently, maps 1 to
"Married". No flip was needed.

*Validation.* Not possible. Wells 2000's Table 1 describes the study sites, not
the patients, and mentions marriage only when discussing retention. The
Fletcher 2021b report gives no marital breakdown either. Two papers, neither
reports the quantity.

*What did change.* The two studies are not asking the same question. ds_11 asks
whether a spouse lives in the household, ds_32 whether the patient is currently
married. A married person living apart answers yes to one and no to the other;
an unmarried cohabiting couple the reverse. The 54.5% against 32.0% gap is
partly cohort and partly construct. The column is renamed
**`has_spouse_or_partner`**, which is what the two questions share and no more,
with each study's exact wording recorded.

While chasing this, ds_11's `lives_alone` was validated exactly: the paper
reports "Live alone 130 (13.9) 109 (11.7)" by arm, 239 of 1,868, and the
harmonized column gives 12.8%.


## Diagnostics added, and what they immediately found

A shared `checks.py` now backs every cluster, and `concat` and `build` carry
structural checks of their own. The rule throughout is the repo's: a data
problem warns and drops to missing, a code or schema problem raises, and no
value is ever logged.

What the harness checks: that a study's declared source columns exist and that
the study has rows at all (raise); that `HARMONIZED_COLS` matches what
`harmonize()` actually returned, that two clusters never claim the same column
name, and that every emitted column has a provenance entry (raise); that no
harmonized column is empty across all studies (raise). Then it reports the
join key's uniqueness, which column names are shared between studies, coverage
and dtype per column, columns from a single study, studies contributing
nothing, and columns answered per study.

Running it dropped the warning count from 18 to 6, and the twelve that
disappeared were all real:

* **"not asked" was being recorded as "no".** ds_12 records its ICD diagnosis
  list once, on the baseline row; ds_24 records a roster the same way. Rows
  where the list was simply not taken were reading as negative findings. They
  are now missing. This is the same class of error as the blank-means-no trap,
  in the opposite direction.
* **A roster answers only the questions it asks.** ds_24's 49 condition names
  include nothing renal, so `has_renal_disease` was False for all 1,860 of its
  rows, which claims the study asked and found nothing. It now contributes no
  value at all, and the column drops from 5 studies to 4. That is a loss of
  coverage and a gain in honesty.
* **The baseline invariant was being checked on the wrong series.** The check
  ran before the month-0 value was resolved, so it flagged twelve columns as
  varying within patient when the output was in fact constant. Checking the
  resolved column instead confirms the invariant holds everywhere.
* **A percentage came out negative**, which is how I noticed that the tobacco
  column is derived from a roster rather than read from a source column of the
  same length.

The six remaining warnings are the documented data problems, not defects:
ds_26's non-integer scores, ds_13's response coded 9, ds_02's undocumented
third value, and ds_12's unclassifiable "Anderer Schulabschluss".

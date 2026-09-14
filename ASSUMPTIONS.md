# Assumptions the harness and clusters rest on, and how each was tested

Every harmonized column is built on beliefs about the raw data. These are the
ones I could name, each tested against the frame rather than argued about.
Twenty-one tests, three of which found something.

## Frame assembly

| # | assumption | result |
|---|---|---|
| A1 | (study, patient, visit) is a unique key | **pass**, no duplicates |
| A2 | patient ids are only unique within a study | 2,475 ids appear in more than one study, which is safe because every group-by keys on study as well |
| A3 | every study has a month-0 row | **pass** |
| A4 | every patient has a month-0 row | **pass**, so the baseline rule never falls back |
| A5 | a shared column name means the same type everywhere | **false**: `sex`, `Sex` and `Group` hold int, str and float across studies |
| B4 | no source column is mixed *within* one study | **pass**, which is what makes the `errors="raise"` reads safe despite A5 |
| B2 | every declared source column exists | **pass**, 410 declared |
| B3 | no declared source column is entirely empty | 7 empty: ds_12's `ICD117`-`ICD123`, diagnosis slots nobody filled. Harmless |

## Instruments and scales

| # | assumption | result |
|---|---|---|
| C1 | the declared EQ-5D version matches the data | **pass** for all five studies; the 5L studies do reach level 5, so a 3L study cannot be silently mislabelled |
| C2 | PHQ-9 items are in canonical order | item 9 has the lowest mean overall, as expected |
| C3 | ...in every study | **ds_30 flagged**, item 7 lower than item 9. Chased to its codebook: the order is correct (`phq7` is concentration, `phq9` is "better off dead"). A false positive of the heuristic, and that cohort simply reports concentration problems less often |
| E | every numeric column sits in its instrument's range | **pass** for all 15 |
| D | missing-value sentinels do not leak | no value outside a plausible range. The 77s and 88s flagged are real ages and VAS scores |
| D2 | no Stata or SPSS missing encoding leaks as a number | **pass**: 3,374 numeric columns scanned, nothing at or above Stata's byte 101, int 32741, long 2147483621, float 1.7e38 or double 8.99e307 thresholds in any consumed column |
| D3 | no consumed column carries an out-of-distribution missing code | **pass** across all 410 |
| D4 | no consumed column is a date or identifier read as a number | **pass** now, and guarded: `checks.check_magnitude` warns above 1e6. Found ds_10's `withdraw` (Unix timestamps) and ds_13's drug identifiers, neither consumed |

## Structure

| # | assumption | result |
|---|---|---|
| F1 | `harmonize()` is deterministic | **pass** |
| F2 | output stays row-aligned to input | **pass** |
| F3 | clusters do not depend on each other's output | **pass**, reversing the order changes nothing |
| F4 | no cluster mutates the input frame | **pass** |
| F5 | no two clusters claim the same column name | **pass**, and the harness now raises if they do |
| F6 | the written CSV round-trips | **pass** |

## Robustness to change

| # | scenario | result |
|---|---|---|
| G1 | a loader is renamed and a source column disappears | **raises**, naming the cluster, study and column |
| G2 | a study drops out of the exports | **raises** |
| G3 | a new unexpected code appears in a mapped column | **warns and leaves missing** |
| G4 | a harmonized column ends up empty everywhere | **raises** in the final audit |

## What is still not covered

* **A sentinel inside a valid range.** ds_13 coded two GAD-7 answers as 9,
  caught only because 9 exceeds that item's range. A study coding missing as 3
  on a 0-3 item would be invisible to every check here. Only a codebook can
  rule that out, and 56% of columns have none.
* **A permuted item order that looks plausible.** C3 can flag an ordering
  anomaly but cannot prove an order correct; ds_30 needed its codebook.
* **The meaning of an unlabelled binary.** `lives_alone`, ds_32's `WORK` and
  `MARRIED` rest on the column name and a plausible prevalence. An inverted
  coding near 50% would pass everything here.
* **Whether a study's population matches its paper.** Cohort definitions were
  checked during the loader audit, not here.
* **ds_08's continuous follow-up.** Nothing pools counts across studies, but
  any future logic that aligns visits by equality will break on it.

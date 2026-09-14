# Harmonization Conventions

## 1. Column Naming

- Use lowercase `snake_case`.
- Prefer clarity over brevity.
- Column names should be expressive and unambiguous, even when this makes them relatively verbose.

Example:

Prefer:

`is_palliative_care_specialist_involved`

over:

`pcs` or just `palliative_care_specialist`

Prefer:

`visits_per_month`

over:

`visit_freq`

---

## 2. Longitudinal Data Structure

Longitudinal/repeated measurements should be represented in row-wise (long) format rather than column-wise (wide) format.

Each measurement time point should occupy a separate row.

Example:

Preferred:

| patient_id | follow_up_months | phq9_total |
|------------|------------------|------------|
| 1          | 0                | 18         |
| 1          | 3                | 12         |
| 1          | 6                | 8          |

Instead of:

| patient_id | phq9_0 | phq9_3 | phq9_6 |
|------------|--------|--------|--------|
| 1          | 18     | 12     | 8      |

---

## 3. Data Loading

If a raw dataset stores repeated measurements in column-wise (wide) format, its dataset-specific `load()` function should reshape the data into row-wise (long) format before returning the DataFrame.

This ensures that downstream harmonization functions receive datasets with a consistent longitudinal structure.

---

## 4. Categorical Encoding

Variables that represent categories but are encoded numerically or as binary values should be converted to descriptive categorical labels during harmonization.

Example:

Prefer:

`0 -> "no"`
`1 -> "yes"`

instead of leaving the values as:

`0`
`1`

Similarly, for study_arm variables:

`1 -> "control"`
`2 -> "intervention"`

rather than keeping the original numerical codes.

The goal is to make harmonized datasets self-explanatory and reduce reliance on
dataset-specific codebooks.

Missing or unknown values should remain missing and should not be automatically
converted to `"no"` or another category.

See section 5 for the dtype each harmonized column should end up with.

---

## 5. Column Data Types

Harmonized columns carry a dtype that matches their meaning, not whatever
pandas inferred.

**Categorical.** A fixed, finite value set uses `category`, not `object`:

`harmonized_df["sex"] = map_with_check(df["gender"], SEX_MAPPING).astype("category")`

Declare the order where order means something (severity, age bands, NYHA class):

`pd.CategoricalDtype(categories=["<40", "40-49", "50-59", "60-69", "70+"], ordered=True)`

**Boolean.** A yes/no fact (named `is_` or `has_` per section 1) uses the
nullable `"boolean"` dtype, not a category and not 0/1. Plain `bool` cannot hold
a missing value, and `.astype(bool)` turns every `NaN` into `True`, breaking
section 4:

`harmonized_df["is_nurse_involved"] = map_with_check(df["nurse"], {0: False, 1: True}).astype("boolean")`

**Numeric.** Scores and measurements stay numeric at their natural resolution.
Do not bin a continuous scale, and do not store a number as a string. Coerce
with `errors="raise"`, so an unparseable value fails the run instead of becoming
`NaN`:

`harmonized_df["age"] = pd.to_numeric(harmonized_df["age"], errors="raise")`

A whole number that can be missing uses `"Int64"`. Plain `int` upcasts the whole
column to `float64` on the first missing value, so `n_hospitalizations` reads
back as `1.0, 2.0, nan` instead of `1, 2, <NA>`:

`harmonized_df["n_hospitalizations"] = pd.array([1, 2, None], dtype="Int64")`

Plain `bool` and `int` are fine where the column is guaranteed complete.

`category`, `boolean` and `Int64` are in-memory dtypes and do not survive
`to_csv()`. These rules describe what a harmonization function returns; code
reading a harmonized CSV back must re-apply them.

---

## 6. Follow-up Time

Use `follow_up_months` to represent the timing of each measurement relative
to baseline.

The value should indicate the number of months since baseline.

Example:

| patient_id | follow_up_months | phq9_total |
|------------|------------------|------------|
| 1          | 0                | 18         |
| 1          | 3                | 12         |
| 1          | 6                | 8          |

Baseline should be represented as:

`follow_up_months = 0`

If the original dataset uses another variable to represent measurement timing,
it should be harmonized to `follow_up_months`.


## 7. Outcome Variables

Outcome variables that measure the same construct should use consistent names across datasets.

Measurement timing should not be included in the variable name. Timing should instead be represented by `follow_up_months`.

### PHQ-9

Use:

- `phq9_1` to `phq9_9` for item-level scores
- `phq9_total` for the total score

The same naming convention should be applied to other symptom scales.

Examples:

- GAD-7: `gad7_1` to `gad7_7`, `gad7_total`
- BDI: `bdi1_1`, `bdi1_2`, ..., `bdi1_total`
- BDI-II: `bdi2_1`, `bdi2_2`, ..., `bdi2_total`

BDI and BDI-II should remain distinct in the harmonized data and should not both be renamed simply as `bdi`.
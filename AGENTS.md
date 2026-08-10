# AGENTS.md

## Data access & privacy rules

This repo contains sensitive datasets. Never inspect or log raw row-level data:
no printing, logging, `head()`, `sample()`, `display()`, or notebook cell output
of individual records, and never include actual values in commit messages, PR
descriptions, or error messages.

**Allowed:** schema/metadata (column names, types, row/column counts) and
aggregates (counts, means, quantiles, null-rates, distributions). Processing
the data (transforms, joins, training) is fine as long as values are never
printed or logged.

**Not allowed:** `SELECT *` on unreviewed tables, writing raw data or samples
to files/fixtures/debug output, or pasting data into prompts or external tools.

If you need to debug something that seems to require real values, try:
synthetic/masked data instead, reducing the problem to a shape/type/null check,
or asking a human to check out-of-band. If none of that works, stop and ask a
human rather than inspecting raw values yourself.

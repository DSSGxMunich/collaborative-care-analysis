# Development

## Environment

```bash
uv sync                 # create .venv and install all dependencies
uv add <package>        # add a runtime dependency (updates pyproject.toml and uv.lock)
uv add --dev <package>  # add a dev-only dependency
```

Python is pinned to `~=3.10.0` in `pyproject.toml` and `.python-version`.

## Linting and formatting

The project uses [Ruff](https://docs.astral.sh/ruff/) with a line length of 99
and sorted imports (`force-sort-within-sections`, first-party package
`collaborative_care_analysis`).

```bash
uv run ruff check . --fix && uv run ruff format
```

CI (`.github/workflows/lint.yml`) runs `ruff check` and `ruff format --check`
on every push and pull request to `main`.

## Pre-commit hooks (optional)

```bash
uvx pre-commit install
```

On each commit, the hooks run:

1. `ruff check --fix`
2. `ruff format`
3. **the full pipeline** (`dataset.py run`). You need the raw data locally, and
   the commit is slower.
4. `uv-lock`, which keeps `uv.lock` in sync with `pyproject.toml`.

If any hook fails, the commit is aborted.

## Notebooks

Notebooks live in `notebooks/`. Name them with a number prefix for ordering
(`01_filter_datasets.ipynb`).

Outputs are stripped from commits with
[nbstripout](https://github.com/kynan/nbstripout). Set it up once per clone:

```bash
uv add nbstripout
nbstripout --install
uv run nbstripout --status   # verify
```

Your local notebooks keep their outputs; only the committed version is
stripped. Still follow the [privacy rules](data-privacy.md) in local outputs.

## Code conventions

- Log with **loguru** (`logger.info`, `logger.success`, `logger.warning`).
  Logs may contain shapes, counts and column names, never values.
- **Fail loudly**: raise on unexpected input instead of silently coercing it.
  Use `map_with_check` instead of `.map()` for recoding.
- Put paths in `config.py` ([Configuration](reference/configuration.md)).
  Do not hard-code `data/…` strings.
- Normalize anything that becomes or is compared with a `STUDY_ID` with
  `normalize_study_id`.
- Follow the [Harmonization conventions](harmonization-conventions.md) for
  harmonized columns.

## Documentation

These docs are in `docs/`:

```text
docs/
├── mkdocs.yml     ← site configuration and navigation
├── docs/          ← the Markdown pages
└── site/          ← build output (git-ignored)
```

```bash
uv run mkdocs serve -f docs/mkdocs.yml   # live preview at http://127.0.0.1:8000
uv run mkdocs build -f docs/mkdocs.yml   # build into docs/site/
```

The site uses MkDocs' built-in `readthedocs` theme with no CDN assets, so it
builds and displays offline. `use_directory_urls: false` makes
`docs/site/index.html` work when opened directly from disk.

To add a page, create the `.md` file under `docs/docs/` and add it to `nav` in
`mkdocs.yml`. `harmonization-conventions.md` is a copy of the root
`HARMONIZATION_CONVENTIONS.md`, so update both when a convention changes.

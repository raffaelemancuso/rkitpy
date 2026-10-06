# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

`rkitpy` is a Python (≥3.13) helper library for data wrangling. Its headline
feature is **STATA-like change logging** layered onto pandas and polars via a
`.raffa` accessor/namespace, plus `.docx` export. It also bundles small,
mostly-independent utilities (logging setup, pickling, progress bars, Selenium,
SQLAlchemy view helpers, bibliometrics/Scopus helpers).

Packaged with the `uv_build` backend in a **src layout** (`src/rkitpy/`).

## Commands

All workflows go through `uv`:

```console
uv sync --extra dev            # install dev deps (ruff + pytest)
uv run pytest                  # run the test suite
uv run pytest tests/test_polars.py                 # one file
uv run pytest tests/test_polars.py::test_endlog_removed_rows   # one test
uv run ruff check              # lint
uv run ruff format             # format
```

Doctests in the narrative docs are executable and run in CI (`.github/workflows/docs.yml`).
Run them locally with the pandas + polars + docs extras:

```console
uv run --extra docs --extra pandas --extra polars \
  sphinx-build -b doctest docs/source docs/_build/doctest
```

CI runs in two workflows: `.github/workflows/tests.yml` (a `lint` job running
`ruff check` + `ruff format --check`, and a `pytest` job with the
pandas/polars/db/web/bibliometrics extras so nothing is skipped) and
`.github/workflows/docs.yml` (the doctests above).

## Architecture

### The two backends share one message builder — this is the central invariant

`src/rkitpy/_logutils.py` is the **single source of truth for all
human-readable log text** (row/column deltas, changed-cell counts, join
provenance, elapsed time, the `JoinCounts` dataclass). `pandas.py` and
`polars.py` only do backend-specific mechanics (state storage, cloning, value
comparison) and then call into `_logutils` for the wording.

Consequence: the pandas and polars accessors are designed to emit **byte-identical
log output**. When changing any log message, edit `_logutils.py` only — never
hand-edit a string in one backend. Doing so silently breaks parity.

Tests and docs are tightly coupled to the exact wording: `tests/test_pandas.py`
and `tests/test_polars.py` assert on literal substrings via `caplog`, and the
`.rst` doctests in `docs/source/` reproduce exact output. Any message change
requires updating those assertions and doctests together.

### How the `.raffa` accessors persist state across a pipeline

`startlog()` stashes the initial shape / optional clone / start time, then
`endlog()` reads it back to compute the diff. The two backends store that state
differently:

- **pandas** (`pandas.py`): registers via `@pd.api.extensions.register_*_accessor("raffa")`
  and appends `_initial_shape` / `_initial_df` / `_start_time` to the object's
  `_metadata` so they survive pandas operations. `endlog()` `del`s them when done.
- **polars** (`polars.py`): polars frames have no attribute storage, so state
  lives in the `config_meta` namespace from the **`polars-config-meta`** package
  (imported for its import side effect). `endlog()` first checks the metadata
  exists and warns "You have to call startlog() before..." if not.

Both register on import: `import rkitpy.pandas` / `import rkitpy.polars` is
what installs the `.raffa` accessor. Each module deletes any pre-existing
`.raffa` accessor at import time to suppress pandas/polars override warnings.

`clone=True` in `startlog()` keeps a full copy so value-level changes can be
detected when the shape is unchanged; `clone=False` (default) only tracks shape
and emits `_logutils.CLONE_FALSE_MSG`. Null-vs-null is treated as *unchanged* in
both backends (pandas masks `isna() & isna()`; polars uses `ne_missing`).

### The logging `join` wrapper

`df.raffa.join(...)` wraps `pd.DataFrame.merge` / `pl.DataFrame.join`, adding
hidden `source_left` / `source_right` row-index columns to reconstruct row
provenance (left-only / right-only / both, duplicate keys, dropped rows), then
logging it via `_logutils.join_log`. Filtering joins (`how="semi"`/`"anti"`) are
detected and logged separately via `filtering_join_log`. pandas has no native
semi/anti join so it is emulated with an inner merge; pandas `"full"` is
translated to merge's `"outer"`. `keep_row_index=True` keeps the source-index
columns in the output (polars uses the `polars-permute` `permute` namespace to
move them to the end).

### `.docx` export

`export_docx.py` holds `DocxFile`, a python-docx wrapper for page setup,
styled tables, and matplotlib/plotly figures. The `DataFrame.raffa.to_docx()`
methods build the table cell-by-cell on top of it and take **two separate
dicts**: `doc_options` goes to `DocxFile.__init__` (document/heading options
such as `heading_text` or `landscape`) and `table_options` to `add_table`
(table options such as `table_style`). The pandas backend renders MultiIndex
columns as one merged header row per level and injects `table_header_rows`
into `table_options` unless the caller sets it explicitly.

### `logging.py`

`create_logger()` is the opinionated entry point users call to actually see the
output (plain `StreamHandler` or `rich.RichHandler`). It re-enables the
`rkitpy.pandas` / `rkitpy.polars` loggers explicitly after `dictConfig`.

## Conventions

- **Every pandas/polars extension lives on the `.raffa` namespace**: all
  Series/DataFrame helper functions are methods of the registered `.raffa`
  accessor (pandas) / namespace (polars) classes — e.g. `s.raffa.toset()`,
  `df.raffa.join(...)`. Never monkey-patch methods directly onto
  `pd.Series` / `pd.DataFrame` / `pl.Series` / `pl.DataFrame`; add new helpers
  to the corresponding `Raffa*` class instead.
- **Optional deps are real**: only `humanize`, `jsonpickle`, `natsort`,
  `python-docx`, `rich`, `tqdm` are core. pandas, polars, sqlalchemy, selenium,
  Pillow/PyMuPDF (`rnote`), etc. live behind extras (see `pyproject.toml`). Tests guard their
  imports with `pytest.importorskip(...)` so the suite passes without every
  extra installed — follow that pattern for any new optional-dep test.
- Every source file carries the **GPL-3.0-or-later license header**. Keep it on
  new files.
- Docstrings use **reStructuredText field lists** (`:param:` / `:type:` /
  `:return:` / `:rtype:`) and are rendered by `sphinx-autoapi`.
- No `[tool.ruff]` config — ruff runs on defaults.

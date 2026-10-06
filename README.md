# rkitpy

A Python library of helper functions for data wrangling. Its main purpose is to
enrich [pandas](https://pandas.pydata.org/) and [polars](https://pola.rs/) with
[STATA](https://www.stata.com/)-like logging and `.docx` export capabilities, but
it also bundles assorted utilities for logging, pickling, progress bars, Selenium,
SQLAlchemy, and bibliometrics.

📖 **Documentation:** <https://raffalib-python.readthedocs.io> —
[Quickstart](https://raffalib-python.readthedocs.io/en/latest/quickstart.html) ·
[Examples](https://raffalib-python.readthedocs.io/en/latest/examples.html) ·
API Reference

> ⚠️ This project is under active development.

## Highlights

- **STATA-like logging** — wrap a pandas/polars pipeline in `startlog()` / `endlog()`
  and get a log line describing how many rows, columns, or cell values changed (plus
  the new shape when rows or columns are added/removed, and optionally how long it took).
- **`.docx` export** — write any DataFrame straight to a Word table with `to_docx()`.
- **Frequency & cross tables** — `freq()` and `crosstab()` accessors for quick
  tabulations.
- **Smarter joins** — a `join()` wrapper (pandas *and* polars) that logs where the
  output rows came from (left only / right only / both, dropped rows, duplicate keys),
  and auto-detects filtering (`semi`/`anti`) joins.

## Installation

Requires **Python ≥ 3.13**. The package is distributed as a local/editable install.

```console
# with uv
uv add --editable /path/to/rkitpy

# or with pip
python3 -m pip install --editable /path/to/rkitpy
```

### Optional dependencies

Core install is intentionally light. Heavier integrations live behind extras, so you
only pull in what you use:

| Extra            | Enables                                              |
| ---------------- | ---------------------------------------------------- |
| `pandas`         | `rkitpy.pandas` accessors                          |
| `polars`         | `rkitpy.polars` accessors and join logging         |
| `bibliometrics`  | Scopus helpers                                       |
| `db`             | SQLAlchemy view helpers                              |
| `rnote`          | Write Rnote (`.rnote`) notebooks from images and text|
| `web`            | Selenium helpers                                     |
| `docs`           | Build the Sphinx documentation                       |
| `dev`            | Ruff + pytest for development                        |

```console
# example: install with the pandas and polars extras
uv add --editable "/path/to/rkitpy[pandas,polars]"
```

## Quick start

### Logging changes in a pandas pipeline

```python
import numpy as np
import pandas as pd
import rkitpy
import rkitpy.pandas  # registers the `.raffa` accessor

logger = rkitpy.create_logger(rich=False, fmt="{message}")

df = pd.DataFrame(
    {
        "species": ["Adelie", "Adelie", "Adelie", "Gentoo", "Gentoo", "Chinstrap"],
        "bill_depth_mm": [18.7, np.nan, 18.0, np.nan, 16.3, 17.9],
        "body_mass_g": [3750.0, 3800.0, np.nan, 4500.0, 5700.0, 3500.0],
    }
)

# Shape changes are logged automatically
_ = df.raffa.startlog().dropna(subset=["bill_depth_mm"]).raffa.endlog(timeit=False)
# -> Removed 2/6 (33.33%) rows. New shape: (4; 3).

# Pass clone=True to also detect value-level changes when the shape is unchanged
_ = df.raffa.startlog(clone=True).fillna(0).raffa.endlog(timeit=False)
# -> Changed 3/18 (16.67%) values.
```

### The same with polars

```python
import polars as pl
import rkitpy
import rkitpy.polars  # registers the `.raffa` namespace

logger = rkitpy.create_logger(rich=False, fmt="{message}")

df = pl.DataFrame(
    {
        "species": ["Adelie", "Adelie", "Adelie", "Gentoo", "Gentoo", "Chinstrap"],
        "bill_depth_mm": [18.7, None, 18.0, None, 16.3, 17.9],
        "body_mass_g": [3750.0, 3800.0, None, 4500.0, 5700.0, 3500.0],
    }
)

_ = df.raffa.startlog().filter(pl.col("species") == "Adelie").raffa.endlog(timeit=False)
# -> Removed 3/6 (50.00%) rows. New shape: (3; 3).
```

Both backends share the same `startlog(clone=False)` / `endlog(custom_msg=None, timeit=True)`
signature. Set `timeit=True` (the default) to append an elapsed-time line.

### Logging joins (pandas & polars)

Both accessors expose the same `join()` wrapper — over `pd.DataFrame.merge` for
pandas and `pl.DataFrame.join` for polars — with identical logging output:

```python
df1 = pd.DataFrame({"A": ["a1", "a2", "a3", "a4"], "B": ["b1", "b2", "b3", "b4"]})
df2 = pd.DataFrame({"A": ["a1", "a2", "a3", "a5", "a6"], "C": ["c1", "c2", "c3", "c5", "c6"]})

out = df1.raffa.join(df2, on="A", how="left")
# Total rows in output table: 4
#     From left only: 1/4 (25.00%)
#     From right only: 0/4 (0.00%)
#     From both: 3/4 (75.00%)
#         Duplicate left keys among the matched rows: 0
#         Duplicate right keys among the matched rows: 0
#         Join cardinality: one-to-one
# Left input rows absent from the output: 0/4 (0.00%)
# Right input rows absent from the output: 2/5 (40.00%)
```

Filtering joins (`how="semi"` / `how="anti"`) are detected automatically, and
`keep_row_index=True` keeps the source row-index columns in the output.

### Exporting to Word

```python
df.raffa.to_docx("table.docx")

# Heading and table options are routed to the right place automatically
df.raffa.to_docx("table.docx", heading_text="Table 1", table_style="Light Grid")
```

See the [Examples](https://raffalib-python.readthedocs.io) page for the full walkthrough.

## Modules

| Module                  | What it provides                                                        |
| ----------------------- | ---------------------------------------------------------------------- |
| `rkitpy.pandas`       | `.raffa` accessor: `startlog`/`endlog`/`midlog`, `join`, `freq`, `to_docx`, `add_prefix_if_not_exists`, `get_duplicates`, `sort_columns` |
| `rkitpy.polars`       | `.raffa` namespace: `startlog`/`endlog`/`midlog`, `freq`, `crosstab`, `join`, `replace_string_with_null`, `to_docx` |
| `rkitpy.logging`      | `create_logger` — opinionated logging setup (plain or `rich`)          |
| `rkitpy.export_docx`  | `DocxFile` — low-level Word document/table builder                     |
| `rkitpy.tqdm`         | `tqdm_batch` — batched progress bars                                    |
| `rkitpy.itertools`    | `batch_boundaries` — compute batch start/end indices                   |
| `rkitpy.list_replace` | `list_replace` — replace occurrences in a list                         |
| `rkitpy.mypickle`     | `read_pickle` / `write_pickle` helpers                                  |
| `rkitpy.selenium`     | Scrolling and explicit-wait helpers for Selenium WebDriver             |
| `rkitpy.sqlalchemy`   | SQLAlchemy `CREATE VIEW` / `DROP VIEW` constructs and a `view()` helper |
| `rkitpy.ScopusUtils`  | Scopus API helpers                                                      |

## Development

```console
uv sync --extra dev
uv run pytest        # run the test suite
uv run ruff check    # lint
uv run ruff format   # format
```

The examples in the documentation (`docs/source/quickstart.rst` and
`examples.rst`) are executable doctests. They run in CI and can be checked
locally with:

```console
uv run --extra docs --extra pandas --extra polars \
  sphinx-build -b doctest docs/source docs/_build/doctest
```

## License

Released under the [GNU General Public License v3.0 or later](LICENSE.txt).

Copyright © 2026 Raffaele Mancuso.

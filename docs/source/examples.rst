########
Examples
########

This guide walks through the main features of **rkitpy**. For a faster
introduction see :doc:`quickstart`.

The code snippets on this page are executable :mod:`doctest` examples, verified
with ``sphinx-build -b doctest`` (see :ref:`running-the-doctests`). They build
small inline DataFrames, so they run without any network access or data files.

****************
Logging concepts
****************

Importing :mod:`rkitpy.pandas` or :mod:`rkitpy.polars` registers a ``.raffa``
accessor (a namespace on polars, an accessor on pandas) that adds STATA-like
change logging to a Series or DataFrame.

The pattern is always the same: call ``startlog()`` before an operation and
``endlog()`` after it. ``endlog`` logs how the data changed — rows or columns
added/removed (followed by the resulting shape) or, when the shape is unchanged,
how many cell values changed.

``startlog(clone=False)``
   Snapshots the current shape (and a timestamp). Pass ``clone=True`` to also
   keep a copy of the data, so that **value-level** changes can be detected when
   the shape does not change. This costs extra memory.

``endlog(custom_msg=None, timeit=True)``
   Logs the change. ``custom_msg`` is prepended to the message; ``timeit=True``
   appends the elapsed time since ``startlog``. The signature is identical for
   pandas and polars.

``midlog(custom_msg=None, timeit=True, clone=False)``
   A convenience alias for ``endlog().startlog()`` — log the current step and
   immediately start the next one. Available on both pandas and polars. ``clone``
   is forwarded to the restarted ``startlog``, so pass ``clone=True`` when the
   next segment should detect value-level changes.

Messages are emitted through the standard :mod:`logging` module. Configure it
once with :func:`rkitpy.create_logger` so the messages reach your console:

.. code-block:: python

   import rkitpy

   rkitpy.create_logger(rich=False, fmt="{message}")

The doctests below assume such a message-only logger. Most of them pass
``timeit=False`` so the output is deterministic; in real use you will usually
keep the default ``timeit=True``, which appends a ``Took: …`` line.

******
pandas
******

Logging
=======

Build a small DataFrame to work with:

>>> import pandas as pd
>>> import numpy as np
>>> import rkitpy.pandas  # registers the `.raffa` accessor
>>> df = pd.DataFrame(
...     {
...         "species": ["Adelie", "Adelie", "Adelie", "Adelie", "Adelie",
...                     "Gentoo", "Gentoo", "Gentoo", "Chinstrap", "Chinstrap"],
...         "island": ["Torgersen"] * 5 + ["Biscoe"] * 3 + ["Dream"] * 2,
...         "bill_length_mm": [39.1, 39.5, 40.3, np.nan, 36.7, 46.1, 50.0, np.nan, 46.5, 50.0],
...         "bill_depth_mm": [18.7, 17.4, 18.0, np.nan, 19.3, 13.2, 16.3, np.nan, 17.9, 19.5],
...         "flipper_length_mm": [181.0, 186.0, 195.0, np.nan, 193.0, 211.0, 230.0, 210.0, 192.0, 196.0],
...         "body_mass_g": [3750.0, 3800.0, 3250.0, np.nan, 3450.0, 4500.0, 5700.0, 4800.0, 3500.0, 3900.0],
...         "sex": ["male", "female", "female", None, "female", "female", "male", None, "female", "male"],
...         "year": [2007, 2007, 2007, 2007, 2007, 2007, 2007, 2008, 2007, 2008],
...     }
... )
>>> df.head()
  species     island  bill_length_mm  bill_depth_mm  flipper_length_mm  body_mass_g     sex  year
0  Adelie  Torgersen            39.1           18.7              181.0       3750.0    male  2007
1  Adelie  Torgersen            39.5           17.4              186.0       3800.0  female  2007
2  Adelie  Torgersen            40.3           18.0              195.0       3250.0  female  2007
3  Adelie  Torgersen             NaN            NaN                NaN          NaN     NaN  2007
4  Adelie  Torgersen            36.7           19.3              193.0       3450.0  female  2007

Removing rows, filtering, or dropping columns changes the shape, which is
logged automatically:

>>> _ = df.raffa.startlog().dropna(subset=["bill_depth_mm"]).raffa.endlog(timeit=False)
Removed 2/10 (20.00%) rows. New shape: (8; 8).
>>> _ = df.raffa.startlog().query("species=='Adelie'").raffa.endlog(timeit=False)
Removed 5/10 (50.00%) rows. New shape: (5; 8).
>>> _ = df.raffa.startlog().drop(["bill_length_mm", "bill_depth_mm"], axis=1).raffa.endlog(timeit=False)
Removed 2/8 (25.00%) columns. New shape: (10; 6).

With the default ``timeit=True``, ``endlog`` appends the elapsed time on a
second line (the duration varies from run to run):

>>> _ = df.raffa.startlog().dropna(subset=["bill_depth_mm"]).raffa.endlog()
Removed 2/10 (20.00%) rows. New shape: (8; 8).
Took: ...

Operations that change values but not the shape need ``clone=True`` so the
initial data can be compared against:

>>> _ = df.raffa.startlog().fillna(0).raffa.endlog(timeit=False)
Shape is the same. No value-level comparison done because clone=False was used in startlog().
>>> _ = df.raffa.startlog(clone=True).fillna(0).raffa.endlog(timeit=False)
Changed 8/80 (10.00%) values.

The same accessor is available on a Series:

>>> s = df["bill_length_mm"]
>>> _ = s.raffa.startlog().dropna().raffa.endlog(timeit=False)
Removed 2/10 (20.00%) values. New shape: (8).
>>> _ = s.raffa.startlog(clone=True).fillna(0).raffa.endlog(timeit=False)
Changed 2/10 (20.00%) values.

Frequency tables
================

``freq`` builds a frequency table with counts, proportions, and a ``Total`` row:

>>> s = pd.Series(["a", "a", "a", "b", "b", "c"], name="letter")
>>> s.raffa.freq()
        count  proportion
letter
a           3    0.500000
b           2    0.333333
c           1    0.166667
Total       6    1.000000

On a DataFrame, pass the column name (it delegates to the Series accessor):

>>> df.raffa.freq("species")
           count  proportion
species
Adelie         5         0.5
Gentoo         3         0.3
Chinstrap      2         0.2
Total         10         1.0

Joins
=====

The ``join`` accessor wraps :meth:`pandas.DataFrame.merge` and logs where the
output rows come from. It mirrors the polars ``join`` accessor described below.

>>> df1 = pd.DataFrame({"A": ["a1", "a2", "a3", "a4"], "B": ["b1", "b2", "b3", "b4"]})
>>> df2 = pd.DataFrame({"A": ["a1", "a2", "a3", "a5", "a6"], "C": ["c1", "c2", "c3", "c5", "c6"]})

Mutating joins
--------------

Outer join:

>>> _ = df1.raffa.join(df2, on="A", how="outer")
Total rows in output table: 6
    From left only: 1/6 (16.67%)
    From right only: 2/6 (33.33%)
    From both: 3/6 (50.00%)
        Duplicate left keys among the matched rows: 0
        Duplicate right keys among the matched rows: 0
        Join cardinality: one-to-one
Left input rows absent from the output: 0/4 (0.00%)
Right input rows absent from the output: 0/5 (0.00%)

Inner join:

>>> _ = df1.raffa.join(df2, on="A", how="inner")
Total rows in output table: 3
    From left only: 0/3 (0.00%)
    From right only: 0/3 (0.00%)
    From both: 3/3 (100.00%)
        Duplicate left keys among the matched rows: 0
        Duplicate right keys among the matched rows: 0
        Join cardinality: one-to-one
Left input rows absent from the output: 1/4 (25.00%)
Right input rows absent from the output: 2/5 (40.00%)

Left join:

>>> _ = df1.raffa.join(df2, on="A", how="left")
Total rows in output table: 4
    From left only: 1/4 (25.00%)
    From right only: 0/4 (0.00%)
    From both: 3/4 (75.00%)
        Duplicate left keys among the matched rows: 0
        Duplicate right keys among the matched rows: 0
        Join cardinality: one-to-one
Left input rows absent from the output: 0/4 (0.00%)
Right input rows absent from the output: 2/5 (40.00%)

Right join:

>>> _ = df1.raffa.join(df2, on="A", how="right")
Total rows in output table: 5
    From left only: 0/5 (0.00%)
    From right only: 2/5 (40.00%)
    From both: 3/5 (60.00%)
        Duplicate left keys among the matched rows: 0
        Duplicate right keys among the matched rows: 0
        Join cardinality: one-to-one
Left input rows absent from the output: 1/4 (25.00%)
Right input rows absent from the output: 0/5 (0.00%)

Filtering joins
---------------

``how="semi"`` and ``how="anti"`` are not native to pandas; the accessor
emulates them and detects them as filtering joins:

>>> _ = df1.raffa.join(df2, on="A", how="semi", keep_row_index=False)
Detected filtering join. Rows variation -1/4 (-25.00%), total rows after join: 3/4 (75.00%)
>>> _ = df1.raffa.join(df2, on="A", how="anti", keep_row_index=False)
Detected filtering join. Rows variation -3/4 (-75.00%), total rows after join: 1/4 (25.00%)

Pass ``keep_row_index=True`` on a mutating join to keep the ``source_left`` /
``source_right`` row-index columns in the output.

Word export
===========

Export a DataFrame to a Word ``.docx`` table:

.. code-block:: python

   df.head(5).raffa.to_docx("table.docx")

Document and heading options (e.g. ``heading_text``, ``landscape``) are passed
in ``doc_options`` and forwarded to :class:`~rkitpy.export_docx.DocxFile`;
table options (e.g. ``table_style``, ``table_font_size``) are passed in
``table_options`` and forwarded to its ``add_table`` method:

.. code-block:: python

   df.head(5).raffa.to_docx(
       "table.docx",
       doc_options={"heading_text": "Table 1"},
       table_options={"table_style": "Light Grid"},
   )

******
polars
******

Logging
=======

Import the libraries and build a DataFrame with a few missing values:

>>> import polars as pl
>>> import polars.selectors as cs
>>> import rkitpy.polars  # registers the `.raffa` namespace
>>> df = pl.DataFrame(
...     {
...         "species": ["Adelie", "Adelie", "Adelie", "Adelie", "Adelie",
...                     "Gentoo", "Gentoo", "Gentoo", "Chinstrap", "Chinstrap"],
...         "island": ["Torgersen"] * 5 + ["Biscoe"] * 3 + ["Dream"] * 2,
...         "bill_length_mm": [39.1, 39.5, 40.3, None, 36.7, 46.1, 50.0, None, 46.5, 50.0],
...         "bill_depth_mm": [18.7, 17.4, 18.0, None, 19.3, 13.2, 16.3, None, 17.9, 19.5],
...         "flipper_length_mm": [181.0, 186.0, 195.0, None, 193.0, 211.0, 230.0, 210.0, 192.0, 196.0],
...         "body_mass_g": [3750.0, 3800.0, 3250.0, None, 3450.0, 4500.0, 5700.0, 4800.0, 3500.0, 3900.0],
...         "sex": ["male", "female", "female", None, "female", "female", "male", None, "female", "male"],
...         "year": [2007, 2007, 2007, 2007, 2007, 2007, 2007, 2008, 2007, 2008],
...     }
... )
>>> df.head()
shape: (5, 8)
┌─────────┬───────────┬────────────────┬───────────────┬───────────────────┬─────────────┬────────┬───────┐
│ species ┆ island    ┆ bill_length_mm ┆ bill_depth_mm ┆ flipper_length_mm ┆ body_mass_g ┆ sex    ┆ year  │
│ ---     ┆ ---       ┆ ---            ┆ ---           ┆ ---               ┆ ---         ┆ ---    ┆ ---   │
│ str     ┆ str       ┆ f64            ┆ f64           ┆ f64               ┆ f64         ┆ str    ┆ i64   │
╞═════════╪═══════════╪════════════════╪═══════════════╪═══════════════════╪═════════════╪════════╪═══════╡
│ Adelie  ┆ Torgersen ┆ 39.1           ┆ 18.7          ┆ 181.0             ┆ 3,750.0     ┆ male   ┆ 2,007 │
│ Adelie  ┆ Torgersen ┆ 39.5           ┆ 17.4          ┆ 186.0             ┆ 3,800.0     ┆ female ┆ 2,007 │
│ Adelie  ┆ Torgersen ┆ 40.3           ┆ 18.0          ┆ 195.0             ┆ 3,250.0     ┆ female ┆ 2,007 │
│ Adelie  ┆ Torgersen ┆ null           ┆ null          ┆ null              ┆ null        ┆ null   ┆ 2,007 │
│ Adelie  ┆ Torgersen ┆ 36.7           ┆ 19.3          ┆ 193.0             ┆ 3,450.0     ┆ female ┆ 2,007 │
└─────────┴───────────┴────────────────┴───────────────┴───────────────────┴─────────────┴────────┴───────┘

Removing rows with nulls, filtering values, or selecting columns changes the
shape, which is logged:

>>> _ = df.raffa.startlog().drop_nulls(subset=["bill_depth_mm"]).raffa.endlog(timeit=False)
Removed 2/10 (20.00%) rows. New shape: (8; 8).
>>> _ = df.raffa.startlog().filter(pl.col("species")=="Adelie").raffa.endlog(timeit=False)
Removed 5/10 (50.00%) rows. New shape: (5; 8).
>>> _ = df.raffa.startlog().select(pl.exclude(["bill_length_mm", "bill_depth_mm"])).raffa.endlog(timeit=False)
Removed 2/8 (25.00%) columns. New shape: (10; 6).

As with pandas, the default ``timeit=True`` appends the elapsed time on a second
line (the duration varies from run to run):

>>> _ = df.raffa.startlog().filter(pl.col("species")=="Adelie").raffa.endlog()
Removed 5/10 (50.00%) rows. New shape: (5; 8).
Took: ...

Operations that change values but not the shape need ``clone=True``:

>>> _ = df.raffa.startlog().fill_null(0).raffa.endlog(timeit=False)
Shape is the same. No value-level comparison done because clone=False was used in startlog().
>>> _ = df.raffa.startlog(clone=True).fill_null("0").raffa.endlog(timeit=False)
Changed 2/80 (2.50%) values.

``replace_string_with_null`` turns a sentinel string (such as the literal
``"NA"`` used by some CSV files) into proper nulls across all string columns:

>>> raw = pl.DataFrame({"species": ["Adelie", "NA", "Gentoo"], "sex": ["male", "female", "NA"]})
>>> raw.raffa.replace_string_with_null("NA")
shape: (3, 2)
┌─────────┬────────┐
│ species ┆ sex    │
│ ---     ┆ ---    │
│ str     ┆ str    │
╞═════════╪════════╡
│ Adelie  ┆ male   │
│ null    ┆ female │
│ Gentoo  ┆ null   │
└─────────┴────────┘

Frequency and cross tables
==========================

``freq`` builds a frequency table for a column, with counts, percentages, and a
``Total`` row:

>>> sp = pl.Series("letter", ["a", "a", "a", "b", "b", "c"])
>>> sp.raffa.freq()
shape: (4, 3)
┌───────┬───────┬───────────┐
│ value ┆ count ┆ perc      │
│ ---   ┆ ---   ┆ ---       │
│ str   ┆ u32   ┆ f64       │
╞═══════╪═══════╪═══════════╡
│ a     ┆ 3     ┆ 50.0      │
│ b     ┆ 2     ┆ 33.333333 │
│ c     ┆ 1     ┆ 16.666667 │
│ Total ┆ 6     ┆ 100.0     │
└───────┴───────┴───────────┘

On a DataFrame, pass the column name (equivalent to
``df.get_column("species").raffa.freq()``):

>>> df.raffa.freq("species")
shape: (4, 3)
┌───────────┬───────┬───────┐
│ value     ┆ count ┆ perc  │
│ ---       ┆ ---   ┆ ---   │
│ str       ┆ u32   ┆ f64   │
╞═══════════╪═══════╪═══════╡
│ Adelie    ┆ 5     ┆ 50.0  │
│ Gentoo    ┆ 3     ┆ 30.0  │
│ Chinstrap ┆ 2     ┆ 20.0  │
│ Total     ┆ 10    ┆ 100.0 │
└───────────┴───────┴───────┘

``crosstab`` builds a contingency table of two columns:

>>> ct = pl.DataFrame({"grp": ["x", "x", "y", "y", "y"], "cls": ["m", "n", "m", "m", "n"]})
>>> ct.raffa.crosstab("grp", "cls")
shape: (2, 3)
┌─────┬─────┬─────┐
│ grp ┆ m   ┆ n   │
│ --- ┆ --- ┆ --- │
│ str ┆ u32 ┆ u32 │
╞═════╪═════╪═════╡
│ x   ┆ 1   ┆ 1   │
│ y   ┆ 2   ┆ 1   │
└─────┴─────┴─────┘

Use ``perc`` to express each cell as a percentage along an axis (see
:class:`~rkitpy.polars.PercOptions`):

>>> from rkitpy.polars import PercOptions
>>> ct.raffa.crosstab("grp", "cls", perc=PercOptions.ROWS)
shape: (2, 3)
┌─────┬───────────┬───────────┐
│ grp ┆ m         ┆ n         │
│ --- ┆ ---       ┆ ---       │
│ str ┆ f64       ┆ f64       │
╞═════╪═══════════╪═══════════╡
│ x   ┆ 50.0      ┆ 50.0      │
│ y   ┆ 66.666667 ┆ 33.333333 │
└─────┴───────────┴───────────┘

Joins
=====

The ``join`` accessor wraps :meth:`polars.DataFrame.join` and logs the row
provenance of the result.

>>> df1 = pl.DataFrame({"A": ["a1", "a2", "a3", "a4"], "B": ["b1", "b2", "b3", "b4"]})
>>> df2 = pl.DataFrame({"A": ["a1", "a2", "a3", "a5", "a6"], "C": ["c1", "c2", "c3", "c5", "c6"]})

Mutating joins
--------------

Outer join:

>>> _ = df1.raffa.join(df2, on="A", how="outer")
Total rows in output table: 6
    From left only: 1/6 (16.67%)
    From right only: 2/6 (33.33%)
    From both: 3/6 (50.00%)
        Duplicate left keys among the matched rows: 0
        Duplicate right keys among the matched rows: 0
        Join cardinality: one-to-one
Left input rows absent from the output: 0/4 (0.00%)
Right input rows absent from the output: 0/5 (0.00%)

Inner join:

>>> _ = df1.raffa.join(df2, on="A", how="inner")
Total rows in output table: 3
    From left only: 0/3 (0.00%)
    From right only: 0/3 (0.00%)
    From both: 3/3 (100.00%)
        Duplicate left keys among the matched rows: 0
        Duplicate right keys among the matched rows: 0
        Join cardinality: one-to-one
Left input rows absent from the output: 1/4 (25.00%)
Right input rows absent from the output: 2/5 (40.00%)

Left join:

>>> _ = df1.raffa.join(df2, on="A", how="left")
Total rows in output table: 4
    From left only: 1/4 (25.00%)
    From right only: 0/4 (0.00%)
    From both: 3/4 (75.00%)
        Duplicate left keys among the matched rows: 0
        Duplicate right keys among the matched rows: 0
        Join cardinality: one-to-one
Left input rows absent from the output: 0/4 (0.00%)
Right input rows absent from the output: 2/5 (40.00%)

Right join:

>>> _ = df1.raffa.join(df2, on="A", how="right")
Total rows in output table: 5
    From left only: 0/5 (0.00%)
    From right only: 2/5 (40.00%)
    From both: 3/5 (60.00%)
        Duplicate left keys among the matched rows: 0
        Duplicate right keys among the matched rows: 0
        Join cardinality: one-to-one
Left input rows absent from the output: 1/4 (25.00%)
Right input rows absent from the output: 0/5 (0.00%)

Filtering joins
---------------

Filtering joins (``how="semi"`` / ``how="anti"``) are automatically detected:

>>> _ = df1.raffa.join(df2, on="A", how="semi", keep_row_index=False)
Detected filtering join. Rows variation -1/4 (-25.00%), total rows after join: 3/4 (75.00%)
>>> _ = df1.raffa.join(df2, on="A", how="anti", keep_row_index=False)
Detected filtering join. Rows variation -3/4 (-75.00%), total rows after join: 1/4 (25.00%)

Word export
===========

Export a DataFrame to a Word ``.docx`` file:

.. code-block:: python

   out = pl.DataFrame({"a": [1, 2, 3], "b": ["AAA", "BBB", "CCC"]})
   out.raffa.to_docx("main.docx")

As with pandas, document/heading options are passed in ``doc_options`` and
table options in ``table_options``:

.. code-block:: python

   out.raffa.to_docx(
       "main.docx", doc_options={"heading_text": "Table 1", "landscape": True}
   )

.. _utilities:

*********
Utilities
*********

Beyond the DataFrame accessors, ``rkitpy`` ships a handful of standalone
helpers.

Logger setup
============

:func:`rkitpy.create_logger` configures the standard-library logger used by
the change-logging accessors:

.. code-block:: python

   import rkitpy

   logger = rkitpy.create_logger(rich=False, fmt="{message}")

Pass ``rich=True`` for colourised console output via
`rich <https://rich.readthedocs.io/>`_, or omit ``fmt`` for the default
``timestamp - level - name - message`` layout.

Batched iteration
=================

:func:`rkitpy.tqdm_batch` wraps a sized iterable in a
`tqdm <https://tqdm.github.io/>`_ progress bar that advances once per batch:

.. code-block:: python

   from rkitpy import tqdm_batch

   for batch in tqdm_batch(items, batch_size=100)():
       process(batch)

:func:`rkitpy.itertools.batch_boundaries` is the index-only equivalent,
yielding ``(batch_index, start, end)`` tuples (1-based, inclusive):

>>> from rkitpy.itertools import batch_boundaries
>>> list(batch_boundaries(20, 3))
[(0, 1, 3), (1, 4, 6), (2, 7, 9), (3, 10, 12), (4, 13, 15), (5, 16, 18), (6, 19, 20)]

List editing
============

:func:`rkitpy.list_replace` replaces every occurrence of a value in a list,
in place:

>>> from rkitpy import list_replace
>>> lst = [1, 2, 3, 2, 4]
>>> list_replace(lst, 2, 5)
>>> lst
[1, 5, 3, 5, 4]

Pickling
========

:func:`rkitpy.mypickle.write_pickle` and :func:`rkitpy.mypickle.read_pickle`
serialise arbitrary Python objects with
`jsonpickle <https://jsonpickle.github.io/>`_, writing to a timestamped file
named ``{stem}_{YYYY-MM-DD-HH-MM-SS}``:

.. code-block:: python

   from pathlib import Path
   from rkitpy.mypickle import write_pickle, read_pickle

   write_pickle({"a": 1}, Path("."), "mydata")
   obj = read_pickle(Path("mydata_2026-06-20-09-30-00"))

.. _running-the-doctests:

Running the doctests
====================

Every ``>>>`` example on this page is executed by Sphinx's doctest builder. From
the ``docs`` directory:

.. code-block:: console

   uv run sphinx-build -b doctest source _build/doctest

or, equivalently, ``make doctest`` (``.\make.bat doctest`` on Windows).

Quickstart
==========

This page gets you from zero to a logged data-wrangling pipeline in a couple of
minutes. For the full tour see :doc:`examples`.

Install
-------

Install the package together with the extras you need (see :doc:`installation`
for details):

.. code-block:: console

   uv add --editable "/path/to/rkitpy[pandas,polars]"

Set up a logger
---------------

The change-logging accessors emit their messages through the standard
:mod:`logging` module. Call :func:`rkitpy.create_logger` once to configure it:

.. code-block:: python

   import rkitpy

   rkitpy.create_logger(rich=False, fmt="{message}")

Use ``rich=True`` for colourised console output, or drop ``fmt`` to keep the
default ``timestamp - level - name - message`` format.

Log changes in a pipeline
-------------------------

Importing :mod:`rkitpy.pandas` (or :mod:`rkitpy.polars`) registers a
``.raffa`` accessor. Wrap any pipeline between ``startlog()`` and ``endlog()``
to log how the data changed:

>>> import pandas as pd
>>> import numpy as np
>>> import rkitpy.pandas  # registers the `.raffa` accessor
>>> df = pd.DataFrame(
...     {
...         "species": ["Adelie", "Adelie", "Adelie", "Gentoo", "Gentoo", "Chinstrap"],
...         "bill_depth_mm": [18.7, np.nan, 18.0, np.nan, 16.3, 17.9],
...         "body_mass_g": [3750.0, 3800.0, np.nan, 4500.0, 5700.0, 3500.0],
...     }
... )
>>> # Row/column count changes are logged automatically, with the resulting shape
>>> _ = df.raffa.startlog().dropna(subset=["bill_depth_mm"]).raffa.endlog(timeit=False)
Removed 2/6 (33.33%) rows. New shape: (4; 3).
>>> # Pass clone=True to also detect value-level changes when the shape is unchanged
>>> _ = df.raffa.startlog(clone=True).fillna(0).raffa.endlog(timeit=False)
Changed 3/18 (16.67%) values.

The polars accessor works identically:

>>> import polars as pl
>>> import rkitpy.polars  # registers the `.raffa` namespace
>>> df = pl.DataFrame(
...     {
...         "species": ["Adelie", "Adelie", "Adelie", "Gentoo", "Gentoo", "Chinstrap"],
...         "bill_depth_mm": [18.7, None, 18.0, None, 16.3, 17.9],
...         "body_mass_g": [3750.0, 3800.0, None, 4500.0, 5700.0, 3500.0],
...     }
... )
>>> _ = df.raffa.startlog().filter(pl.col("species") == "Adelie").raffa.endlog(timeit=False)
Removed 3/6 (50.00%) rows. New shape: (3; 3).

Timing each step
----------------

The examples above pass ``timeit=False`` so their output is reproducible. With
the default ``timeit=True``, ``endlog`` appends the wall-clock time the step took
on a second line (the duration varies from run to run):

>>> _ = df.raffa.startlog().filter(pl.col("species") == "Adelie").raffa.endlog()
Removed 3/6 (50.00%) rows. New shape: (3; 3).
Took: ...

Next steps
----------

- :doc:`examples` — logging concepts, ``freq`` / ``crosstab``, logging joins,
  and Word export for both backends.
- **API Reference** (sidebar) — the full, docstring-generated reference.

.. note::

   Every ``>>>`` snippet on this page and in :doc:`examples` is an executable
   doctest, run with ``uv run sphinx-build -b doctest source _build/doctest``
   (or ``make doctest``).

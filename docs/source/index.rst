.. rkitpy documentation master file, created by
   sphinx-quickstart on Mon Feb 16 10:41:01 2026.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

rkitpy documentation
=============================

**rkitpy** is a small library of helper functions for data wrangling.

Its main purpose is to enrich `pandas <https://pandas.pydata.org/>`_ and
`polars <https://pola.rs/>`_ with `STATA <https://www.stata.com/>`_-like logging
and ``.docx`` export capabilities, but it also bundles assorted utilities for
logging, pickling, progress bars, Selenium, SQLAlchemy, and bibliometrics.

Highlights
----------

- **STATA-like logging** — wrap a pandas/polars pipeline in ``startlog()`` /
  ``endlog()`` and get a log line describing how many rows, columns, or cell
  values changed (and optionally how long it took).
- **Logging joins** — a ``join()`` wrapper (for both backends) that logs where
  the output rows came from: left only, right only, both, dropped rows, and
  duplicate keys.
- **Frequency & cross tables** — ``freq()`` and ``crosstab()`` accessors for
  quick tabulations.
- **Word export** — write any DataFrame straight to a ``.docx`` table with
  ``to_docx()``.

A taste
-------

.. code-block:: python

   import pandas as pd
   import numpy as np
   import rkitpy
   import rkitpy.pandas  # registers the `.raffa` accessor

   rkitpy.create_logger(rich=False, fmt="{message}")

   df = pd.DataFrame(
       {
           "species": ["Adelie", "Adelie", "Adelie", "Gentoo", "Gentoo", "Chinstrap"],
           "bill_depth_mm": [18.7, np.nan, 18.0, np.nan, 16.3, 17.9],
           "body_mass_g": [3750.0, 3800.0, np.nan, 4500.0, 5700.0, 3500.0],
       }
   )
   df = df.raffa.startlog().dropna(subset=["bill_depth_mm"]).raffa.endlog()
   # -> Removed 2/6 (33.33%) rows. New shape: (4; 3).
   # -> Took: 0.01 seconds

New here? Start with :doc:`quickstart`, then browse the :doc:`examples` for the
full tour. The complete API reference is generated from the source docstrings
under **API Reference** in the sidebar.

.. note::

   This project is under active development.

.. toctree::
   :hidden:

   Home page <self>
   Install <installation>
   Quickstart <quickstart>
   Examples <examples>

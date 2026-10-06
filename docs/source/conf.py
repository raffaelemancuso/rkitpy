# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
# Problems with imports? Could try `export PYTHONPATH=$PYTHONPATH:`pwd`` from root project dir...
import sys
from pathlib import Path

src_path = Path("../../src")
assert src_path.is_dir()
assert (src_path / "rkitpy").is_dir()
sys.path.insert(0, src_path.resolve())  # Source code dir relative to this file

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "rkitpy"
copyright = "2026, Raffaele Mancuso"
author = "Raffaele Mancuso"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "autoapi.extension",
    "sphinx.ext.doctest",
]

autoapi_dirs = ["../../src"]

# -- doctest configuration ---------------------------------------------------
# The examples in the narrative docs are executable doctests, run with
# ``sphinx-build -b doctest`` (``make doctest``). ELLIPSIS lets the
# non-deterministic ``Took: ...`` timing lines match; NORMALIZE_WHITESPACE makes
# the DataFrame/table reprs robust to incidental spacing differences.
import doctest as _doctest  # noqa: E402

doctest_default_flags = _doctest.ELLIPSIS | _doctest.NORMALIZE_WHITESPACE

# Run once before every doctest group: import the libraries, route rkitpy's
# logging output to stdout so doctest can capture it (mirroring
# ``create_logger(rich=False, fmt="{message}")``), and pin the table-rendering
# width so the captured reprs are deterministic.
doctest_global_setup = """
import logging
import numpy as np
import pandas as pd
import polars as pl
import polars.selectors as cs
import rkitpy
import rkitpy.pandas
import rkitpy.polars


class _DoctestLogHandler(logging.Handler):
    def emit(self, record):
        print(self.format(record))


_handler = _DoctestLogHandler()
_handler.setFormatter(logging.Formatter("%(message)s"))
_raffalogger = logging.getLogger("rkitpy")
_raffalogger.handlers = [_handler]
_raffalogger.setLevel(logging.INFO)
_raffalogger.propagate = False

pd.set_option("display.max_columns", None)
pd.set_option("display.width", 200)
pl.Config(thousands_separator=",", tbl_cols=-1, tbl_width_chars=200)
"""

# Document the class docstring and the __init__ docstring together.
autoapi_python_class_content = "both"

# Keep the default options but drop "imported-members": the package re-exports
# (e.g. ``rkitpy.list_replace``) would otherwise be documented both on the
# package page and on their own module page, producing duplicate-object warnings.
autoapi_options = [
    "members",
    "undoc-members",
    "show-inheritance",
    "show-module-summary",
    "special-members",
]

exclude_patterns = ["_build", "_templates"]

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

html_theme = "sphinx_rtd_theme"

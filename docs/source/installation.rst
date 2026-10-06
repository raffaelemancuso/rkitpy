Installation
============

**rkitpy** requires **Python ≥ 3.13** and is distributed as a
local / editable install.

1. Clone the repository.
2. In the folder of your project, add the requirement:

.. code-block:: console

   uv add --editable [PATH_TO_LOCAL_REPO]

or, if you are not using ``uv``:

.. code-block:: console

   python3 -m pip install --editable [PATH_TO_LOCAL_REPO]

Optional dependencies
---------------------

The core install is intentionally light. The heavier integrations live behind
optional-dependency *extras*, so you only pull in what you use:

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Extra
     - Enables
   * - ``pandas``
     - the :mod:`rkitpy.pandas` accessors
   * - ``polars``
     - the :mod:`rkitpy.polars` accessors and join logging
   * - ``bibliometrics``
     - Scopus helpers
   * - ``crypto``
     - KeePassXC / GnuPG helpers
   * - ``db``
     - SQLAlchemy view helpers
   * - ``rnote``
     - :mod:`rkitpy.rnote`, writing Rnote (``.rnote``) notebooks from images and text
   * - ``web``
     - Selenium helpers
   * - ``docs``
     - build this documentation
   * - ``dev``
     - Ruff + pytest for development

Specify one or more extras in brackets:

.. code-block:: console

   uv add --editable "[PATH_TO_LOCAL_REPO][pandas,polars]"

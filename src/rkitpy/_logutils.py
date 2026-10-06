# rkitpy Miscellaneous functions
# Copyright (C) 2026 Raffaele Mancuso
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
Internal helpers shared by the pandas and polars logging accessors.

These functions only build human-readable log messages; the
library-specific mechanics (metadata storage, cloning, value comparison)
stay in :mod:`rkitpy.pandas` and :mod:`rkitpy.polars`.
"""

import time
import datetime
from dataclasses import dataclass

import humanize

#: Message used when ``startlog(clone=False)`` prevents value-level comparison.
CLONE_FALSE_MSG = (
    "Shape is the same. No value-level comparison done because "
    "clone=False was used in startlog()."
)


def ratio(numerator: int, denominator: int) -> str:
    """
    Format ``numerator/denominator (percentage)``, guarding against a zero
    denominator.

    :param numerator: The count being described.
    :type numerator: int
    :param denominator: The total it is measured against.
    :type denominator: int
    :return: A string like ``"1/4 (25.00%)"``, or ``"0/0 (N/A)"`` when
        ``denominator`` is zero.
    :rtype: str
    """
    if denominator == 0:
        return f"{numerator:,d}/{denominator:,d} (N/A)"
    return f"{numerator:,d}/{denominator:,d} ({numerator / denominator:.2%})"


def count_delta(delta: int, total: int, unit: str) -> str:
    """
    Describe a signed count change along a single dimension.

    :param delta: ``initial - final`` count. Positive means items were removed,
        negative means items were added.
    :type delta: int
    :param total: The initial count, used as the denominator for the percentage.
    :type total: int
    :param unit: Name of the items being counted (e.g. ``"rows"``, ``"values"``).
    :type unit: str
    :return: A message like ``"Removed 5/10 (50.00%) rows."``, or an empty
        string when ``delta`` is zero.
    :rtype: str
    """
    if delta > 0:
        return f"Removed {ratio(delta, total)} {unit}."
    if delta < 0:
        return f"Added {ratio(abs(delta), total)} {unit}."
    return ""


def new_shape(shape: tuple[int, ...]) -> str:
    """
    Report the shape a DataFrame or Series has after rows or columns were
    added or removed.

    :param shape: The shape tuple after the operation (``(n,)`` for a Series,
        ``(n_rows, n_cols)`` for a DataFrame).
    :type shape: tuple[int, ...]
    :return: A message like ``"New shape: (8,000; 6)."``.
    :rtype: str
    """
    return f"New shape: ({'; '.join(f'{n:,d}' for n in shape)})."


def series_shape_delta(initial_shape: tuple[int], final_shape: tuple[int]) -> str:
    """
    Describe how a Series' length changed and report its new shape.

    :param initial_shape: ``(n,)`` before the operation.
    :type initial_shape: tuple[int]
    :param final_shape: ``(n,)`` after the operation.
    :type final_shape: tuple[int]
    :return: The value-count change followed by the new shape, or an empty
        string when the length did not change.
    :rtype: str
    """
    delta = count_delta(initial_shape[0] - final_shape[0], initial_shape[0], "values")
    if not delta:
        return ""
    return f"{delta} {new_shape(final_shape)}"


def dataframe_shape_delta(
    initial_shape: tuple[int, int], final_shape: tuple[int, int]
) -> str:
    """
    Describe how a DataFrame's row and column counts changed and report its
    new shape.

    :param initial_shape: ``(n_rows, n_cols)`` before the operation.
    :type initial_shape: tuple[int, int]
    :param final_shape: ``(n_rows, n_cols)`` after the operation.
    :type final_shape: tuple[int, int]
    :return: The concatenated row and column change messages followed by the
        new shape, or an empty string when neither changed.
    :rtype: str
    """
    nrow0, ncol0 = initial_shape
    nrow1, ncol1 = final_shape
    delta = count_delta(nrow0 - nrow1, nrow0, "rows") + count_delta(
        ncol0 - ncol1, ncol0, "columns"
    )
    if not delta:
        return ""
    return f"{delta} {new_shape(final_shape)}"


def changed_cells(nchanged: int, ntotal: int) -> str:
    """
    Describe how many cells changed when the shape stayed the same.

    :param nchanged: Number of cells whose value changed.
    :type nchanged: int
    :param ntotal: Total number of cells.
    :type ntotal: int
    :return: ``"No changes detected."`` or a message like
        ``"Changed 3/12 (25.00%) values."``.
    :rtype: str
    """
    if nchanged == 0:
        return "No changes detected."
    return f"Changed {ratio(nchanged, ntotal)} values."


def prefix(custom_msg: str | None) -> str:
    """
    Render the optional user message that ``endlog`` prepends to its log line.

    :param custom_msg: The caller-supplied message, or ``None``.
    :type custom_msg: str | None
    :return: ``""`` when ``custom_msg`` is ``None``, otherwise ``"{custom_msg}. "``.
    :rtype: str
    """
    if custom_msg is None:
        return ""
    return f"{custom_msg}. "


@dataclass(frozen=True)
class JoinCounts:
    """
    Row-provenance counts for a mutating join, consumed by :func:`join_log`.

    :ivar n_rows_joined: Number of rows in the joined output.
    :ivar n_left_only: Output rows present only in the left table.
    :ivar n_right_only: Output rows present only in the right table.
    :ivar n_both: Output rows present in both tables.
    :ivar n_left_dups: Matched output rows that share their left source row
        with at least one other output row (left-side fan-out); see
        :func:`join_log` for the exact semantics and examples.
    :ivar n_right_dups: Matched output rows that share their right source row
        with at least one other output row (right-side fan-out); see
        :func:`join_log` for the exact semantics and examples.
    :ivar n_left_dropped: Left input rows absent from the output.
    :ivar n_left_total: Number of rows in the left input table.
    :ivar n_right_dropped: Right input rows absent from the output.
    :ivar n_right_total: Number of rows in the right input table.
    """

    n_rows_joined: int
    n_left_only: int
    n_right_only: int
    n_both: int
    n_left_dups: int
    n_right_dups: int
    n_left_dropped: int
    n_left_total: int
    n_right_dropped: int
    n_right_total: int


def join_cardinality(counts: JoinCounts) -> str:
    """
    Classify the realized cardinality of a mutating join.

    The classification reflects the matches that actually occurred, not the
    uniqueness of the join keys in the inputs: a join between tables with
    duplicated keys is still reported as one-to-one when no duplicated key
    found a match. ``n_left_dups > 0`` means some left row matched several
    right rows (a "many" on the right side), and symmetrically for
    ``n_right_dups``; see :func:`join_log` for how the two counters are
    measured.

    :param counts: The row-provenance counts to classify.
    :type counts: JoinCounts
    :return: ``"one-to-one"``, ``"many-to-one"``, ``"one-to-many"``,
        ``"many-to-many"``, or ``"N/A (no matched rows)"``.
    :rtype: str
    """
    if counts.n_both == 0:
        return "N/A (no matched rows)"
    if counts.n_left_dups == 0 and counts.n_right_dups == 0:
        return "one-to-one"
    if counts.n_left_dups == 0:
        return "many-to-one"
    if counts.n_right_dups == 0:
        return "one-to-many"
    return "many-to-many"


def join_log(counts: JoinCounts) -> str:
    """
    Build the row-provenance log for a mutating join.

    Shared verbatim by the pandas and polars ``join`` accessors so the two
    backends cannot drift apart. Indentation uses spaces, not tabs, because
    the message is reproduced in doctests (``docs/source/examples.rst``) and
    doctest cannot match tab characters in expected output.

    ``n_left_dups`` and ``n_right_dups`` measure key fan-out among the matched
    ("from both") output rows. Each output row remembers which left and right
    input row it came from; ``n_left_dups`` is the number of matched output
    rows whose left source row also produced at least one *other* output row,
    i.e. rows that exist because one left row matched several right rows.
    ``n_right_dups`` is the mirror image. Every member of a duplicated group
    is counted, not only the extra copies (both backends mark duplicates with
    keep-all semantics: pandas ``duplicated(keep=False)``, polars
    ``is_duplicated()``). Both counters are 0 when the join is one-to-one on
    the matched keys. The reported join cardinality follows from the two
    counters via :func:`join_cardinality`.

    Examples, joining on key ``k``:

    - One-to-many: left has one row with ``k=a``, right has three rows with
      ``k=a``. The output has three matched rows, all copies of the same left
      row, each right row used once: ``n_left_dups == 3``,
      ``n_right_dups == 0``, cardinality ``one-to-many``.
    - Many-to-many: left has two rows with ``k=a``, right has two rows with
      ``k=a``. The output has the four cross-product rows; every left and
      every right row is used twice: ``n_left_dups == 4``,
      ``n_right_dups == 4``, cardinality ``many-to-many``.

    :param counts: The row-provenance counts to report.
    :type counts: JoinCounts
    :return: The multi-line, newline-terminated log message.
    :rtype: str
    """
    return (
        f"Total rows in output table: {counts.n_rows_joined:,d}\n"
        f"    From left only: {ratio(counts.n_left_only, counts.n_rows_joined)}\n"
        f"    From right only: {ratio(counts.n_right_only, counts.n_rows_joined)}\n"
        f"    From both: {ratio(counts.n_both, counts.n_rows_joined)}\n"
        f"        Duplicate left keys among the matched rows: {counts.n_left_dups}\n"
        f"        Duplicate right keys among the matched rows: {counts.n_right_dups}\n"
        f"        Join cardinality: {join_cardinality(counts)}\n"
        f"Left input rows absent from the output: {ratio(counts.n_left_dropped, counts.n_left_total)}\n"
        f"Right input rows absent from the output: {ratio(counts.n_right_dropped, counts.n_right_total)}\n"
    )


def filtering_join_log(n_var: int, n_rows_joined: int, n_initial: int) -> str:
    """
    Build the log for a filtering (``semi`` / ``anti``) join.

    Shared verbatim by the pandas and polars ``join`` accessors.

    :param n_var: Signed change in row count (``n_rows_joined - n_initial``).
    :param n_rows_joined: Number of rows kept after the filtering join.
    :param n_initial: Number of rows in the left input table.
    :return: The single-line log message.
    :rtype: str
    """
    return (
        "Detected filtering join. "
        f"Rows variation {ratio(n_var, n_initial)}, "
        f"total rows after join: {ratio(n_rows_joined, n_initial)}"
    )


def elapsed(start_time_ns: int) -> str:
    """
    Describe the elapsed time since a ``time.perf_counter_ns()`` reading.

    :param start_time_ns: A start timestamp from :func:`time.perf_counter_ns`.
    :type start_time_ns: int
    :return: A message like ``"\\nTook: 1.20 seconds"``.
    :rtype: str
    """
    diff = datetime.timedelta(
        microseconds=(time.perf_counter_ns() - start_time_ns) / 1000
    )
    return "\nTook: " + humanize.precisedelta(diff)

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
Extensions for pandas
"""

import pandas as pd
import logging
import time
from natsort import natsorted
from pathlib import Path
from .export_docx import DocxFile
from . import _logutils

logger = logging.getLogger(__name__)

# --- SERIES --- #

try:
    # delete the accessor to avoid warning
    # See: https://stackoverflow.com/questions/69720999/how-to-prevent-pandas-accessor-to-issue-override-warning
    del pd.Series.raffa
except AttributeError:
    pass


@pd.api.extensions.register_series_accessor("raffa")
class RaffaSeries:
    """
    The ``.raffa`` accessor on a :class:`pandas.Series`.

    Registered automatically when :mod:`rkitpy.pandas` is imported. Provides
    STATA-like change logging (:meth:`startlog` / :meth:`endlog` / :meth:`midlog`),
    a :meth:`freq` frequency table, and a :meth:`toset` converter.
    """

    def __init__(self, data):
        self._series = data
        self._series._metadata += [
            "_initial_shape",
            "_initial_series",
            "_start_time",
        ]

    def startlog(self, clone=False):
        """
        Initialize the logger.

        :param clone: Whether to clone the Series. Takes more RAM but allows logging of changed values. Otherwise, only the changed shape is logged.
        :type clone: bool
        :return: The pandas Series for piping.
        :rtype: pd.Series
        """
        self._series._initial_shape = self._series.shape
        self._series._start_time = time.perf_counter_ns()
        if clone:
            self._series._initial_series = self._series.copy()
        else:
            self._series._initial_series = None
        return self._series

    def midlog(
        self, custom_msg: str | None = None, timeit: bool = True, clone: bool = False
    ):
        """
        Alias for `.endlog().startlog(clone=clone)`.

        :param custom_msg: A custom message to log before the actual log
        :type custom_msg: str | None
        :param timeit: Log the time it took for the operation
        :type timeit: bool
        :param clone: Forwarded to the restarted ``startlog``: clone the data so
            the next segment can detect value-level changes when the shape is
            unchanged.
        :type clone: bool
        """
        return self.endlog(custom_msg, timeit=timeit).raffa.startlog(clone=clone)

    def endlog(self, custom_msg: str | None = None, timeit: bool = True):
        """
        Log changes to the Series.

        :param custom_msg: A custom message to log before the actual log
        :type custom_msg: str | None
        :param timeit: Log the time it took for the operation
        :type timeit: bool
        :return: The pandas Series for piping.
        :rtype: pd.Series
        """
        msg = _logutils.prefix(custom_msg)
        initial_shape = self._series._initial_shape
        final_shape = self._series.shape
        if final_shape != initial_shape:
            msg += _logutils.series_shape_delta(initial_shape, final_shape)
        else:
            if self._series._initial_series is not None:
                nchanged = self._series != self._series._initial_series
                # missings are different than themselves
                nchanged[self._series.isna() & self._series._initial_series.isna()] = (
                    False
                )
                nchanged = nchanged.sum()
                msg += _logutils.changed_cells(
                    nchanged, self._series._initial_series.size
                )
            else:
                msg += _logutils.CLONE_FALSE_MSG
        if timeit:
            msg += _logutils.elapsed(self._series._start_time)
        logger.info(msg)
        del self._series._initial_series
        del self._series._initial_shape
        del self._series._start_time
        return self._series

    def freq(self, dropna: bool = False) -> pd.DataFrame:
        """
        Generate frequency table for this series

        :param dropna: Whether to drop missing values before generating frequency table
        :type dropna: bool
        :return: A DataFrame with frequency table
        :rtype: pd.DataFrame
        """
        tempdf = pd.DataFrame(self._series.value_counts(dropna=dropna, normalize=False))
        tempdf = tempdf.join(self._series.value_counts(dropna=dropna, normalize=True))
        totals_row = tempdf.agg({"count": ["sum"], "proportion": ["sum"]}).rename(
            index={"sum": "Total"}
        )
        df = pd.concat([tempdf, totals_row])
        df.index.name = self._series.name
        return df

    def toset(self) -> set:
        """
        Convert the Series values to a Python :class:`set`.

        Mirrors :meth:`pandas.Series.tolist`. Deduplicates by construction;
        missing values are kept (as ``nan``), call ``.dropna()`` first to
        exclude them.

        :return: The set of the Series' values.
        :rtype: set
        """
        return set(self._series)


# --- DATAFRAME --- #
try:
    # delete the accessor to avoid warning
    # See: https://stackoverflow.com/questions/69720999/how-to-prevent-pandas-accessor-to-issue-override-warning
    del pd.DataFrame.raffa
except AttributeError:
    pass


# See: https://pandas.pydata.org/pandas-docs/stable/development/extending.html#registering-custom-accessors
@pd.api.extensions.register_dataframe_accessor("raffa")
class RaffaDataFrame:
    """
    The ``.raffa`` accessor on a :class:`pandas.DataFrame`.

    Registered automatically when :mod:`rkitpy.pandas` is imported. Provides
    STATA-like change logging (:meth:`startlog` / :meth:`endlog` / :meth:`midlog`),
    a logging :meth:`join` wrapper, a :meth:`freq` frequency table, and
    :meth:`to_docx` export, plus small column helpers.
    """

    def __init__(self, data: pd.DataFrame) -> None:
        self._df = data
        # See https://pandas.pydata.org/pandas-docs/stable/development/extending.html#define-original-properties
        self._df._metadata += ["_initial_shape", "_initial_df", "_start_time"]

    def startlog(self, clone: bool = False) -> pd.DataFrame:
        """
        Initialize the logger.

        :param clone: Whether to clone the DataFrame. Takes more RAM but allows logging of changed values. Otherwise, only the changed shape is logged.
        :type clone: bool
        :return: The same DataFrame for piping.
        :rtype: pd.DataFrame
        """
        self._df._initial_shape = self._df.shape
        self._df._start_time = time.perf_counter_ns()
        if clone:
            self._df._initial_df = self._df.copy()
        else:
            self._df._initial_df = None
        return self._df

    def midlog(
        self,
        custom_msg: str | None = None,
        timeit: bool = True,
        clone: bool = False,
    ) -> pd.DataFrame:
        """
        Alias for `.endlog().startlog(clone=clone)`.

        :param custom_msg: A custom message to log before the actual log
        :type custom_msg: str | None
        :param timeit: Log the time it took for the operation
        :type timeit: bool
        :param clone: Forwarded to the restarted ``startlog``: clone the data so
            the next segment can detect value-level changes when the shape is
            unchanged.
        :type clone: bool
        """
        return self.endlog(custom_msg, timeit=timeit).raffa.startlog(clone=clone)

    def endlog(
        self, custom_msg: str | None = None, timeit: bool = True
    ) -> pd.DataFrame:
        """
        Log changes to the DataFrame.

        :param custom_msg: A custom message to log before the actual log
        :type custom_msg: str | None
        :param timeit: Log the time it took for the operation
        :type timeit: bool
        :return: The DataFrame for piping.
        :rtype: pd.DataFrame
        """
        msg = _logutils.prefix(custom_msg)
        final_shape = self._df.shape
        initial_shape = self._df._initial_shape
        if final_shape != initial_shape:
            msg += _logutils.dataframe_shape_delta(initial_shape, final_shape)
        else:
            initial_df = self._df._initial_df
            if initial_df is not None:
                nchanged = self._df != initial_df
                # missings are different than themselves
                # if both values are missing, set changed to False
                nchanged[self._df.isna() & initial_df.isna()] = False
                # Get total number of cells that have changed
                nchanged = nchanged.sum().sum()
                msg += _logutils.changed_cells(nchanged, initial_df.size)
            else:
                msg += _logutils.CLONE_FALSE_MSG
        if timeit:
            msg += _logutils.elapsed(self._df._start_time)
        logger.info(msg)
        del self._df._initial_df
        del self._df._initial_shape
        del self._df._start_time
        return self._df

    def add_prefix_if_not_exists(self, prefix: str) -> pd.DataFrame:
        """
        Add a prefix to all column names that do not already have it.

        :param prefix: The prefix to add
        :type prefix: str
        """
        new_cols = {
            col: f"{prefix}{col}"
            for col in self._df.columns
            if not col.startswith(prefix)
        }
        return self._df.rename(columns=new_cols)

    def get_duplicates(self, *args, **kwargs):
        """
        Alias for `df[df.duplicated(*args, **kwargs)]`.
        """
        mask = self._df.duplicated(*args, **kwargs)
        return self._df[mask]

    def sort_columns(self) -> pd.DataFrame:
        """
        Sort columns using natural sorting.
        """
        self._df = self._df[natsorted(self._df.columns)]
        return self._df

    def join(self, df2: pd.DataFrame, *args, keep_row_index: bool = False, **kwargs):
        """
        Wrapper around `pd.DataFrame.merge` to log join operations.

        :param df2: The dataframe on the right of the join
        :type df2: pd.DataFrame
        :param args: Additional positional arguments passed to `pd.DataFrame.merge`
        :type args: Any
        :param keep_row_index: Whether to keep columns indicating the row index of the source table in the output table
        :type keep_row_index: bool
        :param kwargs: Additional keyword arguments passed to `pd.DataFrame.merge`
        :type kwargs: Any
        :return: The joined DataFrame
        :rtype: pd.DataFrame
        """

        left_col = "source_left"
        right_col = "source_right"
        # Get DataFrames to join, add source row-index column
        df1 = self._df.copy()
        df1[left_col] = range(len(df1))
        df2 = df2.copy()
        df2[right_col] = range(len(df2))
        # Check whether this is a filtering join
        # Filtering joins filter rows from the left table based on the presence or
        # absence of matches in the right table:
        # "semi" returns all rows from the left with a match in the right.
        # "anti" returns all rows from the left without a match in the right.
        how = kwargs.get("how", "inner")
        is_filter = how in ["anti", "semi"]
        # If this is a filtering join, log only the rows variation in the left table
        if is_filter:
            # pandas has no native semi/anti join, so emulate it: an inner merge
            # tells us which left rows have at least one match in the right table.
            match_kwargs = {k: v for k, v in kwargs.items() if k != "how"}
            matched = df1.merge(df2, *args, how="inner", **match_kwargs)[
                left_col
            ].unique()
            mask = df1[left_col].isin(matched)
            if how == "anti":
                mask = ~mask
            joined = df1[mask]
            n_initial = df1.shape[0]
            n_rows_joined = joined.shape[0]
            n_var = n_rows_joined - n_initial
            logger.info(_logutils.filtering_join_log(n_var, n_rows_joined, n_initial))
            return joined.drop(columns=[left_col])
        # pandas uses "outer" where polars uses "full"
        if how == "full":
            kwargs = {**kwargs, "how": "outer"}
        # Join DataFrames
        joined = df1.merge(df2, *args, **kwargs)
        n_rows_joined = joined.shape[0]
        # Detect how many rows in the output table are present in the input tables
        joined_both = joined[joined[left_col].notna() & joined[right_col].notna()]
        n_both = joined_both.shape[0]
        # duplicated(keep=False) marks all duplicates as True, not only the
        # extra copies, so these count every matched output row whose source
        # row is reused (same semantics as polars is_duplicated)
        n_left_dups = int(joined_both[left_col].duplicated(keep=False).sum())
        n_right_dups = int(joined_both[right_col].duplicated(keep=False).sum())
        n_left_only = joined[joined[left_col].notna() & joined[right_col].isna()].shape[
            0
        ]
        n_right_only = joined[
            joined[left_col].isna() & joined[right_col].notna()
        ].shape[0]
        left_dropped = set(df1[left_col]) - set(joined[left_col].dropna())
        n_left_dropped = len(left_dropped)
        right_dropped = set(df2[right_col]) - set(joined[right_col].dropna())
        n_right_dropped = len(right_dropped)
        # Log rows information
        logger.info(
            _logutils.join_log(
                _logutils.JoinCounts(
                    n_rows_joined=n_rows_joined,
                    n_left_only=n_left_only,
                    n_right_only=n_right_only,
                    n_both=n_both,
                    n_left_dups=n_left_dups,
                    n_right_dups=n_right_dups,
                    n_left_dropped=n_left_dropped,
                    n_left_total=df1.shape[0],
                    n_right_dropped=n_right_dropped,
                    n_right_total=df2.shape[0],
                )
            )
        )
        # Drop or relocate row indices
        if not keep_row_index:
            joined = joined.drop(columns=[left_col, right_col])
        else:
            cols = [c for c in joined.columns if c not in (left_col, right_col)]
            joined = joined[cols + [left_col, right_col]]
        return joined

    def freq(self, colname: str, dropna: bool = False) -> pd.DataFrame:
        """
        Generate frequency table for a variable.

        :param colname: The name of the column holding the variable
        :type colname: str
        :param dropna: Whether to drop missing values before generating frequency table
        :type dropna: bool
        :return: A DataFrame with the frequency table
        :rtype: pd.DataFrame
        """
        return self._df[colname].raffa.freq(dropna=dropna)

    def to_docx(
        self,
        outfp: Path,
        include_index: bool = True,
        doc_options: dict | None = None,
        table_options: dict | None = None,
    ):
        """
        Export table in Word .docx file.

        MultiIndex columns are rendered as one header row per level, with
        adjacent header cells that share the same label (within the same
        parent group) merged horizontally.

        :param outfp: The output file
        :type outfp: Path
        :param include_index: Whether to export the index
        :type include_index: bool
        :param doc_options: Options forwarded to
            :class:`~rkitpy.export_docx.DocxFile` (document/heading options
            such as ``heading_text`` or ``landscape``).
        :type doc_options: dict | None
        :param table_options: Options forwarded to
            :meth:`~rkitpy.export_docx.DocxFile.add_table` (table options
            such as ``table_style`` or ``table_font_size``).
            ``table_header_rows`` is set to the number of column levels unless
            given here explicitly.
        :type table_options: dict | None
        :return: None
        :rtype: None
        """

        df = self._df

        # Create table
        # See: https://stackoverflow.com/a/40597684/1719931
        # One header row per column level (1 for flat columns)
        n_header_rows = df.columns.nlevels
        n_rows, n_cols = df.shape[0] + n_header_rows, df.shape[1]
        # If we write the index, the first column will be used for the index
        if include_index:
            n_cols += 1
        col0 = 1 if include_index else 0
        # Create document with table (callers may still override table_header_rows)
        table_options = dict(table_options) if table_options else {}
        table_options.setdefault("table_header_rows", n_header_rows)
        doc = DocxFile(**(doc_options or {}))
        doc.add_table(n_rows, n_cols, **table_options)
        t = doc.table

        # add the header rows: within each level, merge runs of columns that
        # share the same labels on all levels down to (and including) this one,
        # except on the leaf level, where data columns must stay distinct
        cols = [c if isinstance(c, tuple) else (c,) for c in df.columns]
        for lev in range(n_header_rows):
            j = 0
            while j < len(cols):
                k = j
                if lev < n_header_rows - 1:
                    while (
                        k + 1 < len(cols)
                        and cols[k + 1][: lev + 1] == cols[j][: lev + 1]
                    ):
                        k += 1
                cell = t.cell(lev, col0 + j)
                if k > j:
                    cell = cell.merge(t.cell(lev, col0 + k))
                cell.text = str(cols[j][lev])
                j = k + 1

        # add index names
        if include_index:
            if df.index.name is not None:
                # in the bottom header row, next to the leaf column labels
                t.cell(n_header_rows - 1, 0).text = str(df.index.name)
            for i in range(df.shape[0]):
                t.cell(i + n_header_rows, 0).text = str(df.index[i])

        # add the rest of the data frame
        for i in range(df.shape[0]):
            for j in range(df.shape[-1]):
                t.cell(i + n_header_rows, j + col0).text = str(df.values[i, j])

        # Save
        doc.save(outfp)

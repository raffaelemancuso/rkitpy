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

import polars as pl
import polars.selectors as cs
import polars_config_meta  # noqa: F401  registers the `config_meta` namespace on import
import polars_permute  # noqa: F401  registers the `permute` namespace (used by join)

from .export_docx import DocxFile
from . import _logutils
from enum import Enum, auto
import logging
import time
from pathlib import Path

logger = logging.getLogger(__name__)
pl.Config(thousands_separator=",")


class PercOptions(Enum):
    """
    How :meth:`RaffaPolarsDataFrameUtils.crosstab` should express its counts.

    :cvar NO: Report raw counts (no percentages).
    :cvar TOTAL: Each cell as a percentage of the grand total.
    :cvar COLUMNS: Each cell as a percentage of its column total.
    :cvar ROWS: Each cell as a percentage of its row total.
    """

    NO = auto()
    TOTAL = auto()
    COLUMNS = auto()
    ROWS = auto()


# --- SERIES --- #

try:
    # delete the accessor to avoid warning
    # See: https://stackoverflow.com/questions/69720999/how-to-prevent-pandas-accessor-to-issue-override-warning
    del pl.Series.raffa
except AttributeError:
    pass


@pl.api.register_series_namespace("raffa")
class RaffaPolarsSeriesUtils:
    """
    The ``.raffa`` namespace on a :class:`polars.Series`.

    Registered automatically when :mod:`rkitpy.polars` is imported. Provides
    STATA-like change logging (:meth:`startlog` / :meth:`endlog` / :meth:`midlog`),
    tabulation helpers (:meth:`freq`, :meth:`crosstab`), and a :meth:`toset`
    converter.
    """

    def __init__(self, series: pl.Series):
        self._series = series

    def startlog(self, clone=False):
        """
        Initialize the logger.

        :param clone: Whether to clone the Series. Takes more RAM but allows logging of changed values. Otherwise, only the changed shape is logged.
        :type clone: bool
        :return: The same Series for piping.
        :rtype: pl.Series
        """

        self._series.config_meta.set(old_shape=self._series.shape)
        self._series.config_meta.set(start_time=time.perf_counter_ns())
        if clone:
            self._series.config_meta.set(old_series=self._series.clone())
        else:
            self._series.config_meta.set(old_series=None)
        return self._series

    def endlog(self, custom_msg: str | None = None, timeit: bool = True) -> pl.Series:
        """
        Log changes to the Series.

        :param custom_msg: A custom message to log before the actual log
        :type custom_msg: str | None
        :param timeit: Log the time it took for the operation
        :type timeit: bool
        :return: The Series for piping.
        :rtype: pl.Series
        """
        if "old_shape" not in self._series.config_meta.get_metadata():
            logger.info("You have to call startlog() before calling endlog().")
            return self._series

        msg = _logutils.prefix(custom_msg)

        start_time = self._series.config_meta.get_metadata()["start_time"]
        old_shape = self._series.config_meta.get_metadata()["old_shape"]
        new_shape = self._series.shape

        if new_shape != old_shape:
            msg += _logutils.series_shape_delta(old_shape, new_shape)
        else:
            old_series = self._series.config_meta.get_metadata()["old_series"]
            if old_series is None:
                msg += _logutils.CLONE_FALSE_MSG
            else:
                # ne_missing treats null == null as equal and null vs value as changed
                n_changed = self._series.ne_missing(old_series).sum()
                msg += _logutils.changed_cells(n_changed, old_shape[0])

        if timeit:
            msg += _logutils.elapsed(start_time)

        logger.info(msg)
        return self._series

    def midlog(
        self, custom_msg: str | None = None, timeit: bool = True, clone: bool = False
    ) -> pl.Series:
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

    def freq(self) -> pl.DataFrame:
        """
        Frequency table for the Series.

        :return: The frequency table.
        :rtype: pl.DataFrame
        """
        tot = self._series.shape[0]
        counter = (
            self._series.value_counts()
            .select(cs.by_index(0).cast(pl.String).alias("value"), "count")
            .with_columns(((pl.col("count") / tot) * 100).alias("perc"))
            .sort("perc", descending=True)
        )
        tot_row = pl.DataFrame(
            {
                "value": ["Total"],
                "count": [counter.get_column("count").sum()],
                "perc": [counter.get_column("perc").sum()],
            },
            schema={"value": pl.Utf8, "count": pl.UInt32, "perc": pl.Float64},
        )
        counter = pl.concat([counter, tot_row], how="vertical")
        return counter

    def crosstab(
        self, ser_b: pl.Series, perc: PercOptions = PercOptions.NO
    ) -> pl.DataFrame:
        """
        Cross table with another Series.

        :param ser_b: The other Series
        :type ser_b: pl.Series
        :param perc: How to calculate percentages
        :type perc: PercOptions
        :return: The cross table.
        :rtype: pl.DataFrame
        """
        df = pl.DataFrame({self._series.name: self._series, ser_b.name: ser_b})
        return df.raffa.crosstab(self._series.name, ser_b.name, perc=perc)

    def toset(self) -> set:
        """
        Convert the Series values to a Python :class:`set`.

        Mirrors :meth:`polars.Series.to_list`. Deduplicates by construction;
        null values are kept (as ``None``), call ``.drop_nulls()`` first to
        exclude them.

        :return: The set of the Series' values.
        :rtype: set
        """
        return set(self._series.to_list())


# --- DATAFRAME --- #

try:
    # delete the accessor to avoid warning
    # See: https://stackoverflow.com/questions/69720999/how-to-prevent-pandas-accessor-to-issue-override-warning
    del pl.DataFrame.raffa
except AttributeError:
    pass


@pl.api.register_dataframe_namespace("raffa")
class RaffaPolarsDataFrameUtils:
    """
    The ``.raffa`` namespace on a :class:`polars.DataFrame`.

    Registered automatically when :mod:`rkitpy.polars` is imported. Provides
    STATA-like change logging (:meth:`startlog` / :meth:`endlog` / :meth:`midlog`),
    a logging :meth:`join` wrapper, tabulation helpers (:meth:`freq`,
    :meth:`crosstab`), and :meth:`to_docx` export.
    """

    def __init__(self, df: pl.DataFrame):
        self._df = df

    def startlog(self, clone=False) -> pl.DataFrame:
        """
        Initialize the logger.

        :param clone: Whether to clone the DataFrame. Takes more RAM but allows logging of changed values. Otherwise, only the changed shape is logged.
        :type clone: bool
        :return: The same DataFrame for piping.
        :rtype: pl.DataFrame
        """

        self._df.config_meta.set(
            initial_shape=self._df.shape, start_time=time.perf_counter_ns()
        )
        if clone:
            self._df.config_meta.set(initial_df=self._df.clone())
        else:
            self._df.config_meta.set(initial_df=None)
        return self._df

    def endlog(
        self, custom_msg: str | None = None, timeit: bool = True
    ) -> pl.DataFrame:
        """
        Log changes to the DataFrame.

        :param custom_msg: A custom message to log before the actual log
        :type custom_msg: str | None
        :param timeit: Log the time it took for the operation
        :type timeit: bool
        :return: The DataFrame for piping.
        :rtype: pl.DataFrame
        """

        if "initial_shape" not in self._df.config_meta.get_metadata():
            logger.info("You have to call startlog() before calling endlog().")
            return self._df
        initial_shape = self._df.config_meta.get_metadata()["initial_shape"]

        msg = _logutils.prefix(custom_msg)
        start_time = self._df.config_meta.get_metadata()["start_time"]

        final_shape = self._df.shape
        if final_shape != initial_shape:
            msg += _logutils.dataframe_shape_delta(initial_shape, final_shape)
        else:
            initial_df = self._df.config_meta.get_metadata()["initial_df"]
            if initial_df is None:
                msg += _logutils.CLONE_FALSE_MSG
            else:
                a = (self._df != initial_df).fill_null(False).to_numpy()
                b = (
                    self._df.with_columns(pl.all().is_null())
                    != initial_df.with_columns(pl.all().is_null())
                ).to_numpy()
                # Get total number of cells that have changed
                nchanged = (a | b).sum().sum()
                ntot = final_shape[0] * final_shape[1]
                msg += _logutils.changed_cells(nchanged, ntot)
        if timeit:
            msg += _logutils.elapsed(start_time)
        logger.info(msg)
        return self._df

    def midlog(
        self,
        custom_msg: str | None = None,
        timeit: bool = True,
        clone: bool = False,
    ) -> pl.DataFrame:
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

    def replace_string_with_null(self, s):
        """
        Replace a sentinel string with null across all string columns.

        Useful for cleaning CSV files that encode missing values as a literal
        string such as ``"NA"``.

        :param s: The string value to replace with null.
        :type s: str
        :return: The DataFrame with matching string cells set to null.
        :rtype: pl.DataFrame
        """
        # self._df.with_columns(pl.col(pl.String).str.replace(s, None).name.keep())
        self._df = self._df.with_columns(
            pl.when(pl.col(pl.String) == s)
            .then(None)
            .otherwise(pl.col(pl.String))
            .name.keep()
        )
        return self._df

    def freq(self, col, *args, **kwargs) -> pl.DataFrame:
        """
        Frequency table for a single column.

        Delegates to the :class:`polars.Series` ``raffa.freq`` accessor.

        :param col: Name of the column to tabulate.
        :type col: str
        :param args: Extra positional arguments forwarded to the Series accessor.
        :param kwargs: Extra keyword arguments forwarded to the Series accessor.
        :return: A frequency table with ``value``, ``count`` and ``perc`` columns
            plus a ``Total`` row.
        :rtype: pl.DataFrame
        """
        return self._df.get_column(col).raffa.freq(*args, **kwargs)

    def crosstab(
        self, col_a: str, col_b: str, perc: PercOptions = PercOptions.NO
    ) -> pl.DataFrame:
        """
        Cross-tabulation (contingency table) of two columns.

        :param col_a: Column whose distinct values form the rows.
        :type col_a: str
        :param col_b: Column whose distinct values form the columns.
        :type col_b: str
        :param perc: Whether to report raw counts or percentages, and along which
            axis. See :class:`PercOptions`. Defaults to ``PercOptions.NO``.
        :type perc: PercOptions
        :return: The cross table, one row per distinct value of ``col_a``.
        :rtype: pl.DataFrame
        """
        ct = self._df.pivot(
            on=col_b,
            index=col_a,
            values=col_b,
            aggregate_function="len",
            sort_columns=True,
        ).sort(col_a)

        if perc == PercOptions.NO:
            return ct

        values = ~cs.first()

        options = {
            PercOptions.COLUMNS: values.sum(),
            PercOptions.ROWS: pl.sum_horizontal(values),
            PercOptions.TOTAL: pl.sum_horizontal(values).sum(),
        }

        return ct.with_columns(values / options[perc] * 100)

    def join(self, df2: pl.DataFrame, *args, keep_row_index: bool = False, **kwargs):
        """
        Wrapper around `pl.DataFrame.join` to log join operations.

        :param df2: The dataframe on the right of the join
        :type df2: pl.DataFrame
        :param args: Additional positional arguments passed to `pl.DataFrame.join`
        :type args: Any
        :param keep_row_index: Whether to keep columns indicating the row index of the source table in the output table
        :type keep_row_index: bool
        :param kwargs: Additional keyword arguments passed to `pl.DataFrame.join`
        :type kwargs: Any
        :return: The joined DataFrame
        :rtype: pl.DataFrame
        """

        left_col = "source_left"
        right_col = "source_right"
        # Get DataFrame to join, add source column
        df1 = self._df.with_row_index(left_col)
        df2 = df2.with_row_index(right_col)
        # Join DataFrames
        joined = df1.join(df2, *args, **kwargs)
        n_rows_joined = joined.shape[0]
        # Check whether this is a filtering join
        # Filtering joins filter rows from x based on the presence or absence of matches in y:
        # semi_join() return all rows from x with a match in y.
        # anti_join() return all rows from x without a match in y.
        is_filter = kwargs.get("how", None) in ["anti", "semi"]
        # If this is a filtering join, log only the rows variation in the left table
        if is_filter:
            n_initial = df1.shape[0]
            n_var = n_rows_joined - n_initial
            logger.info(_logutils.filtering_join_log(n_var, n_rows_joined, n_initial))
            joined = joined.drop([left_col])
            return joined
        # Detect how many rows in the output table are present in the input tables
        joined_both = joined.filter(
            ~pl.col(left_col).is_null(), ~pl.col(right_col).is_null()
        )
        n_both = joined_both.shape[0]
        # is_duplicated() marks all duplicates as True, not only the extra
        # copies, so these count every matched output row whose source row
        # is reused (same semantics as pandas duplicated(keep=False))
        n_left_dups = joined_both.get_column(left_col).is_duplicated().sum()
        n_right_dups = joined_both.get_column(right_col).is_duplicated().sum()
        n_left_only = joined.filter(
            ~pl.col(left_col).is_null(), pl.col(right_col).is_null()
        ).shape[0]
        n_right_only = joined.filter(
            pl.col(left_col).is_null(), ~pl.col(right_col).is_null()
        ).shape[0]
        left_dropped = set(df1.get_column(left_col).to_list()) - set(
            joined.get_column(left_col).to_list()
        )
        n_left_dropped = len(left_dropped)
        right_dropped = set(df2.get_column(right_col).to_list()) - set(
            joined.get_column(right_col).to_list()
        )
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
        # Drop row indices
        if not keep_row_index:
            joined = joined.drop([left_col, right_col])
        else:
            joined = joined.permute.append([left_col, right_col])
        return joined

    def to_docx(
        self,
        outfp: Path,
        doc_options: dict | None = None,
        table_options: dict | None = None,
    ):
        """
        Export table in Word .docx file.

        :param outfp: The output file
        :type outfp: Path
        :param doc_options: Options forwarded to
            :class:`~rkitpy.export_docx.DocxFile` (document/heading options
            such as ``heading_text`` or ``landscape``).
        :type doc_options: dict | None
        :param table_options: Options forwarded to
            :meth:`~rkitpy.export_docx.DocxFile.add_table` (table options
            such as ``table_style`` or ``table_font_size``).
        :type table_options: dict | None
        :return: None
        :rtype: None
        """
        df = self._df

        # Create table
        # See: https://stackoverflow.com/a/40597684/1719931
        # First row is for the table header (i.e., column names)
        n_rows, n_cols = df.shape[0] + 1, df.shape[1]

        # Create document with table
        doc = DocxFile(**(doc_options or {}))
        doc.add_table(n_rows, n_cols, **(table_options or {}))
        t = doc.table

        # add the header row (column names)
        for j in range(df.shape[1]):
            t.cell(0, j).text = str(df.columns[j])

        # add the rest of the data frame
        values = df.to_numpy()
        for i in range(df.shape[0]):
            for j in range(df.shape[1]):
                t.cell(i + 1, j).text = str(values[i, j])

        # Save
        doc.save(outfp)

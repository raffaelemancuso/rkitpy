import time

import pytest

from rkitpy import _logutils


def test_clone_false_msg():
    assert _logutils.CLONE_FALSE_MSG == (
        "Shape is the same. No value-level comparison done because "
        "clone=False was used in startlog()."
    )


def test_count_delta_removed():
    assert _logutils.count_delta(1, 4, "rows") == "Removed 1/4 (25.00%) rows."


def test_count_delta_added():
    assert _logutils.count_delta(-2, 4, "values") == "Added 2/4 (50.00%) values."


def test_count_delta_zero_is_empty():
    assert _logutils.count_delta(0, 4, "rows") == ""


def test_count_delta_added_to_empty_is_guarded():
    # Adding rows to an initially-empty frame: denominator is zero.
    assert _logutils.count_delta(-3, 0, "rows") == "Added 3/0 (N/A) rows."


def test_count_delta_thousands_separator():
    assert (
        _logutils.count_delta(1500, 3000, "rows")
        == "Removed 1,500/3,000 (50.00%) rows."
    )


def test_dataframe_shape_delta_rows_and_columns():
    msg = _logutils.dataframe_shape_delta((10, 5), (8, 6))
    assert msg == (
        "Removed 2/10 (20.00%) rows.Added 1/5 (20.00%) columns. New shape: (8; 6)."
    )


def test_dataframe_shape_delta_rows_only():
    assert _logutils.dataframe_shape_delta((10, 5), (7, 5)) == (
        "Removed 3/10 (30.00%) rows. New shape: (7; 5)."
    )


def test_dataframe_shape_delta_no_change_is_empty():
    assert _logutils.dataframe_shape_delta((10, 5), (10, 5)) == ""


def test_new_shape_dataframe():
    assert _logutils.new_shape((8, 6)) == "New shape: (8; 6)."


def test_new_shape_series():
    assert _logutils.new_shape((8,)) == "New shape: (8)."


def test_series_shape_delta_removed():
    assert _logutils.series_shape_delta((5,), (3,)) == (
        "Removed 2/5 (40.00%) values. New shape: (3)."
    )


def test_series_shape_delta_added():
    assert _logutils.series_shape_delta((3,), (5,)) == (
        "Added 2/3 (66.67%) values. New shape: (5)."
    )


def test_series_shape_delta_no_change_is_empty():
    assert _logutils.series_shape_delta((5,), (5,)) == ""


def test_ratio_basic():
    assert _logutils.ratio(1, 4) == "1/4 (25.00%)"


def test_ratio_negative_numerator():
    assert _logutils.ratio(-2, 5) == "-2/5 (-40.00%)"


def test_ratio_thousands_separator():
    assert _logutils.ratio(1500, 3000) == "1,500/3,000 (50.00%)"


def test_ratio_zero_denominator_guarded():
    assert _logutils.ratio(0, 0) == "0/0 (N/A)"


def test_changed_cells_none():
    assert _logutils.changed_cells(0, 12) == "No changes detected."


def test_changed_cells_some():
    assert _logutils.changed_cells(3, 12) == "Changed 3/12 (25.00%) values."


def test_elapsed_prefix_and_type():
    msg = _logutils.elapsed(time.perf_counter_ns())
    assert isinstance(msg, str)
    assert msg.startswith("\nTook: ")


def test_prefix_none_is_empty():
    assert _logutils.prefix(None) == ""


def test_prefix_appends_separator():
    assert _logutils.prefix("step 1") == "step 1. "


def test_filtering_join_log():
    assert _logutils.filtering_join_log(-1, 3, 4) == (
        "Detected filtering join. Rows variation -1/4 (-25.00%), "
        "total rows after join: 3/4 (75.00%)"
    )


def test_join_log_matches_expected_layout():
    msg = _logutils.join_log(
        _logutils.JoinCounts(
            n_rows_joined=4,
            n_left_only=1,
            n_right_only=0,
            n_both=3,
            n_left_dups=0,
            n_right_dups=0,
            n_left_dropped=0,
            n_left_total=4,
            n_right_dropped=2,
            n_right_total=5,
        )
    )
    assert msg == (
        "Total rows in output table: 4\n"
        "    From left only: 1/4 (25.00%)\n"
        "    From right only: 0/4 (0.00%)\n"
        "    From both: 3/4 (75.00%)\n"
        "        Duplicate left keys among the matched rows: 0\n"
        "        Duplicate right keys among the matched rows: 0\n"
        "        Join cardinality: one-to-one\n"
        "Left input rows absent from the output: 0/4 (0.00%)\n"
        "Right input rows absent from the output: 2/5 (40.00%)\n"
    )


def test_join_log_guards_zero_denominators():
    msg = _logutils.join_log(
        _logutils.JoinCounts(
            n_rows_joined=0,
            n_left_only=0,
            n_right_only=0,
            n_both=0,
            n_left_dups=0,
            n_right_dups=0,
            n_left_dropped=2,
            n_left_total=2,
            n_right_dropped=2,
            n_right_total=2,
        )
    )
    assert "Total rows in output table: 0" in msg
    assert "From both: 0/0 (N/A)" in msg
    assert "Join cardinality: N/A (no matched rows)" in msg


@pytest.mark.parametrize(
    ("n_both", "n_left_dups", "n_right_dups", "expected"),
    [
        (3, 0, 0, "one-to-one"),
        (2, 0, 2, "many-to-one"),
        (2, 2, 0, "one-to-many"),
        (4, 4, 4, "many-to-many"),
        (0, 0, 0, "N/A (no matched rows)"),
    ],
)
def test_join_cardinality(n_both, n_left_dups, n_right_dups, expected):
    counts = _logutils.JoinCounts(
        n_rows_joined=n_both,
        n_left_only=0,
        n_right_only=0,
        n_both=n_both,
        n_left_dups=n_left_dups,
        n_right_dups=n_right_dups,
        n_left_dropped=0,
        n_left_total=4,
        n_right_dropped=0,
        n_right_total=5,
    )
    assert _logutils.join_cardinality(counts) == expected
    assert f"Join cardinality: {expected}" in _logutils.join_log(counts)

from rkitpy.itertools import batch_boundaries


def test_docstring_example():
    assert list(batch_boundaries(20, 3)) == [
        (0, 1, 3),
        (1, 4, 6),
        (2, 7, 9),
        (3, 10, 12),
        (4, 13, 15),
        (5, 16, 18),
        (6, 19, 20),
    ]


def test_exact_division():
    assert list(batch_boundaries(6, 3)) == [(0, 1, 3), (1, 4, 6)]


def test_total_smaller_than_batch():
    assert list(batch_boundaries(2, 5)) == [(0, 1, 2)]


def test_batch_size_one_covers_every_item():
    # Regression: range(1, total) used to drop the final item.
    assert list(batch_boundaries(3, 1)) == [(0, 1, 1), (1, 2, 2), (2, 3, 3)]


def test_total_on_batch_boundary_covers_last_batch():
    # Regression: batch_boundaries(7, 3) used to drop items 7..7.
    assert list(batch_boundaries(7, 3)) == [(0, 1, 3), (1, 4, 6), (2, 7, 7)]


def test_indices_are_contiguous_and_cover_total():
    total, n = 23, 4
    boundaries = list(batch_boundaries(total, n))
    # First start is 1, last end is total, no gaps between batches.
    assert boundaries[0][1] == 1
    assert boundaries[-1][2] == total
    for (_, _, end), (_, start, _) in zip(boundaries, boundaries[1:]):
        assert start == end + 1

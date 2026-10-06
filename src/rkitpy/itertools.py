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


def batch_boundaries(total, n_per_batch):
    """
    Yield (batchi, start_ix, end_ix) tuples for batches of size n_per_batch.

    :param total: Total number of items to batch.
    :type total: int
    :param n_per_batch: Number of items per batch.
    :type n_per_batch: int
    :return: An iterator of (batch_index, start_index, end_index) tuples where indices are 1-based.
    :rtype: Iterator[tuple[int, int, int]]

    :Example:

    >>> from rkitpy.itertools import batch_boundaries
    >>> list(batch_boundaries(20, 3))
    [(0, 1, 3), (1, 4, 6), (2, 7, 9), (3, 10, 12), (4, 13, 15), (5, 16, 18), (6, 19, 20)]
    """
    start_ixs = list(range(1, total + 1, n_per_batch))
    for batchi, start_ix in enumerate(start_ixs):
        end_ix = min(total, start_ix + n_per_batch - 1)
        yield batchi, start_ix, end_ix

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

import functools
from tqdm.auto import tqdm
import itertools


def tqdm_batch(items, batch_size):
    """
    Create a progress bar wrapper that batches items.

    :param items: The sized iterable to wrap with a progress bar.
    :type items: Sized
    :param batch_size: Number of items per batch.
    :type batch_size: int
    :return: A ``functools.partial`` object that, when called, returns a tqdm progress bar over batched items.
    :rtype: functools.partial

    :Example:

    >>> for batch in tqdm_batch(my_list, 100)():  # doctest: +SKIP
    ...     process(batch)
    """
    n_batches = -(-len(items) // batch_size)  # ceil division
    return functools.partial(
        tqdm,
        iterable=itertools.batched(items, batch_size),
        total=n_batches,
    )

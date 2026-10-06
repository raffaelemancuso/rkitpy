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


def list_replace(lst, old, new):
    """
    Replace all occurrences of a value in a list (in place).

    :param lst: The list to modify (modified in place).
    :type lst: list
    :param old: The value to replace.
    :param new: The new value to insert.
    :return: None
    :rtype: None

    :Example:

    >>> from rkitpy import list_replace
    >>> lst = [1, 2, 3, 2, 4]
    >>> list_replace(lst, 2, 5)
    >>> lst
    [1, 5, 3, 5, 4]
    """
    i = -1
    try:
        while True:
            i = lst.index(old, i + 1)
            lst[i] = new
    except ValueError:
        pass

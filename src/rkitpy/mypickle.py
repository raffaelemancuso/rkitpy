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

import datetime
import jsonpickle
from pathlib import Path


def read_pickle(file: Path):
    """
    Read and decode a jsonpickle-encoded object from a file.

    :param file: Path to the file to read.
    :type file: Path
    :return: The decoded Python object.
    """
    with open(file, "r", encoding="utf8") as fh:
        return jsonpickle.decode(fh.read(), keys=True)


def write_pickle(data, dir_path: Path, file_stem: str):
    """
    Encode an object with jsonpickle and write it to a timestamped file.

    The output file is named ``{file_stem}_{YYYY-MM-DD-HH-MM-SS}`` inside ``dir_path``.

    :param data: The object to encode and write.
    :param dir_path: Directory in which to write the file.
    :type dir_path: Path
    :param file_stem: Stem used to build the output file name.
    :type file_stem: str
    :return: None
    :rtype: None
    """
    ts = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    file_name = file_stem + "_" + ts
    file_path = dir_path / file_name
    with open(file_path, "w", encoding="utf8") as fh:
        fh.write(jsonpickle.encode(data, keys=True))

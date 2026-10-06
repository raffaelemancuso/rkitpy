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

# copied from https://stackoverflow.com/a/93029/1719931
import re
import sys
import unicodedata

# Get string of control characters
all_chars = (chr(i) for i in range(sys.maxunicode))
categories = {"Cc"}
control_chars = "".join(c for c in all_chars if unicodedata.category(c) in categories)
# or equivalently and much more efficiently
# control_chars = ''.join(map(chr, itertools.chain(range(0x00,0x20), range(0x7f,0xa0))))


def preprocess_text_for_rag(s):

    # Build regular expressions
    control_char_re = re.compile("[%s]" % re.escape(control_chars))
    char_rep_re = re.compile(r"(\w|\.)\1{2,}")
    multiple_spaces_re = re.compile(r"\s+")

    # Replace single characters
    s = s.replace("-\n", "").replace("\n", " ").replace("\t", " ")

    # Filter non-printable characters
    # " ".isprintable() -> True
    # "\t".isprintable() -> False
    # "\n".isprintable() -> False
    s = "".join(filter(lambda x: x.isprintable(), s))

    # Apply other regexes
    s = control_char_re.sub(" ", s)
    s = char_rep_re.sub(" ", s)
    s = multiple_spaces_re.sub(" ", s)

    return s

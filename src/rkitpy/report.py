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

"""Fixed-column data-wrangling reports (the house .txt report format).

Every data-wrangling script writes a textual report next to its outputs:
line 1 title, line 2 timestamp (YYYY-MM-DD HH:MM:SS), line 3 blank, then one
line per item. Numbers are right-aligned so the unit digit is always in the
same column (the already-formatted string is padded, never the raw number, so
thousand separators line up too). Items with a denominator append a
fixed-width percentage with the numeric part padded inside the parentheses,
so brackets, decimal points and % signs all sit in fixed columns. Float
values (e.g. precision/recall metrics) print with 3 decimals, right-aligned
to the same column, and never take a percentage.
"""

import time
from pathlib import Path


def _fmt_val(n) -> str:
    if isinstance(n, float) and not n.is_integer():
        return f"{n:.3f}"
    return f"{int(n):,}"


def report_build(spec, title: str, timestamp: str | None = None) -> str:
    """Render a report from `spec` = iterable of (label, value, den) tuples.

    Indent sub-item labels with two spaces inside the label itself; sub-items
    conventionally report their percentage of the parent item's count.
    ``den=None`` suppresses the percentage.
    """
    spec = list(spec)
    nw = max(len(_fmt_val(n)) for _, n, _ in spec)
    lw = max(len(lab) for lab, _, _ in spec) + 2
    body = []
    for lab, n, den in spec:
        s = f"{lab:<{lw}}{_fmt_val(n):>{nw}}"
        if den is not None and not (isinstance(n, float) and not n.is_integer()):
            s += f" ({100 * n / den:5.1f}%)"
        body.append(s)
    header = [title, timestamp or time.strftime("%Y-%m-%d %H:%M:%S"), ""]
    return "\n".join(header + body) + "\n"


def report_save(spec, title: str, fp, logger=None, timestamp: str | None = None) -> str:
    """Build the report, print it, write it to `fp` and return it.

    `fp` is conventionally ``data/<stage>/<N>_report.txt``, numbered after the
    producing script. Pass a rkitpy logger to also log the save location.
    """
    report = report_build(spec, title, timestamp=timestamp)
    print(report, end="")
    Path(fp).write_text(report, encoding="utf-8", newline="\n")
    if logger is not None:
        logger.info(f"Report saved to {fp}")
    return report

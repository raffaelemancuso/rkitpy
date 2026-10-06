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
rkitpy: A library with helper functions for pandas, polars, selenium, and others.

This library enriches pandas and polars with STATA-like logging and .docx export capabilities.
It also provides utilities for backup files, logging configuration, progress bars, and more.
"""

from .tqdm import tqdm_batch
from .logging import create_logger
from .list_replace import list_replace
from .report import report_build, report_save

__all__ = ["tqdm_batch", "create_logger", "list_replace", "report_build", "report_save"]

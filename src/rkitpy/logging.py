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

import logging
import logging.config


def create_logger(
    logger_name: str = "",
    level: str = "INFO",
    rich: bool = False,
    fmt: str | None = None,
    disable_existing_loggers: bool = True,
) -> logging.Logger:
    """
    Create and configure a logger.

    :param logger_name: Name for the logger. If empty, uses the root logger.
    :type logger_name: str
    :param level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL). Defaults to "INFO".
    :type level: str
    :param rich: Whether to use rich formatting for console output. Defaults to False.
    :type rich: bool
    :param fmt: Custom format string for log messages. If None, uses default format.
    :type fmt: str | None
    :param disable_existing_loggers: Whether to disable existing loggers. Defaults to True.
    :type disable_existing_loggers: bool
    :return: A configured logging.Logger instance.
    :rtype: logging.Logger
    """

    datefmt = "%Y-%m-%d %H:%M:%S"
    logging.captureWarnings(True)

    # Default format depends on the handler: a plain StreamHandler prints the
    # full context, whereas RichHandler already renders the timestamp and level
    # itself, so its formatter only needs to add the name and message.
    if fmt is None:
        fmt = (
            "{name} - {message}"
            if rich
            else "{asctime} - {levelname} - {name} - {message}"
        )

    if rich:
        handler_name = "rich"
        handler = {
            "level": level,
            "formatter": "configured",
            "class": "rich.logging.RichHandler",
            "rich_tracebacks": False,
        }
    else:
        handler_name = "console"
        handler = {
            "level": level,
            "formatter": "configured",
            "class": "logging.StreamHandler",
        }

    LOGGING = {
        "version": 1,
        "disable_existing_loggers": disable_existing_loggers,
        "formatters": {
            "configured": {
                "format": fmt,
                "style": "{",
                "datefmt": datefmt,
            },
        },
        "handlers": {
            handler_name: handler,
        },
        "loggers": {
            logger_name: {
                "handlers": [handler_name],
                "level": level,
            },
        },
    }
    logging.config.dictConfig(LOGGING)

    logging.getLogger("rkitpy.pandas").disabled = False
    logging.getLogger("rkitpy.polars").disabled = False

    return logging.getLogger(logger_name)

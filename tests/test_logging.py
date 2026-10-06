import logging

from rich.logging import RichHandler

from rkitpy.logging import create_logger


def _handler(name):
    return logging.getLogger(name).handlers[0]


def test_returns_named_logger():
    lg = create_logger(
        "rkitpy_test_logger", level="INFO", disable_existing_loggers=False
    )
    assert isinstance(lg, logging.Logger)
    assert lg.name == "rkitpy_test_logger"


def test_root_logger_when_name_empty():
    lg = create_logger("", level="WARNING", disable_existing_loggers=False)
    assert isinstance(lg, logging.Logger)


def test_keeps_accessor_loggers_enabled():
    create_logger("whatever", level="INFO", disable_existing_loggers=False)
    assert logging.getLogger("rkitpy.pandas").disabled is False
    assert logging.getLogger("rkitpy.polars").disabled is False


def test_non_rich_uses_plain_streamhandler():
    create_logger("rkitpy_test_plain", rich=False, disable_existing_loggers=False)
    h = _handler("rkitpy_test_plain")
    assert type(h) is logging.StreamHandler


def test_rich_uses_rich_handler():
    create_logger("rkitpy_test_rich", rich=True, disable_existing_loggers=False)
    h = _handler("rkitpy_test_rich")
    assert isinstance(h, RichHandler)


def test_custom_fmt_is_applied():
    create_logger("rkitpy_test_fmt", fmt="{message}", disable_existing_loggers=False)
    h = _handler("rkitpy_test_fmt")
    record = logging.makeLogRecord({"msg": "hello"})
    assert h.format(record) == "hello"


def test_default_fmt_includes_level_and_message():
    create_logger("rkitpy_test_default", disable_existing_loggers=False)
    h = _handler("rkitpy_test_default")
    record = logging.makeLogRecord({"msg": "hello", "levelname": "INFO"})
    out = h.format(record)
    assert "hello" in out
    assert "INFO" in out

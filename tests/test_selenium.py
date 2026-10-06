from unittest.mock import MagicMock

import pytest

pytest.importorskip("selenium")

from rkitpy import selenium as rsel  # noqa: E402


def test_scroll_into_view_js_executes_script():
    driver = MagicMock()
    element = MagicMock()
    rsel.scroll_into_view_js(driver, element)
    driver.execute_script.assert_called_once_with(
        "arguments[0].scrollIntoView(true);", element
    )


def test_wait_element_to_be_visible_uses_timeout(monkeypatch):
    seen = {}

    class FakeWait:
        def __init__(self, driver, timeout):
            seen["timeout"] = timeout

        def until(self, condition):
            seen["until_called"] = True

    monkeypatch.setattr(rsel, "WebDriverWait", FakeWait)
    rsel.wait_element_to_be_visible(MagicMock(), MagicMock(), timeout=7)
    assert seen["timeout"] == 7
    assert seen["until_called"] is True


def test_wait_element_to_be_clickable_uses_default_timeout(monkeypatch):
    seen = {}

    class FakeWait:
        def __init__(self, driver, timeout):
            seen["timeout"] = timeout

        def until(self, condition):
            seen["until_called"] = True

    monkeypatch.setattr(rsel, "WebDriverWait", FakeWait)
    rsel.wait_element_to_be_clickable(MagicMock(), MagicMock())
    assert seen["timeout"] == 10
    assert seen["until_called"] is True

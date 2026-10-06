import pytest

pytest.importorskip("requests")
pytest.importorskip("fake_useragent")

from rkitpy import ScopusUtils as scopus_mod  # noqa: E402


class _FakeResponse:
    def __init__(self, text, status_code=200):
        self.text = text
        self.status_code = status_code


def test_get_new_scopus_id_parses_id(monkeypatch):
    su = scopus_mod.ScopusUtils()
    html = 'prefix nonTombstonedAuthorId="12345678901" suffix'
    monkeypatch.setattr(
        scopus_mod.requests, "get", lambda url, headers: _FakeResponse(html)
    )
    assert su.get_new_scopus_id("999") == "12345678901"


def test_get_new_scopus_id_zero_returns_old(monkeypatch):
    su = scopus_mod.ScopusUtils()
    html = 'nonTombstonedAuthorId="0"'
    monkeypatch.setattr(
        scopus_mod.requests, "get", lambda url, headers: _FakeResponse(html)
    )
    assert su.get_new_scopus_id("55555") == "55555"


def test_get_new_scopus_id_raises_on_malformed_html(monkeypatch):
    su = scopus_mod.ScopusUtils()
    monkeypatch.setattr(
        scopus_mod.requests, "get", lambda url, headers: _FakeResponse("no id here")
    )
    # avoid the real 2s sleeps between the 5 retries
    monkeypatch.setattr(scopus_mod.time, "sleep", lambda *_: None)
    with pytest.raises(Exception, match="Malformed HTML"):
        su.get_new_scopus_id("123")

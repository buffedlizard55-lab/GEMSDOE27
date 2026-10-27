import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "feed", Path(__file__).resolve().parents[1] / "scripts/refresh_source_feed.py"
)
feed = importlib.util.module_from_spec(spec)
spec.loader.exec_module(feed)


class Response:
    def __init__(self, status, location=None):
        self.status_code = status
        self.headers = {"Location": location} if location else {}
        self.closed = False

    def close(self):
        self.closed = True


def test_redirect_to_forbidden_host_is_not_requested(monkeypatch):
    requests = []
    response = Response(302, "https://www.drivendata.org/competitions/")

    def fake_get(url, **kwargs):
        requests.append((url, kwargs))
        return response

    monkeypatch.setattr(feed.requests, "get", fake_get)
    with pytest.raises(SystemExit, match="refusing to request"):
        feed.safe_get("https://example.com/source")
    assert len(requests) == 1 and requests[0][1]["allow_redirects"] is False
    assert response.closed


def test_safe_redirects_and_loop_limit(monkeypatch):
    urls = []

    def fake_get(url, **kwargs):
        urls.append(url)
        return Response(302, "/new") if url.endswith("/old") else Response(200)

    monkeypatch.setattr(feed.requests, "get", fake_get)
    assert feed.safe_get("https://example.com/old").status_code == 200
    assert urls == ["https://example.com/old", "https://example.com/new"]
    monkeypatch.setattr(feed.requests, "get", lambda url, **kw: Response(302, "/loop"))
    with pytest.raises(ValueError, match="too many redirects"):
        feed.safe_get("https://example.com/loop")


def test_cross_host_redirect_drops_authorization(monkeypatch):
    calls = []

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        return Response(302, "https://elsewhere.example/new") if len(calls) == 1 else Response(200)

    monkeypatch.setattr(feed.requests, "get", fake_get)
    feed.safe_get("https://api.github.com/old", headers={"Authorization": "secret", "Accept": "text"})
    assert "Authorization" in calls[0][1]["headers"]
    assert calls[1][1]["headers"] == {"Accept": "text"}


def test_forbidden_subdomain_blocked_before_first_request(monkeypatch):
    monkeypatch.setattr(feed.requests, "get", lambda *a, **kw: pytest.fail("network request made"))
    with pytest.raises(SystemExit):
        feed.safe_get("https://www.drivendata.org/path")

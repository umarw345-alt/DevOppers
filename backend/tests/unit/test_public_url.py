from starlette.requests import Request

from portfolio.routes import public_url


def request(host="devoppers.vercel.app", scheme="http", **headers):
    raw = [(b"host", host.encode())] + [(k.replace("_", "-").encode(), v.encode()) for k, v in headers.items()]
    return Request({"type": "http", "scheme": scheme, "server": (host, 80), "path": "/", "headers": raw})


def test_links_use_the_address_the_request_came_in_on(monkeypatch):
    monkeypatch.delenv("PUBLIC_BASE_URL", raising=False)
    assert public_url(request("localhost:8000"), "jerry") == "http://localhost:8000/jerry"


def test_links_keep_https_behind_a_proxy(monkeypatch):
    monkeypatch.delenv("PUBLIC_BASE_URL", raising=False)
    req = request(x_forwarded_proto="https")
    assert public_url(req, "jerry") == "https://devoppers.vercel.app/jerry"


def test_public_base_url_overrides_the_request(monkeypatch):
    monkeypatch.setenv("PUBLIC_BASE_URL", "http://192.168.1.20:8000/")
    assert public_url(request(), "jerry") == "http://192.168.1.20:8000/jerry"

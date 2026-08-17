from __future__ import annotations


def test_root_serves_spa(client):
    r = client.get("/")
    assert r.status_code == 200, r.text
    assert "text/html" in r.headers["content-type"]


def test_static_assets_served(client):
    js = client.get("/static/js/app.js")
    assert js.status_code == 200, js.text
    assert "javascript" in js.headers["content-type"]

    css = client.get("/static/css/styles.css")
    assert css.status_code == 200, css.text
    assert "text/css" in css.headers["content-type"]


def test_api_and_docs_still_reachable(client):
    # API router still mounted (route exists, auth required).
    assert client.get("/api/v1/exercises").status_code == 401

    # Docs / OpenAPI still served alongside the SPA.
    assert client.get("/docs").status_code == 200
    assert client.get("/openapi.json").status_code == 200

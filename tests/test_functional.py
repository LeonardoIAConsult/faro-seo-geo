"""Tests de functional_audit: resolución de rutas, skip, y detección de rotos."""
import functional_audit as fa


def test_skip_non_navegables():
    assert fa.skip("#") is True
    assert fa.skip("mailto:a@b.com") is True
    assert fa.skip("javascript:void(0)") is True
    assert fa.skip("/pagina.html") is False


def test_is_external():
    assert fa.is_external("https://x.com") is True
    assert fa.is_external("//x.com") is True
    assert fa.is_external("/local.html") is False


def test_resolve_local_relative(site):
    html = site / "blog" / "bad-post.html"
    tgt = fa.resolve_local(site, html, "pagina-que-no-existe.html")
    assert tgt.endswith("pagina-que-no-existe.html")
    import os
    assert not os.path.isfile(tgt)   # enlace roto real


def test_resolve_local_existing(site):
    html = site / "blog" / "good-post.html"
    tgt = fa.resolve_local(site, html, "../index.html")
    import os
    assert os.path.isfile(tgt)       # enlace bueno resuelve


def test_vercel_routes_solo_literales(tmp_path):
    # rewrites/redirects literales entran; los patrones regex/param se ignoran
    import json
    (tmp_path / "vercel.json").write_text(json.dumps({
        "rewrites": [{"source": "/feed", "destination": "/feed.xml"},
                     {"source": "/feed/", "destination": "/feed.xml"}],
        "redirects": [{"source": "/blog/feed", "destination": "/feed"},
                      {"source": "/(.*)", "destination": "https://x/$1"},   # comodín -> fuera
                      {"source": "/blog/:slug", "destination": "/b/:slug"}],  # param -> fuera
    }), encoding="utf-8")
    routes = fa.load_vercel_routes(tmp_path)
    assert "/feed" in routes            # /feed y /feed/ colapsan a /feed
    assert "/blog/feed" in routes
    assert "/(.*)" not in routes        # el comodín NO suprime todo
    assert not any(":" in r for r in routes)


def test_is_vercel_route_normaliza():
    routes = {"/feed", "/blog/feed"}
    assert fa.is_vercel_route("/feed", routes) is True
    assert fa.is_vercel_route("/feed/", routes) is True        # trailing slash
    assert fa.is_vercel_route("/feed?x=1", routes) is True     # query
    assert fa.is_vercel_route("/otra", routes) is False


def test_vercel_routes_sin_vercel_json(tmp_path):
    assert fa.load_vercel_routes(tmp_path) == set()


def test_broken_link_detected_in_fixture(site, monkeypatch):
    # corre el audit sin red sobre el fixture y verifica que caza el enlace roto
    import sys
    monkeypatch.setattr(sys, "argv", ["functional_audit.py", "--site", str(site), "--no-net"])
    fa.main()
    import json

    from _common import TMP
    data = json.loads((TMP / "functional_audit.json").read_text(encoding="utf-8"))
    assert data["resumen"]["enlaces_rotos"] >= 1
    assert data["resumen"]["assets_faltantes"] >= 1
    assert data["resumen"]["ctas_vacios"] >= 1

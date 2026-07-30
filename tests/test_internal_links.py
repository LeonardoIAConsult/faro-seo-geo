"""Tests de internal_links: grafo de enlaces, huérfanas, profundidad, contextual."""
import sys

import internal_links as il


def _run(site, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["internal_links.py", "--site", str(site)])
    il.main()
    import json

    from _common import TMP
    return json.loads((TMP / "internal_links.json").read_text(encoding="utf-8"))


def test_graph_metrics(site, monkeypatch):
    data = _run(site, monkeypatch)
    by = {p["url"]: p for p in data["pages"]}
    # index enlaza a good-post (contextual: el <a> está fuera de <article> en index,
    # pero good-post enlaza a index desde dentro de <article>)
    assert by["/blog/good-post.html"]["inlinks"] >= 1     # index lo enlaza
    assert by["/"]["inlinks"] >= 1                          # good-post enlaza a la home
    # good-post tiene el enlace a la home dentro de <article> => contextual
    assert by["/blog/good-post.html"]["ctx_outlinks"] >= 1


def test_orphans_detected(site, monkeypatch):
    data = _run(site, monkeypatch)
    # bad-post y video-post no reciben inlinks => huérfanas
    assert "/blog/bad-post.html" in data["huerfanas"]
    assert "/blog/video-post.html" in data["huerfanas"]


def test_home_not_orphan(site, monkeypatch):
    data = _run(site, monkeypatch)
    assert "/" not in data["huerfanas"]


def test_depth_from_home(site, monkeypatch):
    data = _run(site, monkeypatch)
    by = {p["url"]: p for p in data["pages"]}
    assert by["/"]["depth"] == 0
    assert by["/blog/good-post.html"]["depth"] == 1   # home -> good-post

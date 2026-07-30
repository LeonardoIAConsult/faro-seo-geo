"""Tests de content_brief: términos, canibalización por título, señales sin TODOs."""
import json
import sys

import content_brief as cb
from _common import TMP


def test_keyterms_filters_stopwords():
    t = cb.keyterms("chatbots para restaurantes")
    assert "chatbots" in t and "restaurantes" in t
    assert "para" not in t   # stopword fuera


def test_keyterms_drops_short():
    assert "de" not in cb.keyterms("ia de negocios")


def test_slug():
    assert cb.slug("Marca Personal 2026!") == "marca-personal-2026"


def _run(site, monkeypatch, kw):
    monkeypatch.setattr(sys, "argv", ["content_brief.py", "--keyword", kw, "--site", str(site)])
    cb.main()
    return json.loads((TMP / f"brief_{cb.slug(kw)}.json").read_text(encoding="utf-8"))


def test_canibalizacion_por_titulo(site, monkeypatch):
    # good-post.html se titula "Cómo automatizar tu negocio..." => canibaliza "automatizar"
    b = _run(site, monkeypatch, "automatizar")
    urls = [c["url"] for c in b["canibalizacion"]]
    assert any("good-post" in u for u in urls)
    assert "actualizar" in b["recomendacion"]


def test_keyword_libre(site, monkeypatch):
    b = _run(site, monkeypatch, "criptomonedas")
    assert b["canibalizacion"] == []
    assert b["recomendacion"] == "crear nueva"


def test_no_todos_en_brief(site, monkeypatch):
    b = _run(site, monkeypatch, "automatizar")
    assert "TODO" not in json.dumps(b)
    assert "gsc" in b and "cluster" in b and "enlazado" in b

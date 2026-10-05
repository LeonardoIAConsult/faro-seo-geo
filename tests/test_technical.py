"""Tests de technical_audit: reglas de severidad sobre las señales on-page."""
import onpage_analyze as op
import technical_audit as ta


def _findings(site):
    pages = [op.analyze_page(site, f) for f in op.html_files(site)]
    return ta.audit(pages)


def _issues_for(findings, url_substr):
    return [f for f in findings if url_substr in f["url"]]


def test_bad_post_high_findings(site):
    f = _findings(site)
    bad = " ".join(x["issue"] for x in _issues_for(f, "bad-post"))
    assert "Sin <title>" in bad
    assert "Sin H1" in bad
    assert "JSON-LD inválido" in bad


def test_good_home_no_high(site):
    f = _findings(site)
    home_high = [x for x in _issues_for(f, "/") if x["severity"] == "HIGH" and x["url"] == "/"]
    assert home_high == []


def test_thresholds_from_config():
    # los umbrales vienen de config (R2)
    assert ta.TITLE_MAX == 60
    assert ta.THIN_WORDS == 300


def test_noindex_allowlist_is_tuple():
    assert isinstance(ta.NOINDEX_OK, tuple)


def _page(url, title_len, robots=""):
    # Forma real de una pagina de onpage.json, con valores sanos salvo el title.
    return {"url": url, "file": url.strip("/"), "title": "t" * title_len, "title_len": title_len,
            "meta_robots": robots, "meta_description": "d" * 120, "meta_desc_len": 120,
            "h1": ["h"], "h1_count": 1, "h2_count": 2, "canonical": "https://ej.com" + url,
            "hreflang": [], "lang": "es", "jsonld_types": ["Article"], "word_count": 800,
            "images": 1, "images_no_alt": 0, "images_no_alt_src": [], "og_title": "t",
            "og_image": "x.webp", "twitter_card": "summary", "internal_links": 5,
            "external_links": 1}


def test_title_largo_en_pagina_publica_es_med():
    f = ta.audit([_page("/blog/x.html", 92)])
    assert any("Title largo" in x["issue"] for x in f)


def test_title_corto_en_noindex_no_es_hallazgo():
    # Plantillas de email del embudo: noindex, nunca salen en el buscador (2026-10-04).
    f = ta.audit([_page("/diagnostico/plantillas/email-1.html", 19, "noindex, nofollow")])
    assert not any("Title" in x["issue"] for x in f)

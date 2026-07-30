"""Tests de report_score: score compuesto, renormalización y diff."""
import report_score as rs

ONPAGE = {"pages": [
    {"url": "/", "word_count": 500, "jsonld_types": ["Person"], "images_no_alt": 0},
    {"url": "/blog/a.html", "word_count": 900, "jsonld_types": ["Article"], "images_no_alt": 0},
]}
TECH_CLEAN = {"summary": {"HIGH": 0, "MED": 0, "LOW": 0}}
TECH_BAD = {"summary": {"HIGH": 4, "MED": 5, "LOW": 10}}
FUNC_CLEAN = {"resumen": {"enlaces_rotos": 0, "assets_faltantes": 0, "ctas_vacios": 0}, "forms": []}
FUNC_FORMKO = {"resumen": {"enlaces_rotos": 0, "assets_faltantes": 0, "ctas_vacios": 0},
               "forms": [{"ok": False}]}
SCHEMA_OK = {"json_invalido": 0, "issues": []}
GEO = {"queries": 10, "citado": 2, "tasa_citacion": 0.2}


def test_perfect_is_high():
    r = rs.compute(ONPAGE, TECH_CLEAN, FUNC_CLEAN, SCHEMA_OK, geo=None)
    assert r["score"] >= 95


def test_high_findings_lower_tecnica():
    r = rs.compute(ONPAGE, TECH_BAD, FUNC_CLEAN, SCHEMA_OK)
    assert r["componentes"]["tecnica"] < 60


def test_form_roto_tanks_funcional():
    r = rs.compute(ONPAGE, TECH_CLEAN, FUNC_FORMKO, SCHEMA_OK)
    assert r["componentes"]["funcional"] <= 60
    assert r["metricas"]["forms_rotos"] == 1


def test_geo_missing_renormalizes():
    # sin GEO el score NO se hunde: el peso se reparte entre lo presente
    con = rs.compute(ONPAGE, TECH_CLEAN, FUNC_CLEAN, SCHEMA_OK, GEO)
    sin = rs.compute(ONPAGE, TECH_CLEAN, FUNC_CLEAN, SCHEMA_OK, geo=None)
    assert "geo" not in sin["componentes"]
    assert sin["score"] > con["score"]   # GEO 20/100 arrastra hacia abajo


def test_score_bounds():
    r = rs.compute(ONPAGE, TECH_BAD, FUNC_FORMKO, {"json_invalido": 5, "issues": ["x"] * 10}, GEO)
    assert 0 <= r["score"] <= 100


def test_noindex_pages_excluded_from_content():
    # una página noindex delgada/sin-schema NO debe penalizar el contenido
    onpage = {"pages": [
        {"url": "/", "word_count": 500, "jsonld_types": ["Person"], "images_no_alt": 0},
        {"url": "/legal/x.html", "word_count": 10, "jsonld_types": [], "images_no_alt": 3,
         "meta_robots": "noindex"},
    ]}
    r = rs.compute(onpage, TECH_CLEAN, FUNC_CLEAN, SCHEMA_OK)
    assert r["metricas"]["thin"] == 0        # la noindex no cuenta
    assert r["metricas"]["sin_schema"] == 0
    assert r["componentes"]["contenido"] == 100


def test_channel_audit_flags_third_person():
    import youtube_pull as yp
    item = {"snippet": {"description": "Su objetivo es brindar a sus clientes exito. No dudes en contactarlo."},
            "brandingSettings": {"channel": {"keywords": "ia"}},
            "statistics": {"subscriberCount": "100", "videoCount": "10", "viewCount": "1000"}}
    a = yp.channel_audit(item)
    assert any("3ª persona" in i or "3a persona" in i or "persona" in i for i in a["issues"])


def test_channel_audit_clean():
    import youtube_pull as yp
    item = {"snippet": {"description": "Te enseño IA y automatización para tu negocio, sin tecnicismos. "
                        "Pide tu diagnóstico gratis en https://example.com"},
            "brandingSettings": {"channel": {"keywords": "ia"}},
            "statistics": {"subscriberCount": "100", "videoCount": "10", "viewCount": "1000"}}
    a = yp.channel_audit(item)
    assert a["issues"] == []


def test_render_diff_arrows():
    cur = {"date": "2026-07-28", "score": 83, "componentes": {"tecnica": 91},
           "metricas": {"high": 0, "geo_citado": 2}}
    prev = {"date": "2026-07-21", "score": 79, "componentes": {"tecnica": 88},
            "metricas": {"high": 2, "geo_citado": 1}}
    md = rs.render(cur, prev)
    assert "83/100" in md
    assert "vs 2026-07-21" in md
    assert "HIGH" in md

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

"""Tests de redirect_audit: canónico de host, 302, loops (excluye host), cadenas."""
import redirect_audit as ra

APEX = "ejemplo.com"
WWW = "https://www.ejemplo.com"

CANONICAL = {"source": "/(.*)", "has": [{"type": "host", "value": APEX}],
             "destination": "https://www.ejemplo.com/$1", "permanent": True}


def _types(findings):
    return {f["tipo"] for f in findings}


def test_host_redirect_no_es_loop():
    findings, canon = ra.analyze([CANONICAL], APEX, WWW)
    assert canon is True
    assert "loop" not in _types(findings)
    assert findings == []   # config canónica limpia


def test_falta_canonico():
    findings, canon = ra.analyze([{"source": "/a", "destination": "/b", "permanent": True}],
                                 APEX, WWW)
    assert canon is False
    assert "sin redirect canónico de host" in _types(findings)


def test_temporal_flag():
    findings, _ = ra.analyze([CANONICAL, {"source": "/x", "destination": "/y", "permanent": False}],
                             APEX, WWW)
    assert "redirect temporal (302)" in _types(findings)


def test_loop_relativo():
    findings, _ = ra.analyze([CANONICAL, {"source": "/loop", "destination": "/loop", "permanent": True}],
                             APEX, WWW)
    assert "loop" in _types(findings)


def test_cadena():
    reds = [CANONICAL,
            {"source": "/a", "destination": "/b", "permanent": True},
            {"source": "/b", "destination": "/c", "permanent": True}]
    findings, _ = ra.analyze(reds, APEX, WWW)
    assert "cadena de redirects" in _types(findings)


def test_dest_path_strips_host_and_placeholder():
    assert ra.dest_path("https://www.ejemplo.com/$1") == "/"
    assert ra.dest_path("/feed") == "/feed"

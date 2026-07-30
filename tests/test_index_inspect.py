"""Tests de index_inspect: lógica pura (clasificación de estado + conflicto de canónica
+ agregación). Sin red: no toca la URL Inspection API."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "execution"))

import index_inspect as ii  # noqa: E402


def test_classify_indexed_por_verdict():
    assert ii.classify("Submitted and indexed", "PASS")[0] == "indexed"


def test_classify_indexed_por_coverage():
    assert ii.classify("Indexed", "")[0] == "indexed"


def test_classify_unknown():
    b, motivo = ii.classify("URL is unknown to Google", "NEUTRAL")
    assert b == "unknown"
    assert "unknown" in motivo.lower()


def test_classify_excluded_alternate():
    # una URL del sitemap que Google pliega como alternativa = excluida (accionable)
    assert ii.classify("Alternate page with proper canonical tag", "NEUTRAL")[0] == "excluded"


def test_classify_excluded_crawled_not_indexed():
    assert ii.classify("Crawled - currently not indexed", "NEUTRAL")[0] == "excluded"


def test_classify_excluded_sin_coverage():
    # sin coverageState = no la indexa; motivo con texto por defecto (no vacío)
    b, motivo = ii.classify("", "FAIL")
    assert b == "excluded"
    assert motivo


def test_canonical_conflict_true():
    assert ii.canonical_conflict("https://x.com/a", "https://x.com/b") is True


def test_canonical_conflict_false_igual_con_barra():
    # misma canónica salvo la barra final -> NO es conflicto
    assert ii.canonical_conflict("https://x.com/a/", "https://x.com/a") is False


def test_canonical_conflict_false_si_falta_uno():
    assert ii.canonical_conflict("", "https://x.com/a") is False
    assert ii.canonical_conflict("https://x.com/a", None) is False


def test_summarize_cuenta_buckets_y_problemas():
    rows = [
        {"url": "/a", "bucket": "indexed", "motivo": "ok", "canonical_conflict": False},
        {"url": "/b", "bucket": "excluded", "motivo": "Crawled - not indexed", "canonical_conflict": False},
        {"url": "/c", "bucket": "unknown", "motivo": "unknown", "canonical_conflict": False},
        {"url": "/d", "bucket": "indexed", "motivo": "ok", "canonical_conflict": True,
         "google_canonical": "/x"},
        {"url": "/e", "error": "HTTP 429 quota"},
    ]
    s = ii.summarize(rows)
    assert s["total"] == 5
    assert s["buckets"] == {"indexed": 2, "excluded": 1, "unknown": 1}
    assert s["errores"] == 1
    assert len(s["excluidas"]) == 1
    assert len(s["desconocidas"]) == 1
    assert len(s["conflictos_canonical"]) == 1

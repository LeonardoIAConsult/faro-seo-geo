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


# --- Lote rotativo + estado persistente (2026-09-16) -------------------------------------
# Estos tests cubren el arreglo de la rutina semanal: inspeccionar por trozos SIN que el
# informe crea que el sitio son solo esos trozos, y sin que la alarma compare un trozo
# contra otro distinto. Nada de red: se sustituye `inspect` por una funcion falsa.

import json  # noqa: E402

import pytest  # noqa: E402


class _SvcFalso:
    pass


@pytest.fixture
def motor(tmp_path, monkeypatch):
    """index_inspect apuntando a un sitio de 5 URLs, con disco propio y sin red."""
    urls = [f"https://ej.com/{n}.html" for n in range(1, 6)]
    veredictos = {u: "indexed" for u in urls}

    monkeypatch.setattr(ii, "ROOT", tmp_path)
    monkeypatch.setattr(ii, "site_dir", lambda: tmp_path)
    monkeypatch.setattr(ii, "sitemap_urls", lambda root, limit: list(urls))
    monkeypatch.setattr(ii.gsc_pull, "service", lambda: _SvcFalso())
    monkeypatch.setattr(ii, "time", type("T", (), {"sleep": staticmethod(lambda s: None)}))
    monkeypatch.setenv("GSC_SITE_URL", "sc-domain:ej.com")

    guardado = {}

    def save_json_falso(nombre, data):
        guardado["data"] = data
        (tmp_path / nombre).write_text(json.dumps(data), encoding="utf-8")
        return str(tmp_path / nombre)

    monkeypatch.setattr(ii, "save_json", save_json_falso)

    def inspect_falso(svc, site, url):
        v = veredictos[url]
        if v == "error":
            return {"url": url, "error": "HTTP 429 quota"}
        if v == "boom":
            raise RuntimeError("proceso matado a mitad del lote")
        return {"url": url, "bucket": v, "motivo": v, "verdict": "", "canonical_conflict": False}

    monkeypatch.setattr(ii, "inspect", inspect_falso)

    def correr(*extra):
        monkeypatch.setattr(ii.sys, "argv", ["index_inspect.py", "--delay", "0", *extra])
        ii.main()
        return guardado["data"]

    return {"urls": urls, "veredictos": veredictos, "correr": correr, "disco": tmp_path}


def test_lote_inspecciona_solo_su_trozo_pero_reporta_el_sitio_acumulado(motor):
    d1 = motor["correr"]("--lote", "2")
    assert d1["inspeccionadas_esta_corrida"] == 2
    assert d1["total"] == 2                      # aun no hay veredicto de las otras 3
    assert d1["cobertura_parcial"] is True

    d2 = motor["correr"]("--lote", "2")
    assert d2["inspeccionadas_esta_corrida"] == 2
    assert d2["total"] == 4                      # las 2 de la corrida 1 NO se pierden
    assert set(d2["sin_inspeccionar_nunca"]) == {motor["urls"][4]}


def test_el_lote_da_la_vuelta_y_cubre_el_sitio_entero(motor):
    for _ in range(3):
        d = motor["correr"]("--lote", "2")
    assert d["total"] == 5
    assert d["sin_inspeccionar_nunca"] == []


def test_una_corrida_muerta_no_se_salta_su_lote(motor):
    marcador = motor["disco"] / ".tmp" / "index_inspect_offset.txt"
    motor["veredictos"][motor["urls"][1]] = "boom"
    with pytest.raises(RuntimeError):
        motor["correr"]("--lote", "2")
    # El marcador solo avanza al terminar el lote: si no, esas URLs no se volverian a
    # mirar hasta la vuelta completa (semanas).
    assert not marcador.exists()

    motor["veredictos"][motor["urls"][1]] = "indexed"
    d = motor["correr"]("--lote", "2")
    assert set(r["url"] for r in d["rows"]) == set(motor["urls"][:2])


def test_un_error_de_cuota_no_borra_el_veredicto_anterior(motor):
    motor["correr"]("--lote", "2")
    motor["veredictos"][motor["urls"][0]] = "error"
    for _ in range(3):                       # completa la vuelta y vuelve a la URL 1
        d = motor["correr"]("--lote", "2")
    assert d["buckets"]["indexed"] == 5      # sigue contando como indexada, no desaparece


def test_url_retirada_del_sitemap_sale_del_estado(motor, monkeypatch):
    motor["correr"]("--lote", "5")
    quedan = motor["urls"][:3]
    monkeypatch.setattr(ii, "sitemap_urls", lambda root, limit: list(quedan))
    d = motor["correr"]("--lote", "5")
    assert d["total"] == 3


def test_url_suelta_no_toca_el_estado_del_sitio(motor):
    motor["correr"]("--lote", "5")
    antes = (motor["disco"] / ii.ESTADO).read_text(encoding="utf-8")
    motor["correr"]("--url", motor["urls"][0])
    assert (motor["disco"] / ii.ESTADO).read_text(encoding="utf-8") == antes


# --- Alarma por proporcion, no por cifra bruta -------------------------------------------

def _alerta(tmp_path, monkeypatch, prev, ahora):
    import _common
    import health_check
    monkeypatch.setattr(_common, "ROOT", tmp_path)
    if prev is not None:
        (tmp_path / "index-coverage-history.json").write_text(json.dumps([prev]), encoding="utf-8")
    enviados = []
    monkeypatch.setattr(health_check, "send_telegram", lambda m: enviados.append(m))
    ii._coverage_alert(ahora)
    return enviados


def _snap(total, no_indexadas):
    return {"total": total,
            "buckets": {"indexed": total - no_indexadas, "excluded": no_indexadas, "unknown": 0},
            "excluidas": [{"url": "https://ej.com/x.html"}], "desconocidas": [],
            "inspeccionadas_esta_corrida": 2}


def test_no_alarma_cuando_solo_crece_el_denominador(tmp_path, monkeypatch):
    # El sitio va MEJOR (20% -> 15%) pero la cifra bruta subio de 2 a 3 porque hay mas
    # URLs medidas. Con la comparacion vieja esto disparaba una alarma falsa cada lunes.
    prev = {"date": "2026-09-08", "total": 10, "not_indexed": 2, "tasa_no_indexadas": 0.2}
    assert _alerta(tmp_path, monkeypatch, prev, _snap(20, 3)) == []


def test_alarma_cuando_empeora_de_verdad(tmp_path, monkeypatch):
    prev = {"date": "2026-09-08", "total": 10, "not_indexed": 2, "tasa_no_indexadas": 0.2}
    enviados = _alerta(tmp_path, monkeypatch, prev, _snap(10, 5))
    assert len(enviados) == 1
    assert "EMPEORO" in enviados[0]


def test_historial_viejo_sin_tasa_sigue_sirviendo(tmp_path, monkeypatch):
    # Entradas anteriores a este cambio no tienen 'tasa_no_indexadas': se deduce de sus cifras.
    prev = {"date": "2026-09-01", "total": 10, "not_indexed": 2}
    assert len(_alerta(tmp_path, monkeypatch, prev, _snap(10, 6))) == 1


def test_consulta_puntual_no_pisa_el_archivo_del_sitio(motor, monkeypatch):
    """Una URL suelta no puede dejar el informe creyendo que el sitio tiene 1 pagina."""
    escritos = []
    orig = ii.save_json

    def espia(nombre, data):
        escritos.append(nombre)
        return orig(nombre, data)

    monkeypatch.setattr(ii, "save_json", espia)
    motor["correr"]("--lote", "5")
    motor["correr"]("--url", motor["urls"][0])
    assert escritos == ["index_inspect.json", "index_inspect_url.json"]

"""Tests de health_check: lógica pura de veredicto (last_two, evaluate, verdict). Sin red."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "execution"))

import health_check as hc  # noqa: E402


def _snap(score, **metricas):
    return {"date": "2026-07-30", "score": score, "metricas": metricas}


def test_last_two():
    hist = {"snapshots": [{"date": "a"}, {"date": "b"}, {"date": "c"}]}
    cur, prev = hc.last_two(hist)
    assert cur["date"] == "c" and prev["date"] == "b"


def test_last_two_vacio_o_uno():
    assert hc.last_two({"snapshots": []}) == (None, None)
    assert hc.last_two(None) == (None, None)
    cur, prev = hc.last_two({"snapshots": [{"date": "a"}]})
    assert cur["date"] == "a" and prev is None


def test_evaluate_sin_cur_es_rojo():
    f = hc.evaluate(None, None)
    assert len(f) == 1 and f[0]["sev"] == "ROJO"


def test_evaluate_sano_no_findings():
    cur = _snap(90, high=0, forms_rotos=0, schema_invalido=0, enlaces_rotos=0, geo_citado=2)
    prev = _snap(90, high=0, geo_citado=2)
    assert hc.evaluate(cur, prev) == []
    assert hc.verdict([]) == "SANO"


def test_evaluate_rojo_high_y_form():
    cur = _snap(70, high=2, forms_rotos=1, schema_invalido=0, enlaces_rotos=0)
    f = hc.evaluate(cur, None)
    sevs = [x["sev"] for x in f]
    assert sevs == ["ROJO", "ROJO"]
    assert hc.verdict(f) == "DEGRADADO"


def test_evaluate_schema_y_enlaces_rotos():
    cur = _snap(80, schema_invalido=1, enlaces_rotos=3)
    msgs = " ".join(x["msg"] for x in hc.evaluate(cur, None))
    assert "schema" in msgs.lower() and "enlace" in msgs.lower()


def test_evaluate_regresion_score():
    cur = _snap(80, high=0)
    prev = _snap(85, high=0)
    f = hc.evaluate(cur, prev, score_drop=3)
    assert any(x["sev"] == "REGRESION" and "cayó" in x["msg"] for x in f)


def test_evaluate_caida_menor_al_umbral_no_alarma():
    cur = _snap(83, high=0)
    prev = _snap(85, high=0)  # cae 2, umbral 3 -> no alarma
    assert hc.evaluate(cur, prev, score_drop=3) == []


def test_evaluate_geo_baja():
    cur = _snap(85, high=0, geo_citado=1)
    prev = _snap(85, high=0, geo_citado=3)
    assert any("Citación IA" in x["msg"] for x in hc.evaluate(cur, prev))


def test_evaluate_conflicto_canonica():
    cur = _snap(85, high=0)
    index = {"conflictos_canonical": [{"url": "/a"}, {"url": "/b"}]}
    f = hc.evaluate(cur, None, index=index)
    assert any("canónica" in x["msg"] for x in f) and hc.verdict(f) == "DEGRADADO"


def test_evaluate_backlinks_bajan():
    cur = _snap(85, high=0)
    f = hc.evaluate(cur, None, bl_cur={"total_backlinks": 2}, bl_prev={"total_backlinks": 5})
    assert any("Backlinks bajaron" in x["msg"] for x in f)


def test_evaluate_backlinks_suben_no_alarma():
    cur = _snap(85, high=0)
    f = hc.evaluate(cur, None, bl_cur={"total_backlinks": 5}, bl_prev={"total_backlinks": 2})
    assert f == []


# --- Datos viejos y accesos de Google vencidos (2026-10-04) --------------------------------
# El tablero dijo SANO del 28-sep al 4-oct con Search Console congelado en el 16-sep y los
# tres tokens de Google muertos. Estas pruebas fijan que eso ahora es ROJO.

def test_stale_rojo_si_pasa_el_maximo():
    f = hc.stale_findings({"Search Console": 16.2, "YouTube": 3.0}, 9)
    assert len(f) == 1 and f[0]["sev"] == "ROJO" and "Search Console" in f[0]["msg"]
    assert hc.verdict(f) == "DEGRADADO"


def test_stale_en_el_limite_no_alarma():
    assert hc.stale_findings({"Bing": 9.0}, 9) == []


def test_stale_fuente_no_configurada_se_salta():
    assert hc.stale_findings({"Google Analytics": None}, 9) == []


def test_token_muerto_es_rojo(tmp_path, monkeypatch):
    monkeypatch.setattr(hc, "ROOT", tmp_path)
    for name in hc.TOKENS.values():
        (tmp_path / name).write_text("{}", encoding="utf-8")
    estados = {"token.json": False, "ga4_token.json": True, "youtube_token.json": None}
    f = hc.token_findings(probe=lambda p: estados[p.name])
    assert len(f) == 1 and "Search Console" in f[0]["msg"] and "reautorizar.py" in f[0]["msg"]


def test_token_ausente_no_alarma(tmp_path, monkeypatch):
    monkeypatch.setattr(hc, "ROOT", tmp_path)
    assert hc.token_findings(probe=lambda p: False) == []


def test_data_ages_lee_mtime_y_fecha_de_backlinks(tmp_path, monkeypatch):
    import os
    import time
    from datetime import date
    monkeypatch.setattr(hc, "TMP", tmp_path)
    monkeypatch.setattr(hc, "BACKLINK_HIST", tmp_path / "bh.json")
    viejo = tmp_path / hc.SOURCES["Search Console"]
    viejo.write_text("{}", encoding="utf-8")
    hace10 = time.time() - 10 * 86400
    os.utime(viejo, (hace10, hace10))
    (tmp_path / "bh.json").write_text('{"snapshots": [{"date": "2026-09-21"}]}', encoding="utf-8")
    ages = hc.data_ages(today=date(2026, 10, 4))
    assert 9.9 < ages["Search Console"] < 10.1
    assert ages["Google Analytics"] is None
    assert ages["Backlinks"] == 13


def _probe_con(monkeypatch, exc):
    from google.oauth2.credentials import Credentials

    def boom(self, request):
        raise exc
    monkeypatch.setattr(Credentials, "refresh", boom)


def _token(tmp_path, refresh=True):
    # Token FALSO serializado por la propia libreria (valores de una letra). Asi el archivo de
    # prueba no imita a mano la forma de un token real, que el escaner de faro-sync bloquea.
    from google.oauth2.credentials import Credentials
    c = Credentials(token="z", refresh_token="r" if refresh else None,
                    client_id="x", client_secret="y", token_uri="https://oauth2.googleapis.com/token")
    p = tmp_path / "t.json"
    p.write_text(c.to_json(), encoding="utf-8")
    if not refresh:  # to_json deja la clave en null; un token sin ella es el caso real a probar
        import json
        d = {k: v for k, v in json.loads(p.read_text(encoding="utf-8")).items() if v is not None}
        p.write_text(json.dumps(d), encoding="utf-8")
    return p


def test_probe_invalid_grant_es_muerto(tmp_path, monkeypatch):
    from google.auth.exceptions import RefreshError
    _probe_con(monkeypatch, RefreshError("invalid_grant"))
    assert hc._probe_token(_token(tmp_path)) is False


def test_probe_5xx_429_no_es_token_muerto(tmp_path, monkeypatch):
    from google.auth.exceptions import RefreshError
    _probe_con(monkeypatch, RefreshError("503", retryable=True))
    assert hc._probe_token(_token(tmp_path)) is None


def test_probe_sin_red_se_salta(tmp_path, monkeypatch):
    from google.auth.exceptions import TransportError
    _probe_con(monkeypatch, TransportError("sin red"))
    assert hc._probe_token(_token(tmp_path)) is None


def test_probe_sin_refresh_token_no_sirve(tmp_path):
    assert hc._probe_token(_token(tmp_path, refresh=False)) is False


def test_hollow_geo_sin_motor_e_indice_todo_fallido():
    f = hc.hollow_findings({"engines": []}, {"inspeccionadas_esta_corrida": 40, "errores": 40})
    assert len(f) == 2 and all(x["sev"] == "ROJO" for x in f)
    assert hc.hollow_findings({"engines": ["gemini"]},
                              {"inspeccionadas_esta_corrida": 40, "errores": 3}) == []


def test_main_cablea_edad_y_tokens(tmp_path, monkeypatch):
    # Sin este cableado las funciones de arriba existen y nadie las llama (paso 28-sep).
    import os
    import time
    monkeypatch.setattr(hc, "TMP", tmp_path)
    monkeypatch.setattr(hc, "HEALTH_MD", tmp_path / "hs.md")
    monkeypatch.setattr(hc, "REPORT_HIST", tmp_path / "rh.json")
    monkeypatch.setattr(hc, "BACKLINK_HIST", tmp_path / "bh.json")
    (tmp_path / "rh.json").write_text('{"snapshots": [{"date": "x", "score": 90, "metricas": {}}]}',
                                      encoding="utf-8")
    viejo = tmp_path / hc.SOURCES["Bing"]
    viejo.write_text("{}", encoding="utf-8")
    hace20 = time.time() - 20 * 86400
    os.utime(viejo, (hace20, hace20))
    monkeypatch.setattr(hc, "token_findings", lambda: [{"sev": "ROJO", "msg": "token"}])
    enviados = []
    monkeypatch.setattr(hc, "send_telegram", lambda m: enviados.append(m))
    monkeypatch.setattr(sys, "argv", ["health_check.py", "--no-build"])
    assert hc.main() == 1
    assert "Bing" in enviados[0] and "token" in enviados[0]


def test_sources_son_los_archivos_que_lee_el_informe():
    # Un nombre mal escrito aqui deja la fuente sin vigilar y ninguna otra prueba lo ve.
    informe = (Path(hc.__file__).with_name("report_build.py")).read_text(encoding="utf-8")
    for fname in hc.SOURCES.values():
        assert f'load("{fname}")' in informe, fname


def test_drift_rojo_si_la_copia_va_atrasada_o_divergida():
    assert hc.drift_findings(3, 0)[0]["sev"] == "ROJO"
    assert hc.drift_findings(0, 1) == []  # adelante = sin publicar, no viejo
    assert hc.drift_findings(0, 0) == []
    assert hc.drift_findings(None, None) == []


def test_site_drift_con_repo_git_real(tmp_path, monkeypatch):
    # Si el rev-list se escribe mal, site_drift devuelve (None, None) y la vigilancia se apaga
    # en silencio; la prueba pura no lo ve (REVISOR B6).
    import subprocess

    def g(cwd, *a):
        subprocess.run(["git", "-C", str(cwd), *a], check=True, capture_output=True)

    def commit(repo, archivo, texto, msg):
        (repo / archivo).write_text(texto)
        g(repo, "add", archivo)
        g(repo, "commit", "-qm", msg)

    remoto, local, otro = tmp_path / "remoto.git", tmp_path / "local", tmp_path / "otro"
    g(tmp_path, "init", "-q", "--bare", "-b", "main", str(remoto))
    for repo in (local, otro):
        g(tmp_path, "clone", "-q", str(remoto), str(repo))
        g(repo, "config", "user.email", "t@t")
        g(repo, "config", "user.name", "t")
    commit(local, "a", "0", "base")
    g(local, "push", "-q", "origin", "HEAD:main")
    g(otro, "pull", "-q", "origin", "main")
    commit(otro, "b", "1", "r1")
    commit(otro, "b", "2", "r2")
    g(otro, "push", "-q", "origin", "HEAD:main")
    commit(local, "c", "x", "local")
    g(local, "fetch", "-q", "origin")
    monkeypatch.setattr(hc, "site_dir", lambda: local)
    assert hc.site_drift() == (2, 1)


def test_critical_css_rojo_si_style_cambio():
    import hashlib
    css = "a{color:red}\n"
    h = hashlib.sha256(css.encode()).hexdigest()[:16]
    html = f"<!-- critical-css:start style.css sha256:{h} — x -->"
    assert hc.critical_css_findings(html, css) == []
    assert hc.critical_css_findings(html, css.replace("\n", "\r\n")) == []  # CRLF no cuenta
    assert hc.critical_css_findings(html, css + "b{}")[0]["sev"] == "ROJO"
    assert hc.critical_css_findings("<html>sin marcador</html>", css) == []


def test_main_sin_sitio_configurado_no_se_cae(tmp_path, monkeypatch):
    # Instalacion nueva de Faro: site_dir() hace SystemExit. Los chequeos opcionales del sitio
    # (copia desfasada, CSS critico) no pueden tumbar el health entero (Verify de Faro, 4-oct).
    monkeypatch.setattr(hc, "TMP", tmp_path)
    monkeypatch.setattr(hc, "HEALTH_MD", tmp_path / "hs.md")
    monkeypatch.setattr(hc, "REPORT_HIST", tmp_path / "rh.json")
    monkeypatch.setattr(hc, "BACKLINK_HIST", tmp_path / "bh.json")
    (tmp_path / "rh.json").write_text('{"snapshots": [{"date": "x", "score": 90, "metricas": {}}]}',
                                      encoding="utf-8")

    def sin_sitio():
        raise SystemExit("sin sitio")
    monkeypatch.setattr(hc, "site_dir", sin_sitio)
    monkeypatch.setattr(hc, "token_findings", lambda: [])
    monkeypatch.setattr(hc, "send_telegram", lambda m: None)
    # --no-build: es el caso que tumbaba el health en Faro (el chequeo del CSS critico corria
    # tambien sin build y llamaba a site_dir). Con build, report_build ya avisa "configura tu sitio".
    monkeypatch.setattr(sys, "argv", ["health_check.py", "--no-build", "--no-tokens"])
    assert hc.main() == 0

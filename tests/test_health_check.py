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

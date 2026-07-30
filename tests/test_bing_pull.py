"""Tests de bing_pull: lógica pura (parseo de fecha WCF, agregación de tráfico,
orden de queries). Sin red: no toca la API de Bing."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "execution"))

import bing_pull as bp  # noqa: E402


def test_parse_ms_date_simple():
    # 1690000000000 ms = 2023-07-22 UTC
    assert bp.parse_ms_date("/Date(1690000000000)/") == "2023-07-22"


def test_parse_ms_date_con_offset():
    assert bp.parse_ms_date("/Date(1690000000000-0700)/") == "2023-07-22"


def test_parse_ms_date_invalida():
    assert bp.parse_ms_date("no-fecha") is None
    assert bp.parse_ms_date(None) is None
    assert bp.parse_ms_date(12345) is None


def test_summarize_traffic_suma_y_ctr():
    rows = [{"Impressions": 100, "Clicks": 5}, {"Impressions": 300, "Clicks": 15}]
    s = bp.summarize_traffic(rows)
    assert s["dias"] == 2
    assert s["impresiones"] == 400
    assert s["clics"] == 20
    assert s["ctr"] == 0.05


def test_summarize_traffic_sin_impresiones_no_divide_por_cero():
    s = bp.summarize_traffic([{"Impressions": 0, "Clicks": 0}])
    assert s["ctr"] == 0.0


def test_summarize_traffic_valores_none():
    s = bp.summarize_traffic([{"Impressions": None, "Clicks": None}])
    assert s["impresiones"] == 0 and s["clics"] == 0


def test_top_queries_ordena_por_impresiones():
    rows = [
        {"Query": "a", "Impressions": 10, "Clicks": 1, "AvgImpressionPosition": 8},
        {"Query": "b", "Impressions": 50, "Clicks": 3, "AvgImpressionPosition": 2},
        {"Query": "c", "Impressions": 30, "Clicks": 0, "AvgImpressionPosition": 5},
    ]
    top = bp.top_queries(rows)
    assert [q["query"] for q in top] == ["b", "c", "a"]
    assert top[0]["impresiones"] == 50
    assert top[0]["pos_impresion"] == 2


def test_top_queries_respeta_n():
    rows = [{"Query": str(i), "Impressions": i} for i in range(30)]
    assert len(bp.top_queries(rows, n=5)) == 5


def test_normalize_links_shape_dict():
    d = {"Links": [{"Url": "/a", "Count": 2}, {"Url": "/b", "Count": 5}]}
    norm = bp.normalize_links(d)
    assert [x["url"] for x in norm] == ["/b", "/a"]  # orden por count desc
    assert norm[0]["count"] == 5


def test_normalize_links_shape_lista():
    norm = bp.normalize_links([{"Url": "/a", "Count": None}])
    assert norm == [{"url": "/a", "count": 0}]  # None -> 0


def test_normalize_links_shape_desconocida():
    assert bp.normalize_links("basura") == []
    assert bp.normalize_links({"otra": 1}) == []

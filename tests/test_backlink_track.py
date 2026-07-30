"""Tests de backlink_track: lógica pura (suma, snapshot, prev, diff). Sin red."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "execution"))

import backlink_track as bt  # noqa: E402


def test_total_backlinks_suma():
    links = [{"url": "/a", "count": 3}, {"url": "/b", "count": 5}]
    assert bt.total_backlinks(links) == 8


def test_total_backlinks_none_y_cero():
    assert bt.total_backlinks([{"url": "/a", "count": None}, {"url": "/b", "count": 0}]) == 0
    assert bt.total_backlinks([]) == 0


def test_snapshot_cuenta_solo_paginas_con_enlaces():
    links = [{"url": "/a", "count": 2}, {"url": "/b", "count": 0}, {"url": "/c", "count": 1}]
    snap = bt.snapshot_from_links(links, "2026-07-30")
    assert snap["total_backlinks"] == 3
    assert snap["paginas_enlazadas"] == 2  # /b tiene 0, no cuenta
    assert snap["por_pagina"] == {"/a": 2, "/b": 0, "/c": 1}
    assert snap["date"] == "2026-07-30"


def test_snapshot_ignora_url_vacia():
    snap = bt.snapshot_from_links([{"url": None, "count": 5}, {"url": "/a", "count": 1}], "2026-07-30")
    assert snap["por_pagina"] == {"/a": 1}
    # total NO cuenta la entrada con url falsy (consistente con por_pagina/paginas_enlazadas)
    assert snap["total_backlinks"] == 1
    assert snap["paginas_enlazadas"] == 1


def test_total_backlinks_excluye_url_falsy():
    assert bt.total_backlinks([{"url": None, "count": 5}, {"url": "/a", "count": 2}]) == 2


def test_find_prev_salta_hoy():
    snaps = [{"date": "2026-07-28"}, {"date": "2026-07-29"}, {"date": "2026-07-30"}]
    assert bt.find_prev(snaps, "2026-07-30")["date"] == "2026-07-29"


def test_find_prev_sin_previo():
    assert bt.find_prev([{"date": "2026-07-30"}], "2026-07-30") is None
    assert bt.find_prev([], "2026-07-30") is None


def test_diff_delta_y_paginas_nuevas():
    prev = {"total_backlinks": 0, "por_pagina": {}}
    cur = {"total_backlinks": 4, "por_pagina": {"/a": 3, "/b": 1}}
    dd = bt.diff_snapshots(prev, cur)
    assert dd["delta_total"] == 4
    assert dd["paginas_nuevas"] == ["/a", "/b"]
    assert dd["paginas_perdidas"] == []
    assert dd["cambios_conteo"] == []


def test_diff_paginas_perdidas_y_cambios():
    prev = {"total_backlinks": 5, "por_pagina": {"/a": 3, "/b": 2}}
    cur = {"total_backlinks": 6, "por_pagina": {"/a": 6}}
    dd = bt.diff_snapshots(prev, cur)
    assert dd["delta_total"] == 1
    assert dd["paginas_perdidas"] == ["/b"]  # /b desapareció
    assert dd["cambios_conteo"] == [{"url": "/a", "antes": 3, "ahora": 6, "delta": 3}]


def test_diff_cambios_ordenados_por_magnitud():
    prev = {"total_backlinks": 10, "por_pagina": {"/a": 5, "/b": 5}}
    cur = {"total_backlinks": 17, "por_pagina": {"/a": 6, "/b": 11}}
    dd = bt.diff_snapshots(prev, cur)
    assert dd["cambios_conteo"][0]["url"] == "/b"  # delta +6 antes que /a delta +1

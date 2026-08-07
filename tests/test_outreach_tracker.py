"""Tests de outreach_tracker: lógica pura (add/advance/funnel). Sin red ni I/O."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "execution"))

import outreach_tracker as ot  # noqa: E402


def test_add_crea_target_en_idea():
    targets = ot.add_target([], "Contxto", "medio", "2026-07-31", nota="pitch dato 125")
    assert len(targets) == 1
    t = targets[0]
    assert t["id"] == 1
    assert t["objetivo"] == "Contxto"
    assert t["tipo"] == "medio"
    assert t["estado"] == "idea"
    assert t["fecha_actualizado"] == "2026-07-31"
    assert t["nota"] == "pitch dato 125"


def test_add_id_autoincremental():
    t1 = ot.add_target([], "A", "medio", "2026-07-31")
    t2 = ot.add_target(t1, "B", "podcast", "2026-07-31")
    assert [t["id"] for t in t2] == [1, 2]


def test_add_tipo_invalido():
    with pytest.raises(ValueError, match="tipo inválido"):
        ot.add_target([], "X", "revista", "2026-07-31")


def test_advance_cambia_estado_y_fecha():
    targets = ot.add_target([], "Contxto", "medio", "2026-07-31")
    out = ot.advance(targets, 1, "enviado", "2026-08-05")
    assert out[0]["estado"] == "enviado"
    assert out[0]["fecha_actualizado"] == "2026-08-05"
    # no muta el original
    assert targets[0]["estado"] == "idea"


def test_advance_ganado_sin_url_falla():
    targets = ot.add_target([], "Contxto", "medio", "2026-07-31")
    with pytest.raises(ValueError, match="exige --url"):
        ot.advance(targets, 1, "ganado", "2026-08-05")


def test_advance_ganado_con_url_guarda_url():
    targets = ot.add_target([], "Contxto", "medio", "2026-07-31")
    out = ot.advance(targets, 1, "ganado", "2026-08-05", url="https://contxto.com/x")
    assert out[0]["estado"] == "ganado"
    assert out[0]["url_conseguida"] == "https://contxto.com/x"


def test_advance_estado_invalido():
    targets = ot.add_target([], "Contxto", "medio", "2026-07-31")
    with pytest.raises(ValueError, match="estado inválido"):
        ot.advance(targets, 1, "publicado", "2026-08-05")


def test_advance_id_inexistente():
    targets = ot.add_target([], "Contxto", "medio", "2026-07-31")
    with pytest.raises(ValueError, match="no existe target"):
        ot.advance(targets, 99, "enviado", "2026-08-05")


def test_advance_conserva_nota_si_no_se_pasa():
    targets = ot.add_target([], "Contxto", "medio", "2026-07-31", nota="original")
    out = ot.advance(targets, 1, "enviado", "2026-08-05")
    assert out[0]["nota"] == "original"


def test_funnel_cuenta_por_estado():
    targets = []
    targets = ot.add_target(targets, "A", "medio", "2026-07-31")
    targets = ot.add_target(targets, "B", "podcast", "2026-07-31")
    targets = ot.add_target(targets, "C", "perfil", "2026-07-31")
    targets = ot.advance(targets, 1, "enviado", "2026-08-01")
    targets = ot.advance(targets, 2, "ganado", "2026-08-01", url="https://b.com")
    f = ot.funnel(targets)
    assert f["conteo"]["idea"] == 1     # C sigue en idea
    assert f["conteo"]["enviado"] == 1  # A
    assert f["conteo"]["ganado"] == 1   # B
    assert f["total"] == 3


def test_funnel_conversion_y_urls_ganadas():
    targets = []
    targets = ot.add_target(targets, "A", "medio", "2026-07-31")
    targets = ot.add_target(targets, "B", "podcast", "2026-07-31")
    targets = ot.advance(targets, 1, "enviado", "2026-08-01")
    targets = ot.advance(targets, 2, "ganado", "2026-08-01", url="https://b.com/post")
    f = ot.funnel(targets)
    # contactados = enviado(1) + respondio(0) + ganado(1) = 2; conversión = 1/2
    assert f["contactados"] == 2
    assert f["conversion"] == 0.5
    assert f["urls_ganadas"] == ["https://b.com/post"]


def test_funnel_conversion_cero_sin_contactados():
    targets = ot.add_target([], "A", "medio", "2026-07-31")
    f = ot.funnel(targets)
    assert f["conversion"] == 0.0
    assert f["urls_ganadas"] == []

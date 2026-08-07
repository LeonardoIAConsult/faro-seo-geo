#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
citation_kit.py — genera snippets LISTOS PARA PEGAR de las cifras del Informe
Diagnóstico E&E 2026 del dueño, cada uno con la cifra + atribución + enlace
canónico, en HTML y Markdown.

Objetivo: que CADA mención de una cifra (en la comunidad, un guest post o
LinkedIn) se convierta en un backlink consistente al informe + una señal GEO
(la IA ve la cifra siempre atada a la misma fuente y URL). Determinista, sin red.

Los datos son la ÚNICA fuente autorizada y viven en `citation-kit-data.json`
en la raíz del repo (datos, no código → editable). El script LEE ese JSON; no
hardcodea las cifras. Guardarraíl anti-invención: si el archivo falta, si no hay
`url_canonica`, o si una stat no trae cifra → NO se emite ese snippet (nunca se
inventa una cifra ni un enlace).

Salidas (a .tmp/):
  - citation-kit.md    bloques Markdown listos para pegar (frase + fuente enlazada).
  - citation-kit.html  snippets HTML embebibles (<blockquote> con la cifra en <strong>).
  - citation-kit.json  estructura con los snippets generados (para consumo de otros scripts).

Uso:
  python execution/citation_kit.py
"""
import html as htmllib
import json
import sys
from pathlib import Path

from _common import ROOT, save_json

# Archivo de datos autorizado (datos, no código → editable a mano).
DATA_FILE = ROOT / "citation-kit-data.json"


def load_data(path: Path = DATA_FILE) -> dict:
    """Lee el JSON de datos autorizado. Falla claro si no existe (guardarraíl:
    sin datos no se emite nada, para no inventar cifras)."""
    if not Path(path).exists():
        raise SystemExit(f"ERROR: falta el archivo de datos {path}. No se emite nada (anti-invención).")
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_snippets(data: dict) -> list:
    """Función pura: convierte el dict de datos en una lista de snippets renderizados.

    Cada snippet lleva: id, cifra, texto, y las variantes md/html ya con la
    cifra + atribución + enlace canónico. Guardarraíles:
      - sin `url_canonica` en el dict → error claro (cada snippet SIEMPRE enlaza).
      - una stat sin `cifra` o sin `texto` → se omite (no se inventa).
    """
    url = (data.get("url_canonica") or "").strip()
    if not url:
        raise SystemExit("ERROR: falta 'url_canonica' en los datos. Sin enlace no se emite (regla dura).")

    fuente = (data.get("fuente") or "").strip()
    atribucion = (data.get("atribucion") or "").strip()

    snippets = []
    for stat in data.get("stats", []):
        cifra = (stat.get("cifra") or "").strip()
        texto = (stat.get("texto") or "").strip()
        if not cifra or not texto:
            # Guardarraíl anti-invención: stat incompleta → no se emite.
            continue
        snippets.append({
            "id": stat.get("id", ""),
            "cifra": cifra,
            "texto": texto,
            "md": render_md(cifra, texto, fuente, url, atribucion),
            "html": render_html(cifra, texto, fuente, url, atribucion),
        })
    return snippets


def render_md(cifra: str, texto: str, fuente: str, url: str, atribucion: str) -> str:
    """Bloque Markdown para pegar: la frase con la cifra + fuente enlazada."""
    frase = f"**{cifra}** {texto}"
    cita = f"(Fuente: [{fuente}]({url}) · {atribucion})"
    return f"{frase} {cita}"


def render_html(cifra: str, texto: str, fuente: str, url: str, atribucion: str) -> str:
    """Snippet HTML embebible e inline-safe: cifra en <strong>, fuente en <cite><a>."""
    c = htmllib.escape(cifra)
    t = htmllib.escape(texto)
    f = htmllib.escape(fuente)
    u = htmllib.escape(url, quote=True)
    a = htmllib.escape(atribucion)
    return (
        f'<blockquote><p><strong>{c}</strong> {t} '
        f'<cite><a href="{u}">{f}</a> · {a}</cite></p></blockquote>'
    )


def compose_md(data: dict, snippets: list) -> str:
    """Documento .md completo: nota de uso (encuadre) arriba + un bloque por stat."""
    lines = ["# Citation Kit — Informe Diagnóstico E&E 2026", ""]
    encuadre = (data.get("encuadre") or "").strip()
    if encuadre:
        lines += ["> **Nota de uso (encuadre):** " + encuadre, ""]
    lines += ["Cada bloque ya incluye la cifra + la fuente enlazada. Copia y pega tal cual.", ""]
    for s in snippets:
        lines += [s["md"], ""]
    return "\n".join(lines).rstrip() + "\n"


def compose_html(data: dict, snippets: list) -> str:
    """Documento .html completo: encuadre como comentario + un snippet por stat."""
    parts = []
    encuadre = (data.get("encuadre") or "").strip()
    if encuadre:
        parts.append(f"<!-- Encuadre: {htmllib.escape(encuadre)} -->")
    for s in snippets:
        parts.append(s["html"])
    return "\n".join(parts) + "\n"


def main():
    data = load_data()
    snippets = build_snippets(data)
    if not snippets:
        print("0 snippets: los datos no tienen stats válidas (con cifra + texto). Nada que emitir.")
        return 0

    (ROOT / ".tmp" / "citation-kit.md").write_text(compose_md(data, snippets), encoding="utf-8")
    (ROOT / ".tmp" / "citation-kit.html").write_text(compose_html(data, snippets), encoding="utf-8")
    save_json("citation-kit.json", {
        "fuente": data.get("fuente", ""),
        "url_canonica": data.get("url_canonica", ""),
        "atribucion": data.get("atribucion", ""),
        "encuadre": data.get("encuadre", ""),
        "snippets": snippets,
    })

    print(f"{len(snippets)} snippets generados en .tmp/ (citation-kit.md / .html / .json).")
    return 0


if __name__ == "__main__":
    sys.exit(main())

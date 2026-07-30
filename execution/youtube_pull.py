#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
youtube_pull.py — extrae los videos del canal de YouTube + senales SEO (Capa 3).

YouTube = 2o buscador del mundo y cada vez lo citan Google + las IA. Este script trae
los ultimos videos del canal con su metadata (titulo, descripcion, tags, stats) y calcula
senales de auditoria basicas. La IA (directiva youtube_audit.md) sugiere mejoras en la voz.

Requiere (gratis):
  - YT_API_KEY en .env   -> clave de API de YouTube Data API v3 (Google Cloud Console).
  - YT_CHANNEL_ID en .env -> id del canal (el dueño: YOUR_CHANNEL_ID).

Salida: .tmp/youtube.json  (videos + senales).
Uso:
  python execution/youtube_pull.py [--max 25]
"""
import os
import sys

from _common import cfg, save_json  # carga .env + config

API = "https://www.googleapis.com/youtube/v3"


def arg(name, default=None):
    for i, a in enumerate(sys.argv):
        if a == name and i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return default


def get(url, params):
    import requests
    r = requests.get(url, params=params, timeout=30)
    if r.status_code != 200:
        raise SystemExit(f"YouTube API {r.status_code}: {r.text[:300]}")
    return r.json()


def iso_seconds(dur):
    """Duracion ISO-8601 (PT#H#M#S) -> segundos. '' -> 0."""
    import re
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", dur or "")
    if not m:
        return 0
    h, mi, s = (int(x) if x else 0 for x in m.groups())
    return h * 3600 + mi * 60 + s


def signals(v):
    sn = v.get("snippet", {})
    st = v.get("statistics", {})
    title = sn.get("title", "")
    desc = sn.get("description", "")
    tags = sn.get("tags", []) or []
    first_lines = "\n".join(desc.splitlines()[:3])
    secs = iso_seconds(v.get("contentDetails", {}).get("duration", ""))
    is_short = "#shorts" in title.lower() or (0 < secs <= 60)
    issues = []
    if not (20 <= len(title) <= 70):
        issues.append(f"titulo {len(title)} chars (ideal 20-70)")
    if len(desc) < 200:
        issues.append("descripcion corta (<200) — amplia con contexto, keywords y CTA")
    if len(tags) < 3:
        issues.append("pocos tags (<3)")
    if "http" not in first_lines:
        issues.append("sin link en las primeras 3 lineas de la descripcion")
    # capitulos: no aplican a Shorts (<=60s) -> se omite ahi (evita falso positivo)
    if not is_short and "\n0:00" not in desc and "0:00" not in first_lines and "capitulo" not in desc.lower():
        issues.append("sin capitulos/timestamps (mejoran retencion y rich results)")
    return {
        "id": v.get("id"), "title": title, "title_len": len(title),
        "desc_len": len(desc), "tags": len(tags), "published": sn.get("publishedAt", ""),
        "views": int(st.get("viewCount", 0)), "likes": int(st.get("likeCount", 0)),
        "duration_s": secs, "is_short": is_short,
        "url": f"https://www.youtube.com/watch?v={v.get('id')}",
        "issues": issues,
    }


def channel_audit(item):
    """Audita el CANAL (no solo los videos): la descripción es tu 'meta description'
    de canal + la ven Google y la IA. Detecta genérico/3ª persona, sin link, sin CTA."""
    sn = item.get("snippet", {})
    bs = item.get("brandingSettings", {}).get("channel", {})
    st = item.get("statistics", {})
    desc = sn.get("description", "")
    dl = desc.lower()
    niche = ["ia", "inteligencia artificial", "automatiz", "pyme", "emprend", "negocio"]
    issues = []
    if len(desc) < 100:
        issues.append("descripcion del canal muy corta (<100) — es tu carta de presentacion")
    if not any(t in dl for t in niche):
        issues.append("la descripcion no menciona tu nicho (IA/automatizacion)")
    if "http" not in dl:
        issues.append("sin link al sitio en la descripcion")
    # 3ª persona / genérico (voz: debe ser 1ª persona)
    if any(t in dl for t in ("su objetivo", "sus clientes", "no dudes en contactarlo", "está comprometido")):
        issues.append("hay texto en 3ª persona/generico — reescribir en 1ra persona (tu voz)")
    if not any(t in dl for t in ("diagn", "contact", "agenda", "escríbeme", "escribeme")):
        issues.append("sin CTA claro (diagnostico/contacto)")
    return {"description": desc, "description_len": len(desc),
            "keywords": bs.get("keywords", ""), "subs": st.get("subscriberCount"),
            "videos": st.get("videoCount"), "views": st.get("viewCount"), "issues": issues}


def main():
    key = os.environ.get("YT_API_KEY")
    ch = os.environ.get("YT_CHANNEL_ID") or cfg("youtube.channel_id", "YOUR_CHANNEL_ID")
    if not key:
        raise SystemExit("Falta YT_API_KEY en .env. Consíguela gratis: Google Cloud Console -> "
                         "habilita 'YouTube Data API v3' -> Credenciales -> Clave de API. Ver directives/youtube_audit.md")
    n = int(arg("--max", "25"))
    # 1) playlist de uploads + audit del canal
    chd = get(f"{API}/channels", {"part": "contentDetails,snippet,brandingSettings,statistics",
                                  "id": ch, "key": key})
    items = chd.get("items", [])
    if not items:
        raise SystemExit(f"Canal {ch} no encontrado.")
    uploads = items[0]["contentDetails"]["relatedPlaylists"]["uploads"]
    chan_name = items[0]["snippet"]["title"]
    chan = channel_audit(items[0])
    # 2) video ids (pagina hasta juntar N; --max grande o --all = todo el canal)
    vids, token = [], None
    while len(vids) < n:
        params = {"part": "contentDetails", "playlistId": uploads,
                  "maxResults": min(n - len(vids), 50), "key": key}
        if token:
            params["pageToken"] = token
        pl = get(f"{API}/playlistItems", params)
        vids += [it["contentDetails"]["videoId"] for it in pl.get("items", [])]
        token = pl.get("nextPageToken")
        if not token:
            break
    if not vids:
        raise SystemExit("Sin videos en el canal.")
    # 3) metadata + stats (en lotes de 50 = limite de videos.list)
    rows = []
    for i in range(0, len(vids), 50):
        vd = get(f"{API}/videos", {"part": "snippet,statistics,contentDetails",
                                   "id": ",".join(vids[i:i + 50]), "key": key})
        rows += [signals(v) for v in vd.get("items", [])]
    con_issues = sum(1 for r in rows if r["issues"])
    out = save_json("youtube.json", {"channel": chan_name, "channel_id": ch,
                                     "channel_audit": chan,
                                     "videos": rows, "con_issues": con_issues})
    print(f"YouTube: {len(rows)} videos de '{chan_name}' ({chan['subs']} subs, {chan['videos']} videos). "
          f"Con issues SEO: {con_issues}. Descripcion del canal: {len(chan['issues'])} issues. -> {out}")
    for i in chan["issues"]:
        print("  [canal] " + i)
    for r in rows[:10]:
        flag = ("! " + "; ".join(r["issues"])) if r["issues"] else "ok"
        print(f"  [{r['views']:>6} vistas] {r['title'][:50]:50} | {flag[:80]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

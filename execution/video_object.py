#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
video_object.py — refuerzo blog<->video (GEO): embed de YouTube + VideoObject JSON-LD
+ cross-link, en los posts del blog que tienen un video del MISMO tema (Capa 3).

Por qué: el mismo tema en blog + video se refuerza en Google y en las IA. El VideoObject
es una senal estructurada fuerte (rich result de video) y el embed sube dwell-time.
Google pide que el VideoObject describa un video PRESENTE en la pagina -> por eso ademas
del schema se inserta el reproductor embebido (schema legitimo, no spam).

Entradas:
  - .tmp/youtube.json         (metadata real del canal; corre youtube_pull.py antes)
  - video_post_map.json       (mapa {archivo_post: video_id}, tematico, curado a mano)

Salida: edita los .html del sitio (in-place). Con guardarrail: verifica que el HTML
siga intacto (head/article cierran, JSON-LD parsea) y REVIERTE el archivo si algo rompe.

Uso:
  python execution/video_object.py --site "C:/ruta/a/tu/sitio" [--dry]
"""
import json
import os
import re
import sys

from _common import TMP, html_intact, site_url  # carpeta .tmp + guardarraíl + url del sitio

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EMOJI = re.compile(
    "[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF✅✔❤▶"
    "\U0001F000-\U0001F0FF️‍]+"
)


def arg(name, default=None):
    for i, a in enumerate(sys.argv):
        if a == name and i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return default


def clean(txt):
    """Quita emojis/simbolos de decoracion y espacios repetidos."""
    return re.sub(r"\s+", " ", EMOJI.sub("", txt or "")).strip()


def iso_duration(secs):
    """Segundos -> ISO-8601 (PT#M#S)."""
    secs = int(secs or 0)
    m, s = divmod(secs, 60)
    h, m = divmod(m, 60)
    out = "PT"
    if h:
        out += f"{h}H"
    if m:
        out += f"{m}M"
    if s or out == "PT":
        out += f"{s}S"
    return out


def video_object_ld(v, page_url, name=None):
    vid = v["id"]
    nm = clean(name) if name else clean(v["title"])
    ld = {
        "@context": "https://schema.org",
        "@type": "VideoObject",
        "name": nm,
        "description": nm,
        "thumbnailUrl": f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg",
        "uploadDate": (v.get("published") or "")[:10],
        "duration": iso_duration(v.get("duration_s")),
        "contentUrl": v["url"],
        "embedUrl": f"https://www.youtube.com/embed/{vid}",
    }
    if page_url:
        ld["mainEntityOfPage"] = page_url
    return json.dumps(ld, ensure_ascii=False)


def embed_block(v, name=None):
    vid = v["id"]
    title = clean(name or v["title"]).replace('"', "&quot;")
    return (
        '\n        <!-- video-embed -->\n'
        '        <div class="video-embed" style="max-width:800px;margin:1.75rem auto;">\n'
        '          <div style="position:relative;width:100%;aspect-ratio:16/9;">\n'
        f'            <iframe src="https://www.youtube.com/embed/{vid}" title="{title}" '
        'loading="lazy" frameborder="0" '
        'allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; '
        'picture-in-picture; web-share" allowfullscreen '
        'style="position:absolute;inset:0;width:100%;height:100%;border:0;border-radius:12px;">'
        '</iframe>\n'
        '          </div>\n'
        f'          <p style="text-align:center;margin-top:.6rem;"><a href="{v["url"]}" '
        'target="_blank" rel="noopener">Ver este tema en video en YouTube &rarr;</a></p>\n'
        '        </div>\n'
    )


def inject(path, v, page_url, dry, name=None):
    with open(path, encoding="utf-8") as f:
        html = f.read()
    if "<!-- video-embed -->" in html or "VideoObject" in html:
        return "ya-tiene"
    # 1) VideoObject JSON-LD antes de </head>
    ld = f'    <script type="application/ld+json">{video_object_ld(v, page_url, name)}</script>\n'
    if "</head>" not in html:
        return "sin-head"
    html = html.replace("</head>", ld + "</head>", 1)
    # 2) embed antes de related-posts (o antes de </article>)
    if "<!-- related-posts -->" in html:
        html = html.replace("        <!-- related-posts -->",
                            embed_block(v, name) + "        <!-- related-posts -->", 1)
    elif "</article>" in html:
        html = html.replace("</article>", embed_block(v, name) + "</article>", 1)
    else:
        return "sin-ancla"
    if not html_intact(html):
        return "ROTO-revertido"
    if dry:
        return "dry-ok"
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return "ok"


def main():
    site = arg("--site")
    dry = "--dry" in sys.argv
    if not site:
        raise SystemExit("Falta --site \"ruta al repo del sitio\"")
    yt_path = os.path.join(TMP, "youtube.json")
    if not os.path.exists(yt_path):
        raise SystemExit("Falta .tmp/youtube.json — corre youtube_pull.py primero.")
    with open(yt_path, encoding="utf-8") as f:
        yt = json.load(f)
    by_id = {v["id"]: v for v in yt["videos"]}
    map_path = os.path.join(HERE, "video_post_map.json")
    if not os.path.exists(map_path):
        raise SystemExit(f"Falta el mapa {map_path} (json {{archivo_post: video_id}}).")
    with open(map_path, encoding="utf-8") as f:
        mapping = json.load(f)

    print(f"video_object: {len(mapping)} posts mapeados. dry={dry}")
    for post, entry in mapping.items():
        # entry = "video_id"  o  {"id": "...", "name": "titulo limpio"}
        if isinstance(entry, dict):
            vid, name = entry.get("id"), entry.get("name")
        else:
            vid, name = entry, None
        v = by_id.get(vid)
        if not v:
            print(f"  [skip] {post}: video {vid} no esta en youtube.json")
            continue
        path = os.path.join(site, "blog", post)
        if not os.path.exists(path):
            print(f"  [skip] {post}: no existe en el sitio")
            continue
        page_url = f"{site_url()}/blog/{post}"
        res = inject(path, v, page_url, dry, name)
        print(f"  [{res:14}] {post}  <-  {clean(name or v['title'])[:45]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

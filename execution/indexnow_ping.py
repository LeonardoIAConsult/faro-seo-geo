#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
indexnow_ping.py — notifica a los buscadores (IndexNow) que unas URLs cambiaron (R11).

IndexNow (Bing, Yandex, Naver, Seznam) indexa en minutos en vez de días. Google no lo
usa directo pero el resto sí, y acelera el descubrimiento. Una llamada avisa "estas URLs
cambiaron, re-rastréalas".

⚠️ ACCIÓN PÚBLICA (avisa a servicios externos) → requiere OK del dueño por lote.
Setup previo: subir el archivo de clave a  https://{host}/{INDEXNOW_KEY}.txt  (contenido =
la propia clave) para que el buscador verifique la propiedad. Clave en .env: INDEXNOW_KEY.

Uso:
  python execution/indexnow_ping.py --urls "https://.../post1.html,https://.../post2.html"
  python execution/indexnow_ping.py --from-sitemap   # (futuro) toma las URLs del sitemap
"""
from __future__ import annotations

import os
import sys
from urllib.parse import urlparse

from _common import site_url

ENDPOINT = "https://api.indexnow.org/indexnow"


def arg(name, default=None):
    for i, a in enumerate(sys.argv):
        if a == name and i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return default


def ping(urls, key, host):
    import requests
    body = {"host": host, "key": key,
            "keyLocation": f"https://{host}/{key}.txt", "urlList": urls}
    r = requests.post(ENDPOINT, json=body, timeout=30)
    return r.status_code, (r.text or "")[:200]


def main():
    key = os.environ.get("INDEXNOW_KEY")
    if not key:
        print("ERROR: falta INDEXNOW_KEY en .env. Genera una clave (32+ hex), súbela a "
              "https://{host}/{clave}.txt, y ponla en .env. (Acción pública: OK del dueño.)")
        return 1
    raw = arg("--urls")
    if not raw:
        print("Uso: indexnow_ping.py --urls \"url1,url2,...\"")
        return 1
    urls = [u.strip() for u in raw.split(",") if u.strip()]
    host = urlparse(site_url()).netloc
    # seguridad: solo URLs del propio host (IndexNow rechaza dominios ajenos)
    urls = [u for u in urls if urlparse(u).netloc == host]
    if not urls:
        print(f"ERROR: ninguna URL pertenece a {host}.")
        return 1
    code, msg = ping(urls, key, host)
    ok = code in (200, 202)
    print(f"IndexNow: {len(urls)} URLs -> HTTP {code} {'OK' if ok else msg}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

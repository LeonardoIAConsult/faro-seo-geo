#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
youtube_apply.py — APLICA los cambios de seo-forge en YouTube (ESCRITURA vía OAuth).

seo-forge deja de ser solo-lectura: con tu OK aplica títulos, descripciones, tags,
miniaturas y la descripción/keywords del canal. Reusa el mismo cliente OAuth Desktop
que GSC (`credentials.json`); la 1ª vez abre el navegador para consentir el permiso de
escritura de YouTube (scope youtube.force-ssl) y guarda `youtube_token.json`.

⚠️ ACCIÓN PÚBLICA E IRREVERSIBLE. Por eso:
  - **--dry por defecto**: muestra QUÉ cambiaría, NO escribe.
  - Solo escribe con **--apply** explícito (el gate del dueño).
  - Nunca escribe sin ese flag.

Plan de cambios: JSON con la forma
{
  "videos":     [{"id":"...", "title":"...", "description":"...", "tags":["..."]}],
  "thumbnails": [{"id":"...", "file":"ruta/al/thumb.jpg"}],
  "channel":    {"description":"...", "keywords":"kw1 kw2 ..."}
}
(cada campo es opcional; se aplica solo lo que venga).

Uso:
  python execution/youtube_apply.py --auth                       # 1a vez: consiente en el navegador
  python execution/youtube_apply.py --plan .tmp/yt_plan.json     # DRY: muestra el diff
  python execution/youtube_apply.py --plan .tmp/yt_plan.json --apply   # ESCRIBE (con OK del dueño)
"""
from __future__ import annotations

import json
import os
import sys

from _common import ROOT

SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]


def arg(name, default=None):
    for i, a in enumerate(sys.argv):
        if a == name and i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return default


def service():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    cred = ROOT / os.environ.get("GSC_CREDENTIALS", "credentials.json")
    tok = ROOT / "youtube_token.json"
    creds = None
    if tok.exists():
        creds = Credentials.from_authorized_user_file(str(tok), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not cred.exists():
                raise SystemExit(f"No existe {cred} (cliente OAuth Desktop). Es el mismo de GSC.")
            creds = InstalledAppFlow.from_client_secrets_file(str(cred), SCOPES).run_local_server(port=0)
        tok.write_text(creds.to_json(), encoding="utf-8")
    return build("youtube", "v3", credentials=creds)


def apply_video(svc, v, dry):
    vid = v["id"]
    cur = svc.videos().list(part="snippet", id=vid).execute().get("items", [])
    if not cur:
        print(f"  [skip] video {vid} no encontrado")
        return
    sn = cur[0]["snippet"]
    changes = []
    new = dict(sn)
    if v.get("title") and v["title"] != sn.get("title"):
        changes.append(f"title: '{sn.get('title','')[:40]}' -> '{v['title'][:40]}'")
        new["title"] = v["title"]
    if v.get("description") and v["description"] != sn.get("description"):
        changes.append("description (nueva)")
        new["description"] = v["description"]
    if v.get("tags") is not None and v["tags"] != sn.get("tags"):
        changes.append(f"tags: {len(sn.get('tags',[]))} -> {len(v['tags'])}")
        new["tags"] = v["tags"]
    if not changes:
        print(f"  [= ] {vid}: sin cambios")
        return
    print(f"  [{'DRY' if dry else 'APPLY'}] {vid}: " + " · ".join(changes))
    if not dry:
        # categoryId es obligatorio en update; se conserva el actual
        body = {"id": vid, "snippet": {"title": new.get("title", ""), "categoryId": sn.get("categoryId", "22"),
                "description": new.get("description", ""), "tags": new.get("tags", [])}}
        if sn.get("defaultLanguage"):
            body["snippet"]["defaultLanguage"] = sn["defaultLanguage"]
        svc.videos().update(part="snippet", body=body).execute()


def set_thumbnail(svc, t, dry):
    from googleapiclient.http import MediaFileUpload
    vid, f = t["id"], t["file"]
    if not os.path.isfile(f):
        print(f"  [skip] thumb {vid}: no existe {f}")
        return
    print(f"  [{'DRY' if dry else 'APPLY'}] thumb {vid} <- {os.path.basename(f)}")
    if not dry:
        svc.thumbnails().set(videoId=vid, media_body=MediaFileUpload(f)).execute()


def apply_channel(svc, ch, dry):
    mine = svc.channels().list(part="brandingSettings", mine=True).execute().get("items", [])
    if not mine:
        print("  [skip] canal no accesible")
        return
    bs = mine[0]["brandingSettings"]
    cid = mine[0]["id"]
    changes = []
    if ch.get("description") and ch["description"] != bs.get("channel", {}).get("description"):
        changes.append("channel description (nueva)")
        bs.setdefault("channel", {})["description"] = ch["description"]
    if ch.get("keywords") and ch["keywords"] != bs.get("channel", {}).get("keywords"):
        changes.append("channel keywords (nuevas)")
        bs.setdefault("channel", {})["keywords"] = ch["keywords"]
    if not changes:
        print("  [= ] canal: sin cambios")
        return
    print(f"  [{'DRY' if dry else 'APPLY'}] canal: " + " · ".join(changes))
    if not dry:
        svc.channels().update(part="brandingSettings", body={"id": cid, "brandingSettings": bs}).execute()


def main():
    if "--auth" in sys.argv:
        service()
        print("OAuth de YouTube (escritura) OK. Token en youtube_token.json.")
        return 0
    plan_path = arg("--plan")
    if not plan_path:
        raise SystemExit("Uso: --plan <json> [--apply]  (o --auth la 1a vez)")
    dry = "--apply" not in sys.argv
    plan = json.loads(open(plan_path, encoding="utf-8").read())
    svc = service()
    print(f"youtube_apply: {'DRY (no escribe)' if dry else 'APLICANDO (escribe en YouTube)'}")
    for v in plan.get("videos", []):
        apply_video(svc, v, dry)
    for t in plan.get("thumbnails", []):
        set_thumbnail(svc, t, dry)
    if plan.get("channel"):
        apply_channel(svc, plan["channel"], dry)
    if dry:
        print("\n(DRY) nada escrito. Para aplicar de verdad: agrega --apply (gate: OK del dueño).")
    return 0


if __name__ == "__main__":
    sys.exit(main())

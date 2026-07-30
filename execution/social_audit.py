#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
social_audit.py — audita los perfiles de redes para reforzar la marca (SEO social + GEO).

Las redes también posicionan: el perfil es una landing, la bio es meta description, y
Google + la IA leen esos perfiles. Este auditor revisa, por red, señales objetivas:
  - perfil accesible (handle correcto en la config)
  - BIO con keyword del nicho + link (la bio es tu "meta description" social)
  - CADENCIA de publicación (días desde el último post; el algoritmo premia constancia)
  - coherencia de marca (nombre + link al sitio)

Arquitectura ENCHUFABLE (como _geo_engines): cada red es un adaptador que devuelve un
dict o None si no está disponible (falta su token). Sin token → se salta y se reporta
honesto (no inventa). Los tokens/handles van en config + .env. GUÍA de APIs por red en
`directives/social_audit.md`.

⚠️ Las APIs de redes son restrictivas/de pago en 2026 (Meta requiere app + revisión;
X es de pago; LinkedIn requiere partner). Por eso empezamos por lo que el dueño pueda
conseguir; los demás quedan gated hasta que tenga token.

Uso:
  python execution/social_audit.py
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from _common import TMP, cfg, site_url

NICHE_TERMS = ["ia", "inteligencia artificial", "automatiz", "pyme", "emprend", "negocio"]


def _bio_signals(bio, website):
    b = (bio or "").lower()
    dom = cfg("brand.domain", "")  # guard: dominio vacío NO debe matchear cualquier bio ("" in b == True)
    return {
        "bio_len": len(bio or ""),
        "bio_keyword": any(t in b for t in NICHE_TERMS),
        "bio_link": bool(website) or ("http" in b) or (bool(dom) and dom in b),
    }


def _days_since(iso):
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - dt).days
    except Exception:
        return None


# ---------------- Instagram (Graph API — Meta) ----------------
def instagram():
    """Requiere IG_ACCESS_TOKEN + IG_USER_ID (cuenta Business/Creator vinculada a una
    página de Facebook). Guía: directives/social_audit.md."""
    tok = os.environ.get("IG_ACCESS_TOKEN")
    uid = os.environ.get("IG_USER_ID") or cfg("social.instagram_user_id")
    if not tok or not uid:
        return None
    import requests
    base = f"https://graph.facebook.com/v20.0/{uid}"
    prof = requests.get(base, params={
        "fields": "username,biography,website,followers_count,media_count",
        "access_token": tok}, timeout=30).json()
    if "error" in prof:
        return {"red": "instagram", "error": prof["error"].get("message", "")[:80]}
    media = requests.get(f"{base}/media", params={
        "fields": "timestamp", "limit": 1, "access_token": tok}, timeout=30).json()
    last = (media.get("data") or [{}])[0].get("timestamp")
    r = {"red": "instagram", "handle": prof.get("username"),
         "followers": prof.get("followers_count"), "posts": prof.get("media_count"),
         "dias_ultimo_post": _days_since(last) if last else None}
    r.update(_bio_signals(prof.get("biography"), prof.get("website")))
    return r


# ---------------- adaptadores gated (guía en la directiva) ----------------
def facebook():
    if not os.environ.get("FB_PAGE_TOKEN"):
        return None
    return {"red": "facebook", "nota": "adaptador pendiente (token presente): implementar /me?fields=..."}


def linkedin():
    if not os.environ.get("LINKEDIN_TOKEN"):
        return None
    return {"red": "linkedin", "nota": "adaptador pendiente (requiere LinkedIn Marketing partner)"}


def twitter():
    if not os.environ.get("X_BEARER_TOKEN"):
        return None
    return {"red": "twitter", "nota": "adaptador pendiente (X API v2, plan de pago)"}


NETWORKS = {"instagram": instagram, "facebook": facebook,
            "linkedin": linkedin, "twitter": twitter}


def audit_profile(r):
    """Convierte las señales en hallazgos accionables."""
    if not r or r.get("error") or r.get("nota"):
        return []
    f = []
    if r.get("bio_len", 0) < 30:
        f.append(f"{r['red']}: bio muy corta ({r.get('bio_len',0)} chars) — es tu 'meta description' social")
    if not r.get("bio_keyword"):
        f.append(f"{r['red']}: la bio no menciona el nicho (IA/automatización/pyme) — no te encuentran por tema")
    if not r.get("bio_link"):
        f.append(f"{r['red']}: sin link en la bio → agrega {site_url()}")
    d = r.get("dias_ultimo_post")
    if d is not None and d > 14:
        f.append(f"{r['red']}: {d} días sin publicar (el algoritmo premia constancia)")
    return f


def main():
    results, findings, ran = [], [], []
    for name, fn in NETWORKS.items():
        try:
            r = fn()
        except Exception as e:
            r = {"red": name, "error": str(e)[:80]}
        if r is None:
            continue  # sin token → se salta (honesto)
        ran.append(name)
        results.append(r)
        findings += audit_profile(r)

    out = TMP / "social_audit.json"
    out.write_text(json.dumps({"redes_auditadas": ran, "perfiles": results,
                               "findings": findings}, ensure_ascii=False, indent=2), encoding="utf-8")
    if not ran:
        print("social_audit: ninguna red con token. Configura al menos una (ver "
              "directives/social_audit.md). Redes soportadas: " + ", ".join(NETWORKS))
        return 0
    print(f"social_audit: auditadas {', '.join(ran)} | hallazgos: {len(findings)} -> {out}")
    for f in findings:
        print("  " + f)
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())

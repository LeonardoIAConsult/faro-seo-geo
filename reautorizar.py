# -*- coding: utf-8 -*-
"""Reautoriza de una sola vez los tres accesos de Google que usa seo-forge.

POR QUE EXISTE: los tres tokens salen del mismo cliente OAuth, asi que mueren a la vez (al revocar
el permiso de la app, o a los 7 dias si la app sigue en estado "Prueba": ver
directives/search_console.md). Pedirlos por separado obliga a pasar tres veces por el
consentimiento; esto lo hace en una.

Escribe los mismos archivos que esperan las herramientas -token.json (Search Console),
ga4_token.json (Analytics) y youtube_token.json (YouTube)- a partir de una única autorizacion
con los tres permisos. Un token con permisos de mas funciona para una peticion que pide menos,
asi que cada script sigue leyendo su archivo sin cambios.

Uso: .venv/Scripts/python.exe -u reautorizar.py
"""
import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).parent / "execution"))

from google_auth_oauthlib.flow import InstalledAppFlow  # noqa: E402

RAIZ = Path(__file__).parent
SCOPES = [
    "https://www.googleapis.com/auth/webmasters.readonly",   # Search Console
    "https://www.googleapis.com/auth/analytics.readonly",    # GA4
    "https://www.googleapis.com/auth/youtube.force-ssl",     # YouTube (solo se usa con --apply)
]
DESTINOS = ["token.json", "ga4_token.json", "youtube_token.json"]

flujo = InstalledAppFlow.from_client_secrets_file(str(RAIZ / "credentials.json"), SCOPES)
creds = flujo.run_local_server(port=0)

for nombre in DESTINOS:
    (RAIZ / nombre).write_text(creds.to_json(), encoding="utf-8")
    print("escrito:", nombre)
print("Listo: tres accesos reautorizados con un solo consentimiento.")

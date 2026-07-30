#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
_geo_engines.py — motores de citación GEO enchufables (para geo_citation.py).

Cada motor le hace una pregunta a un LLM con búsqueda web y devuelve la respuesta +
las FUENTES (dominios) que usó → así medimos si la IA cita a la marca. Interfaz única:

    engine(query: str) -> {"answer": str, "sources": [dominio, ...]}  |  None

Devuelve None si el motor NO está disponible (falta su API key) → el orquestador lo
SALTA y reporta solo los motores que de verdad corrieron (honestidad, cierra G4).

Motores:
  - gemini      GRATIS (GOOGLE_GENERATIVE_AI_API_KEY). Google Search grounding = la
                misma mecánica de AI Overviews. Siempre activo si hay key.
  - openai      DE PAGO (OPENAI_API_KEY). web_search de la Responses API. Off sin key.
  - perplexity  DE PAGO (PERPLEXITY_API_KEY). modelos sonar, citations nativas. Off sin key.

Añadir un motor = una función que respete la interfaz + registrarla en ENGINES.
"""
from __future__ import annotations

import os
import re
from urllib.parse import urlparse

GEMINI_API = "https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={k}"


def domain_of(url_or_title: str) -> str:
    """Normaliza un URL o título a dominio 'registrable' en minúsculas, sin www.
    Devuelve '' si el texto no contiene un dominio real (title sin dominio)."""
    s = (url_or_title or "").strip().lower()
    if not s:
        return ""
    if s.startswith(("http://", "https://")):
        host = urlparse(s).netloc
        return host[4:] if host.startswith("www.") else host
    # título: acepta solo si contiene un dominio (con TLD real)
    m = re.search(r"[a-z0-9-]+(?:\.[a-z0-9-]+)*\.[a-z]{2,}", s)
    if not m:
        return ""
    d = m.group(0)
    return d[4:] if d.startswith("www.") else d


# ---------------- Gemini (gratis) ----------------
def gemini(query, model=None):
    key = os.environ.get("GOOGLE_GENERATIVE_AI_API_KEY")
    if not key:
        return None
    import requests
    model = model or os.environ.get("GEO_GEMINI_MODEL", "gemini-2.5-flash")
    body = {"contents": [{"parts": [{"text": query}]}], "tools": [{"google_search": {}}]}
    r = requests.post(GEMINI_API.format(m=model, k=key), json=body, timeout=60)
    r.raise_for_status()
    cand = r.json()["candidates"][0]
    text = "".join(p.get("text", "") for p in cand.get("content", {}).get("parts", []))
    sources = []
    for c in cand.get("groundingMetadata", {}).get("groundingChunks", []):
        w = c.get("web", {})
        # G3: usa el dominio del title (display) Y del uri si es resoluble
        for cand_str in (w.get("title", ""), w.get("uri", "")):
            d = domain_of(cand_str)
            if d and "vertexaisearch" not in d and d not in sources:
                sources.append(d)
    return {"answer": text, "sources": sources}


def gemini_generate(prompt, model=None, grounding=False):
    """Generación pura con Gemini (GRATIS, misma key que geo). Devuelve el texto o None
    si no hay key. A diferencia de gemini(), NO fuerza google_search (grounding opcional)
    y no extrae fuentes → sirve para tareas de razonamiento/estructura (keywords, clusters).
    Reusable por cualquier script que necesite un LLM gratis y determinista-ish."""
    key = os.environ.get("GOOGLE_GENERATIVE_AI_API_KEY")
    if not key:
        return None
    import requests
    model = model or os.environ.get("GEO_GEMINI_MODEL", "gemini-2.5-flash")
    body = {"contents": [{"parts": [{"text": prompt}]}]}
    if grounding:
        body["tools"] = [{"google_search": {}}]
    r = requests.post(GEMINI_API.format(m=model, k=key), json=body, timeout=90)
    r.raise_for_status()
    cand = r.json()["candidates"][0]
    return "".join(p.get("text", "") for p in cand.get("content", {}).get("parts", []))


# ---------------- OpenAI / ChatGPT (de pago, gated) ----------------
def openai(query, model=None):
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        return None  # sin key -> motor apagado, el orquestador lo salta
    import requests
    # Chat Completions con modelo de busqueda web + web_search_options (via documentada).
    model = model or os.environ.get("GEO_OPENAI_MODEL", "gpt-4o-search-preview")
    r = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}"},
        json={"model": model, "web_search_options": {},
              "messages": [{"role": "user", "content": query}]},
        timeout=90)
    r.raise_for_status()
    msg = r.json()["choices"][0]["message"]
    text = msg.get("content") or ""
    sources = []
    for ann in msg.get("annotations", []) or []:
        url = (ann.get("url_citation") or {}).get("url") or ann.get("url", "")
        d = domain_of(url)
        if d and d not in sources:
            sources.append(d)
    return {"answer": text, "sources": sources}


# ---------------- Perplexity (de pago, gated) ----------------
def perplexity(query, model=None):
    key = os.environ.get("PERPLEXITY_API_KEY")
    if not key:
        return None
    import requests
    model = model or os.environ.get("GEO_PPLX_MODEL", "sonar")
    r = requests.post(
        "https://api.perplexity.ai/chat/completions",
        headers={"Authorization": f"Bearer {key}"},
        json={"model": model, "messages": [{"role": "user", "content": query}]},
        timeout=90)
    r.raise_for_status()
    data = r.json()
    text = data["choices"][0]["message"]["content"]
    sources = []
    for u in data.get("citations", []) or []:
        d = domain_of(u)
        if d and d not in sources:
            sources.append(d)
    return {"answer": text, "sources": sources}


# Registro de motores. El orquestador recorre este dict; los que devuelven None
# (sin key) se saltan solos. Para activar OpenAI/Perplexity: pon su key en .env.
ENGINES = {"gemini": gemini, "openai": openai, "perplexity": perplexity}

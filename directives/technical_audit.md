# Directiva 01 — Auditoría técnica SEO

**Objetivo:** detectar errores que impiden indexar o rankear: titles/meta/H1, canonicals,
lang, robots noindex accidental, JSON-LD roto, duplicados, contenido delgado, imgs sin alt,
coherencia sitemap/robots.

**Entradas:** carpeta del sitio (`SEO_SITE_DIR` o `--site`).

**Herramientas:**
- `execution/onpage_analyze.py` — extrae señales de cada página → `.tmp/onpage.json`.
- `execution/technical_audit.py` — aplica reglas + severidad → `.tmp/technical_audit.json`.
- `execution/sitemap_robots_check.py` — coherencia sitemap↔disco↔robots.

**Ejecución:**
```powershell
$PY = ".\.venv\Scripts\python.exe"
& $PY execution\technical_audit.py --site "C:\Users\Tu Usuario\Documents\tu-sitio-estatico"
& $PY execution\sitemap_robots_check.py --site "C:\Users\Tu Usuario\Documents\tu-sitio-estatico"
```

**Salida:** hallazgos con severidad HIGH/MED/LOW y fix concreto por URL.

**Prioriza:** primero HIGH (sin title, sin H1, noindex, JSON-LD roto, duplicados, URL fantasma en sitemap).

**Casos extremos:**
- HTML de previews/proyectos se excluye en `_common.html_files` (no son páginas públicas).
- Si una regla da falso positivo (ej. página intencionalmente corta), documenta la excepción en Aprendizajes, no cambies el umbral a ciegas.
- El script NO edita el sitio. Aplicar fixes = decisión del orquestador con OK del dueño.

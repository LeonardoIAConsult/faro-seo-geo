# Directiva 12 — Descargar un sitio a disco (auditar cuenta nueva en frío)

**Objetivo:** poder auditar el sitio de un prospecto/cliente cuyo repo NO tienes. El motor lee
el HTML desde disco; este crawler lo descarga primero.

**Cuándo usarla:** onboarding de un cliente nuevo, auditoría de un prospecto, o comparar contra
un competidor (con permiso / uso legítimo). Si YA tienes los archivos del sitio (repo, export
estático), NO hace falta: apunta `SEO_SITE_DIR` directo.

**Reglas (educado por defecto):** mismo dominio, respeta `robots.txt`, delay entre requests,
límite de páginas, User-Agent identificable. Es un GET (lectura). Usar en sitio propio o con
permiso del dueño. No es un scraper agresivo.

## Flujo
1. `site_fetch.py --url https://www.cliente.com --max-pages 200` → descarga a
   `.tmp/site-fetch/<dominio>/` (o `--out <ruta>`). Resumen en `.tmp/site_fetch.json`.
2. Apunta el motor a esa carpeta: `SEO_SITE_DIR="<out>"` (o `--site "<out>"` a cada script).
3. Corre la auditoría normal: `technical_audit.py`, `onpage_analyze.py`, `schema_validate.py`,
   `internal_links.py`, `report_build.py`, etc.
4. Los datos remotos (GSC/GA4/GEO/Trends/keywords/YouTube/GBP/alerts) requieren los tokens del
   cliente y son independientes del crawl.

## Opciones
- `--max-pages N` (def 200) · `--delay S` (def 0.5s) · `--out RUTA` · `--keep-query` (no tirar `?`)
- `--ignore-robots` (solo si es TU sitio y robots bloquea de más; úsalo con criterio).

## Casos extremos
- **Sitio JS puro (SPA sin HTML servido):** el crawler baja el HTML que responde el servidor; si el
  contenido se pinta 100% con JS en cliente, verás poco. Para esos casos, usar `agent-browser`
  (render real) — pendiente de cablear como modo `--render`.
- **Tope alcanzado:** si el sitio es más grande que `--max-pages`, avisa; sube el límite.
- **robots bloquea todo:** se salta esas URLs y lo reporta; no las fuerza.

## Uso
```powershell
$PY = ".\.venv\Scripts\python.exe"
& $PY execution\site_fetch.py --url https://www.cliente.com --max-pages 200
& $PY execution\report_build.py --site ".tmp\site-fetch\cliente.com"
```

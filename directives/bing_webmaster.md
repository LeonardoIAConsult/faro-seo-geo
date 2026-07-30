# Directiva — Bing Webmaster Tools (2º buscador + señal GEO)

## Objetivo
Sumar el 2º buscador. Bing importa por dos razones: (1) **alimenta ChatGPT Search y
Copilot** → aparecer en Bing = presencia en esas IAs (GEO); (2) da datos que GSC NO
expone: recuento de **enlaces entrantes por página** (backlinks), gratis.

## Activación (el dueño, una vez)
1. Entrar a Bing Webmaster Tools (bing.com/webmasters) con su cuenta.
2. **Importar el sitio desde GSC** (1 clic: "Import from Google Search Console") o verificarlo aparte.
3. Settings → **API access** → generar **API key**.
4. Pegarla en `.env`: `BING_API_KEY=...` (y `BING_SITE_URL=` solo si el siteUrl verificado difiere del `SEO_SITE_URL`; descúbrelo con `--report sites`).

## Herramienta
`execution/bing_pull.py` (gratis, **gated** por `BING_API_KEY` → sin key se salta, no rompe).
```powershell
$PY = ".\.venv\Scripts\python.exe"
& $PY execution\bing_pull.py --report sites     # valida la key + lista sitios verificados (1ª vez)
& $PY execution\bing_pull.py --report traffic   # impresiones/clics en Bing
& $PY execution\bing_pull.py --report queries   # keywords reales en Bing + posición
& $PY execution\bing_pull.py --report links     # enlaces entrantes por página (best-effort)
```

## API (referencia)
- JSON: `https://ssl.bing.com/webmaster/api.svc/json/{METHOD}?apikey=KEY&siteUrl=URL`
- Respuesta envuelta en `{"d": ...}`; fechas en formato WCF `/Date(ms)/` (las parsea `parse_ms_date`).
- Métodos usados: `GetUserSites`, `GetRankAndTrafficStats`, `GetQueryStats`, `GetLinkCounts`.

## Salida
`.tmp/bing_traffic.json`, `bing_queries.json`, `bing_links.json`. Cableado al informe
en la **Sección 4d** (soft: si no corriste el script, dice "pendiente").

## Casos extremos / límites
- **Sin key** → se salta con aviso (como los motores GEO de pago). No es error.
- **Shape de `GetLinkCounts` varía** → parseo best-effort; si Bing cambia el formato, `links` sale vacío sin romper. Verificar en la 1ª corrida real y ajustar.
- **`--report sites` primero** en la 1ª activación: confirma que la key es válida y que el `siteUrl` que usarás coincide con el verificado (si no, la API devuelve vacío, no error).
- **Probado en vivo 2026-07-30:** key OK. ⚠️ **Gotcha real:** el sitio verificado en Bing es **NON-www** (`https://example.com/`) ≠ el `www` del resto del motor → OBLIGA a `BING_SITE_URL=https://example.com/` en `.env` o la API devuelve vacío (sin error). Corre `--report sites` para ver el siteUrl exacto. Backlinks = genuinamente 0 (`GetLinkCounts` → `Links:[]`; parser correcto). Footprint 57 días: 263 impresiones, 0 clics (mismo cuadro que Google).

## Diferencia con lo que ya hay
- GSC = índice/rendimiento en Google. Bing = lo mismo en Bing + backlinks por página (GSC no los da completos) + señal para ChatGPT/Copilot.
- NO duplica `indexnow_ping.py` (ese notifica; este LEE datos/insights).

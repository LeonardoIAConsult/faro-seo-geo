# Directiva — Índice real de Google (URL Inspection)

## Objetivo
Saber qué hace Google REALMENTE con cada URL (indexada / excluida + motivo / desconocida)
y si respetó tu `canonical`. El resto del motor audita el HTML en disco; esto pregunta a
Google. Cierra el punto ciego del reporte de cobertura de GSC (que no tiene export por API).

## Entradas
- `credentials.json` + `token.json` (los MISMOS de GSC; el scope `webmasters.readonly` ya cubre urlInspection).
- `GSC_SITE_URL` en `.env` = propiedad verificada (ej. `sc-domain:example.com`).
- `sitemap.xml` del sitio (las URLs que QUEREMOS indexadas). Fallback: pasar `--url`.

## Herramienta
`execution/index_inspect.py`
```powershell
$PY = ".\.venv\Scripts\python.exe"
& $PY execution\index_inspect.py                 # inspecciona todo el sitemap
& $PY execution\index_inspect.py --url https://www.example.com/blog/x.html
& $PY execution\index_inspect.py --max 100 --delay 0.2
```

## Salida
`.tmp/index_inspect.json` → `{ total, buckets{indexed,excluded,unknown}, errores,
excluidas[], desconocidas[], conflictos_canonical[], rows[] }`. Se cablea al informe
en la **Sección 2b** (`report_build.py`, soft: si no corriste el script, dice "pendiente").

## Buckets (qué significan / qué hacer)
- **indexed** — en el índice. OK.
- **excluded** — Google la conoce pero NO la indexa. Motivos típicos y acción:
  - *Discovered - currently not indexed* → la vio pero no la priorizó (thin / poca autoridad / crawl budget). Reforzar contenido + enlaces internos + pedir indexación.
  - *Crawled - currently not indexed* → la crawleó y decidió no indexar (calidad/duplicado). Mejorar valor único.
  - *Alternate page with proper canonical tag* / *Duplicate* → Google la plegó a otra. Si NO querías eso, revisar canonical/redirect.
- **unknown** — "URL is unknown to Google": aún no la descubrió (recién publicada). Está en sitemap → esperar crawl, o pedir indexación en la UI.
- **conflictos_canonical** — Google eligió una canónica DISTINTA a tu `<link canonical>` = fuga real; tu señal se ignora. Investigar por qué (contenido casi-duplicado, señales mixtas).

## Casos extremos / límites
- **Cuota Google:** 2.000 inspecciones/día · 600/min por propiedad. Sitios chicos entran de sobra; para sitios grandes usar `--max`. Un 429/permiso → `inspect()` lo captura por URL (bucket implícito `error`, no rompe el lote).
- **Datos lentos:** reflejan el ÚLTIMO crawl de Google (puede ser días viejo). Tras un fix (redirect/canonical), Google tarda en re-crawlear → el estado no cambia al instante. El informe marca la antigüedad (`fresh_note`).
- **Solo lectura:** NO pide indexación ni valida correcciones (eso es acción en la UI de GSC; no hay API pública para el botón "Validar corrección" ni "Request indexing" de páginas normales).

## Aprendizaje base
Medido 2026-07-30: de 79 URLs del sitemap, 69 indexadas · 3 "Discovered - not indexed" ·
7 unknown (los 3 posts nuevos del día + otros). 13% fuera del índice = parte del orgánico≈0
no es ranking, es **falta de indexación**. Esta señal antes no existía en el motor.

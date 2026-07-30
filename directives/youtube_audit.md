# Directiva 12 — Auditoría y mejora de YouTube (capacidad nueva)

**Objetivo:** optimizar el canal de YouTube del dueño para más descubrimiento (YouTube es el
2º buscador del mundo) y para ser citado por Google + IA. Cada video se vuelve una pieza que
posiciona y atrae, en la voz de marca.

**Requisito (gratis):** `YT_API_KEY` en `.env` — clave de **YouTube Data API v3**.
Sacarla: https://console.cloud.google.com → mismo proyecto del GSC → "APIs y servicios" →
Habilitar **YouTube Data API v3** → Credenciales → Crear credencial → **Clave de API** → pegarla en `.env`.
Canal: `YT_CHANNEL_ID=YOUR_CHANNEL_ID`.

**Insumo:** `execution/youtube_pull.py --max 25` → `.tmp/youtube.json` (videos + señales SEO).

## Rúbrica por video (0-100)
**A. Título (25):** keyword al inicio + gancho, 20-70 chars, sin clickbait vacío.
**B. Descripción (25):** primeras 2-3 líneas con keyword y valor (es lo que se ve y lo que indexa
Google); ≥200 palabras; link a web/lead magnet; CTA; **timestamps/capítulos**; hashtags relevantes.
**C. Tags (10):** 3-8 relevantes, sin relleno.
**D. Miniatura (15):** legible en móvil, texto corto grande, cara/emoción, on-brand (Higgsfield/Canva).
**E. Retención/estructura (15):** hook en los primeros 5s, capítulos, final con CTA/end screen.
**F. GEO / citabilidad (10):** descripción "answer-first" (responde la duda en la 1ª línea);
transcripción/subtítulos activos (los LLM y Google leen el texto del video).

## Flujo
1. `youtube_pull.py` → señales deterministas (largos, tags, links, capítulos).
2. IA revisa cada video con la rúbrica y **sugiere** título/descripción/tags optimizados en la voz
   de marca (`MARCA/perfil-y-voz.md`), grounded en el tema real del video. No inventar.
3. Detecta **gaps de temas**: qué busca la audiencia y no está cubierto → ideas de videos (cruzar con
   keywords de GSC y clusters del blog: el mismo tema en blog + video se refuerzan).
4. Prioriza por **vistas × oportunidad** (arreglar primero los que ya tienen tracción).
5. Miniaturas flojas → pasar a `Desinger_LAP` (Higgsfield/Canva) con brief.

## Aplicar cambios — `youtube_apply.py` (ESCRITURA vía OAuth)
seo-forge SÍ puede aplicar los cambios en YouTube (títulos, descripciones, tags, miniaturas,
descripción/keywords del canal) vía `execution/youtube_apply.py`. Reusa el cliente OAuth Desktop
de GSC (`credentials.json`); scope `youtube.force-ssl`; token en `youtube_token.json` (gitignored).
- **1ª vez:** `youtube_apply.py --auth` → consentir en el navegador (1 clic del dueño).
- **Ver el diff (no escribe):** `youtube_apply.py --plan <json>` (DRY por defecto).
- **Aplicar (ESCRIBE):** `youtube_apply.py --plan <json> --apply` → **gate: OK del dueño por lote**
  (acción pública/irreversible). Nunca escribe sin `--apply`.
- **Plan** = JSON `{videos:[{id,title,description,tags}], thumbnails:[{id,file}], channel:{description,keywords}}`.

## ⚠️ Capítulos/timestamps — SOLO reales
Nunca poner capítulos inventados (`0:00` repetido) ni placeholders. Un timestamp falso es info falsa.
El check "sin capítulos" del auditor es SUGERENCIA, no orden de inventarlos.

**Método probado (2026-07-28) para capítulos REALES:**
1. `youtube_apply.service()` (OAuth dueño) → `captions().list(videoId)` → `captions().download(id, tfmt="srt")`.
   Funciona para los videos PROPIOS (scraping público de captions y yt-dlp están bloqueados por bot-check).
2. Parsear SRT a `M:SS texto`; en videos largos, downsamplear (~130 líneas cubriendo todo).
3. `gemini-2.5-flash` genera 3-6 capítulos: primero 0:00, tiempos SOLO del transcript, repartidos.
4. Agregar `⏱ Capítulos:` + líneas al final de la descripción → `youtube_apply --apply`.
Aplicado en vivo a los 7 videos capitulables del top 8 (el de 22s Short no lleva).

## Watchdog semanal (local, automático)
La tarea Windows `seo-forge-rank-track` (lunes 9am, `run-rank-track.cmd`) ahora también audita el canal:
1. `youtube_pull.py --max 30` → data fresca del canal en `.tmp/youtube.json`.
2. `youtube_track.py` → snapshot en `youtube-history.json` + **diff vs la semana anterior**, y escribe el tablero `youtube-audit-status.md` (versionado). Avisa de:
   - **videos nuevos** desde la última corrida (aún sin optimizar),
   - videos cuyos issues **bajaron** (aplicaste un fix ✓) o **subieron** (regresión),
   - **crecimiento de vistas** (qué video ganó tracción → priorizar),
   - videos con issues que **NO están en el deliverable** (agregarlos con títulos/descr en la voz).
- **No reescribe el deliverable** (los títulos optimizados son juicio/voz, no deterministas): solo vigila y avisa. Abrir `youtube-audit-status.md` para ver qué actuar.
- Decisión del dueño 2026-07-27: la auditoría periódica de YouTube corre **local** (misma tarea que rank_track; la key vive en `.env` local, no se expone en la nube). Cloud = pendiente si algún día se quiere sin laptop (necesitaría `YT_API_KEY` como secreto de la rutina + editar su prompt).

## Casos extremos
- Nunca inventar datos ni promesas. Respetar voz canónica.
- Sin `YT_API_KEY` → marcar "requiere key (gratis)" y no continuar.
- Cruzar con blog: un post y un video del mismo tema se enlazan (video embebido en el post con
  schema `VideoObject`; el post en la descripción del video). Refuerzo mutuo SEO+GEO.

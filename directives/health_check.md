# Directiva — Verificación maestra de salud SEO/GEO (health_check)

## Objetivo
Que el SEO/GEO esté **siempre de punta**: no esperar a que un humano corra el motor para
enterarse de una regresión. Vigila la salud y **avisa** cuando algo se rompe o cae.

## Por qué existe
Las rutinas semanales (`rank_track`, `backlink_track`, `geo_citation`, `youtube_*`) rastrean
**movimiento** pero solo REGISTRAN — no alarmaban. El chequeo maestro (`report_build` +
`report_score`) solo corría **on-demand**. Faltaba el watchdog que corre solo, compara y AVISA.

## Herramienta
`execution/health_check.py`. Fuentes: `report-history.json` (score/métricas, lo actualiza
`report_build`), `.tmp/index_inspect.json` (conflictos de canónica), `backlink-history.json`.

## Flujo (determinista salvo red)
1. Corre `report_build.py --site <sitio>` (refresca auditores locales + soft-carga los
   intermedios de red frescos + `report_score` actualiza `report-history.json`).
   Con `--no-build` usa el historial existente sin re-auditar.
2. Lee los 2 últimos snapshots (cur, prev) + índice + backlinks.
3. **Evalúa** (lógica pura, testeada):
   - **ROJO (algo roto AHORA, alarma siempre):** HIGH>0 · formulario roto · schema JSON-LD
     inválido · enlace interno roto · conflicto de canónica (Google ignora tu `canonical`).
   - **REGRESIÓN (cayó vs anterior):** Salud SEO baja ≥ `health.score_drop_alarm` (config, def 3) ·
     citación IA (GEO) baja · backlinks bajan.
4. **Veredicto:** DEGRADADO si hay ROJO/REGRESIÓN, si no SANO. Escribe `health-status.md`.
5. Si DEGRADADO → **alarma Telegram** (mismo bot del Brain: `TELEGRAM_BOT_TOKEN`/`CHAT_ID` de
   env o `TOOLS/flujo2-reunion/.secrets.env`). Exit code 1 (degradado) / 0 (sano) / 2 (no pudo correr).

## Cadencia
Tarea Windows **`seo-forge-health`** (diaria 10:00) → `run-health-check.cmd`. Diaria porque los
checks duros (schema/HIGH/form/enlaces) pescan regresiones tras cada deploy de NOVA; los componentes
de red se comparan con lo que refrescó la tarea semanal (con nota de antigüedad).

## Flags
- `--no-build` — no re-audita, evalúa el `report-history` existente.
- `--dry-run` — evalúa + tablero pero NO envía Telegram (para probar sin alarmar).

## Umbral / calibración
`score_drop_alarm` en `faro.config.json` (`health`). El score-drop es más ruidoso que los
checks absolutos (depende de qué componentes de red estaban presentes en cada corrida → cambia la
renormalización). Los checks ROJO absolutos son la señal dura. Si hay falsas alarmas de score, subir
el umbral. **Nunca** apagar los checks ROJO.

## Seguridad
El token de Telegram va en la URL de la API → **nunca imprimir la respuesta/URL cruda** (el código
ya lo evita: solo imprime el tipo de excepción). Gated: sin credenciales → tablero, sin romper.

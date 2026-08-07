# Directiva 11 — Monitoreo de menciones (Google Alerts)

**Objetivo:** vigilar menciones de la marca, el nombre del dueño, la competencia y el nicho
para reputación, oportunidades de GEO/backlink e ideas de contenido — sin trabajo manual.

**Fuente honesta:** Google Alerts NO tiene API oficial. El canal reusable es el **feed RSS/Atom**
que cada alerta puede entregar. Este flujo lee esos feeds; es gratis, stdlib, determinista.

## Entradas (una sola vez, las pone el dueño)
1. Entrar a https://www.google.com/alerts
2. Crear alertas para: `Your Name`, `Your Brand`, el dominio, y 2-3
   términos del nicho/competencia que importen.
3. En cada alerta → **Mostrar opciones → Entregar a: Feed RSS**. Copiar la URL del feed.
4. Pegar las URLs en `faro.config.json` → `alerts.feeds` (lista). Son públicas, no secretas.

## Flujo
1. `alerts_monitor.py` — lee todos los feeds, parsea menciones, extrae el URL real (los links de
   Alerts van envueltos en un redirect `google.com/url?url=`), marca **[MARCA]** vs **[nicho]**
   (por `brand.names`), deduplica contra `alerts-history.json` y flaggea las **nuevas**.
2. Salida: `.tmp/alerts.json` (`{generado, feeds, total, nuevas, entradas:[...]}`).
3. **Interpretar (Capa 2):** revisar las nuevas menciones → decidir acción:
   - Mención de marca sin enlace → oportunidad de pedir backlink / responder.
   - Sitio que cita el nicho pero no al dueño → candidato de GEO/outreach.
   - Tema que sube → idea para `content_brief.py` / `marca-content-pipeline`.

## Salida
Lista priorizada de menciones nuevas + acción sugerida por cada una. No publica ni contacta
nada solo: propone, el dueño decide (regla de marca).

## Casos extremos
- **Sin feeds configurados:** el script se salta limpio (no es error). Avisar al dueño que
  cree las alertas con entrega RSS.
- **Feed caído / cambia de formato:** best-effort — ese feed se salta, los demás siguen.
- **Nunca inventar menciones.** Si un feed no responde, se reporta menos, no se rellena.

## Uso
```powershell
$PY = ".\.venv\Scripts\python.exe"
& $PY execution\alerts_monitor.py                                  # usa config alerts.feeds
& $PY execution\alerts_monitor.py --feed "https://www.google.com/alerts/feeds/123/456"
```

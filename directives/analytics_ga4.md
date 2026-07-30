# Directiva — Analytics (GA4) + Tendencias (Google Trends)

> Cierran 2 gaps del motor: **comportamiento** (qué hace la gente al llegar) y **tendencias**
> (qué empieza a buscar el nicho). Ambos GRATIS y opcionales (gated: sin config, se saltan).

## Capacidad 1 — GA4 (comportamiento real)
**Objetivo:** el motor sabía qué buscas (GSC) pero no qué pasa DESPUÉS del clic. GA4 aporta
páginas top por vistas, engagement, canales de tráfico y conversiones (keyEvents).

**Script:** `execution/ga4_pull.py` · **Fuente:** Google Analytics Data API v1beta (oficial, gratis).

**Setup (una vez):**
1. Habilitar **"Google Analytics Data API"** en la misma consola de Google (donde GSC/PageSpeed).
2. `GA4_PROPERTY_ID` en `.env` = id **numérico** de la propiedad (GA → Admin → Configuración de la
   propiedad → ID de la propiedad). **No** es el `G-XXXX` del tag; es un número como `123456789`.
3. Primer run abre el navegador para autorizar (scope `analytics.readonly`) → guarda `ga4_token.json`.

**Uso:** `python execution/ga4_pull.py --report all --days 28`
→ `.tmp/ga4_overview.json` · `ga4_pages.json` · `ga4_channels.json`.

**Lectura:** cruzar con GSC → páginas con muchas impresiones (GSC) pero bajo engagement (GA4) =
prioridad de mejora. Canales → si orgánico es ~0, el problema es descubrimiento (SEO/GEO), no la página.

## Capacidad 2 — Google Trends (tendencias del nicho)
**Objetivo:** escribir sobre lo que la gente **empieza** a buscar (estacionalidad + consultas que
suben), no solo lo de siempre. Alimenta el content brief.

**Script:** `execution/trends_pull.py` · **Fuente:** `pytrends` (⚠️ **NO oficial** — scraping de
Google Trends; puede rate-limitar/fallar → es best-effort, si no responde se salta sin romper).

**Config (opcional):** `geo.trends_geo` (ej. `"CO"` Colombia; `""` = mundial) · `geo.trends_hl`
(idioma, def `"es"`). Keywords: de `--kw`, o `geo.queries`, o el top de `gsc_queries.json`.

**Uso:** `python execution/trends_pull.py --kw "ia para pymes,automatizar negocio"`
→ `.tmp/trends.json` (por keyword: dirección sube/baja/estable + % + consultas "rising").

## Casos extremos / honestidad
- GA4: sin `GA4_PROPERTY_ID` → se salta (no es error). El id equivocado (poner `G-XXXX`) da 400.
- Trends: sin API oficial → tratar los datos como **señal**, no verdad absoluta. Si Google bloquea,
  el motor lo dice y sigue. Nunca inventar tendencias.
- Ambos son **gratis** → respetan la regla "solo fuentes gratis/deterministas" (Trends = best-effort).

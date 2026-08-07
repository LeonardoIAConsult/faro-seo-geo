# Directiva — Onboarding: conectar y autorizar todas las fuentes (GAP2)

**Objetivo:** llevar a un usuario NUEVO (o a un sitio nuevo) de cero a "todas las fuentes de datos
conectadas", guiándolo paso a paso. seo-forge no es solo un motor de auditoría: parte de su trabajo
es **ayudar al usuario a instalar, aplicar y autorizar** las conexiones que hacen su SEO/GEO top —
incluidas las **platform properties sociales** de Google Search (IG/TikTok/X/YT, feature jul-2026).

**Herramienta motor:** `execution/doctor.py` (diagnóstico determinista). NO reimplementa OAuth: cada
autorización la dispara el `*_pull.py` que ya la hace en su primera corrida (abre el navegador).

## Flujo (el agente lo conduce, el usuario autoriza)

1. **Diagnóstico inicial** — `python execution/doctor.py`
   Muestra por fuente 🟢 conectada / 🟡 parcial / 🔴 falta, con qué falta y la directiva de cada una.

2. **Un paso a la vez** — `python execution/doctor.py --next`
   Imprime la ÚNICA cosa a hacer ahora (la fuente pendiente de mayor prioridad) + el comando exacto.
   Repetir este paso tras cada conexión hasta que diga "🟢 Todo conectado".

3. **Validar de verdad los tokens** — `python execution/doctor.py --probe`
   El chequeo offline solo ve que el archivo de token EXISTE; `--probe` llama a la API y confirma que
   el token SIRVE (caza tokens expirados/revocados → `invalid_grant`). Correr al terminar y ante
   cualquier "conectada pero falla".

## Orden recomendado de conexión (fundacional → opcional)

| # | Fuente | Cómo se conecta | Notas |
|---|--------|-----------------|-------|
| 1 | **Google Search Console (web)** | Cloud Console: proyecto → habilitar "Google Search Console API" → OAuth **Desktop app** → guardar `credentials.json`. Poner `GSC_SITE_URL` en `.env`. Correr `gsc_pull.py --report queries` → autorizar en navegador (genera `token.json`). | Fundacional; muchas fuentes reusan este OAuth. Ver `directives/search_console.md`. |
| 2 | **Platform properties (social→Search)** | En `https://search.google.com/search-console/welcome` añadir y **autorizar** cada red (IG/TikTok/X/YT) con su OAuth. Si ya se reclamó el Search profile, las cuentas verificadas se agregan solas. | La UI es la vía; el acceso por API aún NO está documentado. Usar `doctor --probe` para ver si la API las lista. |
| 3 | **Google Analytics 4** | Habilitar "Google Analytics Data API" (mismo `credentials.json`). Poner `GA4_PROPERTY_ID` (numérico) en `.env`. Correr `ga4_pull.py --report overview` → autoriza (genera `ga4_token.json`). | El ID es el número, NO el `G-XXXX`. Ver `directives/analytics_ga4.md`. |
| 4 | **Bing Webmaster** | Bing WMT → Settings → API access. Poner `BING_API_KEY` (y `BING_SITE_URL` si el host difiere) en `.env`. | 2º buscador + alimenta ChatGPT/Copilot (GEO). Ver `directives/bing_webmaster.md`. |
| 5 | **YouTube Data API** | `YT_API_KEY` en `.env` + `youtube.channel_id` en config. | Solo si hay canal. Ver `directives/youtube_audit.md`. |
| 6 | **Google Business Profile** | Correr `gbp_pull.py --report accounts` para descubrir IDs. Además Google debe **APROBAR** el acceso a las Business Profile APIs (403 hasta aprobar). | Solo si el SEO local aplica. Ver `directives/local_seo.md`. |
| — | PageSpeed / CWV | `PAGESPEED_API_KEY` opcional en `.env`. | Sin key funciona, con rate limit más bajo. |

## Guardarraíles (seguridad)
- `credentials.json`, `token.json`, `ga4_token.json`, `gbp_token.json`, `.env` = **secretos**
  (gitignored). Nunca commitear, nunca imprimir su contenido.
- El agente **NO** entra contraseñas ni crea cuentas: las pantallas de login/consentimiento OAuth las
  aprueba el USUARIO en su navegador. El agente guía, no suplanta.
- No deployar ni publicar nada como parte del onboarding.

## Casos extremos
- **Token expirado/revocado** (`invalid_grant`) → re-correr el `*_pull.py` de esa fuente para re-autorizar.
- **Sitio nuevo (modo "nuevo sitio")** → `cp config.example.json faro.config.json`, editar
  site/brand/keywords/geo con los datos del sitio, y `cp .env.example .env` con las claves. El motor
  lee toda la identidad de la config (no hay nada de marca hardcodeado en el código), así que con eso
  queda listo para auditar cualquier sitio. Correr `doctor.py` para ver qué conexiones faltan.
- **403 en GBP** → falta la aprobación de Google (no es bug); documentar y seguir con el resto.

## Criterio de hecho
`python execution/doctor.py` reporta las fuentes aplicables en 🟢 y `--probe` confirma que los tokens
OAuth responden (sin `invalid_grant`).

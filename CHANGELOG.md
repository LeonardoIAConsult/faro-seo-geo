# Changelog

Todos los cambios notables de Faro SEO·GEO. Formato basado en
[Keep a Changelog](https://keepachangelog.com/es/1.1.0/).

## [0.2.1] — 2026-10-04

### Fixed
- **El tablero ya no dice "sano" con Google desconectado.** `health_check.py` marca ROJO si
  una fuente remota (Search Console, índice, GEO, YouTube, Analytics, Bing, Core Web Vitals,
  backlinks) pasa de `health.max_data_age_days` (9 por defecto), si la última corrida vino
  vacía, o si un token de Google ya no se puede renovar. `--no-tokens` salta esa comprobación.
- **Las rutinas desatendidas no se cuelgan.** Con `SEO_FORGE_UNATTENDED=1`, `gsc_pull` y
  `ga4_pull` fallan en segundos ante un token vencido en vez de abrir el navegador y esperar.
  `ga4_pull` ya no revienta con `RefreshError`.
- **GEO:** el modelo de Gemini por defecto pasa a `gemini-3.6-flash` (2.5-flash dejó de estar
  disponible para proyectos nuevos) y el informe registra el modelo que se usó de verdad.

### Added
- `reautorizar.py`: renueva los tres accesos de Google (Search Console, Analytics, YouTube)
  con un solo consentimiento.
- Directiva de Search Console: publicar la app OAuth ("En producción"). En estado "Prueba"
  Google vence los tokens a los 7 días.

## [0.2.0] — 2026-08-06

### Added
- **`doctor.py` — chequeo de conexiones + onboarding guiado.** Reporta por fuente
  (Search Console, Analytics, YouTube, Bing, Business Profile, PageSpeed) si está
  conectada, qué falta y el siguiente paso. `--probe` valida los tokens contra la
  API; `--next` da la única acción siguiente; `--json` para integración. Directiva
  `onboarding.md` (flujo de 0 a conectado).
- **`health_check.py` — watchdog de salud.** Corre el chequeo maestro, compara vs la
  corrida anterior y alarma (Telegram) si algo se rompe o el score cae.
- **Campaña de autoridad:** `citation_kit.py` (snippets citables con enlace canónico),
  `outreach_tracker.py` (CRM de link-building), `publish_optimize.py` (enlazado interno
  + IndexNow al publicar).

### Changed
- **Multi-tenant real:** la identidad de marca (URL, nombre, autor, dominio) ya no está
  hardcodeada en el código — se lee de la config. El motor corre en cualquier sitio
  cambiando solo `faro.config.json`.
- **195 tests** (antes 110). README al día (comando `doctor` en el quickstart).

### Fixed
- **Arranque roto:** el quickstart decía copiar a `faro.config.json` pero el motor leía
  otro nombre → la config del comprador no cargaba. Ahora `faro.config.json` se lee por
  defecto.
- **`gsc_pull.py` ya no crashea con un token OAuth expirado/revocado** — re-autoriza en
  el navegador en vez de reventar.

## [Unreleased] — 2026-07-29

### Fixed
- **`report_build.py` crasheaba (`KeyError: 'redirects'`) al auditar un sitio en
  frío** — cualquier sitio sin `vercel.json` (todo prospecto crawleado con
  `site_fetch`, todo sitio no-Vercel). El agregador accedía la clave por índice
  directo tras un `if redir:` que un dict nota-only pasaba. Ahora guarda por
  presencia de clave y degrada mostrando la nota del auditor. Rompía el caso de
  uso estrella "audita cualquier sitio". (`01d6504`)
- **`UnicodeEncodeError` en consola Windows (cp1252)** al imprimir emoji
  (`site_fetch` y demás scripts): el quickstart del README no seteaba
  `PYTHONUTF8=1`. Ahora `_common.py` fuerza UTF-8 en `stdout`/`stderr` al import
  (raíz, cubre todos los scripts). (`01d6504`)

### Changed
- Badge y menciones del README: 109 → **110 tests**. (`270beb9`)

## [0.1.0] — 2026-07-29

### Added
- **Motor Faro SEO·GEO** — posicionamiento SEO clásico + GEO (citación por IA):
  auditoría técnica, on-page, schema, enlaces internos, Core Web Vitals,
  keywords/clusters, YouTube, redes, SEO local (GBP), datos reales
  (Search Console/GA4/Trends), Salud SEO 0–100 e informe priorizado. (`42fdd69`)
- **`site_fetch`** — crawler educado (mismo dominio, respeta robots.txt) para
  auditar cualquier sitio (cliente/prospecto) en frío sin tener su código.
  (`fc8f82c`)

### Security
- Fixes de auditoría cyber-neo: path traversal, SSRF, XML-bomb; `.gitignore`
  para tokens. (`0a44682`)

### Supply chain
- `requirements.lock` con versiones fijas + hashes SHA-256 para install
  reproducible y verificado. (`f979252`)

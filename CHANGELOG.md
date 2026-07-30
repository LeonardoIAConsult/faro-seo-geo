# Changelog

Todos los cambios notables de Faro SEO·GEO. Formato basado en
[Keep a Changelog](https://keepachangelog.com/es/1.1.0/).

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

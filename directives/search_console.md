# Directiva 11 — Conexión Google Search Console (OAuth)

**Objetivo:** enchufar los datos reales de ranking del dueño (keywords, posición, clics,
impresiones). Es gratis y es el mejor combustible del SEO. Se hace UNA vez.

## Setup (una sola vez)
1. **Verificar la propiedad** `https://www.example.com/` en https://search.google.com/search-console (ya debería estar si el sitio recibe tráfico).
2. **Google Cloud Console** (https://console.cloud.google.com):
   - Crear/elegir un proyecto.
   - Habilitar **"Google Search Console API"**.
   - APIs y servicios → Credenciales → Crear credenciales → **ID de cliente OAuth** → tipo **App de escritorio**.
   - Descargar el JSON → guardarlo como `credentials.json` en `TOOLS/seo-forge/` (ya en `.gitignore`).
3. **Pantalla de consentimiento OAuth:** modo "Testing" está bien; agregar como usuario de prueba la cuenta que tiene verificada la propiedad en GSC: **`tu-cuenta-gsc@gmail.com`** (misma cuenta del dueño). Autorizar con ESA cuenta en el navegador.
4. Copiar `.env.example` a `.env` y confirmar `GSC_SITE_URL=https://www.example.com/`.

## Primer uso (abre navegador para autorizar)
```powershell
$PY = ".\.venv\Scripts\python.exe"
& $PY execution\gsc_pull.py --report queries --days 90
```
Autoriza en el navegador → se guarda `token.json` (no volver a pedir hasta que caduque).

## Reportes
- `--report queries` — top keywords reales.
- `--report pages` — rendimiento por página.
- `--report opportunities` — posición 5-20 (subir a top 5 = ganancia rápida). **El más accionable.**

## Casos extremos
- `credentials.json` no existe → el script explica el paso 2.
- Error SSL (Norton) → `pip-system-certs` ya en requirements; reinstala en el venv si reaparece.
- GSC tiene ~2 días de lag → el script ya resta 2 días al rango.
- La API pública de GSC NO da el reporte completo de backlinks (ver `backlinks_link_gap.md`).
- **Seguridad:** `credentials.json` y `token.json` son secretos → nunca commitear (están en `.gitignore`).

# Directiva — Auditoría de Redes Sociales (social_audit.py)

**Objetivo:** auditar los perfiles de redes como activos de SEO/GEO (el perfil es una landing;
la bio es tu meta description; Google y la IA los leen). `execution/social_audit.py` es
**enchufable**: cada red es un adaptador que se activa SOLO si tienes su token (si no, se salta y
se reporta honesto). Empieza por la red que puedas conseguir; las demás quedan gated.

**Qué mide por red:** bio con keyword del nicho · link en bio · cadencia (días sin publicar) ·
coherencia de marca (nombre + link al sitio) · seguidores/posts.

---

## Guía para conseguir cada API (paso a paso, para el USUARIO)

> Regla: los tokens van en `.env` (NUNCA en git). Los handles/IDs no-secretos pueden ir en
> `faro.config.json` (`social.*`). Sin token, esa red simplemente no se audita.

### 1. Instagram — la más útil para tu marca (Meta Graph API) · dificultad: media
Requiere cuenta **Business o Creator** (no personal) vinculada a una **página de Facebook**.
1. Convierte tu IG a cuenta **Business/Creator** (Ajustes → Cuenta → Cambiar a profesional).
2. Vincula esa cuenta IG a una **Página de Facebook** (Ajustes de la página → Instagram).
3. Ve a **developers.facebook.com** → *Crear app* → tipo **Business**.
4. Agrega el producto **Instagram Graph API**.
5. En **Graph API Explorer** genera un token con permisos: `instagram_basic`,
   `pages_show_list`, `business_management`. Cámbialo a **token de larga duración** (60 días)
   con el endpoint `oauth/access_token?grant_type=fb_exchange_token`.
6. Consigue tu **IG_USER_ID**: `GET /me/accounts` → toma el `id` de la página → 
   `GET /{page-id}?fields=instagram_business_account`.
7. En `.env`:  `IG_ACCESS_TOKEN=...`  ·  en config:  `"social": { "instagram_user_id": "..." }`
> ⚠️ El token de 60 días caduca — hay que renovarlo (o montar refresh). Se avisa cuando falle.

### 2. Facebook Página (Meta Graph API) · dificultad: media
Misma app de arriba. Token de página (`pages_read_engagement`). En `.env`: `FB_PAGE_TOKEN=...`.
Adaptador `facebook()` = pendiente de implementar (hoy stub gated).

### 3. LinkedIn · dificultad: ALTA
La API de LinkedIn es cerrada: requiere ser **Marketing Developer Partner** (aprobación manual,
suele rechazar perfiles personales). **Realista:** auditoría manual del perfil por ahora, o
scraping cuidadoso con `agent-browser` (respeta ToS). En `.env` (si algún día hay token):
`LINKEDIN_TOKEN=...`. Adaptador = stub gated.

### 4. X / Twitter (API v2) · dificultad: media, DE PAGO
X API v2 es de pago (Basic ~US$100/mes). Para un perfil, el tier gratis apenas da lectura
limitada. **Recomendación:** no priorizar salvo que X sea canal clave. En `.env`:
`X_BEARER_TOKEN=...`. Adaptador = stub gated.

---

## Alternativa SIN APIs (cuando las APIs son un muro)
Para redes cuya API es cara/cerrada, usar **`agent-browser`** (skill ya instalada) para abrir el
perfil público y extraer bio/link/último post — respetando ToS y sin login intrusivo. Es la vía
pragmática para LinkedIn/X. (Pendiente de cablear como adaptador `*_browser`.)

## Prioridad recomendada
1. **Instagram** (tu feed principal; API conseguible) → activar primero.
2. **Facebook Página** (misma app).
3. LinkedIn / X → manual o `agent-browser` hasta que haya token.

## Flujo
1. Consigue el token de al menos 1 red (guía arriba) → `.env` + config.
2. `python execution/social_audit.py` → `.tmp/social_audit.json` + hallazgos por stdout.
3. Los hallazgos (bio sin keyword, sin link, días sin publicar) → arreglar en la red, o pasar a
   NOVA/Desinger_LAP para reescribir bio en la voz.
4. (Futuro) cablear al `report_build` como Sección 8, y sumar cadencia al watchdog semanal.

## Empaquetado (cuando seo-forge se distribuya)
Este módulo es el ejemplo de "trae tu propia key": el `.env.example` lista las vars, esta
directiva es la guía, y sin token la red se salta. Cualquier usuario pone SUS tokens y audita
SUS redes. Ninguna credencial viaja en el repo.

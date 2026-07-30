# Directiva 06 — SEO Local

**Objetivo:** optimizar presencia local si el dueño capta clientes por zona (Colombia / ciudad).

**Alcance (confirmado 2026-07-29):** el SEO local SÍ aplica. Se mide con datos REALES de la ficha
vía `gbp_pull.py` (Google Business Profile), además del checklist + schema.

## Datos reales de la ficha — `gbp_pull.py`

Trae categoría, completitud del perfil, reseñas (media / sin responder) y rendimiento
(impresiones Búsqueda+Maps, clics a la web, llamadas, cómo-llegar). Gratis (APIs oficiales), gated.

**⚠️ GATE DE ACCESO (decir al dueño — no es opcional):** las Business Profile APIs requieren,
además del OAuth:
1. Habilitar en el proyecto Google Cloud: *My Business Account Management API*, *My Business
   Business Information API*, *Business Profile Performance API*.
2. **Solicitud de acceso aprobada por Google** (formulario "Business Profile APIs"). Puede tardar
   días. Hasta la aprobación, las llamadas devuelven **403** y `gbp_pull.py` lo avisa (no rompe).
3. Tener una **ficha GBP verificada** de "Your Brand" / el dueño.

**Flujo:**
1. `gbp_pull.py --report accounts` → descubre account_id + location_id (solo necesita OAuth).
   Guardarlos en `.env` (GBP_ACCOUNT_ID/GBP_LOCATION_ID) o config (`local.account_id/location_id`).
2. `gbp_pull.py --report profile` → completitud 0-100 + categoría + qué campos faltan.
3. `gbp_pull.py --report reviews` → media, distribución, **reseñas sin responder** (acción directa).
4. `gbp_pull.py --report performance --days 30` → cómo te encuentran (Búsqueda vs Maps) + acciones.
5. Interpretar y proponer: completar campos faltantes, responder reseñas, corregir categoría.

**Palancas:**
- **Google Business Profile:** categoría correcta, descripción con keywords, fotos, reseñas, posts. (Gestión fuera del repo — checklist paral dueño.)
- **NAP consistente:** Nombre-Dirección-Teléfono idénticos en web, GBP y directorios. Rellenar en `schema_generate.py --type LocalBusiness`.
- **Schema LocalBusiness** en home/contacto con `address`, `telephone`, `geo`, `openingHours`.
- **Página de contacto** con mapa embebido + NAP en texto (no solo imagen).

**Entradas necesarias del dueño:** dirección, teléfono, ciudad, horario, categoría GBP.

**Salida:** checklist GBP + bloque schema LocalBusiness relleno.

**Casos extremos:** si el negocio es remoto/nacional, priorizar SEO nacional sobre local; no crear
señales locales falsas (dirección inventada = penalización).

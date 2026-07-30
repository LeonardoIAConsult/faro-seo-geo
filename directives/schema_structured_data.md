# Directiva 02 — Schema / Datos estructurados

**Objetivo:** generar JSON-LD válido por tipo de página para rich results y comprensión por IA.

**Mapa de tipos:**
- Home (`/`) → `Person` + `Organization` (el dueño + Your Brand).
- Posts (`/blog/*.html`) → `BlogPosting` (con author, publisher, fecha, imagen).
- Página con FAQs → `FAQPage` (el script detecta patrón pregunta/respuesta).
- Página de servicios/contacto local → `LocalBusiness` (plantilla, rellenar NAP).

**Herramienta:** `execution/schema_generate.py --file <html> --type <Tipo>` → imprime el bloque
`<script type="application/ld+json">` listo para pegar en `<head>`.

**Ejecución:**
```powershell
& $PY execution\schema_generate.py --file "...\blog\que-es-seo-search-engine-optimization.html" --type Article
```

**Salida:** bloque JSON-LD. El orquestador lo inserta en el HTML tras revisar (no automático).

**Casos extremos:**
- Verifica el resultado en https://validator.schema.org antes de dar por bueno.
- No dupliques schema si la página ya tiene uno válido (revisa `onpage.json → jsonld_types`).
- `LocalBusiness` trae campos `TODO` (dirección, teléfono): rellenar con datos reales del WIKI, nunca inventar.

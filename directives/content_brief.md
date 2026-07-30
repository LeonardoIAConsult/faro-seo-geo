# Directiva 09 — Content Brief (SEÑALES SEO, no redacción)

**Objetivo:** dar las señales SEO duras para decidir y armar un artículo. **NO redacta**
(decisión del dueño 2026-07-28): la redacción en la voz la hacen los skills de contenido
(`marca-content-pipeline` / `Desinger_LAP`). content_brief SOLO alimenta con datos.

**Herramienta:** `execution/content_brief.py --keyword "<keyword>"` → señales deterministas:
- **canibalización** (keyword en el TÍTULO de una página = ya la apunta → actualizar, no duplicar),
- **GSC real** de la keyword (posición/impresiones/clics) + queries relacionadas,
- **clúster**: posts relacionados con sus `inlinks`/`ctx_outlinks` (del grafo de `internal_links.py`),
- **longitud** objetivo (media del sitio vs mínimo competitivo),
- **enlazar-desde**: qué posts del clúster deberían enlazar contextualmente al nuevo/actualizado.

**Flujo:**
1. `content_brief.py --keyword "..."` → `.tmp/brief_<slug>.json` (señales puras, sin TODOs).
2. Si `canibalizacion` > 0 → **actualizar** el post existente, no crear duplicado.
3. Pasar las señales a `marca-content-pipeline` / `Desinger_LAP`, que redactan en la voz + diseñan.
4. Validar contra `technical_audit` (title/meta/H1/schema) antes de publicar.
5. Tras publicar: agregar el enlace contextual desde los posts de `enlazar_desde` (autoridad).

**Estándares de un buen post:**
- Title 30-60 chars con keyword al inicio. Meta 70-160 con gancho.
- H1 único = tema. Answer-first en el primer párrafo (GEO).
- ≥ 900 palabras para temas competitivos (o el largo que la intención pida).
- Enlaces internos a pillar + hermanos. Schema Article. Imagen con alt.

**Casos extremos:** no relleno de keywords; no publicar sin OK del dueño; respetar voz canónica.

# Directiva 11 — Auditor de Contenido NOVA (SEO + GEO, auto-fix + auto-aprendizaje)

**Objetivo:** que cada artículo que publica NOVA quede optimizado para (1) posicionar #1 en
buscadores y (2) ser **citado/recomendado por IA** (ChatGPT, Gemini, Perplexity, AI Overviews).
El auditor **corrige solo** lo objetivo, **sugiere** lo subjetivo, **investiga tendencias** en la
web y **aprende** de cada corrida para mejorar su propio criterio.

**Runtime (decisión del dueño 2026-07-27):** corre en **sesiones de Claude Code agendadas** (sin API
key extra). Auto-fix habilitado. Autonomía: sí (ver `## Autonomía`).

**Alcance de datos:** gratis/deterministas + investigación web (WebSearch/WebFetch). Volumen de
keyword y backlinks de competencia = pendiente DataForSEO (el dueño pidió costo antes de decidir).

---

## Cuándo corre
- Diario (o tras un lote de NOVA). El schedule dispara una sesión que ejecuta ESTA directiva.
- Primero procesa **posts nuevos/cambiados** desde la última corrida (ver `last_run` en el learnings).
  Si hay hueco de tiempo, hace un barrido completo de bajo costo.

## Insumos
1. `execution/report_build.py --site <SITE>` → `.tmp/onpage.json` + `technical_audit.json` (estado técnico).
2. HTML de los posts en `tu-sitio-estatico/blog/`.
3. `MARCA/perfil-y-voz.md` + `manifiesto-editorial.md` (voz canónica — NO violarla).
4. GSC (`gsc_pull.py`) para queries/posición reales del post si existen.
5. Web (tendencias + best-practices del mes) — ver `## Investigación de tendencias`.

## Rúbrica de auditoría (puntúa 0-100 por post)
**A. SEO on-page (35 pts)**
- Title 30-60 chars, keyword al inicio, sin relleno (8)
- Meta description 70-160 con gancho (5)
- 1 solo H1 = tema; H2/H3 jerárquicos y descriptivos (6)
- ≥900 palabras si el tema es competitivo (o lo que pida la intención) (6)
- Slug limpio con keyword (3)
- Imágenes con alt descriptivo (ya lo asegura el guardián CI) (3)
- Canonical + en sitemap (4)

**B. GEO / citabilidad por IA (35 pts)**
- **Answer-first:** responde la pregunta central en las 1-2 primeras frases (10) ← clave
- **FAQPage schema** con 2-4 Q&A reales del texto (8) ← clave, hoy 0/66
- H2 en forma de **pregunta** (imita cómo se le pregunta a un LLM) (5)
- TL;DR / resumen extraíble arriba (4)
- Entidades explícitas y enlazadas (el dueño → Your Brand → tema) (4)
- Fecha visible + autor con E-E-A-T (schema Person/Article) (4)

**C. Autoridad temática / enlazado interno (20 pts)**
- ≥3 enlaces internos **contextuales** en el cuerpo a pillar + hermanos del cluster (10) ← hoy ~0
- Encaja en un cluster (pillar identificado); no canibaliza a un hermano (10)

**D. Marca + hashtags/social (10 pts)**
- Tono en la voz canónica; sin promesas de ingresos exageradas (YMYL) (5)
- Hashtags/OG/Twitter correctos para el share (5)

## Auto-fix (aplica sin preguntar — objetivo/reversible)
- FAQPage schema: extraer 2-4 Q&A reales del post → inyectar JSON-LD (ampliar `schema_generate.py` con kind `FAQ` por post).
- Enlaces internos contextuales: el **guardián CI `ensure_links.py`** (2026-08-03, sistema #4) ya da a cada post nuevo su bloque de relacionados + inlinks de hermanos en el push; el auditor MIDE con `internal_links.py` y solo completa enlaces contextuales EN EL CUERPO si faltan (los del bloque de relacionados no cuentan como contextuales).
- Answer-first: si el 1er párrafo no responde, **reordenar** para que la definición/respuesta vaya primero (sin inventar contenido).
- TL;DR: añadir bloque resumen extraíble si falta.
- OG/Twitter/alt: ya lo asegura el guardián CI (`ensure_seo.py`).
- Registrar cada cambio en el commit + en el learnings.

## Sugerir (NO auto-editar — subjetivo)
- Reescritura de title/hook (dar 2-3 opciones en el reporte; el dueño elige).
- Recortes de posts con title/meta largos (56 title largo, 10 meta larga hoy).
- Nuevos posts para llenar gaps de cluster.

## Investigación de tendencias (cada corrida, acota a 2-4 búsquedas)
- Buscar cambios recientes en: algoritmo Google / AI Overviews, best-practices GEO, formato que los
  LLM citan más, keywords emergentes del nicho (IA + negocios + marketing en español).
- Fuentes fiables (Search Engine Land, Google Search Central, Ahrefs/Semrush blog, docs de OpenAI/Google).
- Si algo cambia la rúbrica → actualizar ESTA directiva + anotar en learnings con la fecha y la fuente.

## Autonomía + auto-aprendizaje
- Archivo vivo: `TOOLS/seo-forge/nova-audit-learnings.md`. Cada corrida añade: `last_run`, posts tocados,
  patrones detectados, decisiones, y ajustes de rúbrica por tendencias. Ordenado por fecha, más reciente arriba.
- **Loop de resultados:** guardar posición GSC del post al auditarlo; en corridas siguientes comparar → si
  subió/bajó, anotar qué cambió y refinar el criterio (esto es el "aprender de resultados", requiere GSC + tiempo).
- Higiene: consolidar aprendizajes viejos; no acumular ruido.

## Guardarraíles (duros)
- **Regla de Escritura Humana (REH):** toda pieza cumple `MARCA/regla-escritura-humana.md` — humano de verdad (experiencia real + voz + edición humana), NO evasión de detectores. Corre su checklist §7 (10 casillas) al auditar; señales de "AI slop" (muletillas §2, ritmo uniforme, tono promocional) = FALLA → sugerir reescritura. El tono promocional además baja la cita en IA 26%.
- Nunca inventar datos, testimonios ni cifras (regla Brain). Todo respaldo sale del Brain / assets reales.
- **Citation Kit (sistema #2, 2026-08-03):** toda mención de una cifra del Informe Diagnóstico E&E 2026 (85.6% Semilla · 85% Excel+WhatsApp · 22% sin herramientas · 69.6% solo su ciudad) debe llevar el **enlace canónico del kit** (`MARCA/citation-kit-informe-eye.md`, generado por `citation_kit.py` desde `citation-kit-data.json` — única fuente autorizada). Cifra del informe suelta SIN enlace = FALLA → auto-fix: añadir el enlace canónico (objetivo/reversible). Cifra que NO esté en el data file = inventada → quitar/señalar.
- Nunca violar la voz canónica.
- Nunca relleno de keywords (los LLM y Google penalizan).
- Cambios de contenido público = **auto-fix objetivo OK**; reescritura editorial = requiere OK del dueño.
- Si tras un auto-fix el `technical_audit` empeora → revertir esa corrida.

## Salida por corrida
1. Auto-fixes aplicados + commit al repo del sitio (o PR si el dueño lo prefiere).
2. Reporte breve: posts auditados, puntaje antes/después, sugerencias editoriales pendientes.
3. Entrada nueva en `nova-audit-learnings.md`.

# Directiva 00 — Overview y flujo maestro

**Objetivo:** dar posicionamiento SEO a `www.example.com` con fuentes gratis/deterministas.

## Orden recomendado de ejecución
1. `technical_audit.md` — arreglar HIGH primero (base sana antes de todo).
2. `search_console.md` — conectar GSC (datos reales de ranking).
3. `keyword_research_clusters.md` — con GSC + IA, definir clusters/temas.
4. `core_web_vitals.md` — medir velocidad, priorizar arreglos.
5. `schema_structured_data.md` — datos estructurados por tipo de página.
6. `eeat_evaluation.md` + `geo_ai_seo.md` — calidad + optimización para IA.
7. `content_brief.md` — briefs para keywords de oportunidad.
8. `local_seo.md` — si aplica presencia local.
9. `site_audit_report.md` — compilar informe entregable.

## Reglas transversales
- **No inventar datos.** Backlinks de competencia y volumen de mercado NO están disponibles (sin API de pago). Si falta el dato, escríbelo como "pendiente", no lo estimes como si fuera real.
- **Voz de marca** en toda salida pública (`Brain_Master_Business/MARCA/`).
- **No deploy sin OK del dueño.** Los scripts solo leen/analizan; editar el HTML del sitio es decisión del orquestador tras revisión.
- Todo intermedio en `.tmp/`; el informe final en `Brain/OUTPUTS/seo/`.

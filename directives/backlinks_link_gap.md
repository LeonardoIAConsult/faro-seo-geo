# Directiva 08 — Backlinks & Link Gap

**Objetivo:** entender el perfil de enlaces y detectar oportunidades.

**Alcance honesto — LIMITADO sin API de pago:**
- El perfil de backlinks de COMPETENCIA y el link-gap real requieren Ahrefs/Semrush/Majestic/DataForSEO (de pago). **NO disponible hoy.** No inventar dominios ni métricas.
- Lo que SÍ tenemos gratis:
  - **GSC → "Links"** (enlaces a tu sitio, según Google): revisar en la interfaz de Search Console; la API pública no expone el reporte de links completo.
  - **Enlaces internos** (`onpage.json → internal_links`): optimizar estructura interna (pillar↔cluster) es la palanca de mayor ROI y 100% gratis/en control.

**Flujo gratis recomendado:**
1. Auditar y mejorar **enlazado interno** (mayor impacto inmediato, cero costo): cada post enlaza a su pillar y a 2-3 hermanos relevantes (`content_brief.py` sugiere enlaces internos).
2. Revisar backlinks actuales en la UI de GSC manualmente.
3. **Link building manual:** guest posts, directorios de calidad, menciones (fuera del repo, checklist paral dueño).

**Si en el futuro se contrata DataForSEO:** enchufar en `execution/` un `backlinks_pull.py` (variables ya previstas en `.env.example`).

**Casos extremos:** nunca comprar enlaces (penalización Google). Nunca reportar backlinks de competencia como si los tuviéramos: marcar "requiere API de pago".

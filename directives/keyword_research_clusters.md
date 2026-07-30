# Directiva 07 — Keyword Research + Topic Clusters

**Objetivo:** encontrar oportunidades y agrupar keywords en clusters temáticos para construir
autoridad (modelo pillar + clusters).

**Alcance honesto:** SIN API de pago no hay *volumen de búsqueda de mercado*. Sí tenemos:
- **GSC** (`gsc_pull.py`): keywords reales por las que YA apareces + impresiones + posición.
- **Análisis del sitio** (`onpage.json`): qué temas ya cubres (66 posts).
- **IA:** expandir semilla, agrupar en clusters, mapear intención.

**Flujo:**
1. `gsc_pull.py --report queries --days 90` → keywords reales.
2. `gsc_pull.py --report opportunities` → posición 5-20 = subir rápido (máxima prioridad).
3. `onpage_analyze.py` (si no está `.tmp/onpage.json`) → temas ya cubiertos por el sitio.
4. `gemini_keywords.py` → Gemini agrupa semillas + queries GSC + temas del sitio en **clusters**
   (pillar → hijos), mapea **intención** y detecta **gaps** + `enlazar_desde`. Salida:
   `.tmp/keyword_clusters.json`. Gated por `GOOGLE_GENERATIVE_AI_API_KEY` (sin key = se salta).
5. **Gaps** → candidatos a crear (pasar el pillar/hijo a `content_brief.py`).
6. **Canibalización** → varias URLs compitiendo por la misma query → consolidar (ver `notas` del JSON).

**Salida:** `keyword_clusters.json` (pillar + hijos + intención + gaps + enlazar_desde) en `.tmp/`;
si es un entregable paral dueño, promover a `OUTPUTS/seo/`.

**Casos extremos:** si GSC no está conectado aún, trabaja solo con temas del sitio + expansión IA,
y marca "volumen: no disponible (sin API de pago)". No inventes cifras de volumen.

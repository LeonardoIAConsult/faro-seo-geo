# Directiva 05 — GEO / AI SEO (ChatGPT, Google AI Overviews, Perplexity)

**Objetivo:** que el contenido del dueño sea citado por buscadores con IA, no solo por el
buscador clásico. GEO = Generative Engine Optimization.

**Insumo:** `.tmp/onpage.json` + el HTML de los posts.

**Palancas (orquestador IA revisa/aplica):**
- **Respuestas extraíbles:** cada post debe responder una pregunta concreta en las primeras 1-2 frases (los LLM citan definiciones limpias). Muchos posts ya son "qué es X" — ventaja.
- **Estructura clara:** H2 en forma de pregunta, listas, tablas, TL;DR arriba. Facilita el "chunking" del modelo.
- **Datos estructurados:** `FAQPage`, `Article`, `Person` (ver schema). Ayudan a la máquina a entender entidad y autor.
- **Entidades explícitas:** nombrar conceptos y relacionarlos (el dueño → Your Brand → marketing digital → marca personal). Refuerza el "knowledge graph".
- **Frescura + autoría:** fecha visible + autor con expertise (E-E-A-T se solapa).
- **Accesibilidad al crawler de IA:** `robots.txt` no bloquea GPTBot/PerplexityBot (hoy `Allow: /` ✓). Si el dueño quiere PERMITIR explícitamente, no agregar Disallow para esos bots.

**Salida:** lista de posts prioritarios a reescribir con formato "answer-first" + FAQ schema.

**Casos extremos:** no rellenar de keywords (los LLM penalizan texto no natural). Optimizar para
ser *la fuente más clara y citable*, en la voz de marca.

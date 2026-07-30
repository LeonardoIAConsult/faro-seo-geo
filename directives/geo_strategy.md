# Directiva — GEO a la punta (que la IA cite al dueño) + auto-aprendizaje

**Objetivo:** que ChatGPT/Gemini/Perplexity/AI Overviews **citen y recomienden al dueño**
cuando alguien pregunta por su nicho (IA + automatización para pymes/emprendedores).
GEO es un juego de **sistema + tiempo**, no un fix. seo-forge lo lleva como un loop que aprende.

## Qué mueve la aguja en GEO (las palancas, en orden)
1. **Contenido answer-first que responde LA pregunta exacta.** La IA cita páginas que responden
   directo, con FAQPage, H2 en pregunta, y entidad clara. → lo produce NOVA con las señales de seo-forge.
2. **Autoridad de entidad.** La IA tiene que "entender" que el dueño = consultor de IA para pymes.
   Schema `Person` con `sameAs` + `knowsAbout` (ya está) · bio consistente en todos lados (web, YT, redes) ·
   ser mencionado/enlazado desde sitios que la IA confía (directorios, prensa, guest posts).
3. **Cobertura del espacio de preguntas.** No basta 1 post: hay que cubrir el abanico de preguntas
   del nicho. Cada hueco = un post.
4. **Frescura + estructura.** Contenido actualizado, fechado, con datos propios (Prueba A/B) que la
   IA no puede copiar de otro → te vuelve la fuente citable.
5. **Medición honesta multi-motor.** Gemini+grounding gratis (proxy de AI Overviews); sumar
   ChatGPT/Perplexity (de pago, gate) para señal robusta.

## El LOOP de auto-aprendizaje (así seo-forge te lleva a la punta solo)
Corre semanal (tarea `seo-forge-rank-track`):
1. **`geo_citation.py`** — pregunta a la IA las queries del nicho (config + GSC) → snapshot de quién te
   cita, quién no, y qué competidores dominan → `geo-citation-history.json`.
2. **`geo_learn.py`** — compara contra el historial y **aprende**:
   - traza la trayectoria de cada pregunta (ausente → mencionado → citado),
   - clasifica GANADAS / PERDIDAS / **HUECOS persistentes** / estables,
   - mide la tendencia de la tasa,
   - detecta los competidores que dominan (a estudiar/ganar),
   - deja una observación fechada en **`geo-learnings.md`** (se acumula: el sistema recuerda qué pasó),
   - escribe **`geo-next-actions.json`** = los objetivos priorizados (huecos a atacar + competidor rival).
3. **Contenido dirigido, con GATE de temas (decisión del dueño 2026-07-28):** los `geo-next-actions`
   se convierten en **títulos/ángulos propuestos** en `geo-topics-propuestos.md` (estado `pendiente-aprobacion`).
   **el dueño revisa y aprueba los temas ANTES de escribir nada.** Solo con su OK se emite la orden a NOVA.
   GEO es parte FIJA del plan (2-3 posts/semana), pero los temas siempre pasan por su aprobación.
4. **Re-mide** a la semana → ¿la pregunta pasó de ausente a citado? El learning lo registra → se sabe
   qué ángulo/estructura funcionó → se repite en lo que sí mueve.

> **Auto-aprendizaje real:** cada ciclo el sistema (a) sabe qué preguntas ganó/perdió, (b) prioriza los
> huecos, (c) alimenta el contenido, (d) verifica el efecto. Con las semanas, `geo-learnings.md` acumula
> qué funciona (tipo de pregunta, ángulo, cifra propia) y afina la estrategia. Una sesión LLM puede leer
> el log y promover reglas ("las 'quién es' se ganan con Person+menciones; las 'cómo' con posts answer-first").

## Lo que el dueño debe decidir para acelerar
- **Activar ChatGPT/Perplexity** (keys de pago) → medición multi-motor real. Hoy: solo Gemini (gratis).
- **Autoridad off-site** (backlinks/menciones/directorios) — fuera del sitio; requiere acción (PR, guest posts).
- **Cadencia de contenido GEO** (cuántos posts/semana a los huecos).

## Estado (2026-07-28)
Tasa 0.07 · 8 huecos persistentes (queries genéricas donde la IA cita a la competencia: google,
tuimpulsalab, godaddy, esade, mailchimp). 3 posts GEO ya publicados (aún sin indexar/citar — toma semanas).
Próximo: NOVA ataca los `geo-next-actions` → re-medir en 2-3 semanas.

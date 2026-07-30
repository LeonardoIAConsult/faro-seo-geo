# Directiva — Medidor de citación GEO

## Objetivo
Saber si la IA (ChatGPT/Gemini/Perplexity, vía AI Overviews) **de hecho cita** al dueño cuando alguien del nicho pregunta. Optimizar para GEO sin medir la citación es trabajar a ciegas. Cierra el hueco #1 de seo-forge.

## Cómo funciona
`execution/geo_citation.py` le hace a **Gemini con Google Search grounding** (la misma mecánica que alimenta AI Overviews) las preguntas que haría un cliente del nicho, y clasifica cada respuesta:
- **CITADO (fuente):** el dominio del dueño es una de las URLs que el modelo usó → señal GEO real y fuerte.
- **mencionado (texto):** aparece en la respuesta pero no como fuente citada → señal débil.
- **ausente:** no aparece → el competidor se lleva ese cliente.

Además captura **qué dominios dominan** cada pregunta = inteligencia de competencia GEO.

## Cuándo correrlo
- Mensual (o tras un empujón de contenido). Gasta ~10 llamadas a Gemini (segundos, casi gratis).
- `python execution/geo_citation.py` — requiere `GOOGLE_GENERATIVE_AI_API_KEY` (la misma de gbrain, ya seteada).
- Histórico en `geo-citation-history.json` → ves si la tasa sube corrida a corrida.

## Cómo leer el resultado
- **Tasa de citación** (citado/preguntas): meta = subirla en las preguntas GENÉRICAS del nicho, no solo en las de marca (esas son fáciles).
- **Ausente en genéricas** = donde están los clientes reales. Ahí hay que ganar terreno con contenido answer-first + FAQ + autoridad.
- **Top competidores** = a quién estudiar (qué contenido/estructura tienen que la IA prefiere).

## Cómo subir la tasa (acciones)
1. Crear/reforzar posts que respondan EXACTAMENTE esas preguntas genéricas (answer-first, FAQPage, datos citables).
2. Autoridad (E-E-A-T): la IA cita fuentes con señales de confianza → autor, experiencia real, datos propios (los 125 diagnosticados).
3. Con el tiempo, backlinks (DataForSEO) para ganarle autoridad a los competidores del top.

## Editar las preguntas
La lista `QUERIES` vive en el script. Añadir/quitar preguntas del nicho ahí. `BRAND_DOMAIN`/`BRAND_NAMES` = lo que cuenta como "aparición del dueño".

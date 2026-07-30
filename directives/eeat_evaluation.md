# Directiva 04 — E-E-A-T (Experiencia, Expertise, Autoridad, Confianza)

**Objetivo:** evaluar y subir las señales de calidad que Google usa para contenido, sobre todo
en YMYL (dinero/negocios — el nicho del dueño).

**Insumo determinista:** `.tmp/onpage.json` (autor, schema Person, enlaces, longitud).

**Evaluación (orquestador IA sobre cada post/página clave):**
- **Experience:** ¿hay experiencia de primera mano? (casos reales, clientes: tus clientes reales — usar `tu-sitio-estatico/testimonios` y `/clientes`).
- **Expertise:** bio de autor visible, credenciales (CV en `docs/`), schema `Person` con `sameAs`.
- **Authoritativeness:** enlaces salientes a fuentes fiables, menciones, backlinks (ver GSC).
- **Trust:** HTTPS (✓), páginas legales (`/legal/` ✓ privacidad/términos/cookies), contacto claro, sin claims sin respaldo.

**Checklist de salida por página YMYL:**
1. ¿Autor identificado + bio + enlace a perfil? 
2. ¿Schema Person/Article con author?
3. ¿Fecha de publicación/actualización visible?
4. ¿Fuentes citadas?
5. ¿CTA honesto, sin promesas exageradas de ingresos?

**Casos extremos:** no fabricar credenciales ni testimonios. Todo respaldo sale del Brain / assets reales.
Marca en Aprendizajes las páginas que faltan de bio de autor para arreglo por lote.

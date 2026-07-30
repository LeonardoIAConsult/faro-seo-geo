# Directiva 03 — Core Web Vitals

**Objetivo:** medir y mejorar LCP, INP, CLS (métricas de experiencia que Google usa para rankear).

**Herramienta:** `execution/core_web_vitals.py` — PageSpeed Insights API (gratis).
Con `PAGESPEED_API_KEY` en `.env` sube el límite a 25.000/día; sin key funciona limitado.

**Ejecución:**
```powershell
& $PY execution\core_web_vitals.py --url https://www.example.com/ --strategy mobile
& $PY execution\core_web_vitals.py --url https://www.example.com/ --strategy desktop
```

**Umbrales "bueno" (Google):** LCP ≤ 2.5s · INP ≤ 200ms · CLS ≤ 0.1.

**Salida:** `.tmp/cwv.json` con score + lab (Lighthouse) + campo (CrUX real de usuarios).
Prioriza el dato de **campo** si existe; el lab es proxy.

**Palancas típicas en sitio estático Vercel:**
- LCP: optimizar imagen hero (webp, tamaño, `fetchpriority=high`, preload), fuentes con `font-display:swap`.
- CLS: dimensiones explícitas en `<img>`, reservar espacio para elementos que cargan tarde.
- INP: reducir JS de terceros (GA/reCAPTCHA ya en CSP), diferir scripts no críticos.

**Casos extremos:**
- Página nueva sin tráfico → sin datos de campo CrUX; usa lab.
- Error SSL → Norton; confirma `pip-system-certs` en el venv.
- Rate limit sin key → espera unos segundos o añade `PAGESPEED_API_KEY`.

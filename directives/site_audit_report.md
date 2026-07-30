# Directiva 10 — Site Audit + Reporting

**Objetivo:** ejecutar la auditoría completa y generar un informe profesional entregable.

**Herramienta:** `execution/report_build.py --site "<ruta>"` — corre los análisis deterministas
(onpage, technical, sitemap/robots), agrega los opcionales si existen (CWV, GSC) y compila Markdown.

**Ejecución:**
```powershell
& $PY execution\report_build.py --site "C:\Users\Tu Usuario\Documents\tu-sitio-estatico"
```

**Para un informe COMPLETO, antes corre los opcionales (red/OAuth):**
```powershell
& $PY execution\core_web_vitals.py --url https://www.example.com/ --strategy mobile
& $PY execution\gsc_pull.py --report opportunities --days 90
& $PY execution\report_build.py --site "..."
```

**Salida:** `Brain/OUTPUTS/seo/informe-seo-YYYY-MM-DD.md` con: salud técnica, indexación, Core Web
Vitals, oportunidades de ranking (GSC), contenido a reforzar.

**Entrega a cliente:** convertir a PDF con `/make-pdf` si el dueño quiere formato presentable.

**Casos extremos:** si CWV/GSC no corrieron, el informe los marca "pendiente" (no inventa). El informe
es reproducible: borra `.tmp/` y vuelve a correr.

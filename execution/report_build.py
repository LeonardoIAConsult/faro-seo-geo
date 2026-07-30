"""seo-forge — compila el informe SEO completo en Markdown (Capa 3).

Agrega los intermedios de .tmp/ (onpage, technical_audit, sitemap_robots, cwv, gsc_*)
en un informe profesional listo para revisar/entregar.
Corre los sub-análisis que falten (deterministas). NO llama GSC/PSI si no hay datos
(esos requieren red/OAuth) — los marca como "pendiente".

Salida: OUTPUTS/seo/informe-seo-YYYY-MM-DD.md  (dentro del Brain) o .tmp si no existe.
Uso:  python execution/report_build.py --site "<ruta>"
"""
from __future__ import annotations

import json
import subprocess
import sys
from collections import Counter
from datetime import date
from pathlib import Path

from _common import ROOT, TMP, now, site_dir, site_url


def ensure(script, root):
    subprocess.run([sys.executable, str(Path(__file__).with_name(script)), "--site", str(root)], check=True)


def load(name):
    f = TMP / name
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None


def fresh_note(name):
    """G1: marca la antigüedad de un intermedio que NO se regenera en cada informe
    (CWV/GSC/GEO/YouTube usan red/OAuth). Así el informe no miente por datos viejos."""
    import time
    f = TMP / name
    if not f.exists():
        return ""
    age = (time.time() - f.stat().st_mtime) / 86400
    if age < 1:
        return ""
    warn = " — ⚠️ **desactualizado, re-corre el script**" if age >= 7 else ""
    return f"  _(datos de hace {int(age)} día{'s' if int(age) != 1 else ''}{warn})_"


def main():
    root = site_dir()
    # deterministas: siempre frescos
    ensure("onpage_analyze.py", root)
    ensure("technical_audit.py", root)
    ensure("sitemap_robots_check.py", root)
    ensure("schema_validate.py", root)
    ensure("internal_links.py", root)
    ensure("redirect_audit.py", root)
    for opt in ("functional_audit.py", "dup_check.py"):  # soft (functional usa red)
        try:
            subprocess.run([sys.executable, str(Path(__file__).with_name(opt)), "--site", str(root)],
                           check=False, timeout=150)
        except Exception:
            pass

    onpage = load("onpage.json")
    tech = load("technical_audit.json")
    smr = load("sitemap_robots.json")
    cwv = load("cwv.json")       # opcional (red)
    gsc = load("gsc_opportunities.json")  # opcional (OAuth)
    func = load("functional_audit.json")  # salud funcional
    dup = load("dup_check.json")          # duplicados
    schema = load("schema_validate.json") # validez JSON-LD
    ilinks = load("internal_links.json")  # enlazado interno (autoridad + descubrimiento)
    redir = load("redirect_audit.json")   # redirects (fugas SEO)
    idxreal = load("index_inspect.json")  # índice REAL de Google (corre index_inspect.py; OAuth GSC)
    bing_t = load("bing_traffic.json")    # Bing: rendimiento (corre bing_pull.py; BING_API_KEY)
    bing_q = load("bing_queries.json")    # Bing: keywords reales
    geo = load("geo_citation.json")       # ¿te cita la IA? (corre geo_citation.py)
    yt = load("youtube.json")             # canal YouTube (corre youtube_pull.py; requiere YT_API_KEY)
    ga4_ov = load("ga4_overview.json")    # comportamiento real (corre ga4_pull.py; requiere GA4_PROPERTY_ID + OAuth)
    ga4_pg = load("ga4_pages.json")       # páginas top por vistas
    ga4_ch = load("ga4_channels.json")    # canales de adquisición

    d = date.today().isoformat()
    L = []
    L.append(f"# Informe SEO — {site_url()}")
    L.append(f"\n_Generado por seo-forge · {now()}_\n")
    L.append(f"**Páginas analizadas:** {onpage['count']}\n")

    # Salud SEO: score compuesto + diff vs la corrida anterior (lo primero que se lee)
    import report_score
    L.append(report_score.section(onpage, tech, func, schema, geo))
    L.append("")

    # Salud funcional (lo primero: si no convierte, el SEO no importa)
    L.append("## 0. Salud funcional (¿la web convierte?)")
    if func:
        r = func["resumen"]
        forms_ko = [x for x in func["forms"] if x["ok"] is False]
        L.append(f"\n- Formularios: **{r['forms']}** — " +
                 (f"🔴 {len(forms_ko)} ROTOS" if forms_ko else "✅ endpoint(s) OK"))
        for x in forms_ko:
            L.append(f"  - 🔴 {x['endpoint']} — {x['detail']}")
        L.append(f"- Enlaces internos rotos: **{r['enlaces_rotos']}** · Assets faltantes: "
                 f"**{r['assets_faltantes']}** · CTAs sin destino: **{r['ctas_vacios']}**")
        for x in func["findings"][:12]:
            L.append(f"  - {x['sev']} · {x['tipo']}: {x['detalle']}")
    else:
        L.append("\n_Pendiente: corre `functional_audit.py`._")
    if dup:
        n = len(dup["pares_duplicados"])
        L.append("- Contenido duplicado: **" + ("✅ 0 (único)" if n == 0 else f"🔴 {n} pares") + "**")
        for p in dup["pares_duplicados"][:8]:
            L.append(f"  - {p['sim']} · {p['a']} ↔ {p['b']}")
    if schema:
        ni = schema["json_invalido"]
        nf = len(schema["issues"])
        estado = "✅ válido (genera rich results)" if (ni == 0 and nf == 0) else f"🔴 {ni} JSON inválido · {nf} campos faltantes"
        L.append(f"- Schema JSON-LD ({schema['paginas_con_schema']} páginas): **{estado}**")
        for i in schema["issues"][:8]:
            L.append(f"  - 🔴 {i}")
        nrec = len(schema.get("recomendaciones", []))
        if nrec:
            L.append(f"  - 💡 {nrec} campo(s) recomendado(s) para mejorar rich results "
                     "(opcional, no rompe): ver `schema_validate.json`")
    L.append("")

    # Resumen técnico
    s = tech["summary"]
    L.append("## 1. Salud técnica")
    L.append(f"\n| Severidad | Hallazgos |\n|---|---|\n| 🔴 HIGH | {s.get('HIGH',0)} |\n| 🟡 MED | {s.get('MED',0)} |\n| 🟢 LOW | {s.get('LOW',0)} |\n")
    highs = [f for f in tech["findings"] if f["severity"] == "HIGH"]
    if highs:
        L.append("### Prioridad alta (arreglar primero)\n")
        for f in highs[:25]:
            L.append(f"- **{f['url']}** — {f['issue']}. _{f['fix']}_")
    L.append("")

    # Sitemap
    L.append("## 2. Indexación (sitemap / robots)")
    L.append(f"\n- Páginas en disco: **{smr['real_pages']}** · en sitemap: **{smr['sitemap_urls']}**")
    if smr["real_not_in_sitemap"]:
        L.append(f"- 🟡 **{len(smr['real_not_in_sitemap'])} páginas huérfanas** (no en sitemap): " +
                 ", ".join(smr["real_not_in_sitemap"][:10]))
    if smr["in_sitemap_not_real"]:
        L.append(f"- 🔴 **{len(smr['in_sitemap_not_real'])} URLs fantasma** (en sitemap, sin archivo).")
    for f in smr["findings"]:
        if "url" not in f:
            L.append(f"- {f['issue']} — _{f['fix']}_")
    if redir and "redirects" in redir:
        canon = "✅" if redir.get("canonico_host") else "🔴 FALTA"
        L.append(f"- Redirects: **{redir['redirects']}** · canónico de host: {canon} · "
                 f"fugas: **{len(redir['findings'])}**")
        for f in redir["findings"][:6]:
            L.append(f"  - {f['sev']} · {f['tipo']}: {f['detalle']}")
    elif redir and redir.get("nota"):
        L.append(f"- Redirects: _{redir['nota']}_")
    L.append("")

    # Índice REAL de Google (qué indexa/excluye de verdad, no lo que creemos)
    L.append("## 2b. Índice real de Google (URL Inspection)" + fresh_note("index_inspect.json"))
    if idxreal:
        b = idxreal["buckets"]
        L.append(f"\n- De **{idxreal['total']}** URLs del sitemap: **{b['indexed']} indexadas** · "
                 f"{b['excluded']} excluidas · {b['unknown']} desconocidas"
                 + (f" · {idxreal['errores']} error(es) API" if idxreal.get("errores") else ""))
        conf = idxreal.get("conflictos_canonical", [])
        if conf:
            L.append(f"- 🔴 **{len(conf)} conflicto(s) de canónica** (Google ignora tu `canonical`):")
            for r in conf[:8]:
                L.append(f"  - {r['url']} → Google usa `{r['google_canonical']}`")
        if idxreal.get("excluidas"):
            L.append(f"- 🟡 Excluidas del índice (arreglar para que aparezcan): "
                     f"**{len(idxreal['excluidas'])}**")
            for r in idxreal["excluidas"][:10]:
                L.append(f"  - {r['url']} — _{r['motivo']}_")
        if idxreal.get("desconocidas"):
            L.append(f"- 🟡 Aún desconocidas para Google (pedir indexación / esperar crawl): "
                     f"**{len(idxreal['desconocidas'])}**")
            for r in idxreal["desconocidas"][:10]:
                L.append(f"  - {r['url']}")
    else:
        L.append("\n_Pendiente: corre `index_inspect.py` (URL Inspection API; usa el OAuth de GSC)._")
    L.append("")

    # Core Web Vitals
    L.append("## 3. Core Web Vitals" + fresh_note("cwv.json"))
    if cwv:
        L.append(f"\n- **Score performance ({cwv['strategy']})**: {cwv['performance_score']}/100")
        L.append(f"- Lab: LCP {cwv['lab']['LCP']} · CLS {cwv['lab']['CLS']} · TBT {cwv['lab']['TBT']}")

        def crux(v):  # field_crux trae {'p75':..,'category':..}; si no hay datos de campo, dilo
            if isinstance(v, dict):
                p75 = v.get("p75")
                return f"{p75} ({v.get('category')})" if p75 is not None else "s/d"
            return str(v)
        f = cwv["field_crux"]
        campo = f"LCP {crux(f['LCP'])} · INP {crux(f['INP'])} · CLS {crux(f['CLS'])}"
        if all(isinstance(f[k], dict) and f[k].get("p75") is None for k in ("LCP", "INP", "CLS")):
            campo = "sin datos de campo (tráfico insuficiente para CrUX) — usa los de laboratorio"
        L.append(f"- Campo (CrUX): {campo}")
    else:
        L.append("\n_Pendiente: corre `core_web_vitals.py` (requiere red)._")
    L.append("")

    # GSC
    L.append("## 4. Oportunidades de ranking (Search Console)" + fresh_note("gsc_opportunities.json"))
    if gsc:
        L.append("\nKeywords en posición 5-20 (subir a top 5 = ganancia rápida):\n")
        L.append("| Keyword | Pos | Impresiones | Clics |\n|---|---|---|---|")
        for r in gsc["rows"][:20]:
            L.append(f"| {r['query']} | {r['position']} | {r['impressions']} | {r['clicks']} |")
    else:
        L.append("\n_Pendiente: conecta GSC y corre `gsc_pull.py --report opportunities` (requiere OAuth)._")
    L.append("")

    # GEO: ¿te cita la IA?
    L.append("## 4b. Citación GEO (¿te cita la IA?)" + fresh_note("geo_citation.json"))
    if geo:
        engs = ", ".join(geo.get("engines", [])) or geo.get("model", "gemini")
        L.append(f"\n- Medido en **{engs}** con búsqueda web ({geo['queries']} preguntas del nicho + GSC)")
        L.append(f"- **Citado (alguna IA): {geo['citado']}/{geo['queries']}** · Mencionado: "
                 f"{geo['mencionado']}/{geo['queries']} · Tasa: **{geo['tasa_citacion']}**")
        pm = geo.get("por_motor", {})
        if len(pm) > 1:
            L.append("- Por motor: " + " · ".join(
                f"{k} {v['citado']}/{v['queries']}" for k, v in pm.items()))
        if geo["top_competidores"]:
            L.append("- Dominios que dominan tu nicho en la IA (a quién le ganas terreno):")
            for c in geo["top_competidores"][:8]:
                L.append(f"  - {c['apariciones']}× {c['dominio']}")
        aus = [r["query"] for r in geo["detalle"] if r["status"] == "ausente"]
        if aus:
            L.append(f"- 🟡 Ausente en {len(aus)} preguntas genéricas (ahí están los clientes): " +
                     "; ".join(aus[:5]))
    else:
        L.append("\n_Pendiente: corre `geo_citation.py` (mide si ChatGPT/Gemini/Perplexity te citan)._")
    L.append("")

    # Comportamiento real: GSC/GEO dicen qué te busca; GA4 dice qué hacen al llegar.
    L.append("## 4c. Comportamiento real (Google Analytics)" + fresh_note("ga4_overview.json"))
    if ga4_ov and ga4_ov.get("rows"):
        o = ga4_ov["rows"][0]
        dur = o.get("averageSessionDuration", 0)
        L.append(f"\n- Ventana: **{ga4_ov.get('days', 28)} días**")
        L.append(f"- Usuarios: **{int(o.get('activeUsers', 0))}** · Sesiones: "
                 f"**{int(o.get('sessions', 0))}** · Vistas: **{int(o.get('screenPageViews', 0))}**")
        L.append(f"- Engagement: **{round(o.get('engagementRate', 0) * 100)}%** · "
                 f"Duración media sesión: **{int(dur // 60)}m {int(dur % 60)}s** · "
                 f"Key events: **{int(o.get('keyEvents', 0))}**")
        if ga4_ch and ga4_ch.get("rows"):
            canales = " · ".join(f"{c['sessionDefaultChannelGroup']} {int(c['sessions'])}"
                                 for c in ga4_ch["rows"][:6])
            L.append(f"- Canales (sesiones): {canales}")
        if ga4_pg and ga4_pg.get("rows"):
            L.append("\nPáginas más vistas:\n")
            L.append("| Página | Vistas | Engagement |\n|---|---|---|")
            for r in ga4_pg["rows"][:10]:
                L.append(f"| {r['pagePath']} | {int(r['screenPageViews'])} | "
                         f"{round(r.get('engagementRate', 0) * 100)}% |")
    else:
        L.append("\n_Pendiente: corre `ga4_pull.py` (requiere `GA4_PROPERTY_ID` numérico + OAuth)._")
    L.append("")

    # Bing (2º buscador; además alimenta ChatGPT Search + Copilot = señal GEO)
    L.append("## 4d. Bing (2º buscador + señal GEO)" + fresh_note("bing_traffic.json"))
    if bing_t or bing_q:
        if bing_t:
            s = bing_t["resumen"]
            L.append(f"\n- Rendimiento ({s['dias']} días): **{s['impresiones']} impresiones · "
                     f"{s['clics']} clics** · CTR {s['ctr']}")
        if bing_q and bing_q.get("queries"):
            L.append("- Top keywords en Bing (aparecer aquí = presencia en ChatGPT/Copilot):")
            for q in bing_q["queries"][:8]:
                L.append(f"  - {q['impresiones']} imp · pos {q['pos_impresion']} · {q['query']}")
    else:
        L.append("\n_Pendiente: corre `bing_pull.py` (gratis; requiere `BING_API_KEY` + sitio "
                 "verificado en Bing WMT — importable 1-clic desde GSC)._")
    L.append("")

    # Contenido delgado. Excluye noindex (plantillas/legales no son contenido público → ruido),
    # igual que la sección técnica; antes la 5 los contaba e inflaba el reporte.
    def _noidx(p):
        return "noindex" in (p.get("meta_robots") or "").lower()
    pub = [p for p in onpage["pages"] if not _noidx(p)]
    thin = [p for p in pub if p["word_count"] < 300 and p["url"] != "/"]
    noschema = [p for p in pub if not p["jsonld_types"]]
    L.append("## 5. Contenido a reforzar")
    L.append(f"\n- Páginas públicas con <300 palabras: **{len(thin)}**"
             + ("" if not thin else " — " + ", ".join(f"{p['url']} ({p['word_count']}w)" for p in thin[:10])))
    L.append(f"- Sin datos estructurados: **{len(noschema)}**"
             + ("" if not noschema else " — " + ", ".join(p["url"] for p in noschema[:10])))
    L.append(f"- Con imágenes sin alt: **{sum(1 for p in pub if p['images_no_alt']>0)}**\n")

    # YouTube (2o buscador del mundo; cada video posiciona y lo citan Google + IA)
    L.append("## 6. YouTube (descubrimiento + citación)" + fresh_note("youtube.json"))
    if yt:
        vids = yt["videos"]
        con = yt.get("con_issues", sum(1 for v in vids if v["issues"]))
        L.append(f"\n- Canal **{yt['channel']}** — {len(vids)} videos analizados · "
                 f"**{con} con issues SEO**")
        # issues más comunes (dónde está la palanca)
        import re
        issue_kind = Counter()
        for v in vids:
            for it in v["issues"]:
                key = re.sub(r"\d+", "N", it.split("—")[0].split("(")[0]).strip()
                issue_kind[key] += 1
        if issue_kind:
            L.append("- Problemas más comunes (arreglar en lote = mayor palanca):")
            for k, n in issue_kind.most_common(6):
                L.append(f"  - {n}× {k}")
        # peores con tracción: los que YA tienen vistas y tienen issues (arreglar primero)
        con_traccion = sorted([v for v in vids if v["issues"] and v["views"] > 0],
                              key=lambda v: -v["views"])[:8]
        if con_traccion:
            L.append("\nPrioridad (ya tienen vistas + tienen issues → arreglar primero):\n")
            L.append("| Vistas | Video | Issues |\n|---|---|---|")
            for v in con_traccion:
                L.append(f"| {v['views']} | [{v['title'][:45]}]({v['url']}) | {len(v['issues'])} |")
        L.append("\n_Optimización redactada en la voz → `OUTPUTS/youtube/`. "
                 "Auto-aplicar = OAuth de YouTube (gate: OK el dueño)._")
    else:
        L.append("\n_Pendiente: corre `youtube_pull.py --max 25` (requiere `YT_API_KEY` gratis)._")
    L.append("")

    # Enlazado interno (autoridad + descubrimiento)
    L.append("## 7. Enlazado interno (autoridad + descubrimiento)")
    if ilinks:
        r = ilinks["resumen"]
        L.append(f"\n- Huérfanas de enlace (0 inlinks): **{r['huerfanas']}**"
                 + (f" 🔴 {', '.join(ilinks['huerfanas'][:8])}" if r["huerfanas"] else " ✅"))
        L.append(f"- Inalcanzables desde la home: **{r['inalcanzables']}**"
                 + (" ✅" if not r["inalcanzables"] else ""))
        L.append(f"- Con < {ilinks['min_contextual']} enlaces contextuales (cuerpo): "
                 f"**{r['pobres_contextual']}**"
                 + (f" — {', '.join(ilinks['pobres_contextual'][:8])}" if r["pobres_contextual"] else " ✅"))
        if ilinks["mas_profundas"]:
            peor = ilinks["mas_profundas"][0]
            L.append(f"- Página más profunda: {peor['url']} (clic-depth {peor['depth']})")
    else:
        L.append("\n_Pendiente: corre `internal_links.py`._")
    L.append("")

    L.append("---\n_Reproducible: borra `.tmp/` y corre `report_build.py` de nuevo._")

    out_dir = ROOT.parent.parent / "OUTPUTS" / "seo"
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        out = out_dir / f"informe-seo-{d}.md"
    except OSError:
        out = TMP / f"informe-seo-{d}.md"
    out.write_text("\n".join(L), encoding="utf-8")
    print(f"Informe SEO -> {out}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
import urllib.request, urllib.parse, xml.etree.ElementTree as ET
import json, re, html, hashlib
from pathlib import Path
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone, timedelta

OUT = Path(__file__).with_name("blog-data.json")
MAX_PER_LANG = 54
DAYS = 365

QUERIES = {
    "fr": [
        '"Power BI" OR "tableau de bord" OR "business intelligence"',
        '"Power Query" OR "préparation des données" OR "transformation des données"',
        '"langage R" OR "programmation R" OR "R analyse de données"',
        '"analyse de données" OR "visualisation de données" OR "data visualisation"',
        '"reporting" OR "indicateurs de performance" OR "KPI"',
        '"cartographie" OR "analyse géographique" OR "données géospatiales"'
    ],
    "en": [
        '"Power BI" OR dashboard OR "business intelligence"',
        '"Power Query" OR "data preparation" OR "data transformation"',
        '"R programming" OR "R data science" OR "R analytics"',
        '"data analysis" OR "data visualization" OR analytics',
        'reporting OR KPI OR "performance indicators"',
        'mapping OR geospatial OR "geographic analysis"'
    ]
}

LOCALE = {
    "fr": ("fr", "FR", "FR:fr"),
    "en": ("en-US", "US", "US:en")
}

def clean(text):
    text = re.sub(r'<[^>]+>', ' ', text or '')
    text = html.unescape(text)
    return re.sub(r'\s+', ' ', text).strip()

def classify(title, lang):
    t = title.lower()
    if "power query" in t or "transformation" in t or "préparation" in t or "data preparation" in t or "data wrangling" in t:
        theme = "Préparation des données" if lang=="fr" else "Data preparation"
        subject = "Power Query"
    elif "power bi" in t or "dashboard" in t or "tableau de bord" in t:
        theme = "Tableaux de bord" if lang=="fr" else "Dashboards"
        subject = "Power BI"
    elif re.search(r'(^|[^a-z])r([^a-z]|$)', t) or "rstudio" in t or "posit" in t:
        theme = "Formation" if lang=="fr" else "Training"
        subject = "R"
    elif "cartograph" in t or "geospatial" in t or "mapping" in t or "géograph" in t:
        theme = "Analyse de données" if lang=="fr" else "Data analysis"
        subject = "Cartographie" if lang=="fr" else "Mapping"
    elif "report" in t or "kpi" in t or "indicateur" in t:
        theme = "Tableaux de bord" if lang=="fr" else "Dashboards"
        subject = "Reporting"
    else:
        theme = "Analyse de données" if lang=="fr" else "Data analysis"
        subject = "Analyse" if lang=="fr" else "Analysis"
    return theme, subject

def fetch_feed(query, lang):
    hl, gl, ceid = LOCALE[lang]
    params = urllib.parse.urlencode({"q":query, "hl":hl, "gl":gl, "ceid":ceid})
    url = "https://news.google.com/rss/search?" + params
    req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0 ConsultationDataBlog/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read()
    root = ET.fromstring(raw)
    return root.findall(".//item")

def main():
    cutoff = datetime.now(timezone.utc) - timedelta(days=DAYS)
    collected = {"fr":{}, "en":{}}

    for lang, queries in QUERIES.items():
        for q in queries:
            try:
                items = fetch_feed(q, lang)
            except Exception as e:
                print("Feed error", lang, q, e)
                continue

            for item in items:
                title = clean(item.findtext("title"))
                url = clean(item.findtext("link"))
                desc = clean(item.findtext("description"))
                pub = item.findtext("pubDate") or ""
                source_el = item.find("source")
                source = clean(source_el.text if source_el is not None else "")
                try:
                    dt = parsedate_to_datetime(pub)
                    if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
                except Exception:
                    continue
                if dt < cutoff:
                    continue
                if not title or not url:
                    continue

                # Remove source suffix often appended by Google News
                if source and title.endswith(" - " + source):
                    title = title[:-(len(source)+3)].strip()

                theme, subject = classify(title + " " + desc, lang)
                key = hashlib.sha1((title.lower()+source.lower()).encode()).hexdigest()[:14]
                excerpt = desc
                if len(excerpt) > 230:
                    excerpt = excerpt[:227].rsplit(" ",1)[0] + "…"
                if not excerpt:
                    excerpt = ("Article récent sélectionné pour sa pertinence avec les services de Consultation Data."
                               if lang=="fr" else
                               "Recent article selected for its relevance to Consultation Data services.")
                collected[lang][key] = {
                    "id": f"{lang}-{key}",
                    "lang": lang,
                    "title": title,
                    "source": source or "Google News",
                    "date": dt.date().isoformat(),
                    "url": url,
                    "theme": theme,
                    "subject": subject,
                    "excerpt": excerpt
                }

    articles = []
    for lang in ("fr","en"):
        vals = sorted(collected[lang].values(), key=lambda x:x["date"], reverse=True)[:MAX_PER_LANG]
        articles.extend(vals)

    OUT.write_text(json.dumps({"updated":datetime.now(timezone.utc).isoformat(), "articles":articles}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(articles)} articles to {OUT}")

if __name__ == "__main__":
    main()

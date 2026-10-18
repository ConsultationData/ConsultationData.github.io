#!/usr/bin/env python3
import urllib.request, urllib.parse, xml.etree.ElementTree as ET
import json, re, html, hashlib
from pathlib import Path
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone, timedelta

OUT = Path(__file__).with_name("blog-data.json")
MAX_PER_LANG = 54
DAYS = 540

SOURCE_ALLOW = {
    "fr": [
        "LeBigData", "DataScientest", "LeMagIT", "Journal du Net",
        "ActuIA", "Microsoft", "Microsoft Fabric", "Microsoft Learn",
        "Université Laval", "Posit"
    ],
    "en": [
        "Microsoft Fabric Community", "Microsoft Learn", "Microsoft",
        "Posit", "Posit Open Source", "DataCamp", "KDnuggets",
        "Towards Data Science", "InfoWorld", "TechTarget",
        "R-bloggers", "Data Science Central"
    ]
}

THEMES = {
    "fr": {
        "Langage de programmation": ["programmation","langage","code","dax","script","fonction","package","ide"],
        "Visualisation de données": ["visualisation","tableau de bord","dashboard","graphique","reporting","storytelling"],
        "Analyse de données": ["analyse","analytics","adoption","entreprise","roi","décision","performance","data science"]
    },
    "en": {
        "Programming language": ["programming","language","code","dax","script","function","package","ide"],
        "Data visualization": ["visualization","dashboard","chart","reporting","storytelling","visual"],
        "Data analysis": ["analysis","analytics","adoption","enterprise","roi","decision","performance","data science"]
    }
}

SUBJECT_QUERIES = {
    "R": ['"R programming"', '"R language"', 'RStudio', 'Posit', 'tidyverse', '"R data science"'],
    "Power BI": ['"Power BI"'],
    "Power Query": ['"Power Query"', '"M language"', '"langage M"']
}

LOCALE = {"fr":("fr","FR","FR:fr"), "en":("en-US","US","US:en")}

def clean(text):
    text = re.sub(r'<[^>]+>', ' ', text or '')
    return re.sub(r'\s+', ' ', html.unescape(text)).strip()

def allowed_source(source, lang):
    s=(source or "").lower()
    return any(x.lower() in s for x in SOURCE_ALLOW[lang])

def subject_match(text, subject):
    t=text.lower()
    if subject=="R":
        return bool(re.search(r'(^|[^a-z])r([^a-z]|$)', t)) or any(x in t for x in ["rstudio","posit","tidyverse"])
    if subject=="Power BI":
        return "power bi" in t
    if subject=="Power Query":
        return "power query" in t or "m language" in t or "langage m" in t
    return False

def theme_match(text, lang, theme):
    t=text.lower()
    return any(k in t for k in THEMES[lang][theme])

def fetch_feed(query, lang):
    hl,gl,ceid=LOCALE[lang]
    params=urllib.parse.urlencode({"q":query,"hl":hl,"gl":gl,"ceid":ceid})
    url="https://news.google.com/rss/search?"+params
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 ConsultationDataBlog/2.0"})
    with urllib.request.urlopen(req,timeout=30) as r:
        raw=r.read()
    return ET.fromstring(raw).findall(".//item")

def main():
    cutoff=datetime.now(timezone.utc)-timedelta(days=DAYS)
    found={"fr":{}, "en":{}}

    for lang in ("fr","en"):
        for subject, subject_terms in SUBJECT_QUERIES.items():
            for theme, theme_terms in THEMES[lang].items():
                q=f"({' OR '.join(subject_terms)}) ({' OR '.join(theme_terms[:5])})"
                try:
                    items=fetch_feed(q,lang)
                except Exception as e:
                    print("Feed error",lang,subject,theme,e)
                    continue

                for item in items:
                    title=clean(item.findtext("title"))
                    url=clean(item.findtext("link"))
                    desc=clean(item.findtext("description"))
                    source_el=item.find("source")
                    source=clean(source_el.text if source_el is not None else "")
                    pub=item.findtext("pubDate") or ""

                    if not allowed_source(source,lang):
                        continue
                    text=f"{title} {desc}"
                    if not subject_match(text,subject):
                        continue
                    if not theme_match(text,lang,theme):
                        continue

                    try:
                        dt=parsedate_to_datetime(pub)
                        if dt.tzinfo is None: dt=dt.replace(tzinfo=timezone.utc)
                    except Exception:
                        continue
                    if dt<cutoff:
                        continue

                    if source and title.endswith(" - "+source):
                        title=title[:-(len(source)+3)].strip()

                    key=hashlib.sha1((title.lower()+source.lower()).encode()).hexdigest()[:14]
                    excerpt=desc
                    if len(excerpt)>230:
                        excerpt=excerpt[:227].rsplit(" ",1)[0]+"…"
                    if not excerpt:
                        excerpt=("Article sélectionné pour sa pertinence directe avec les services de Consultation Data."
                                 if lang=="fr" else
                                 "Article selected for its direct relevance to Consultation Data services.")

                    found[lang][key]={
                        "id":f"{lang}-{key}",
                        "lang":lang,
                        "title":title,
                        "source":source,
                        "date":dt.date().isoformat(),
                        "url":url,
                        "theme":theme,
                        "subject":subject,
                        "excerpt":excerpt
                    }

    articles=[]
    for lang in ("fr","en"):
        vals=sorted(found[lang].values(),key=lambda x:x["date"],reverse=True)
        articles.extend(vals[:MAX_PER_LANG])

    OUT.write_text(json.dumps({"updated":datetime.now(timezone.utc).isoformat(),"articles":articles},
                              ensure_ascii=False,indent=2),encoding="utf-8")
    print(f"Wrote {len(articles)} relevant articles")

if __name__=="__main__":
    main()

#!/usr/bin/env python3
import urllib.request, urllib.parse, xml.etree.ElementTree as ET
import json, re, html, hashlib
from pathlib import Path
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone, timedelta

OUT = Path(__file__).with_name("blog-data.json")

# 4 pages x 9 articles
MAX_PER_LANG = 36
TARGET_PER_SUBJECT = 12
HISTORY_DAYS = 1095  # 3 ans pour pouvoir constituer un historique pertinent

# Sources spécialisées Data / BI / Data Science.
SOURCE_ALLOW = {
    "fr": [
        "LeBigData", "DataScientest", "LeMagIT", "Journal du Net",
        "ActuIA", "Microsoft", "Microsoft Fabric", "Microsoft Learn",
        "Université Laval", "Posit", "R-bloggers", "Developpez.com",
        "ZDNet France", "Clubic"
    ],
    "en": [
        "Microsoft Fabric Community", "Microsoft Learn", "Microsoft",
        "Posit", "Posit Open Source", "DataCamp", "KDnuggets",
        "Towards Data Science", "InfoWorld", "TechTarget",
        "R-bloggers", "Data Science Central", "Analytics Vidhya",
        "SQLBI", "RADACAD", "Power BI Tips", "Guy in a Cube",
        "Appsilon", "Jumping Rivers"
    ]
}

LOCALE = {
    "fr": ("fr", "FR", "FR:fr"),
    "en": ("en-US", "US", "US:en")
}

SUBJECT_QUERIES = {
    "fr": {
        "R": [
            '"R programming"', '"langage R"', '"R data science"',
            'RStudio', 'Posit R', 'tidyverse'
        ],
        "Power BI": [
            '"Power BI"', '"Power BI entreprise"', '"Power BI adoption"',
            '"Power BI dashboard"', '"Power BI DAX"'
        ],
        "Power Query": [
            '"Power Query"', '"Power Query M"', '"langage M"',
            '"Power Query transformation"', '"Power Query entreprise"'
        ]
    },
    "en": {
        "R": [
            '"R programming"', '"R language"', '"R data science"',
            'RStudio', 'Posit R', 'tidyverse'
        ],
        "Power BI": [
            '"Power BI"', '"Power BI enterprise"', '"Power BI adoption"',
            '"Power BI dashboard"', '"Power BI DAX"'
        ],
        "Power Query": [
            '"Power Query"', '"Power Query M"', '"M language"',
            '"Power Query transformation"', '"Power Query enterprise"'
        ]
    }
}

THEME_TERMS = {
    "fr": {
        "Langage de programmation": [
            "programmation", "langage", "code", "dax", "script",
            "fonction", "package", "ide", "m language", "langage m"
        ],
        "Visualisation de données": [
            "visualisation", "tableau de bord", "dashboard", "graphique",
            "reporting", "storytelling", "visuel", "rapport"
        ],
        "Analyse de données": [
            "analyse", "analytics", "adoption", "entreprise", "roi",
            "décision", "performance", "data science", "données"
        ]
    },
    "en": {
        "Programming language": [
            "programming", "language", "code", "dax", "script",
            "function", "package", "ide", "m language"
        ],
        "Data visualization": [
            "visualization", "dashboard", "chart", "reporting",
            "storytelling", "visual", "report"
        ],
        "Data analysis": [
            "analysis", "analytics", "adoption", "enterprise", "roi",
            "decision", "performance", "data science", "data"
        ]
    }
}

def clean(text):
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", html.unescape(text)).strip()

def allowed_source(source, lang):
    s = (source or "").lower()
    return any(name.lower() in s for name in SOURCE_ALLOW[lang])

def subject_match(text, subject):
    t = text.lower()
    if subject == "R":
        return (
            bool(re.search(r"(^|[^a-z])r([^a-z]|$)", t))
            or any(k in t for k in ["rstudio", "posit", "tidyverse"])
        )
    if subject == "Power BI":
        return "power bi" in t
    if subject == "Power Query":
        return "power query" in t or "langage m" in t or "m language" in t
    return False

def choose_theme(text, lang):
    t = text.lower()
    scores = {}
    for theme, terms in THEME_TERMS[lang].items():
        scores[theme] = sum(1 for term in terms if term in t)

    # Priorité au thème le plus explicite. En cas d'égalité ou absence,
    # on classe en analyse de données : c'est le thème le plus général.
    best = max(scores, key=scores.get)
    if scores[best] == 0:
        return "Analyse de données" if lang == "fr" else "Data analysis"
    return best

def fetch_feed(query, lang):
    hl, gl, ceid = LOCALE[lang]
    params = urllib.parse.urlencode({
        "q": query,
        "hl": hl,
        "gl": gl,
        "ceid": ceid
    })
    url = "https://news.google.com/rss/search?" + params
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 ConsultationDataBlog/3.0"}
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read()
    return ET.fromstring(raw).findall(".//item")

def article_key(title, source):
    return hashlib.sha1(
        (title.strip().lower() + "|" + source.strip().lower()).encode()
    ).hexdigest()[:16]

def load_existing():
    if not OUT.exists():
        return []
    try:
        data = json.loads(OUT.read_text(encoding="utf-8"))
        return data.get("articles", [])
    except Exception:
        return []

def normalize_existing(article):
    # Garde uniquement les thèmes / sujets actuellement utilisés.
    if article.get("subject") not in {"R", "Power BI", "Power Query"}:
        return None

    lang = article.get("lang")
    if lang not in {"fr", "en"}:
        return None

    valid_themes = (
        {"Langage de programmation", "Visualisation de données", "Analyse de données"}
        if lang == "fr"
        else {"Programming language", "Data visualization", "Data analysis"}
    )

    if article.get("theme") not in valid_themes:
        article["theme"] = choose_theme(
            f"{article.get('title','')} {article.get('excerpt','')}", lang
        )

    return article

def main():
    cutoff = datetime.now(timezone.utc) - timedelta(days=HISTORY_DAYS)

    pool = {"fr": {}, "en": {}}

    # 1) Conserver l'historique déjà pertinent.
    for article in load_existing():
        article = normalize_existing(article)
        if not article:
            continue
        try:
            dt = datetime.fromisoformat(article["date"] + "T12:00:00+00:00")
        except Exception:
            continue
        if dt < cutoff:
            continue

        key = article_key(article.get("title", ""), article.get("source", ""))
        pool[article["lang"]][key] = article

    # 2) Ajouter les nouveaux articles.
    for lang in ("fr", "en"):
        for subject in ("R", "Power BI", "Power Query"):
            for query in SUBJECT_QUERIES[lang][subject]:
                try:
                    items = fetch_feed(query, lang)
                except Exception as e:
                    print("Feed error:", lang, subject, query, e)
                    continue

                for item in items:
                    title = clean(item.findtext("title"))
                    url = clean(item.findtext("link"))
                    desc = clean(item.findtext("description"))
                    pub = item.findtext("pubDate") or ""
                    source_el = item.find("source")
                    source = clean(source_el.text if source_el is not None else "")

                    if not title or not url or not allowed_source(source, lang):
                        continue

                    text = f"{title} {desc}"
                    if not subject_match(text, subject):
                        continue

                    try:
                        dt = parsedate_to_datetime(pub)
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)
                    except Exception:
                        continue

                    if dt < cutoff:
                        continue

                    if source and title.endswith(" - " + source):
                        title = title[:-(len(source) + 3)].strip()

                    excerpt = desc
                    if len(excerpt) > 240:
                        excerpt = excerpt[:237].rsplit(" ", 1)[0] + "…"
                    if not excerpt:
                        excerpt = (
                            "Article spécialisé sélectionné pour sa pertinence avec les services de Consultation Data."
                            if lang == "fr"
                            else
                            "Specialized article selected for its relevance to Consultation Data services."
                        )

                    key = article_key(title, source)
                    pool[lang][key] = {
                        "id": f"{lang}-{key}",
                        "lang": lang,
                        "title": title,
                        "source": source,
                        "date": dt.date().isoformat(),
                        "url": url,
                        "theme": choose_theme(text, lang),
                        "subject": subject,
                        "excerpt": excerpt
                    }

    # 3) Construire une sélection équilibrée :
    # jusqu'à 12 R + 12 Power BI + 12 Power Query = 36 articles / langue.
    final_articles = []

    for lang in ("fr", "en"):
        all_values = list(pool[lang].values())
        selected = []
        selected_ids = set()

        for subject in ("R", "Power BI", "Power Query"):
            rows = [
                a for a in all_values
                if a.get("subject") == subject
            ]
            rows.sort(key=lambda a: a.get("date", ""), reverse=True)

            for article in rows[:TARGET_PER_SUBJECT]:
                selected.append(article)
                selected_ids.add(article["id"])

        # Si un sujet n'atteint pas son quota, compléter avec les meilleurs
        # articles spécialisés restants, sans dépasser 36.
        if len(selected) < MAX_PER_LANG:
            remaining = [
                a for a in all_values
                if a.get("id") not in selected_ids
            ]
            remaining.sort(key=lambda a: a.get("date", ""), reverse=True)
            selected.extend(remaining[:MAX_PER_LANG - len(selected)])

        selected = sorted(
            selected[:MAX_PER_LANG],
            key=lambda a: a.get("date", ""),
            reverse=True
        )

        final_articles.extend(selected)

        counts = {
            s: sum(1 for a in selected if a.get("subject") == s)
            for s in ("R", "Power BI", "Power Query")
        }
        print(lang, "articles:", len(selected), counts)

    OUT.write_text(
        json.dumps({
            "updated": datetime.now(timezone.utc).isoformat(),
            "articles": final_articles
        }, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print("Total articles written:", len(final_articles))

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import json
import re
import html
import hashlib
from pathlib import Path
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse

OUT = Path(__file__).with_name("blog-data.json")

# 4 pages maximum × 9 articles
MAX_PER_LANG = 36
HISTORY_DAYS = 1095

LOCALE = {
    "fr": ("fr", "FR", "FR:fr"),
    "en": ("en-US", "US", "US:en")
}

SUBJECT_QUERIES = {
    "fr": {
        "R": ['"R programming"', '"langage R"', '"R data science"', 'RStudio', 'tidyverse', 'Shiny'],
        "Power BI": ['"Power BI"', '"Power BI DAX"', '"Power BI dashboard"', '"Power BI reporting"'],
        "Power Query": ['"Power Query"', '"Power Query M"', '"langage M"', '"Power Query transformation"']
    },
    "en": {
        "R": ['"R programming"', '"R language"', '"R data science"', 'RStudio', 'tidyverse', 'Shiny'],
        "Power BI": ['"Power BI"', '"Power BI DAX"', '"Power BI dashboard"', '"Power BI reporting"'],
        "Power Query": ['"Power Query"', '"Power Query M"', '"M language"', '"Power Query transformation"']
    }
}

THEME_TERMS = {
    "fr": {
        "Langage de programmation": [
            "programmation", "langage", "code", "dax", "script", "fonction",
            "package", "ide", "langage m", "m language", "shiny", "rstudio"
        ],
        "Visualisation de données": [
            "visualisation", "tableau de bord", "dashboard", "graphique",
            "reporting", "storytelling", "visuel", "rapport", "dataviz"
        ],
        "Analyse de données": [
            "analyse", "analytics", "adoption", "entreprise", "roi",
            "décision", "performance", "data science", "données", "kpi"
        ]
    },
    "en": {
        "Programming language": [
            "programming", "language", "code", "dax", "script", "function",
            "package", "ide", "m language", "shiny", "rstudio"
        ],
        "Data visualization": [
            "visualization", "dashboard", "chart", "reporting",
            "storytelling", "visual", "report", "dataviz"
        ],
        "Data analysis": [
            "analysis", "analytics", "adoption", "enterprise", "roi",
            "decision", "performance", "data science", "data", "kpi"
        ]
    }
}

# STRICT whitelist: only specialist blogs / software publishers / practitioner communities.
# No TV, radio, university pages, download portals or general news sites.
SOURCES = {
    "fr": [
        {"name": "LeBigData", "domain": "lebigdata.fr", "aliases": ["LeBigData"]},
        {"name": "ThinkR", "domain": "thinkr.fr", "aliases": ["ThinkR"]},
        {"name": "DataScientest", "domain": "datascientest.com", "aliases": ["DataScientest", "Liora"]},
        {"name": "ActuIA", "domain": "actuia.com", "aliases": ["ActuIA"]},
        {"name": "Microsoft Fabric Community", "domain": "community.fabric.microsoft.com",
         "aliases": ["Microsoft Fabric Community", "Microsoft Fabric Community Blog"]},
        {"name": "Microsoft Power BI Blog", "domain": "powerbi.microsoft.com",
         "aliases": ["Microsoft Power BI Blog", "Power BI Blog"]},
    ],
    "en": [
        {"name": "Microsoft Fabric Community", "domain": "community.fabric.microsoft.com",
         "aliases": ["Microsoft Fabric Community", "Microsoft Fabric Community Blog"]},
        {"name": "Microsoft Power BI Blog", "domain": "powerbi.microsoft.com",
         "aliases": ["Microsoft Power BI Blog", "Power BI Blog"]},
        {"name": "SQLBI", "domain": "sqlbi.com", "aliases": ["SQLBI"]},
        {"name": "RADACAD", "domain": "radacad.com", "aliases": ["RADACAD"]},
        {"name": "Power BI Tips", "domain": "powerbi.tips", "aliases": ["Power BI Tips"]},
        {"name": "Guy in a Cube", "domain": "guyinacube.com", "aliases": ["Guy in a Cube"]},
        {"name": "Posit", "domain": "posit.co", "aliases": ["Posit"]},
        {"name": "Posit Open Source", "domain": "opensource.posit.co", "aliases": ["Posit Open Source"]},
        {"name": "R-bloggers", "domain": "r-bloggers.com", "aliases": ["R-bloggers"]},
        {"name": "DataCamp", "domain": "datacamp.com", "aliases": ["DataCamp"]},
        {"name": "KDnuggets", "domain": "kdnuggets.com", "aliases": ["KDnuggets"]},
        {"name": "Towards Data Science", "domain": "towardsdatascience.com",
         "aliases": ["Towards Data Science"]},
        {"name": "Analytics Vidhya", "domain": "analyticsvidhya.com",
         "aliases": ["Analytics Vidhya"]},
        {"name": "Appsilon", "domain": "appsilon.com", "aliases": ["Appsilon"]},
        {"name": "Jumping Rivers", "domain": "jumpingrivers.com", "aliases": ["Jumping Rivers"]},
    ]
}

BLOCKED_WORDS = [
    "tf1", "radio", "television", "télévision", "university", "université",
    "college", "collège", "download", "télécharger", "softonic", "clubic",
    "zdnet", "journal du net", "le figaro", "le monde", "bfm", "franceinfo",
    "cnews", "cnn", "bbc", "reuters", "youtube"
]

def clean(text):
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", html.unescape(text)).strip()

def norm(text):
    return re.sub(r"\s+", " ", (text or "").strip().lower())

def source_rule(source_text, lang):
    s = norm(source_text)
    for rule in SOURCES[lang]:
        if any(s == norm(alias) for alias in rule["aliases"]):
            return rule
    return None

def blocked(text):
    t = norm(text)
    return any(word in t for word in BLOCKED_WORDS)

def subject_match(text, subject):
    t = text.lower()
    if subject == "R":
        return (
            bool(re.search(r"(^|[^a-z])r([^a-z]|$)", t))
            or any(k in t for k in ["rstudio", "posit", "tidyverse", "shiny"])
        )
    if subject == "Power BI":
        return "power bi" in t
    if subject == "Power Query":
        return "power query" in t or "langage m" in t or "m language" in t
    return False

def choose_theme(text, lang):
    t = text.lower()
    scores = {
        theme: sum(1 for term in terms if term in t)
        for theme, terms in THEME_TERMS[lang].items()
    }
    best = max(scores, key=scores.get)
    if scores[best] == 0:
        return "Analyse de données" if lang == "fr" else "Data analysis"
    return best

def fetch_feed(query, lang):
    hl, gl, ceid = LOCALE[lang]
    params = urllib.parse.urlencode({"q": query, "hl": hl, "gl": gl, "ceid": ceid})
    url = "https://news.google.com/rss/search?" + params
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 ConsultationDataBlog/5.0"}
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        return ET.fromstring(response.read()).findall(".//item")

def resolve_url(url):
    """Resolve Google News redirects to the real article when possible."""
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 ConsultationDataBlog/5.0"}
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            return response.geturl()
    except Exception:
        return url

def hostname(url):
    try:
        return (urlparse(url).hostname or "").lower().removeprefix("www.")
    except Exception:
        return ""

def path_is_blog_like(url, rule):
    """
    Reject obvious home pages, category pages, PDFs, downloads and help/course portals.
    Allow article-style pages from specialist sources.
    """
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().removeprefix("www.")
    path = (parsed.path or "").lower()

    if host != rule["domain"] and not host.endswith("." + rule["domain"]):
        return False

    if path in {"", "/"}:
        return False

    if any(x in path for x in [".pdf", "/download", "/downloads", "/help/", "/support/", "/course", "/courses", "/training"]):
        return False

    if rule["domain"] == "community.fabric.microsoft.com":
        return "/blog/" in path
    if rule["domain"] == "powerbi.microsoft.com":
        return "/blog/" in path
    if rule["domain"] == "posit.co":
        return "/blog/" in path
    if rule["domain"] == "opensource.posit.co":
        return "/blog/" in path
    if rule["domain"] == "datacamp.com":
        return "/blog/" in path and "/category/" not in path
    if rule["domain"] == "datascientest.com":
        return not any(sub in host for sub in ["help.", "support.", "allianz.", "michelin."])

    return True

def article_key(title, source):
    raw = f"{title.strip().lower()}|{source.strip().lower()}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]

def load_existing():
    if not OUT.exists():
        return []
    try:
        return json.loads(OUT.read_text(encoding="utf-8")).get("articles", [])
    except Exception:
        return []

def valid_existing(article):
    lang = article.get("lang")
    if lang not in {"fr", "en"}:
        return False

    subject = article.get("subject")
    if subject not in {"R", "Power BI", "Power Query"}:
        return False

    source = article.get("source", "")
    url = article.get("url", "")
    rule = source_rule(source, lang)
    if not rule:
        return False

    if blocked(f"{source} {article.get('title','')} {url}"):
        return False

    if not path_is_blog_like(url, rule):
        return False

    return True

def main():
    cutoff = datetime.now(timezone.utc) - timedelta(days=HISTORY_DAYS)
    pool = {"fr": {}, "en": {}}

    # 1) Keep only existing articles that still pass the STRICT whitelist.
    removed = 0
    for article in load_existing():
        if not valid_existing(article):
            removed += 1
            continue

        try:
            dt = datetime.fromisoformat(article["date"] + "T12:00:00+00:00")
        except Exception:
            removed += 1
            continue

        if dt < cutoff:
            removed += 1
            continue

        if article.get("theme") not in THEME_TERMS[article["lang"]]:
            article["theme"] = choose_theme(
                f"{article.get('title','')} {article.get('excerpt','')}",
                article["lang"]
            )

        key = article_key(article.get("title", ""), article.get("source", ""))
        pool[article["lang"]][key] = article

    print(f"Existing articles rejected by strict source rules: {removed}")

    # 2) Discover new content source-by-source.
    # Every query is explicitly restricted with site:domain.
    for lang in ("fr", "en"):
        for rule in SOURCES[lang]:
            for subject in ("R", "Power BI", "Power Query"):
                for terms in SUBJECT_QUERIES[lang][subject]:
                    query = f"site:{rule['domain']} {terms}"

                    try:
                        items = fetch_feed(query, lang)
                    except Exception as e:
                        print("Feed error:", rule["name"], subject, e)
                        continue

                    for item in items:
                        title = clean(item.findtext("title"))
                        google_url = clean(item.findtext("link"))
                        desc = clean(item.findtext("description"))
                        pub = item.findtext("pubDate") or ""
                        source_el = item.find("source")
                        source_text = clean(source_el.text if source_el is not None else "")

                        if not title or not google_url:
                            continue

                        matched_rule = source_rule(source_text, lang)
                        if not matched_rule or matched_rule["domain"] != rule["domain"]:
                            continue

                        if blocked(f"{title} {desc} {source_text}"):
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

                        real_url = resolve_url(google_url)

                        # If Google keeps its redirect URL, reject it rather than guessing.
                        if hostname(real_url).endswith("google.com") or hostname(real_url).endswith("googleusercontent.com"):
                            continue

                        if not path_is_blog_like(real_url, matched_rule):
                            continue

                        if source_text and title.endswith(" - " + source_text):
                            title = title[:-(len(source_text) + 3)].strip()

                        excerpt = desc
                        if len(excerpt) > 240:
                            excerpt = excerpt[:237].rsplit(" ", 1)[0] + "…"
                        if not excerpt:
                            excerpt = (
                                "Article spécialisé sélectionné pour sa pertinence en data, Business Intelligence et logiciels analytiques."
                                if lang == "fr"
                                else
                                "Specialist article selected for its relevance to data, Business Intelligence and analytics software."
                            )

                        key = article_key(title, matched_rule["name"])
                        pool[lang][key] = {
                            "id": f"{lang}-{key}",
                            "lang": lang,
                            "title": title,
                            "source": matched_rule["name"],
                            "date": dt.date().isoformat(),
                            "url": real_url,
                            "theme": choose_theme(text, lang),
                            "subject": subject,
                            "excerpt": excerpt
                        }

    # 3) Max 36 per language. No junk padding: if only 14 good articles exist, show 14.
    final_articles = []

    for lang in ("fr", "en"):
        articles = list(pool[lang].values())
        articles.sort(key=lambda x: x.get("date", ""), reverse=True)

        # Balance subjects so one tool does not take the whole blog.
        selected = []
        selected_ids = set()
        per_subject_target = MAX_PER_LANG // 3

        for subject in ("R", "Power BI", "Power Query"):
            candidates = [a for a in articles if a.get("subject") == subject]
            for article in candidates[:per_subject_target]:
                selected.append(article)
                selected_ids.add(article["id"])

        if len(selected) < MAX_PER_LANG:
            for article in articles:
                if article["id"] in selected_ids:
                    continue
                selected.append(article)
                selected_ids.add(article["id"])
                if len(selected) >= MAX_PER_LANG:
                    break

        selected.sort(key=lambda x: x.get("date", ""), reverse=True)
        final_articles.extend(selected[:MAX_PER_LANG])

        print(f"{lang.upper()}: {min(len(selected), MAX_PER_LANG)} strict specialist articles")

    OUT.write_text(
        json.dumps({
            "updated": datetime.now(timezone.utc).isoformat(),
            "articles": final_articles
        }, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print("Total saved:", len(final_articles))

if __name__ == "__main__":
    main()

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


# ============================================================
# CONFIGURATION
# ============================================================

OUT = Path(__file__).with_name("blog-data.json")

# 9 articles/page × 4 pages
MAX_PER_LANG = 36

# 3 thèmes × 3 sujets = 9 combinaisons
# 4 articles par combinaison = 36 articles maximum
PER_COMBINATION = 4

# On accepte jusqu'à 3 ans d'historique afin d'avoir assez
# de contenu pertinent sans utiliser des articles hors sujet.
HISTORY_DAYS = 1095


THEMES = {
    "fr": [
        "Langage de programmation",
        "Visualisation de données",
        "Analyse de données",
    ],
    "en": [
        "Programming language",
        "Data visualization",
        "Data analysis",
    ],
}


SUBJECTS = [
    "R",
    "Power BI",
    "Power Query",
]


# Sources spécialisées privilégiées.
# Le script interroge Google News avec site:...
DOMAINS = {
    "fr": [
        "lebigdata.fr",
        "datascientest.com",
        "lemagit.fr",
        "actuia.com",
        "developpez.com",
        "microsoft.com",
        "learn.microsoft.com",
        "posit.co",
    ],
    "en": [
        "community.fabric.microsoft.com",
        "learn.microsoft.com",
        "microsoft.com",
        "posit.co",
        "datacamp.com",
        "kdnuggets.com",
        "towardsdatascience.com",
        "r-bloggers.com",
        "sqlbi.com",
        "radacad.com",
        "powerbi.tips",
        "appsilon.com",
        "jumpingrivers.com",
    ],
}


LOCALE = {
    "fr": ("fr", "FR", "FR:fr"),
    "en": ("en-US", "US", "US:en"),
}


# ============================================================
# TERMES DE RECHERCHE
# ============================================================

SUBJECT_TERMS = {
    "fr": {
        "R": [
            '"langage R"',
            '"R programming"',
            '"R data science"',
            'RStudio',
            'Posit',
            'tidyverse',
        ],
        "Power BI": [
            '"Power BI"',
            '"Power BI entreprise"',
            '"Power BI adoption"',
            '"Power BI DAX"',
        ],
        "Power Query": [
            '"Power Query"',
            '"langage M"',
            '"Power Query transformation"',
        ],
    },

    "en": {
        "R": [
            '"R programming"',
            '"R language"',
            '"R data science"',
            'RStudio',
            'Posit',
            'tidyverse',
        ],
        "Power BI": [
            '"Power BI"',
            '"Power BI enterprise"',
            '"Power BI adoption"',
            '"Power BI DAX"',
        ],
        "Power Query": [
            '"Power Query"',
            '"M language"',
            '"Power Query transformation"',
        ],
    },
}


THEME_TERMS = {
    "fr": {
        "Langage de programmation": [
            "programmation",
            "langage",
            "code",
            "DAX",
            "script",
            "fonction",
            "package",
            "langage M",
        ],

        "Visualisation de données": [
            "visualisation",
            "tableau de bord",
            "dashboard",
            "graphique",
            "reporting",
            "rapport",
            "data storytelling",
        ],

        "Analyse de données": [
            "analyse",
            "analytics",
            "entreprise",
            "adoption",
            "performance",
            "décision",
            "ROI",
            "data science",
        ],
    },

    "en": {
        "Programming language": [
            "programming",
            "language",
            "code",
            "DAX",
            "script",
            "function",
            "package",
            "M language",
        ],

        "Data visualization": [
            "visualization",
            "dashboard",
            "chart",
            "reporting",
            "report",
            "storytelling",
        ],

        "Data analysis": [
            "analysis",
            "analytics",
            "enterprise",
            "adoption",
            "performance",
            "decision",
            "ROI",
            "data science",
        ],
    },
}


# ============================================================
# OUTILS
# ============================================================

def clean(text):
    """Nettoyer du texte HTML/RSS."""
    text = text or ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def make_key(title, source):
    raw = f"{title.lower().strip()}|{source.lower().strip()}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def fetch_feed(query, lang):
    """Interroger Google News RSS."""

    hl, gl, ceid = LOCALE[lang]

    params = urllib.parse.urlencode({
        "q": query,
        "hl": hl,
        "gl": gl,
        "ceid": ceid,
    })

    url = "https://news.google.com/rss/search?" + params

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent":
            "Mozilla/5.0 ConsultationDataBlog/4.0"
        },
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        xml_data = response.read()

    root = ET.fromstring(xml_data)

    return root.findall(".//item")


def subject_matches(text, subject):
    text = text.lower()

    if subject == "Power BI":
        return "power bi" in text

    if subject == "Power Query":
        return (
            "power query" in text
            or "langage m" in text
            or "m language" in text
        )

    if subject == "R":
        return (
            bool(
                re.search(
                    r"(^|[^a-z])r([^a-z]|$)",
                    text
                )
            )
            or "rstudio" in text
            or "posit" in text
            or "tidyverse" in text
        )

    return False


def load_existing_articles():
    """Conserver les bons articles déjà présents."""

    if not OUT.exists():
        return []

    try:
        data = json.loads(
            OUT.read_text(encoding="utf-8")
        )

        return data.get("articles", [])

    except Exception:
        return []


def valid_existing_article(article):

    lang = article.get("lang")
    subject = article.get("subject")
    theme = article.get("theme")

    if lang not in {"fr", "en"}:
        return False

    if subject not in SUBJECTS:
        return False

    if theme not in THEMES[lang]:
        return False

    return True


# ============================================================
# CONSTRUCTION DES REQUÊTES
# ============================================================

def build_queries(lang, subject, theme):

    subject_terms = SUBJECT_TERMS[lang][subject]
    theme_terms = THEME_TERMS[lang][theme]

    subject_query = " OR ".join(subject_terms)
    theme_query = " OR ".join(
        f'"{term}"'
        if " " in term
        else term
        for term in theme_terms
    )

    queries = []

    # Regrouper les domaines par 3 pour ne pas créer
    # des requêtes trop longues.
    domains = DOMAINS[lang]

    for i in range(0, len(domains), 3):

        group = domains[i:i + 3]

        source_query = " OR ".join(
            f"site:{domain}"
            for domain in group
        )

        query = (
            f"({subject_query}) "
            f"({theme_query}) "
            f"({source_query})"
        )

        queries.append(query)

    return queries


# ============================================================
# PROGRAMME PRINCIPAL
# ============================================================

def main():

    cutoff = (
        datetime.now(timezone.utc)
        - timedelta(days=HISTORY_DAYS)
    )

    # Articles déjà connus
    existing = load_existing_articles()

    pools = {
        "fr": {},
        "en": {},
    }

    # --------------------------------------------------------
    # 1. CONSERVER L'HISTORIQUE PERTINENT
    # --------------------------------------------------------

    for article in existing:

        if not valid_existing_article(article):
            continue

        try:
            article_date = datetime.fromisoformat(
                article["date"]
                + "T12:00:00+00:00"
            )
        except Exception:
            continue

        if article_date < cutoff:
            continue

        lang = article["lang"]

        key = make_key(
            article.get("title", ""),
            article.get("source", ""),
        )

        pools[lang][key] = article


    # --------------------------------------------------------
    # 2. RECHERCHE DE NOUVEAUX ARTICLES
    # --------------------------------------------------------

    for lang in ("fr", "en"):

        for subject in SUBJECTS:

            for theme in THEMES[lang]:

                queries = build_queries(
                    lang,
                    subject,
                    theme,
                )

                for query in queries:

                    try:
                        items = fetch_feed(
                            query,
                            lang,
                        )

                    except Exception as error:
                        print(
                            "Erreur RSS:",
                            lang,
                            subject,
                            theme,
                            error,
                        )
                        continue


                    for item in items:

                        title = clean(
                            item.findtext("title")
                        )

                        url = clean(
                            item.findtext("link")
                        )

                        description = clean(
                            item.findtext("description")
                        )

                        published = (
                            item.findtext("pubDate")
                            or ""
                        )

                        source_element = (
                            item.find("source")
                        )

                        source = clean(
                            source_element.text
                            if source_element
                            is not None
                            else ""
                        )


                        if not title or not url:
                            continue


                        full_text = (
                            title
                            + " "
                            + description
                        )


                        # L'article doit réellement parler
                        # du sujet sélectionné.
                        if not subject_matches(
                            full_text,
                            subject,
                        ):
                            continue


                        try:

                            dt = parsedate_to_datetime(
                                published
                            )

                            if dt.tzinfo is None:
                                dt = dt.replace(
                                    tzinfo=timezone.utc
                                )

                        except Exception:
                            continue


                        if dt < cutoff:
                            continue


                        # Google News ajoute souvent
                        # " - Nom de la source"
                        if (
                            source
                            and title.endswith(
                                " - " + source
                            )
                        ):

                            title = title[
                                :-(len(source) + 3)
                            ].strip()


                        excerpt = description

                        if len(excerpt) > 240:

                            excerpt = (
                                excerpt[:237]
                                .rsplit(" ", 1)[0]
                                + "…"
                            )


                        if not excerpt:

                            excerpt = (
                                "Article spécialisé sélectionné "
                                "pour sa pertinence avec les "
                                "services de Consultation Data."
                                if lang == "fr"
                                else
                                "Specialized article selected "
                                "for its relevance to "
                                "Consultation Data services."
                            )


                        key = make_key(
                            title,
                            source,
                        )


                        pools[lang][key] = {

                            "id":
                            f"{lang}-{key}",

                            "lang":
                            lang,

                            "title":
                            title,

                            "source":
                            source or "Google News",

                            "date":
                            dt.date().isoformat(),

                            "url":
                            url,

                            "theme":
                            theme,

                            "subject":
                            subject,

                            "excerpt":
                            excerpt,
                        }


    # --------------------------------------------------------
    # 3. CRÉER LES 4 PAGES
    # --------------------------------------------------------

    final_articles = []


    for lang in ("fr", "en"):

        all_articles = list(
            pools[lang].values()
        )

        selected = []

        already_used = set()


        # 9 combinaisons :
        # 3 sujets × 3 thèmes
        for subject in SUBJECTS:

            for theme in THEMES[lang]:

                candidates = [

                    article

                    for article
                    in all_articles

                    if (
                        article.get("subject")
                        == subject

                        and article.get("theme")
                        == theme
                    )
                ]


                candidates.sort(
                    key=lambda x:
                    x.get("date", ""),
                    reverse=True,
                )


                combo_count = 0


                for article in candidates:

                    if combo_count >= PER_COMBINATION:
                        break


                    article_id = article.get("id")


                    if article_id in already_used:
                        continue


                    selected.append(article)

                    already_used.add(
                        article_id
                    )

                    combo_count += 1


        # ----------------------------------------------------
        # Si certaines combinaisons n'ont pas 4 articles,
        # compléter avec les meilleurs articles restants.
        # ----------------------------------------------------

        if len(selected) < MAX_PER_LANG:

            remaining = [

                article

                for article
                in all_articles

                if article.get("id")
                not in already_used
            ]


            remaining.sort(
                key=lambda x:
                x.get("date", ""),
                reverse=True,
            )


            needed = (
                MAX_PER_LANG
                - len(selected)
            )


            selected.extend(
                remaining[:needed]
            )


        # Maximum 36
        selected = selected[
            :MAX_PER_LANG
        ]


        # Page 1 = plus récents
        selected.sort(
            key=lambda x:
            x.get("date", ""),
            reverse=True,
        )


        final_articles.extend(
            selected
        )


        print(
            f"{lang.upper()} : "
            f"{len(selected)} articles"
        )


        for subject in SUBJECTS:

            count = sum(

                1
                for article
                in selected

                if article.get("subject")
                == subject
            )

            print(
                f"  {subject}: "
                f"{count}"
            )


    # --------------------------------------------------------
    # 4. SAUVEGARDE
    # --------------------------------------------------------

    data = {

        "updated":
        datetime.now(
            timezone.utc
        ).isoformat(),

        "articles":
        final_articles,
    }


    OUT.write_text(

        json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
        ),

        encoding="utf-8",
    )


    print(
        "Total:",
        len(final_articles),
        "articles enregistrés."
    )


if __name__ == "__main__":
    main()

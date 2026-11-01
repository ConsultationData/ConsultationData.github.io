CORRECTIF BLOG — SOURCES STRICTEMENT SPÉCIALISÉES

Remplace à la racine de ton dépôt GitHub :
- update_blog.py
- blog-data.json

Ce correctif :
- supprime les sources hors sujet déjà présentes (TV, radio, universités, médias généralistes, téléchargement) ;
- autorise uniquement une liste blanche de blogs / médias spécialisés Data, BI, analytics et éditeurs logiciels ;
- recherche uniquement les sujets R, Power BI et Power Query ;
- conserve les thèmes Programmation, Visualisation de données et Analyse de données ;
- refuse les pages d'accueil, PDF, téléchargements, cours, support et pages de formation ;
- essaie de conserver uniquement des pages de type article/blog ;
- limite à 36 articles par langue (4 pages de 9 maximum) ;
- n'ajoute pas de contenu hors sujet simplement pour remplir les pages.

Sources autorisées principales :
FR : LeBigData, ThinkR, DataScientest, ActuIA, Microsoft Fabric Community, Microsoft Power BI Blog.
EN : Microsoft Fabric Community, Microsoft Power BI Blog, SQLBI, RADACAD, Power BI Tips, Guy in a Cube, Posit, R-bloggers, DataCamp, KDnuggets, Towards Data Science, Analytics Vidhya, Appsilon, Jumping Rivers.

Après remplacement :
1. Commit changes
2. Actions > Update Blog Articles > Run workflow
3. Attendre le workflow puis Pages build and deployment
4. Ctrl + Shift + R

Important :
Le script privilégie la qualité des sources. S'il ne trouve que 12 bons articles, il affichera 12 articles au lieu d'ajouter des pages universitaires, télé, radio ou téléchargements.

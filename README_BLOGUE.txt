CONSULTATION DATA — AJOUT DU BLOGUE

FICHIERS À AJOUTER / REMPLACER À LA RACINE
- index.html
- blog.html
- blog.css
- blog.js
- blog-data.json
- update_blog.py
- styles.css
- script.js
- realisations_futuristes.png
- realisations_futuristes_en.png

DOSSIER À AJOUTER POUR LA MISE À JOUR MENSUELLE
.github/workflows/update-blog.yml

FONCTIONNEMENT DU BLOGUE
- 9 articles par page.
- Le système conserve jusqu'à 54 articles FR + 54 articles EN, soit jusqu'à 6 pages par langue.
- Page 1 = articles les plus récents.
- Dernière page = articles les plus anciens.
- Filtres par thème :
  Préparation des données / Analyse de données / Tableaux de bord / Formation.
- Filtres par sujet :
  Power BI / Power Query / R / Reporting / Cartographie / Analyse.
- FR affiche les articles francophones.
- EN affiche les articles anglophones.
- Le filtre et la pagination fonctionnent sans recharger la page.

MISE À JOUR AUTOMATIQUE
Le workflow GitHub Actions s'exécute le 1er de chaque mois à 10:15 UTC.
Il interroge Google News RSS en français et en anglais, classe les articles,
garde les 54 plus récents de chaque langue et met à jour blog-data.json.

APRÈS LE PREMIER DÉPLOIEMENT
1. Va dans GitHub > Actions.
2. Ouvre "Update Blog Articles".
3. Clique "Run workflow" une première fois.
4. Attends la fin du workflow.
5. Le blogue sera alors alimenté avec jusqu'à 54 articles FR + 54 EN.
6. Ensuite, la mise à jour mensuelle se fera automatiquement.

SI GITHUB NE PERMET PAS DE DÉPOSER LE DOSSIER .github
Add file > Create new file
Nom du fichier :
.github/workflows/update-blog.yml
Puis colle le contenu du fichier update-blog.yml fourni dans le ZIP.

CORRECTIF 4 PAGES — VERSION 2

Pourquoi tu voyais encore 1 page :
- 36 était seulement un maximum.
- L'ancien robot était trop strict et supprimait l'historique.
- La pagination dépend aussi du filtre actif : avec R sélectionné, seuls les articles R comptent.

Nouvelle logique :
- conserve les articles pertinents déjà trouvés ;
- ajoute les nouveaux chaque mois ;
- historique possible sur 3 ans ;
- sources Data / BI / Data Science uniquement ;
- vise jusqu'à 12 articles R ;
- jusqu'à 12 articles Power BI ;
- jusqu'à 12 articles Power Query ;
- maximum 36 articles par langue = 4 pages de 9.

Sur GitHub :
1. Remplace seulement update_blog.py.
2. Commit changes.
3. Actions > Update Blog Articles > Run workflow.
4. Attends le workflow vert.
5. Attends ensuite Pages build and deployment.
6. Recharge le blogue avec Ctrl + Shift + R.
7. Mets les filtres Thème = Tous et Sujet = Tous pour voir la pagination globale.

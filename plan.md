# Media 4 u — plan

> Projet perso : savoir quoi regarder (films + séries), **sans LLM**, **sans spoil**.
> Version 2 — 2026-10-10

## 1. Objectif

Un petit outil qui répond à deux questions :

1. **Qu'est-ce qui est sorti et qui fait parler de lui ?** Quatre périodes, aucun goût requis.
2. **Dans tout ça, qu'est-ce qui va plaire à ta chérie ?** On lui fait donner une liste de titres qu'elle a aimés, et le classement s'ajuste.

### Décisions déjà prises

| Sujet | Décision |
|---|---|
| IA | **Aucun LLM, aucun modèle ML.** Matching déterministe et explicable (TF-IDF, similarité, co-occurrences). |
| Usage | Perso, non commercial, pour deux personnes. Pas de sujet de licence (TMDB gratuit en non-commercial). |
| Médias v1 | Films + séries (TMDB couvre les deux, anime inclus). Jeux / livres / manga plus tard, si envie. |
| Plateformes | **Facultatif.** Pas de classement par plateforme. Au mieux un petit badge « dispo sur : … » (voir §7). |
| Spoil | Zéro, **par construction** (voir §6). |

## 2. Les 4 périodes

Fenêtres glissantes, calculées à partir de la date du jour, sans chevauchement (un titre n'apparaît qu'une fois) :

| # | Période | Fenêtre de sortie | Critère de sélection |
|---|---|---|---|
| P1 | **Le mois dernier** | J-30 → aujourd'hui | Buzz récent |
| P2 | **Les 6 derniers mois** | J-6 mois → J-30 | Buzz |
| P3 | **L'année dernière** | J-12 mois → J-6 mois | Buzz + recul (les notes se stabilisent) |
| P4 | **Les cultes** | J-15 ans → J-12 mois | Beaucoup de votes **et** note élevée, qui tiennent dans le temps |

Chaque période est produite pour **films** et **séries** séparément : 8 listes de ~20 titres.

> À confirmer : « l'année dernière » = les 12 mois glissants (choix ci-dessus, sans doublon) ou l'année civile précédente ? Et « cultes » = tout ce qui a 1 à 15 ans, ou plutôt 10 à 15 ans ?

## 3. Données (TMDB)

Une seule source pour la v1 : TMDB (gratuit en non-commercial, clé API à créer sur un compte gratuit, mention TMDB obligatoire dans le pied de page).

| Besoin | Endpoint | Statut |
|---|---|---|
| Titres d'une fenêtre de dates, triés par popularité / votes | `GET /3/discover/movie` (`primary_release_date.gte/lte`, `sort_by`, `vote_count.gte`) | Confirmé |
| Idem pour les séries | `GET /3/discover/tv` (`first_air_date.gte/lte`, `sort_by`, `vote_count.gte`) | Confirmé |
| « Les gens qui ont aimé X ont aussi aimé… » | `GET /3/movie/{id}/recommendations`, `GET /3/tv/{id}/recommendations` | Confirmé |
| Mots-clés d'un film | `GET /3/movie/{id}/keywords` | Confirmé |
| Mots-clés d'une série | `GET /3/tv/{id}/keywords` | À vérifier |
| Dispo par plateforme (facultatif) | `GET /3/movie/{id}/watch/providers` (+ équivalent TV) | Film confirmé, attribution **JustWatch** obligatoire |

Volume : ~160 titres par rafraîchissement. Très en dessous des limites TMDB.

Pistes écartées pour la v1 : Trakt (« watched / trending » par période) comme second signal de buzz. À vérifier au moment de construire, rien dans le plan n'en dépend.

## 4. Mode générique — « ça fait parler »

Pas de goût, juste des signaux de TMDB, calculés **dans chaque fenêtre** (percentiles à l'intérieur de la liste, donc comparables).

```
buzz(P1..P3) = 0.5·pct(popularité) + 0.3·pct(nb de votes) + 0.2·pct(note pondérée)
buzz(P4)     = 0.4·pct(nb de votes) + 0.4·pct(note pondérée) + 0.2·pct(popularité)
```

- **Note pondérée** (formule bayésienne type IMDb) : `WR = v/(v+m)·R + m/(v+m)·C`, avec `v` = votes du titre, `R` = sa note, `m` = seuil de votes, `C` = note moyenne du lot. Évite qu'un titre à 12 votes et 9.2 passe devant tout.
- **Seuil minimal de votes** (`m`), calibré sur TMDB le 2026-10-10 : films P1 10 · P2 50 · P3 100 · P4 3 000. Séries P1 5 · P2 20 · P3 50 · P4 1 500. Les valeurs de départ (50 / 200 / 500) ne laissaient que 12 à 17 titres sur les périodes récentes ; ces seuils donnent ≥ 50 candidats par liste. Réglables dans `config.py`.
- « Culte » n'est pas directement mesurable : on le **mesure par proxy** (beaucoup de votes + bonne note, des années après). Idée à tester : bonus si TMDB porte le mot-clé « cult film ».

## 5. Mode perso — matching pur

C'est du **filtrage par contenu** classique, avec un signal collaboratif « emprunté » à TMDB.

### Entrée

Une liste de 10 à 20 titres qu'elle a aimés, avec 3 niveaux : **adoré** (+2) · **aimé** (+1) · **pas aimé** (−1). Les « pas aimé » comptent autant que les autres : ils évitent les contresens.

### Profil de goûts

Pour chaque titre de la liste, on récupère ses caractéristiques, puis on additionne en pondérant par la note donnée :

| Groupe | Contenu | Poids de départ |
|---|---|---|
| Mots-clés | Mots-clés TMDB, pondérés TF-IDF (un mot rare pèse plus) | 0.30 |
| Genres | Genres TMDB | 0.25 |
| Personnes | Réalisateur·rice / créateur·rice + 5 premiers rôles | 0.20 |
| Langue / pays | Langue originale, pays | 0.10 |
| Format | Durée, nombre de saisons | 0.10 |
| Époque | Décennie | 0.05 |

### Score d'un candidat

```
score = 0.45·similarité(profil, candidat)      # cosinus sur les groupes ci-dessus
      + 0.30·co-reco(candidat)                 # nb de titres aimés dont TMDB le recommande
      + 0.15·qualité(candidat)                 # note pondérée du §4
      − 0.30·proximité(candidat, « pas aimé »)
```

Puis **diversité** : pas plus de 3 titres du même genre principal dans un top 10.

Poids de départ : on les règle ensuite avec le test du §8, pas à l'intuition.

### Explication (sans texte généré)

Gabarit fixe : « **Proche de :** A, B » (les 1 à 2 titres aimés qui contribuent le plus) + « **Genres :** … ». Rien d'autre.

### Combien de titres ?

Sans LLM, il n'y a aucune connaissance a priori : le profil n'est que la somme de ce qu'on lui donne. D'où un seuil un peu plus haut que dans le premier plan :

- **5** : ça démarre, mais bruité.
- **15 à 20** : cible raisonnable. Sur MovieLens, le gain est rapide jusqu'à ~21 notes, puis seulement linéaire (voir sources).
- **Au-delà de 25** : peu de gain pour l'effort.

Ces chiffres viennent de systèmes collaboratifs. Pour **ton** système, la réponse se mesure : voir §8.

## 6. Anti-spoil (par construction)

Sans LLM, on ne génère pas de texte : on **n'affiche que des champs sûrs**.

| Affiché par défaut | Caché derrière un clic | Jamais |
|---|---|---|
| Titre, année, genres, durée / nb de saisons, affiche, note TMDB, tagline, badge plateforme | Synopsis TMDB (« voir le synopsis ») | Critiques, titres ou résumés d'épisodes, images de fond / stills, mots-clés, changements de casting, bande-annonce |

Règles :
- **Mots-clés : usage interne seulement.** Certains peuvent spoiler (retournements, morts). Ils servent au score, jamais à l'affichage.
- **Une reco = une série, décrite par son niveau série.** Pas de données de saison ≥ 2 ni d'épisodes.
- **Séries déjà commencées** : on ne les montre pas dans les recos.

Limite assumée : la tagline est un texte marketing, très probablement sûr mais non garanti. Le synopsis étant masqué par défaut, le risque est porté par un clic volontaire.

## 7. Plateformes (facultatif)

- **Par défaut : rien.** L'info « où le regarder » n'est pas dans le périmètre v1.
- **Option légère** : un badge « dispo en France sur : Netflix, Prime… » sur chaque carte, via `watch/providers`. Un appel par titre affiché, **pas de regroupement par plateforme**. Attribution JustWatch obligatoire dans la page.
- Donnée à prendre comme indicative : quelques jours de retard possibles.

## 8. Évaluation (sans juge LLM)

Tout est testable avec **sa propre liste**, de façon déterministe :

1. **Leave-one-out** : on cache 3 titres qu'elle a adorés, on les mélange à ~200 titres tirés au hasard, on regarde leur rang.
   - Métrique : **Hit@10** (combien des 3 sont dans le top 10).
   - Cible : mieux que le classement générique (§4).
2. **Courbe « combien de titres »** : on refait le test avec 5, 10, 15, 20 titres de sa liste. Le point où ça plafonne donne **le x de ta question**.
3. **Réglage des poids** : petite recherche sur grille des poids du §5, on garde la combinaison qui maximise Hit@10.
4. **Test réel** : sur les 20 premières recos, au moins la moitié du genre « oui, je regarderais ».

## 9. Limites assumées (sans LLM)

- **Le ton et l'ambiance** (« lent », « cosy », « sombre ») ne sont captés que via les mots-clés TMDB, inégaux d'un titre à l'autre. C'est la principale perte par rapport à un LLM.
- **Les nouveautés** (P1, P2) ont peu de mots-clés et peu de recommandations TMDB : la communauté ne les a pas encore renseignés. Pour elles, le score s'appuie davantage sur genres + personnes + langue, et moins sur mots-clés + co-reco. Le plan les repondère automatiquement.
- **Biais de popularité** : TMDB favorise ce qui est déjà populaire. On peut ajouter un petit bouton « surprends-moi » (pénalise la popularité).
- **Explication courte** : « proche de X » plutôt qu'une phrase rédigée.

## 10. Architecture

Python 3 + SQLite + une page HTML. Pas de framework lourd.

```
TMDB ──► ingest.py (hebdo) ──► SQLite : titres, mots-clés, personnes, recos, profil, vus
                                  │
        mode générique (§4) ──────┤
        mode perso (§5) ──────────┤
                                  ▼
                   build_page.py ──► index.html (8 listes, onglets périodes)
```

Fichiers prévus : `ingest.py`, `score.py`, `build_page.py`, `profile.json`, `.env` (clé TMDB, hors dépôt).

## 11. Phases

| Phase | Contenu | Terminé quand |
|---|---|---|
| **0. Setup** | Clé TMDB, projet Python, SQLite | Un titre est récupéré et stocké |
| **1. Générique** | 4 périodes × films/séries, scoring §4, page HTML | La page affiche 8 listes sans spoil |
| **2. Profil** | Recherche par titre, saisie des 10-20 titres avec leur niveau | `profile.json` rempli et relu |
| **3. Matching** | Scoring §5, explications, test §8 | Hit@10 > classement générique |
| **4. Retour** | Boutons « déjà vu » / « pas intéressé » qui ajustent le profil | Un clic change le classement |
| **5. Rafraîchissement** | Lancement hebdo automatique (launchd/cron), cache | La page se met à jour seule |
| **6. Facultatif** | Badge plateforme · mode « duo » (ses goûts + les tiens) · autres médias | À la demande |

**Avancement (2026-10-10) :** phases 0 et 1 faites. `python3 refresh.py` produit `output/index.html` (8 listes de 20 titres, synopsis repliés). Prochaine étape : phase 2 (profil de goûts).

## 12. Points à confirmer

1. **Périodes** : « année dernière » = 12 mois glissants ou année civile ? « Cultes » = 1 à 15 ans ou 10 à 15 ans ? (§2)
2. **Accès** : sur ton Mac seulement, sur le réseau local (téléphone de ta chérie), ou un fichier HTML envoyé ? Le « retour » de la phase 4 en dépend.
3. **Badge plateforme** : oui / non. (§7)
4. **Clé TMDB** : à créer par toi, c'est un compte à ton nom.

## Sources

- [TMDB — FAQ / conditions d'usage](https://developer.themoviedb.org/docs/faq)
- [TMDB — discover movie](https://developer.themoviedb.org/reference/discover-movie)
- [TMDB — discover tv](https://developer.themoviedb.org/reference/discover-tv)
- [TMDB — recommandations séries](https://developer.themoviedb.org/reference/tv-series-recommendations)
- [TMDB — mots-clés films](https://developer.themoviedb.org/reference/movie-keywords)
- [TMDB — watch providers](https://developer.themoviedb.org/reference/movie-watch-providers)
- [Cold start : nombre minimal de notes (arXiv 2106.00102)](https://ar5iv.labs.arxiv.org/html/2106.00102)
- [Cold start : « kinda cold » 10-20 notes (UMN)](https://www-users.cse.umn.edu/~kluve018/static/EvaluatingRecommenderBehavior.pdf)

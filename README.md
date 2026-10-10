# Media 4 u

Ce qui est sorti et fait parler de lui (films + séries), par période, sans spoil, avec un
classement personnalisé et une liste qui se met à jour quand on marque un titre « déjà vu ».
Le plan et les choix de conception sont dans [plan.md](plan.md).

## Utilisation

1. Mets ta clé TMDB (v3) dans un fichier `.env` à la racine : `TMDB_API_KEY=...`
2. `python3 refresh.py` : récupère les données TMDB (environ 1 minute, 6 la toute première fois)
   et génère la page `docs/index.html`.
   `python3 refresh.py --page-only` régénère la page depuis la base locale, sans appeler TMDB.
3. `python3 quiz.py` : un quiz (≈ 3 minutes) construit un profil de goûts dans `profiles/`
   et ouvre la page. Un profil par personne.

La page est **autonome** : données, moteur de classement et interface sont dans un seul fichier.
Elle peut être ouverte telle quelle ou publiée (GitHub Pages sert le dossier `docs/`).

### Mise à jour de la liste

Sur la page, « Déjà vu » demande un avis (adoré / aimé / bof / pas aimé) : le titre sort de la
liste, la liste est recalculée avec ce nouvel avis et se remplit de nouveau à 20 titres.
« Pas intéressé » masque un titre sans toucher aux goûts. Ces choix sont gardés dans le
navigateur (par appareil). Pour les conserver durablement :

1. Dans la page : « Mes titres vus » → « Sauvegarder mes choix » (télécharge un fichier).
2. `python3 merge_state.py celia ~/Downloads/media4u-celia-….json` les ajoute au profil.
3. `python3 refresh.py --page-only` régénère la page avec le profil enrichi.

## Fichiers

| Fichier | Rôle |
|---|---|
| `config.py` | Périodes, seuils, poids |
| `tmdb.py` | Client TMDB |
| `ingest.py` | Récupération des viviers et des fiches |
| `score.py` | Score « ça fait parler » |
| `taxonomy.py` | Familles et goûts précis du quiz |
| `personal.py` | Matching « pour toi » (Python : quiz, duels, vérification) |
| `web/engine.js` | Jumeau JavaScript de `personal.py` : classe dans le navigateur |
| `web/app.js`, `web/style.css` | Interface de la page |
| `build_page.py` | Assemble `docs/index.html` |
| `quiz.py`, `quiz.html` | Quiz local qui produit un profil |
| `merge_state.py` | Intègre une sauvegarde de la page dans un profil |
| `check_parity.py` | Vérifie que Python et JavaScript classent pareil (Node requis) |
| `refresh.py` | Point d'entrée |

Python 3.10+, aucune dépendance. Les réglages sont dans `config.py` (périodes, seuils) et
`personal.py` (poids du matching). **Après avoir changé une formule, relance
`python3 check_parity.py`** : le moteur Python et le moteur JavaScript doivent rester jumeaux.

This product uses the TMDB API but is not endorsed or certified by TMDB.

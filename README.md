# Media 4 u

Ce qui est sorti et fait parler de lui (films + séries), par période, sans spoil.
Le plan et les choix de conception sont dans [plan.md](plan.md).

## Utilisation

1. Mets ta clé TMDB (v3) dans un fichier `.env` à la racine : `TMDB_API_KEY=...`
2. Lance `python3 refresh.py` (environ 1 minute), puis ouvre `output/index.html`.
   `python3 refresh.py --page-only` régénère la page depuis la base locale, sans appeler TMDB.

Python 3.10+ suffit, aucune dépendance à installer.
Les réglages (périodes, seuils de votes, poids du score) sont dans `config.py`.

## Fichiers

| Fichier | Rôle |
|---|---|
| `config.py` | Périodes, seuils, poids |
| `tmdb.py` | Client TMDB |
| `ingest.py` | Récupération des viviers et des fiches |
| `score.py` | Score « ça fait parler » |
| `build_page.py` | Génération de la page HTML |
| `refresh.py` | Point d'entrée |

This product uses the TMDB API but is not endorsed or certified by TMDB.

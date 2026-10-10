"""Réglages du projet : périodes, seuils de votes, poids du score.

Tout ce qui est « à calibrer » (seuils, poids) est ici : on ajuste sans toucher au code.
"""
import calendar
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).parent
DB_PATH = ROOT / "media4u.db"
OUTPUT_DIR = ROOT / "docs"       # page publiée (GitHub Pages sert /docs)
PROFILES_DIR = ROOT / "profiles"   # un fichier JSON par personne (versionné)
QUIZ_PORT = 8765

LANGUAGE = "fr-FR"
LIST_SIZE = 20          # titres affichés par liste
DETAIL_TTL_DAYS = 7     # une fiche plus récente que ça n'est pas re-téléchargée
REQUIRE_POSTER = True   # écarte les fiches sans affiche (souvent du bruit)

# Genres TV écartés : ce n'est pas ce qu'on cherche à regarder le soir.
TV_EXCLUDED_GENRES = {10763, 10766, 10767}  # News, Soap, Talk

MEDIA = {"movie": "Films", "tv": "Séries"}

# Poids du score de buzz (voir plan.md §4). Pourcentiles calculés dans chaque liste.
WEIGHTS = {
    "buzz": {"popularity": 0.5, "votes": 0.3, "wr": 0.2},
    "cult": {"votes": 0.4, "wr": 0.4, "popularity": 0.2},
}

# `sort_by` choisit le *vivier* récupéré chez TMDB ; `formula` le score appliqué ensuite.
# `min_votes` sert à la fois de filtre TMDB (vote_count.gte) et de seuil `m` de la note pondérée.
# Seuils calibrés le 2026-10-10 pour garder ≥ 50 candidats par liste (mesure sur TMDB) :
# les valeurs du plan (50/200/500) laissaient 12 à 17 titres sur les périodes récentes.
PERIODS = [
    {"key": "p1", "label": "Le mois dernier", "hint": "sortis ces 30 derniers jours",
     "sort_by": "popularity.desc", "pages": 5, "formula": "buzz",
     "min_votes": {"movie": 10, "tv": 5}},
    {"key": "p2", "label": "Les 6 derniers mois", "hint": "sortis il y a 1 à 6 mois",
     "sort_by": "popularity.desc", "pages": 5, "formula": "buzz",
     "min_votes": {"movie": 50, "tv": 20}},
    {"key": "p3", "label": "L'année dernière", "hint": "sortis il y a 6 à 12 mois",
     "sort_by": "popularity.desc", "pages": 5, "formula": "buzz",
     "min_votes": {"movie": 100, "tv": 50}},
    {"key": "p4", "label": "Les cultes", "hint": "sortis il y a 1 à 15 ans",
     "sort_by": "vote_average.desc", "pages": 10, "formula": "cult",
     "min_votes": {"movie": 3000, "tv": 1500}},
]


def add_months(d: date, months: int) -> date:
    index = d.year * 12 + (d.month - 1) + months
    year, month = divmod(index, 12)
    month += 1
    return date(year, month, min(d.day, calendar.monthrange(year, month)[1]))


def period_windows(today: date | None = None) -> dict[str, tuple[date, date]]:
    """Fenêtres de sortie glissantes, contiguës et sans chevauchement (bornes incluses)."""
    today = today or date.today()
    one_day = timedelta(days=1)
    p1_start = today - timedelta(days=30)
    p2_start = add_months(today, -6)
    p3_start = add_months(today, -12)
    p4_start = add_months(today, -15 * 12)
    return {
        "p1": (p1_start, today),
        "p2": (p2_start, p1_start - one_day),
        "p3": (p3_start, p2_start - one_day),
        "p4": (p4_start, p3_start - one_day),
    }

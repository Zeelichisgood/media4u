"""Récupération des données TMDB : viviers par période, puis fiches détaillées."""
import json
import unicodedata
from datetime import date, datetime, timedelta, timezone

from config import (DETAIL_TTL_DAYS, MEDIA, PERIODS, REQUIRE_POSTER,
                    TV_EXCLUDED_GENRES, period_windows)
from tmdb import TMDB

# média -> (endpoint discover, champ de date utilisé pour la fenêtre)
DISCOVER = {
    "movie": ("/discover/movie", "primary_release_date"),
    "tv": ("/discover/tv", "first_air_date"),
}


def fetch_genres(client: TMDB, conn) -> None:
    for media in MEDIA:
        data = client.get(f"/genre/{media}/list")
        conn.executemany(
            "INSERT OR REPLACE INTO genres (media, id, name) VALUES (?, ?, ?)",
            [(media, g["id"], g["name"]) for g in data["genres"]],
        )
    conn.commit()


def keep(item: dict, media: str) -> bool:
    if REQUIRE_POSTER and not item.get("poster_path"):
        return False
    if media == "tv" and TV_EXCLUDED_GENRES & set(item.get("genre_ids", [])):
        return False
    return True


def fetch_pool(client: TMDB, media: str, period: dict, window: tuple[date, date]) -> list[dict]:
    """Vivier de candidats d'une période : on récupère large, le score trie ensuite."""
    path, date_field = DISCOVER[media]
    gte, lte = window
    params = {
        "sort_by": period["sort_by"],
        f"{date_field}.gte": gte.isoformat(),
        f"{date_field}.lte": lte.isoformat(),
        "vote_count.gte": period["min_votes"][media],
        "include_adult": "false",
    }
    if media == "tv":
        params["without_genres"] = "|".join(str(g) for g in sorted(TV_EXCLUDED_GENRES))

    found: dict[int, dict] = {}
    for page in range(1, period["pages"] + 1):
        data = client.get(path, page=page, **params)
        for item in data["results"]:
            found.setdefault(item["id"], item)  # le tri bouge parfois entre deux pages
        if page >= data.get("total_pages", 1):
            break
    return [item for item in found.values() if keep(item, media)]


def clean(text: str) -> str:
    """Retire les caractères invisibles de mise en forme (TMDB en glisse dans certains titres)."""
    return "".join(ch for ch in text if unicodedata.category(ch) != "Cf").strip()


def to_row(media: str, item: dict) -> dict:
    return {
        "media": media,
        "tmdb_id": item["id"],
        "title": clean(item.get("title") or item.get("name") or ""),
        "release_date": item.get("release_date") or item.get("first_air_date") or None,
        "genre_ids": json.dumps(item.get("genre_ids", [])),
        "original_language": item.get("original_language"),
        "poster_path": item.get("poster_path"),
        "vote_average": item.get("vote_average") or 0,
        "vote_count": item.get("vote_count") or 0,
        "popularity": item.get("popularity") or 0,
        "overview": item.get("overview") or None,
    }


UPSERT_TITLE = """
INSERT INTO titles (media, tmdb_id, title, release_date, genre_ids, original_language,
                    poster_path, vote_average, vote_count, popularity, overview)
VALUES (:media, :tmdb_id, :title, :release_date, :genre_ids, :original_language,
        :poster_path, :vote_average, :vote_count, :popularity, :overview)
ON CONFLICT (media, tmdb_id) DO UPDATE SET
    title = excluded.title,
    release_date = excluded.release_date,
    genre_ids = excluded.genre_ids,
    original_language = excluded.original_language,
    poster_path = excluded.poster_path,
    vote_average = excluded.vote_average,
    vote_count = excluded.vote_count,
    popularity = excluded.popularity,
    overview = COALESCE(excluded.overview, titles.overview)
"""


def fetch_pools(client: TMDB, conn, today: date | None = None) -> None:
    windows = period_windows(today)
    for period in PERIODS:
        gte, lte = windows[period["key"]]
        for media in MEDIA:
            pool = fetch_pool(client, media, period, (gte, lte))
            conn.execute("DELETE FROM period_items WHERE period = ? AND media = ?",
                         (period["key"], media))
            conn.executemany(UPSERT_TITLE, [to_row(media, item) for item in pool])
            conn.executemany(
                "INSERT INTO period_items (period, media, tmdb_id) VALUES (?, ?, ?)",
                [(period["key"], media, item["id"]) for item in pool],
            )
            conn.commit()
            print(f"  {period['key']} {media:<5} {gte} → {lte} : {len(pool)} candidats")


def fetch_details(client: TMDB, conn) -> None:
    """Fiche détaillée (durée, saisons, tagline) pour les seuls titres affichés."""
    limit = (datetime.now(timezone.utc) - timedelta(days=DETAIL_TTL_DAYS)).isoformat()
    todo = conn.execute(
        """
        SELECT DISTINCT t.media, t.tmdb_id
        FROM titles t JOIN period_items p ON p.media = t.media AND p.tmdb_id = t.tmdb_id
        WHERE p.rank IS NOT NULL
          AND (t.detail_fetched_at IS NULL OR t.detail_fetched_at < ?)
        """,
        (limit,),
    ).fetchall()
    print(f"  {len(todo)} fiches à récupérer")
    for row in todo:
        data = client.get(f"/{row['media']}/{row['tmdb_id']}")
        runtime = data.get("runtime")
        if row["media"] == "tv":
            episode_runtimes = data.get("episode_run_time") or []
            runtime = episode_runtimes[0] if episode_runtimes else None
        conn.execute(
            """
            UPDATE titles SET tagline = ?, runtime = ?, seasons = ?,
                   overview = COALESCE(?, overview), detail_fetched_at = ?
            WHERE media = ? AND tmdb_id = ?
            """,
            (
                data.get("tagline") or None,
                runtime or None,
                data.get("number_of_seasons"),
                data.get("overview") or None,
                datetime.now(timezone.utc).isoformat(),
                row["media"],
                row["tmdb_id"],
            ),
        )
        conn.commit()

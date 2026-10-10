"""Base SQLite : schéma et connexion."""
import sqlite3

from config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS genres (
    media TEXT NOT NULL,
    id    INTEGER NOT NULL,
    name  TEXT NOT NULL,
    PRIMARY KEY (media, id)
);

CREATE TABLE IF NOT EXISTS titles (
    media             TEXT NOT NULL,           -- 'movie' | 'tv'
    tmdb_id           INTEGER NOT NULL,
    title             TEXT NOT NULL,
    release_date      TEXT,
    genre_ids         TEXT NOT NULL DEFAULT '[]',
    original_language TEXT,
    poster_path       TEXT,
    vote_average      REAL NOT NULL DEFAULT 0,
    vote_count        INTEGER NOT NULL DEFAULT 0,
    popularity        REAL NOT NULL DEFAULT 0,
    overview          TEXT,
    tagline           TEXT,
    runtime           INTEGER,                 -- minutes (film, ou durée d'épisode)
    seasons           INTEGER,                 -- séries uniquement
    detail_fetched_at TEXT,
    PRIMARY KEY (media, tmdb_id)
);

CREATE TABLE IF NOT EXISTS period_items (
    period  TEXT NOT NULL,
    media   TEXT NOT NULL,
    tmdb_id INTEGER NOT NULL,
    buzz    REAL,
    wr      REAL,
    rank    INTEGER,                           -- NULL si hors du top affiché
    PRIMARY KEY (period, media, tmdb_id)
);

-- Caractéristiques servant au matching (mots-clés, équipe, recommandations TMDB)
CREATE TABLE IF NOT EXISTS features (
    media      TEXT NOT NULL,
    tmdb_id    INTEGER NOT NULL,
    keywords   TEXT NOT NULL DEFAULT '[]',     -- noms TMDB (anglais), minuscules
    cast_ids   TEXT NOT NULL DEFAULT '[]',     -- 5 premiers rôles
    crew_ids   TEXT NOT NULL DEFAULT '[]',     -- réalisateur·rice(s) ou créateur·rice(s)
    reco_ids   TEXT NOT NULL DEFAULT '[]',     -- recommandations TMDB (même média)
    fetched_at TEXT NOT NULL,
    PRIMARY KEY (media, tmdb_id)
);
"""


def connect(path=DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn

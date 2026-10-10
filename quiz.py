"""Quiz de goûts : petit serveur local qui produit un profil, puis régénère la page.

    python3 quiz.py            # ouvre http://127.0.0.1:8765
    python3 quiz.py --no-open  # sans ouvrir le navigateur

Le serveur n'écoute que sur 127.0.0.1 et garde la clé TMDB côté Python.
"""
import json
import sys
import urllib.parse
import webbrowser
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import build_page
import ingest
import personal
import taxonomy
from config import OUTPUT_DIR, QUIZ_PORT, ROOT
from db import connect
from tmdb import TMDB, TMDBError

HOST = "127.0.0.1"
POSTER = "https://image.tmdb.org/t/p/w342"
MAX_BODY = 200_000


def client_taxonomy() -> str:
    """Ce que le navigateur a besoin de connaître (sans les listes de mots-clés)."""
    return json.dumps({
        "families": [{k: f[k] for k in ("id", "label", "emoji", "hint")} for f in taxonomy.FAMILIES],
        "tastes": [{k: t[k] for k in ("id", "family", "label", "hint")} for t in taxonomy.TASTES],
    }, ensure_ascii=False)


def clean_profile(payload: dict) -> dict:
    name = str(payload.get("name") or "Moi").strip()[:40] or "Moi"
    families = {k: int(v) for k, v in (payload.get("families") or {}).items()
                if k in taxonomy.FAMILY_BY_ID and v in (-1, 1)}
    tastes = {k: int(v) for k, v in (payload.get("tastes") or {}).items()
              if k in taxonomy.TASTE_BY_ID and v in (-1, 1)}
    favorites = []
    for fav in payload.get("favorites") or []:
        try:
            media, tmdb_id, level = fav["media"], int(fav["id"]), float(fav["level"])
        except (KeyError, TypeError, ValueError):
            continue
        if media not in ("movie", "tv") or not -2 <= level <= 2:
            continue
        favorites.append({
            "media": media, "id": tmdb_id, "level": level,
            "title": str(fav.get("title") or "")[:120],
            "source": "duel" if fav.get("source") == "duel" else "fav",
        })
    return {"name": name, "families": families, "tastes": tastes, "favorites": favorites}


def card_for(conn, ref) -> dict:
    row = conn.execute("SELECT * FROM titles WHERE media = ? AND tmdb_id = ?", ref).fetchone()
    names = {g["id"]: g["name"] for g in
             conn.execute("SELECT id, name FROM genres WHERE media = ?", (ref[0],))}
    return {
        "media": ref[0],
        "id": ref[1],
        "title": row["title"],
        "year": (row["release_date"] or "")[:4],
        "poster": POSTER + row["poster_path"] if row["poster_path"] else None,
        "genres": [names[g] for g in json.loads(row["genre_ids"]) if g in names][:3],
        "tagline": row["tagline"],
        "format": "Film" if ref[0] == "movie" else "Série",
    }


def search(query: str) -> list[dict]:
    if len(query) < 2:
        return []
    data = TMDB().get("/search/multi", query=query, include_adult="false")
    found = []
    for r in data.get("results", []):
        if r.get("media_type") not in ("movie", "tv"):
            continue
        found.append({
            "media": r["media_type"],
            "id": r["id"],
            "title": r.get("title") or r.get("name") or "",
            "year": (r.get("release_date") or r.get("first_air_date") or "")[:4],
            "poster": POSTER + r["poster_path"] if r.get("poster_path") else None,
        })
    return found[:8]


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):  # silencieux
        pass

    def send_bytes(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, payload, status: int = 200) -> None:
        self.send_bytes(status, json.dumps(payload, ensure_ascii=False).encode(),
                        "application/json; charset=utf-8")

    def read_json(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY:
            raise ValueError("requête trop grosse")
        return json.loads(self.rfile.read(length) or b"{}")

    def do_GET(self) -> None:
        url = urllib.parse.urlparse(self.path)
        try:
            if url.path == "/":
                page = (ROOT / "quiz.html").read_text(encoding="utf-8")
                page = page.replace("/*__TAXONOMY__*/null", client_taxonomy())
                self.send_bytes(200, page.encode(), "text/html; charset=utf-8")
            elif url.path == "/site":
                out = OUTPUT_DIR / "index.html"
                if not out.exists():
                    self.send_bytes(404, "Lance d'abord python3 refresh.py".encode(), "text/plain; charset=utf-8")
                else:
                    self.send_bytes(200, out.read_bytes(), "text/html; charset=utf-8")
            elif url.path == "/api/search":
                query = urllib.parse.parse_qs(url.query).get("q", [""])[0].strip()
                self.send_json(search(query))
            else:
                self.send_bytes(404, b"Not found", "text/plain")
        except (TMDBError, OSError) as error:
            self.send_json({"error": str(error)}, 502)

    def do_POST(self) -> None:
        try:
            payload = self.read_json()
            conn = connect()
            if self.path == "/api/duel":
                profile = clean_profile(payload)
                shown = {(m, int(i)) for m, i in payload.get("shown") or [] if m in ("movie", "tv")}
                pair = personal.pick_duel(conn, profile, shown)
                if pair is None:
                    self.send_json({"done": True})
                else:
                    self.send_json({"a": card_for(conn, pair[0].ref), "b": card_for(conn, pair[1].ref)})
            elif self.path == "/api/profile":
                profile = clean_profile(payload)
                profile["created"] = date.today().isoformat()
                existing = personal.PROFILES_DIR / f"{personal.slugify(profile['name'])}.json"
                if existing.exists():  # refaire le quiz garde les titres masqués
                    try:
                        profile["hidden"] = json.loads(existing.read_text(encoding="utf-8")).get("hidden", [])
                    except (OSError, ValueError):
                        pass
                client = TMDB()
                for fav in profile["favorites"]:
                    ingest.ensure_title(client, conn, fav["media"], fav["id"])
                slug = personal.save_profile(profile)
                build_page.build(conn)
                self.send_json({"ok": True, "slug": slug, "url": f"/site#{slug}"})
            else:
                self.send_bytes(404, b"Not found", "text/plain")
        except (ValueError, TypeError) as error:
            self.send_json({"error": f"requête invalide : {error}"}, 400)
        except (TMDBError, OSError) as error:
            self.send_json({"error": str(error)}, 502)


def main(argv: list[str]) -> int:
    server = ThreadingHTTPServer((HOST, QUIZ_PORT), Handler)
    url = f"http://{HOST}:{QUIZ_PORT}/"
    print(f"Quiz : {url}   (Ctrl+C pour arrêter)")
    if "--no-open" not in argv:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nArrêt.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

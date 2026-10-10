"""Génère docs/index.html : une page autonome (données + moteur + interface).

Le classement « pour toi » est recalculé dans le navigateur à partir des données embarquées :
la page fonctionne telle quelle sur GitHub Pages, sans serveur, et chaque titre « déjà vu »
met la liste à jour instantanément (voir web/engine.js, jumeau de personal.py).

Affiché par défaut : titre, année, genres, durée / saisons, affiche, note, tagline.
Caché derrière un clic : synopsis. Jamais affiché : mots-clés bruts, critiques, épisodes, stills.
Les puces « goûts » viennent d'un vocabulaire maison (taxonomy.py), pas des mots-clés TMDB.
"""
import json
from datetime import date

import personal
from config import LIST_SIZE, MEDIA, OUTPUT_DIR, PERIODS, ROOT, period_windows

WEB_DIR = ROOT / "web"

PAGE = """<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>Media 4 u</title>
<style>/*__CSS__*/</style>
</head>
<body>
<div class="wrap" id="app"><p class="empty">Chargement…</p></div>
<div class="toast" id="toast" hidden></div>
<noscript><p class="empty">Cette page a besoin de JavaScript pour s'afficher.</p></noscript>
<script type="application/json" id="data">/*__DATA__*/</script>
<script>/*__ENGINE__*/</script>
<script>/*__APP__*/</script>
</body>
</html>
"""


def fmt_date(d: date) -> str:
    return d.strftime("%d/%m/%Y")


def site_data(conn, today: date, profiles: list[dict]) -> dict:
    """Tout ce dont la page a besoin, sous une forme compacte."""
    windows = period_windows(today)
    extra = personal.profile_refs(profiles)
    signals = personal.signal_map(conn)

    rows = conn.execute(
        """
        SELECT t.*, f.keywords, f.cast_ids, f.crew_ids, f.reco_ids,
               (SELECT p.period FROM period_items p
                WHERE p.media = t.media AND p.tmdb_id = t.tmdb_id) AS period
        FROM titles t JOIN features f ON f.media = t.media AND f.tmdb_id = t.tmdb_id
        """
    ).fetchall()
    selected = sorted(
        (r for r in rows if r["period"] or (r["media"], r["tmdb_id"]) in extra),
        key=lambda r: (r["period"] or "~", r["media"], r["tmdb_id"]),
    )
    known = {(r["media"], r["tmdb_id"]) for r in selected}

    keyword_index: dict[str, int] = {}

    def index_of(keyword: str) -> int:
        return keyword_index.setdefault(keyword, len(keyword_index))

    items = []
    for r in selected:
        ref = (r["media"], r["tmdb_id"])
        buzz, quality = signals.get(ref, (0.0, 0.0))
        items.append({
            "m": r["media"], "i": r["tmdb_id"], "t": r["title"],
            "y": (r["release_date"] or "")[:4],
            "g": json.loads(r["genre_ids"]),
            "k": [index_of(k) for k in sorted(json.loads(r["keywords"]))],
            "cr": json.loads(r["crew_ids"]),
            "ca": json.loads(r["cast_ids"]),
            # Sans perte : le moteur ne teste que des paires de titres embarqués.
            "rc": [i for i in json.loads(r["reco_ids"]) if (r["media"], i) in known],
            "p": r["period"], "bz": buzz, "q": quality,
            "n": r["vote_count"], "v": r["vote_average"],
            "rt": r["runtime"], "se": r["seasons"],
            "tg": r["tagline"], "ov": r["overview"], "po": r["poster_path"],
        })

    genres: dict[str, dict[int, str]] = {m: {} for m in MEDIA}
    for g in conn.execute("SELECT media, id, name FROM genres"):
        genres[g["media"]][g["id"]] = g["name"]

    import taxonomy  # local : évite un import circulaire au chargement
    return {
        "generated": fmt_date(today),
        "config": {
            "listSize": LIST_SIZE,
            "familySpillover": personal.FAMILY_SPILLOVER,
            "simScale": personal.SIM_SCALE,
            "coRecoBonus": personal.CO_RECO_BONUS,
            "becauseMin": personal.BECAUSE_MIN,
            "weakBelow": personal.WEAK_BELOW,
            "weights": personal.COMPONENT_WEIGHTS,
        },
        "periods": [
            {"key": p["key"], "label": p["label"], "hint": p["hint"],
             "gte": fmt_date(windows[p["key"]][0]), "lte": fmt_date(windows[p["key"]][1])}
            for p in PERIODS
        ],
        "media": MEDIA,
        "genres": genres,
        "keywords": [k for k, _ in sorted(keyword_index.items(), key=lambda kv: kv[1])],
        "taxonomy": {
            "families": [{k: f[k] for k in ("id", "label", "emoji", "hint", "genres")}
                         for f in taxonomy.FAMILIES],
            "tastes": [{"id": t["id"], "family": t["family"], "label": t["label"],
                        "hint": t["hint"], "kw": sorted(t["kw"]), "genres": sorted(t["genres"]),
                        "need": t["need"], "show": t["show"]} for t in taxonomy.TASTES],
        },
        "items": items,
        "profiles": [
            {"slug": p["slug"], "name": p["name"],
             "families": p.get("families", {}), "tastes": p.get("tastes", {}),
             "favorites": p.get("favorites", []), "hidden": p.get("hidden", [])}
            for p in profiles
        ],
    }


def build(conn, today: date | None = None) -> str:
    today = today or date.today()
    data = site_data(conn, today, personal.load_profiles())
    # « < » échappé : la donnée ne peut jamais refermer la balise <script>.
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")

    page = (PAGE
            .replace("/*__CSS__*/", (WEB_DIR / "style.css").read_text(encoding="utf-8"))
            .replace("/*__ENGINE__*/", (WEB_DIR / "engine.js").read_text(encoding="utf-8"))
            .replace("/*__APP__*/", (WEB_DIR / "app.js").read_text(encoding="utf-8"))
            .replace("/*__DATA__*/", payload))
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / ".nojekyll").touch()   # GitHub Pages : servir tel quel, sans Jekyll
    out = OUTPUT_DIR / "index.html"
    out.write_text(page, encoding="utf-8")
    return str(out)

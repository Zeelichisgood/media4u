"""Génère output/index.html : 4 périodes × films/séries, sans spoil par construction.

Affiché par défaut : titre, année, genres, durée / saisons, affiche, note, tagline.
Caché derrière un clic : synopsis. Jamais affiché : mots-clés, critiques, épisodes, stills.
"""
import html
import json
from datetime import date

from config import LIST_SIZE, MEDIA, OUTPUT_DIR, PERIODS, period_windows

POSTER_BASE = "https://image.tmdb.org/t/p/w342"
TMDB_LOGO = ("https://www.themoviedb.org/assets/v4/logos/v2/"
             "blue_short-8e7b30f73a4020692ccca9c88bafe5dcb6f8a62a4c6bc55cd9ba82bb2cd95f6c.svg")
TMDB_NOTICE = "This product uses the TMDB API but is not endorsed or certified by TMDB."

CSS = """
:root{--bg:#f6f5f2;--card:#fff;--text:#1d1d1f;--muted:#6b6b72;--line:#e3e1db;--accent:#b4442f;--accent-soft:#f6e4df}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#17171a;--card:#212125;--text:#f1f0ed;--muted:#a3a3ab;--line:#33333a;--accent:#ef8a73;--accent-soft:#3a2723}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font:16px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:1040px;margin:0 auto;padding:0 16px}
header.top{padding:28px 0 8px}
h1{margin:0;font-size:1.7rem;letter-spacing:-.02em}
.sub{margin:4px 0 0;color:var(--muted)}
.tabs{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin:20px 0 12px}
.tab{appearance:none;border:1px solid var(--line);background:var(--card);color:var(--text);border-radius:12px;padding:10px 12px;text-align:left;cursor:pointer;font:inherit}
.tab .t{display:block;font-weight:600}
.tab .h{display:block;font-size:.8rem;color:var(--muted)}
.tab[aria-selected="true"]{border-color:var(--accent);background:var(--accent-soft)}
.switch{display:inline-flex;border:1px solid var(--line);border-radius:999px;overflow:hidden;margin-bottom:16px;background:var(--card)}
.switch button{appearance:none;border:0;background:transparent;color:var(--text);padding:8px 20px;font:inherit;cursor:pointer}
.switch button[aria-pressed="true"]{background:var(--accent);color:#fff}
.window{color:var(--muted);font-size:.9rem;margin:0 0 12px}
ol.cards{list-style:none;margin:0;padding:0;display:grid;gap:12px;grid-template-columns:repeat(2,1fr)}
.card{display:flex;gap:14px;background:var(--card);border:1px solid var(--line);border-radius:14px;padding:12px;position:relative}
.card img,.card .noposter{width:92px;flex:none;aspect-ratio:2/3;object-fit:cover;border-radius:8px;background:var(--line)}
.card .noposter{display:grid;place-items:center;color:var(--muted);font-size:.8rem;text-align:center}
.rank{position:absolute;top:-8px;left:-8px;background:var(--accent);color:#fff;font-weight:700;font-size:.8rem;min-width:26px;height:26px;border-radius:13px;display:grid;place-items:center;padding:0 6px}
.card h3{margin:0;font-size:1.02rem;line-height:1.3}
.card .year{color:var(--muted);font-weight:400}
.meta,.note{margin:2px 0;font-size:.88rem;color:var(--muted)}
.note strong{color:var(--text)}
.tagline{margin:6px 0 0;font-size:.9rem;font-style:italic}
details{margin-top:8px;font-size:.88rem}
summary{cursor:pointer;color:var(--accent)}
details p{margin:6px 0 0;color:var(--muted)}
.empty{color:var(--muted)}
footer{margin:36px 0 28px;padding-top:16px;border-top:1px solid var(--line);color:var(--muted);font-size:.82rem;display:flex;gap:14px;align-items:center;flex-wrap:wrap}
footer img{height:14px}
@media (max-width:720px){.tabs{grid-template-columns:repeat(2,1fr)}ol.cards{grid-template-columns:1fr}}
"""

JS = """
(function () {
  var periods = %s, medias = %s, state = { period: periods[0], media: medias[0] };
  try {
    var saved = JSON.parse(localStorage.getItem("media4u") || "{}");
    if (periods.indexOf(saved.period) > -1) state.period = saved.period;
    if (medias.indexOf(saved.media) > -1) state.media = saved.media;
  } catch (e) {}
  function render() {
    document.querySelectorAll(".list").forEach(function (el) {
      el.hidden = !(el.dataset.period === state.period && el.dataset.media === state.media);
    });
    document.querySelectorAll("[data-kind]").forEach(function (b) {
      var on = state[b.dataset.kind] === b.dataset.value;
      b.setAttribute(b.dataset.kind === "period" ? "aria-selected" : "aria-pressed", on);
    });
    try { localStorage.setItem("media4u", JSON.stringify(state)); } catch (e) {}
  }
  document.addEventListener("click", function (e) {
    var b = e.target.closest("[data-kind]");
    if (!b) return;
    state[b.dataset.kind] = b.dataset.value;
    render();
  });
  render();
})();
"""


def esc(value) -> str:
    return html.escape(str(value), quote=True)


def fmt_runtime(minutes: int) -> str:
    hours, rest = divmod(minutes, 60)
    if hours == 0:
        return f"{rest} min"
    return f"{hours} h {rest:02d}" if rest else f"{hours} h"


def fmt_date(d: date) -> str:
    return d.strftime("%d/%m/%Y")


def card(rank: int, row, genre_names: dict[int, str], media: str) -> str:
    year = (row["release_date"] or "")[:4]
    meta = [genre_names[g] for g in json.loads(row["genre_ids"]) if g in genre_names][:3]
    if row["runtime"]:
        meta.append(fmt_runtime(row["runtime"]) + (" / épisode" if media == "tv" else ""))
    if media == "tv" and row["seasons"]:
        meta.append(f"{row['seasons']} saison{'s' if row['seasons'] > 1 else ''}")

    if row["poster_path"]:
        poster = f'<img src="{POSTER_BASE}{esc(row["poster_path"])}" alt="" loading="lazy">'
    else:
        poster = '<div class="noposter">Pas d\'affiche</div>'

    note = f"{row['vote_average']:.1f}".replace(".", ",")
    votes = f"{row['vote_count']:,}".replace(",", " ")
    tagline = f'<p class="tagline">« {esc(row["tagline"])} »</p>' if row["tagline"] else ""
    synopsis = ""
    if row["overview"]:
        synopsis = (
            "<details><summary>Voir le synopsis (peut spoiler)</summary>"
            f"<p>{esc(row['overview'])}</p></details>"
        )

    return (
        f'<li class="card"><span class="rank">{rank}</span>{poster}<div>'
        f'<h3>{esc(row["title"])} <span class="year">({esc(year)})</span></h3>'
        f'<p class="meta">{esc(" · ".join(meta))}</p>'
        f'<p class="note"><strong>★ {note}</strong> · {votes} votes</p>'
        f"{tagline}{synopsis}</div></li>"
    )


def build(conn, today: date | None = None) -> str:
    today = today or date.today()
    windows = period_windows(today)
    genre_names: dict[str, dict[int, str]] = {m: {} for m in MEDIA}
    for g in conn.execute("SELECT media, id, name FROM genres"):
        genre_names[g["media"]][g["id"]] = g["name"]

    tabs = "".join(
        f'<button class="tab" role="tab" data-kind="period" data-value="{p["key"]}">'
        f'<span class="t">{esc(p["label"])}</span><span class="h">{esc(p["hint"])}</span></button>'
        for p in PERIODS
    )
    switch = "".join(
        f'<button data-kind="media" data-value="{key}">{esc(label)}</button>'
        for key, label in MEDIA.items()
    )

    sections = []
    for period in PERIODS:
        gte, lte = windows[period["key"]]
        for media in MEDIA:
            rows = conn.execute(
                """
                SELECT t.*, p.rank FROM period_items p
                JOIN titles t ON t.media = p.media AND t.tmdb_id = p.tmdb_id
                WHERE p.period = ? AND p.media = ? AND p.rank IS NOT NULL
                ORDER BY p.rank LIMIT ?
                """,
                (period["key"], media, LIST_SIZE),
            ).fetchall()
            body = "".join(card(r["rank"], r, genre_names[media], media) for r in rows)
            if not body:
                body = '<li class="empty">Rien à afficher pour cette période.</li>'
            sections.append(
                f'<section class="list" data-period="{period["key"]}" data-media="{media}" hidden>'
                f'<p class="window">Sortis du {fmt_date(gte)} au {fmt_date(lte)}</p>'
                f'<ol class="cards">{body}</ol></section>'
            )

    page = f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Media 4 u</title>
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
<header class="top">
<h1>Media 4 u</h1>
<p class="sub">Ce qui est sorti et fait parler de lui. Aucun spoil : les synopsis restent repliés.</p>
</header>
<nav class="tabs" role="tablist">{tabs}</nav>
<div class="switch">{switch}</div>
<main>{"".join(sections)}</main>
<footer>
<img src="{TMDB_LOGO}" alt="TMDB">
<span>{esc(TMDB_NOTICE)}</span>
<span>Mise à jour : {fmt_date(today)}</span>
</footer>
</div>
<script>{JS % (json.dumps([p["key"] for p in PERIODS]), json.dumps(list(MEDIA)))}</script>
</body>
</html>
"""
    OUTPUT_DIR.mkdir(exist_ok=True)
    out = OUTPUT_DIR / "index.html"
    out.write_text(page, encoding="utf-8")
    return str(out)

"""Vérifie que le moteur JavaScript de la page (web/engine.js) classe comme personal.py.

    python3 check_parity.py

À relancer après toute modification d'une formule (poids, saturation, similarité…) :
la page et Python doivent donner les mêmes listes. Nécessite Node.js.
"""
import copy
import json
import subprocess
import sys
from datetime import date

import build_page
import personal
import taxonomy
from config import LIST_SIZE, MEDIA, PERIODS, ROOT
from db import connect

TOLERANCE = 1e-9


def python_rankings(conn, items, signals, profile):
    matcher = personal.Matcher(profile, items)
    result = {}
    for period in PERIODS:
        for media in MEDIA:
            refs = [(media, r["tmdb_id"]) for r in conn.execute(
                "SELECT tmdb_id FROM period_items WHERE period = ? AND media = ?",
                (period["key"], media))]
            scored = [
                (matcher.evaluate(items[ref], signals.get(ref, (0.0, 0.0))), ref)
                for ref in refs if ref in items and ref not in matcher.seen
            ]
            scored.sort(key=lambda pair: -pair[0]["score"])
            result[f"{period['key']}|{media}"] = [
                {"ref": f"{ref[0]}:{ref[1]}", "score": e["score"], "titles": e["titles"],
                 "tastes": e["tastes"], "weak": bool(e["weak"])}
                for e, ref in scored[:LIST_SIZE]
            ]
    return result


def synthetic_case(base: dict, general_top: list[str]) -> dict:
    """Un profil qui exerce les cas limites : titres masqués, « bof », « pas aimé », duel."""
    case = copy.deepcopy(base)
    case["slug"] = "synthetique"
    case["hidden"] = general_top[:3]
    favorites = case.setdefault("favorites", [])
    for ref, level, source in zip(general_top[3:7], (0, -1, 2, 1), ("fav", "fav", "fav", "duel")):
        media, _, tmdb_id = ref.partition(":")
        favorites.append({"media": media, "id": int(tmdb_id), "level": level,
                          "source": source, "title": ref})
    return case


def main() -> int:
    conn = connect()
    profiles = personal.load_profiles()
    base = profiles[0] if profiles else {"slug": "vide", "name": "Vide", "families": {
        taxonomy.FAMILIES[0]["id"]: 1}, "tastes": {}, "favorites": []}
    items = personal.load_items(conn, personal.profile_refs(profiles))
    signals = personal.signal_map(conn)

    data = build_page.site_data(conn, date.today(), profiles)
    first_list = conn.execute(
        "SELECT media, tmdb_id FROM period_items WHERE period = 'p2' AND media = 'movie' "
        "ORDER BY buzz DESC LIMIT 7").fetchall()
    top_refs = [f"{r['media']}:{r['tmdb_id']}" for r in first_list]
    cases = profiles + [synthetic_case(base, top_refs)]

    payload = json.dumps({"data": data, "cases": cases, "generalHidden": top_refs[:2]})
    node = subprocess.run(["node", str(ROOT / "web" / "parity.js")], input=payload,
                          capture_output=True, text=True)
    if node.returncode != 0:
        print("Node a échoué :", node.stderr.strip() or node.stdout.strip())
        return 2
    js = json.loads(node.stdout)

    problems = []
    checked = 0
    for case in cases:
        expected = python_rankings(conn, items, signals, case)
        for key, py_list in expected.items():
            js_list = js["profiles"][case["slug"]][key]
            checked += 1
            if len(py_list) != len(js_list):
                problems.append(f"{case['slug']} {key} : {len(py_list)} titres (Python) contre {len(js_list)} (JS)")
                continue
            for i, (a, b) in enumerate(zip(py_list, js_list)):
                if abs(a["score"] - b["score"]) > TOLERANCE:
                    problems.append(f"{case['slug']} {key} #{i + 1} : score {a['score']:.9f} ≠ {b['score']:.9f}")
                    break
                if a["ref"] != b["ref"]:
                    tied = abs(a["score"] - py_list[min(i + 1, len(py_list) - 1)]["score"]) < TOLERANCE
                    if not tied:
                        problems.append(f"{case['slug']} {key} #{i + 1} : {a['ref']} ≠ {b['ref']}")
                        break
                if (a["titles"], a["tastes"], a["weak"]) != (b["titles"], b["tastes"], b["weak"]):
                    problems.append(f"{case['slug']} {key} #{i + 1} : explications différentes "
                                    f"({a['titles']},{a['tastes']},{a['weak']}) / "
                                    f"({b['titles']},{b['tastes']},{b['weak']})")
                    break

    # Classement général : buzz décroissant, puis votes, titres masqués exclus.
    hidden = set(top_refs[:2])
    for period in PERIODS:
        for media in MEDIA:
            rows = conn.execute(
                """SELECT p.media || ':' || p.tmdb_id AS ref FROM period_items p
                   JOIN titles t ON t.media = p.media AND t.tmdb_id = p.tmdb_id
                   WHERE p.period = ? AND p.media = ? ORDER BY p.buzz DESC, t.vote_count DESC""",
                (period["key"], media)).fetchall()
            expected = [r["ref"] for r in rows if r["ref"] not in hidden][:LIST_SIZE]
            got = [e["ref"] for e in js["general"][f"{period['key']}|{media}"]]
            checked += 1
            if expected != got:
                problems.append(f"général {period['key']}|{media} : ordre différent")

    if problems:
        print(f"{len(problems)} écart(s) sur {checked} listes :")
        for line in problems[:15]:
            print("  -", line)
        return 1
    print(f"OK : Python et JavaScript donnent les mêmes {checked} listes "
          f"({len(cases)} profils dont 1 synthétique + général).")
    return 0


if __name__ == "__main__":
    sys.exit(main())

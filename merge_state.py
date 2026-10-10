"""Intègre une sauvegarde de la page (« Sauvegarder mes choix ») dans le profil.

    python3 merge_state.py celia ~/Downloads/media4u-celia-2026-10-10.json
    python3 refresh.py --page-only

Les titres notés deviennent des « préférés » du profil : ils enrichissent le classement et ne
sont plus recommandés. Les titres masqués rejoignent `hidden`. Le profil est ainsi conservé
dans `profiles/<nom>.json` et repris par tous les appareils à la prochaine publication.
"""
import json
import sys
from pathlib import Path

from config import PROFILES_DIR
from db import connect


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    slug, export_path = argv
    profile_path = PROFILES_DIR / f"{slug}.json"
    if not profile_path.exists():
        print(f"Profil introuvable : {profile_path}")
        return 1

    try:
        export = json.loads(Path(export_path).expanduser().read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        print(f"Fichier illisible : {error}")
        return 1
    if export.get("app") != "media4u" or not isinstance(export.get("seen"), dict):
        print("Ce fichier n'est pas une sauvegarde Media 4 u.")
        return 1
    if export.get("profile") not in (None, slug):
        print(f"Attention : ce fichier vient du profil « {export['profile']} », pas « {slug} ».")
        return 1

    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    conn = connect()
    favorites = {(f["media"], int(f["id"])): f for f in profile.get("favorites", [])}
    added = changed = 0
    for ref, level in export["seen"].items():
        media, _, tmdb_id = ref.partition(":")
        if media not in ("movie", "tv") or not tmdb_id.isdigit() or not -2 <= float(level) <= 2:
            continue
        key = (media, int(tmdb_id))
        row = conn.execute("SELECT title FROM titles WHERE media = ? AND tmdb_id = ?", key).fetchone()
        previous = favorites.get(key)
        if previous is None:
            added += 1
        elif previous.get("level") != float(level):
            changed += 1
        favorites[key] = {"media": media, "id": key[1], "level": float(level),
                          "title": row["title"] if row else ref, "source": "fav"}
    profile["favorites"] = list(favorites.values())

    hidden = list(dict.fromkeys(list(profile.get("hidden", [])) + list(export.get("hidden", []))))
    profile["hidden"] = hidden

    profile_path.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{slug} : {added} titre(s) ajouté(s), {changed} avis modifié(s), "
          f"{len(hidden)} titre(s) masqué(s) au total.")
    print("Étape suivante : python3 refresh.py --page-only")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

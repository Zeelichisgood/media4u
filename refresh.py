"""Point d'entrée : met à jour les données TMDB puis régénère la page.

    python3 refresh.py              # tout (≈ 1 à 2 minutes)
    python3 refresh.py --page-only  # régénère la page depuis la base, sans appel TMDB
"""
import sys
from datetime import date

import build_page
import ingest
import score
from db import connect
from tmdb import TMDB, TMDBError


def main(argv: list[str]) -> int:
    conn = connect()
    today = date.today()

    if "--page-only" not in argv:
        try:
            client = TMDB()
            print("1/4 Genres")
            ingest.fetch_genres(client, conn)
            print("2/4 Viviers par période")
            ingest.fetch_pools(client, conn, today)
            print("3/4 Score")
            score.rank_all(conn)
            print("4/4 Fiches détaillées")
            ingest.fetch_details(client, conn)
            print(f"  {client.calls} appels TMDB")
        except TMDBError as error:
            print(f"Erreur : {error}", file=sys.stderr)
            return 1

    print("Page :", build_page.build(conn, today))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

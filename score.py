"""Score « ça fait parler » (plan.md §4) : pourcentiles dans chaque liste, sans modèle."""
from statistics import mean

from config import LIST_SIZE, MEDIA, PERIODS, WEIGHTS


def percentiles(values: list[float]) -> list[float]:
    """Rang normalisé entre 0 et 1 (les ex æquo partagent le rang moyen)."""
    n = len(values)
    if n <= 1:
        return [1.0] * n
    order = sorted(range(n), key=lambda i: values[i])
    result = [0.0] * n
    start = 0
    while start < n:
        end = start
        while end + 1 < n and values[order[end + 1]] == values[order[start]]:
            end += 1
        average_rank = (start + end) / 2
        for position in range(start, end + 1):
            result[order[position]] = average_rank / (n - 1)
        start = end + 1
    return result


def weighted_rating(rating: float, votes: int, m: int, c: float) -> float:
    """Note pondérée type IMDb : tire vers la moyenne `c` quand il y a peu de votes."""
    return votes / (votes + m) * rating + m / (votes + m) * c


def rank_all(conn) -> None:
    for period in PERIODS:
        weights = WEIGHTS[period["formula"]]
        for media in MEDIA:
            rows = conn.execute(
                """
                SELECT t.tmdb_id, t.vote_average, t.vote_count, t.popularity
                FROM period_items p JOIN titles t ON t.media = p.media AND t.tmdb_id = p.tmdb_id
                WHERE p.period = ? AND p.media = ?
                """,
                (period["key"], media),
            ).fetchall()
            if not rows:
                continue

            m = period["min_votes"][media]
            c = mean(r["vote_average"] for r in rows)
            wr = [weighted_rating(r["vote_average"], r["vote_count"], m, c) for r in rows]
            pct = {
                "popularity": percentiles([r["popularity"] for r in rows]),
                "votes": percentiles([r["vote_count"] for r in rows]),
                "wr": percentiles(wr),
            }
            buzz = [sum(weights[k] * pct[k][i] for k in weights) for i in range(len(rows))]

            order = sorted(range(len(rows)), key=lambda i: (-buzz[i], -rows[i]["vote_count"]))
            rank_of = {idx: pos + 1 for pos, idx in enumerate(order[:LIST_SIZE])}
            conn.executemany(
                "UPDATE period_items SET buzz = ?, wr = ?, rank = ? "
                "WHERE period = ? AND media = ? AND tmdb_id = ?",
                [
                    (buzz[i], wr[i], rank_of.get(i), period["key"], media, rows[i]["tmdb_id"])
                    for i in range(len(rows))
                ],
            )
            conn.commit()

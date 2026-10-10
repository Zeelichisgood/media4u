"""Classement « pour toi » : matching déterministe entre un profil et les titres du vivier.

Aucun modèle : mots-clés, genres, équipe et recommandations TMDB combinés par une formule
fixe (plan.md §5). Tout est explicable : chaque point vient d'un goût ou d'un titre aimé.
"""
import json
import math
import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, field

import taxonomy
from config import MEDIA, PERIODS, PROFILES_DIR
from score import percentiles

# Poids des composantes ; renormalisés quand le profil n'en fournit pas une (buzz et qualité restent).
# buzz = ce qui fait parler dans la liste ; qualité = note pondérée (évite de remonter ce que le
# public juge mauvais juste parce que ça ressemble).
COMPONENT_WEIGHTS = {"taste": 0.36, "genre": 0.09, "fav": 0.25, "buzz": 0.20, "quality": 0.10}
FAMILY_SPILLOVER = 0.5   # une réponse de « famille » pèse moitié moins qu'une réponse précise
WEAK_BELOW = 0.2         # sous cette affinité (goûts / titres), on affiche « peu de rapport »
CO_RECO_BONUS = 0.25     # titre aimé présent dans les recos TMDB du candidat (ou l'inverse)
SIM_SCALE = 2.0          # un cosinus de 0,5 est déjà une très forte ressemblance
BECAUSE_MIN = 0.15       # affinité minimale pour afficher « Proche de : … »

Ref = tuple[str, int]


@dataclass(eq=False)
class Item:
    ref: Ref
    title: str
    genres: set
    keywords: set
    recos: set
    vec: dict = field(default_factory=dict)
    norm: float = 1.0


# ── Profils ────────────────────────────────────────────────────────────────

def slugify(name: str) -> str:
    ascii_name = unicodedata.normalize("NFKD", name.lower()).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_name).strip("-") or "profil"


def load_profiles() -> list[dict]:
    profiles = []
    for path in sorted(PROFILES_DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        data["slug"] = path.stem
        data.setdefault("name", path.stem)
        profiles.append(data)
    return profiles


def save_profile(profile: dict) -> str:
    PROFILES_DIR.mkdir(exist_ok=True)
    slug = slugify(profile["name"])
    path = PROFILES_DIR / f"{slug}.json"
    path.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
    return slug


def taste_weights(profile: dict) -> dict[str, float]:
    """Poids par goût : les réponses précises l'emportent sur la réponse de la famille."""
    weights: dict[str, float] = {}
    for family_id, value in (profile.get("families") or {}).items():
        for taste in taxonomy.TASTES_BY_FAMILY.get(family_id, []):
            weights[taste["id"]] = FAMILY_SPILLOVER * float(value)
    for taste_id, value in (profile.get("tastes") or {}).items():
        weights[taste_id] = float(value)
    return {k: v for k, v in weights.items() if v}


def genre_weights(profile: dict) -> dict[int, float]:
    weights: dict[int, float] = defaultdict(float)
    for family_id, value in (profile.get("families") or {}).items():
        family = taxonomy.FAMILY_BY_ID.get(family_id)
        for genre in (family or {}).get("genres", []):
            weights[genre] += FAMILY_SPILLOVER * float(value)
    return {k: v for k, v in weights.items() if v}


# ── Données ────────────────────────────────────────────────────────────────

def profile_refs(profiles: list[dict]) -> set[Ref]:
    """Titres cités par les profils (préférés, vus) : on garde leurs caractéristiques."""
    return {(f["media"], int(f["id"])) for p in profiles for f in p.get("favorites") or []}


def load_items(conn, extra_refs: set[Ref] = frozenset()) -> dict[Ref, Item]:
    """Titres du vivier courant + `extra_refs`. Le périmètre définit aussi l'IDF : le moteur
    JavaScript de la page embarque exactement ce même ensemble (voir check_parity.py)."""
    rows = conn.execute(
        """
        SELECT t.media, t.tmdb_id, t.title, t.genre_ids,
               f.keywords, f.cast_ids, f.crew_ids, f.reco_ids,
               EXISTS (SELECT 1 FROM period_items p
                       WHERE p.media = t.media AND p.tmdb_id = t.tmdb_id) AS in_pool
        FROM titles t JOIN features f ON f.media = t.media AND f.tmdb_id = t.tmdb_id
        """
    ).fetchall()
    items: dict[Ref, Item] = {}
    people: dict[Ref, tuple[list, list]] = {}
    document_frequency: Counter = Counter()
    for r in rows:
        if not r["in_pool"] and (r["media"], r["tmdb_id"]) not in extra_refs:
            continue
        item = Item(
            ref=(r["media"], r["tmdb_id"]),
            title=r["title"],
            genres=set(json.loads(r["genre_ids"])),
            keywords=set(json.loads(r["keywords"])),
            recos=set(json.loads(r["reco_ids"])),
        )
        items[item.ref] = item
        people[item.ref] = (json.loads(r["crew_ids"]), json.loads(r["cast_ids"]))
        document_frequency.update(item.keywords)

    n = len(items)
    for ref, item in items.items():
        vec = {("g", g): 1.5 for g in item.genres}
        for keyword in item.keywords:  # un mot-clé rare pèse plus (TF-IDF)
            vec[("k", keyword)] = math.log((n + 1) / (document_frequency[keyword] + 1)) + 1.0
        crew, cast = people[ref]
        for person in crew:
            vec[("p", person)] = 2.0
        for person in cast:
            vec.setdefault(("p", person), 0.5)
        item.vec = vec
        item.norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
    return items


def signal_map(conn) -> dict[Ref, tuple[float, float]]:
    """Par titre : (buzz, qualité), deux nombres 0..1 relatifs à la liste du titre."""
    signals: dict[Ref, tuple[float, float]] = {}
    for period in PERIODS:
        for media in MEDIA:
            rows = conn.execute(
                "SELECT tmdb_id, buzz, wr FROM period_items WHERE period = ? AND media = ?",
                (period["key"], media),
            ).fetchall()
            for row, quality in zip(rows, percentiles([r["wr"] or 0.0 for r in rows])):
                signals[(media, row["tmdb_id"])] = (row["buzz"] or 0.0, quality)
    return signals


# ── Matching ───────────────────────────────────────────────────────────────

def cosine(a: Item, b: Item) -> float:
    small, large = (a.vec, b.vec) if len(a.vec) <= len(b.vec) else (b.vec, a.vec)
    dot = sum(w * large[k] for k, w in small.items() if k in large)
    return dot / (a.norm * b.norm)


def co_recommended(a: Item, b: Item) -> bool:
    return a.ref[0] == b.ref[0] and (b.ref[1] in a.recos or a.ref[1] in b.recos)


def saturate(x: float) -> float:
    """Rendements décroissants : deux concordances comptent plus qu'une, pas deux fois plus."""
    return 1.0 - math.exp(-x)


def taste_match(item: Item, taste: dict) -> float:
    if taste["genres"] and not (taste["genres"] & item.genres):
        return 0.0
    hits = len(taste["kw"] & item.keywords)
    return min(1.0, hits / taste["need"]) if hits else 0.0


class Matcher:
    def __init__(self, profile: dict, items: dict[Ref, Item]):
        self.tastes = [
            (taxonomy.TASTE_BY_ID[tid], w)
            for tid, w in taste_weights(profile).items() if tid in taxonomy.TASTE_BY_ID
        ]
        self.genre_w = genre_weights(profile)
        self.liked: list[tuple[Item, float]] = []
        self.disliked: list[tuple[Item, float]] = []
        self.seen: set[Ref] = set()          # déjà vus ou masqués : jamais recommandés
        for ref in profile.get("hidden") or []:
            media, _, tmdb_id = str(ref).partition(":")
            self.seen.add((media, int(tmdb_id)))
        for fav in profile.get("favorites") or []:
            ref = (fav["media"], int(fav["id"]))
            if fav.get("source", "fav") == "fav":
                self.seen.add(ref)
            item = items.get(ref)
            level = float(fav.get("level", 1))
            if item is None:
                continue
            if level > 0:
                self.liked.append((item, min(1.0, level / 2)))    # adoré = 1, aimé = 0,5
            elif level < 0:
                self.disliked.append((item, min(1.0, -level)))
            # level == 0 : vu sans avis marqué, seulement écarté des recommandations
        self.active = {
            "taste": bool(self.tastes),
            "genre": bool(self.genre_w),
            "fav": bool(self.liked or self.disliked),
        }

    def evaluate(self, item: Item, signal: tuple[float, float]) -> dict:
        taste_pos = taste_neg = 0.0
        matched: list[tuple[float, str]] = []
        for taste, weight in self.tastes:
            m = taste_match(item, taste)
            if not m:
                continue
            if weight > 0:
                taste_pos += weight * m
                if taste["show"]:  # les sujets sensibles comptent au score mais ne s'affichent pas
                    matched.append((weight * m, taste["label"]))
            else:
                taste_neg += -weight * m
        taste = saturate(taste_pos) - saturate(taste_neg)

        genre_pos = sum(w for g, w in self.genre_w.items() if w > 0 and g in item.genres)
        genre_neg = sum(-w for g, w in self.genre_w.items() if w < 0 and g in item.genres)
        genre = saturate(genre_pos) - saturate(genre_neg)

        sims: list[tuple[float, str]] = []
        for fav, strength in self.liked:
            s = cosine(item, fav) * SIM_SCALE
            if co_recommended(item, fav):
                s += CO_RECO_BONUS
            sims.append((min(1.0, s) * strength, fav.title))
        sims.sort(reverse=True)
        top = [s for s, _ in sims[:3]] + [0.0, 0.0, 0.0]
        fav_pos = min(1.0, top[0] + 0.5 * top[1] + 0.25 * top[2])
        fav_neg = max(
            (min(1.0, cosine(item, fav) * SIM_SCALE) * strength for fav, strength in self.disliked),
            default=0.0,
        )
        fav_score = fav_pos - fav_neg

        buzz, quality = signal
        parts = {"taste": taste, "genre": genre, "fav": fav_score, "buzz": buzz, "quality": quality}
        always_on = ("buzz", "quality")
        weights = {k: COMPONENT_WEIGHTS[k] for k in parts if k in always_on or self.active[k]}
        score = sum(parts[k] * w for k, w in weights.items()) / sum(weights.values())

        labels: list[str] = []
        for _, label in sorted(matched, reverse=True):
            if label not in labels:
                labels.append(label)
        weak = (self.active["taste"] or self.active["fav"]) and (
            saturate(taste_pos) < WEAK_BELOW and fav_pos < WEAK_BELOW
        )
        return {
            "score": score,
            "titles": [title for s, title in sims if s >= BECAUSE_MIN][:2],
            "tastes": labels[:2],
            "weak": weak,
        }


# ── Duels du quiz ──────────────────────────────────────────────────────────

def pick_duel(conn, profile: dict, shown: set[Ref], top_k: int = 25,
              min_buzz: float = 0.6) -> tuple[Item, Item] | None:
    """Deux titres plausibles pour le profil actuel mais aussi différents que possible :
    c'est ce qui rend la réponse informative. Seuls les titres connus (bon buzz dans leur
    liste) sont proposés : on ne peut pas choisir entre deux titres qu'on ne connaît pas."""
    items = load_items(conn, profile_refs([profile]))
    signals = signal_map(conn)
    matcher = Matcher(profile, items)
    scored = []
    for ref, signal in signals.items():
        item = items.get(ref)
        if item is None or signal[0] < min_buzz or ref in shown or ref in matcher.seen:
            continue
        scored.append((matcher.evaluate(item, signal)["score"], item))
    if len(scored) < 2:
        return None
    scored.sort(key=lambda pair: -pair[0])
    pool = [item for _, item in scored[:top_k]]
    first = pool[0]
    second = min(pool[1:], key=lambda item: cosine(first, item))
    return first, second

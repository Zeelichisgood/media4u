"""Vocabulaire des goûts : des familles larges, puis des goûts précis.

Un goût précis est un groupe de mots-clés TMDB (noms exacts, minuscules) avec, au besoin,
un filtre de genres (`genres` : le titre doit en avoir au moins un) et un seuil `need`
(nombre de mots-clés du groupe pour compter comme une correspondance complète).

Règles de rédaction :
- Un libellé décrit un point de départ (cadre, ton, sujet), jamais un événement de l'intrigue.
- `show: False` = utilisé pour le score mais jamais affiché sur une carte (sujets sensibles).
- Les noms de mots-clés absents de TMDB sont inoffensifs : ils ne correspondent à rien.
"""

# genres : identifiants TMDB (films et séries réunis)
FAMILIES = [
    {"id": "enquetes", "emoji": "🔍", "label": "Enquêtes & mystères",
     "hint": "Démêler une affaire, chercher la vérité", "genres": [9648, 80]},
    {"id": "crime", "emoji": "🕶️", "label": "Crime & pègre",
     "hint": "Gangsters, braquages, espions, justiciers", "genres": [80, 53]},
    {"id": "suspense", "emoji": "😰", "label": "Suspense & tension",
     "hint": "Thrillers, survie, course contre la montre", "genres": [53]},
    {"id": "horreur", "emoji": "👻", "label": "Horreur & frissons",
     "hint": "Fantômes, monstres, slashers", "genres": [27]},
    {"id": "sf", "emoji": "🚀", "label": "Science-fiction",
     "hint": "Espace, futurs, technologies", "genres": [878, 10765]},
    {"id": "fantasy", "emoji": "🧙", "label": "Fantasy & surnaturel",
     "hint": "Magie, mondes imaginaires", "genres": [14, 10765]},
    {"id": "action", "emoji": "💥", "label": "Action & super-héros",
     "hint": "Combats, aventures, héros", "genres": [28, 12, 10759]},
    {"id": "humour", "emoji": "😂", "label": "Humour",
     "hint": "Rire franc, absurde, bandes de potes", "genres": [35]},
    {"id": "romance", "emoji": "💞", "label": "Romance & relations",
     "hint": "Amour, amitié, liens", "genres": [10749]},
    {"id": "grandir", "emoji": "🎒", "label": "Ados & famille",
     "hint": "Grandir, lycée, liens familiaux", "genres": [10751]},
    {"id": "drame", "emoji": "🎭", "label": "Drames humains",
     "hint": "Émotions fortes, vies intimes, société", "genres": [18]},
    {"id": "histoire", "emoji": "🏛️", "label": "Histoire & faits réels",
     "hint": "Époques, histoires vraies, guerre", "genres": [36, 10752, 10768, 99]},
    {"id": "animation", "emoji": "🎨", "label": "Animation & anime",
     "hint": "Anime, dessin animé, pour grands ou pour tous", "genres": [16]},
    {"id": "ambiance", "emoji": "🌗", "label": "Ambiances",
     "hint": "Le ton, plus que le sujet", "genres": []},
    {"id": "format", "emoji": "📚", "label": "Formats & origines",
     "hint": "Adaptations, mini-séries, suites", "genres": []},
]

TASTES = [
    # ── Enquêtes & mystères ────────────────────────────────────────────────
    {"id": "enquete_policiere", "family": "enquetes", "label": "Enquête policière",
     "hint": "flics, détectives, affaires à résoudre",
     "keywords": ["investigation", "detective", "police", "murder investigation",
                  "police procedural", "fbi agent", "fbi", "whodunit", "murder mystery",
                  "private detective", "cold case", "forensic", "police detective", "homicide"]},
    {"id": "tueur_serie", "family": "enquetes", "label": "Tueur en série",
     "hint": "profilage, traque d'un meurtrier",
     "keywords": ["serial killer", "profiler", "true crime", "manhunt"]},
    {"id": "disparition", "family": "enquetes", "label": "Disparitions & mystères",
     "hint": "quelqu'un manque, un secret à percer",
     "keywords": ["disappearance", "missing person", "kidnapping", "child kidnapping",
                  "missing child", "mystery", "family secrets"]},
    {"id": "judiciaire", "family": "enquetes", "label": "Procès & judiciaire",
     "hint": "avocats, tribunaux",
     "keywords": ["lawyer", "legal drama", "courtroom", "trial", "judge", "attorney"]},

    # ── Crime & pègre ──────────────────────────────────────────────────────
    {"id": "mafia", "family": "crime", "label": "Mafia & gangsters",
     "hint": "pègre, cartels, familles criminelles",
     "keywords": ["gangster", "organized crime", "crime boss", "mafia", "mob", "drug cartel",
                  "drug dealer", "cartel", "crime family"]},
    {"id": "braquage", "family": "crime", "label": "Braquages & arnaques",
     "hint": "coups montés, escrocs",
     "keywords": ["heist", "robbery", "con artist", "bank robbery", "swindler", "scam", "thief"]},
    {"id": "espionnage", "family": "crime", "label": "Espionnage & complots",
     "hint": "agents secrets, conspirations",
     "keywords": ["spy", "conspiracy", "central intelligence agency (cia)", "secret organization",
                  "secret agent", "espionage", "assassin", "terrorism", "covert operation"]},
    {"id": "justicier", "family": "crime", "label": "Vengeance & justicier",
     "hint": "faire justice soi-même",
     "keywords": ["revenge", "vigilante", "bounty hunter", "hitman", "anti hero"]},
    {"id": "prison", "family": "crime", "label": "Prison & évasion",
     "hint": "derrière les barreaux",
     "keywords": ["prison", "prison escape", "prisoner", "jail"]},

    # ── Suspense & tension ─────────────────────────────────────────────────
    {"id": "thriller_psy", "family": "suspense", "label": "Thriller psychologique",
     "hint": "manipulation, obsession, doutes",
     "keywords": ["psychological thriller", "psychological", "manipulation", "obsession",
                  "paranoid", "mind game", "stalker"]},
    {"id": "survie", "family": "suspense", "label": "Survie & course contre la montre",
     "hint": "tenir bon, s'échapper",
     "keywords": ["survival", "race against time", "struggle for survival", "on the run",
                  "rescue mission", "disaster", "plane crash", "trapped", "stranded"]},
    {"id": "tension", "family": "suspense", "label": "Suspense pur",
     "hint": "ça se joue à rien",
     "keywords": ["thriller", "suspenseful", "suspense", "tense"]},

    # ── Horreur & frissons ─────────────────────────────────────────────────
    {"id": "horreur_surnat", "family": "horreur", "label": "Horreur surnaturelle",
     "hint": "fantômes, démons, malédictions", "genres": [27, 53, 9648],
     "keywords": ["supernatural horror", "ghost", "haunted house", "possession", "demon",
                  "evil spirit", "curse", "exorcism", "paranormal", "haunting"]},
    {"id": "slasher_gore", "family": "horreur", "label": "Slasher & gore",
     "hint": "tueurs masqués, horreur graphique",
     "keywords": ["slasher", "gore", "body horror", "splatter", "masked killer"]},
    {"id": "monstres", "family": "horreur", "label": "Monstres & créatures",
     "hint": "zombies, vampires, bêtes",
     "keywords": ["monster", "creature", "zombie", "werewolf", "vampire", "giant monster",
                  "kaiju", "undead"]},
    {"id": "horreur_psy", "family": "horreur", "label": "Horreur psychologique",
     "hint": "la peur qui s'installe",
     "keywords": ["psychological horror", "survival horror", "folk horror", "dread"]},
    {"id": "horreur_fete", "family": "horreur", "label": "Frissons entre amis",
     "hint": "Halloween, horreur ado ou drôle",
     "keywords": ["teen horror", "halloween", "comedy horror", "horror comedy", "campy"]},

    # ── Science-fiction ────────────────────────────────────────────────────
    {"id": "espace", "family": "sf", "label": "Espace & exploration",
     "hint": "vaisseaux, planètes, astronautes",
     "keywords": ["space", "space travel", "spacecraft", "astronaut", "space opera", "alien",
                  "alien invasion", "outer space", "extraterrestrial"]},
    {"id": "dystopie", "family": "sf", "label": "Dystopie & post-apocalypse",
     "hint": "mondes qui s'effondrent",
     "keywords": ["dystopia", "post-apocalyptic future", "post-apocalyptic", "apocalypse",
                  "cyberpunk", "near future", "totalitarian"]},
    {"id": "ia_robots", "family": "sf", "label": "IA & robots",
     "hint": "machines et humanité",
     "keywords": ["artificial intelligence (a.i.)", "robot", "android", "transhumanism",
                  "technology", "cyborg", "virtual reality", "simulation"]},
    {"id": "temps_multivers", "family": "sf", "label": "Voyages dans le temps & multivers",
     "hint": "boucles, réalités parallèles",
     "keywords": ["time travel", "multiverse", "alternate timeline", "parallel world",
                  "alternate history", "time loop", "alternate reality"]},

    # ── Fantasy & surnaturel ───────────────────────────────────────────────
    {"id": "magie", "family": "fantasy", "label": "Magie & sorcellerie",
     "hint": "sorciers, pouvoirs, écoles de magie",
     "keywords": ["magic", "witch", "wizard", "sorcerer", "magical", "urban fantasy", "spell",
                  "witchcraft"]},
    {"id": "monde_imaginaire", "family": "fantasy", "label": "Mondes imaginaires & quêtes",
     "hint": "royaumes, dragons, épopées", "genres": [14, 10765, 12, 10759, 16],
     "keywords": ["fantasy world", "quest", "dragon", "sword and sorcery", "dark fantasy",
                  "mythology", "medieval", "king", "kingdom", "epic fantasy", "elf", "fairy tale"]},
    {"id": "surnaturel", "family": "fantasy", "label": "Surnaturel au quotidien",
     "hint": "pouvoirs, au-delà, esprits",
     "keywords": ["supernatural", "supernatural power", "afterlife", "reincarnation", "god",
                  "angel", "spirit", "psychic"]},

    # ── Action & super-héros ───────────────────────────────────────────────
    {"id": "superheros", "family": "action", "label": "Super-héros",
     "hint": "pouvoirs, capes, univers partagés",
     "keywords": ["superhero", "super power", "superhero team", "masked superhero",
                  "supervillain", "marvel cinematic universe (mcu)", "mutant",
                  "secret identity", "dc comics", "marvel comics"]},
    {"id": "combats", "family": "action", "label": "Combats & arts martiaux",
     "hint": "duels, tournois, kung-fu",
     "keywords": ["martial arts", "fighting", "fight", "battle", "warrior", "kung fu", "samurai",
                  "sword fight", "tournament", "boxer"]},
    {"id": "aventure", "family": "action", "label": "Aventure & exploration",
     "hint": "îles, trésors, grands voyages",
     "keywords": ["adventure", "adventurer", "pirate", "treasure", "island", "expedition",
                  "treasure hunt", "jungle", "road trip"]},

    # ── Humour ─────────────────────────────────────────────────────────────
    {"id": "humour_noir", "family": "humour", "label": "Humour noir & absurde",
     "hint": "rire jaune, satire, décalé",
     "keywords": ["dark comedy", "absurd", "satire", "black comedy", "farcical", "parody",
                  "breaking the fourth wall", "biting", "dramedy", "deadpan", "quirky"]},
    {"id": "rigolade", "family": "humour", "label": "Franche rigolade",
     "hint": "ça fait vraiment rire",
     "keywords": ["hilarious", "witty", "playful", "slapstick", "comedy", "funny", "amusing"]},
    {"id": "potes", "family": "humour", "label": "Comédies de bande",
     "hint": "potes, sitcoms, duos",
     "keywords": ["buddy comedy", "sitcom", "bromance", "ensemble cast", "workplace comedy",
                  "friends"]},

    # ── Romance & relations ────────────────────────────────────────────────
    {"id": "romcom", "family": "romance", "label": "Comédie romantique",
     "hint": "séduction, quiproquos",
     "keywords": ["romcom", "romantic comedy", "love triangle", "wedding", "enemies to lovers",
                  "fake relationship", "dating"]},
    {"id": "grande_romance", "family": "romance", "label": "Grandes histoires d'amour",
     "hint": "passion, amours impossibles",
     "keywords": ["romance", "romantic drama", "love", "first love", "second chance",
                  "forbidden love", "star-crossed lovers", "love story", "romantic",
                  "unrequited love"]},
    {"id": "lgbt", "family": "romance", "label": "Histoires LGBT+",
     "hint": "amours et identités queer",
     "keywords": ["lgbt", "gay theme", "lesbian", "lesbian relationship", "lgbt teen",
                  "boys' love (bl)", "gay", "bisexual", "transgender", "coming out", "queer"]},
    {"id": "amitie", "family": "romance", "label": "Amitié & fratrie",
     "hint": "bandes d'amis, frères et sœurs",
     "keywords": ["friendship", "female friendship", "best friend", "found family",
                  "sibling relationship", "brother brother relationship",
                  "sister sister relationship", "brother sister relationship",
                  "group of friends"]},

    # ── Ados & famille ─────────────────────────────────────────────────────
    {"id": "coming_of_age", "family": "grandir", "label": "Passage à l'âge adulte",
     "hint": "adolescence, premiers émois",
     "keywords": ["coming of age", "teenager", "teenage girl", "teenage boy", "teen drama",
                  "teenage romance", "adolescence", "growing up", "youth"]},
    {"id": "lycee", "family": "grandir", "label": "Lycée & campus",
     "hint": "cours, bandes, rivalités",
     "keywords": ["high school", "school", "school life", "college", "japanese high school",
                  "university", "bullying", "teacher", "student"]},
    {"id": "famille", "family": "grandir", "label": "Liens familiaux",
     "hint": "parents, enfants, fratries", "need": 2,
     "keywords": ["family", "family relationships", "dysfunctional family",
                  "parent child relationship", "father daughter relationship",
                  "mother son relationship", "father son relationship",
                  "mother daughter relationship", "parenting", "family drama",
                  "husband wife relationship", "marriage"]},

    # ── Drames humains ─────────────────────────────────────────────────────
    {"id": "drame_intime", "family": "drame", "label": "Drames intimes",
     "hint": "blessures, reconstruction", "show": False,
     "keywords": ["grief", "trauma", "depression", "loneliness", "mental health",
                  "loss of loved one", "suicide", "alcoholism", "addiction",
                  "psychological drama", "melancholy", "drugs", "tragedy"]},
    {"id": "drame_social", "family": "drame", "label": "Drames sociaux & politiques",
     "hint": "société, pouvoir, injustices",
     "keywords": ["social commentary", "racism", "politics", "corruption", "capitalism",
                  "social issues", "feminism", "political corruption", "inequality", "poverty",
                  "power struggle", "political drama", "immigration"]},

    # ── Histoire & faits réels ─────────────────────────────────────────────
    {"id": "faits_reels", "family": "histoire", "label": "Inspiré de faits réels",
     "hint": "histoires vraies, biographies",
     "keywords": ["based on true story", "biography", "historical figure", "based on real events",
                  "docudrama", "true crime"]},
    {"id": "epoque", "family": "histoire", "label": "Fresques d'époque",
     "hint": "costumes, siècles passés",
     "keywords": ["period drama", "historical drama", "period piece", "historical fiction",
                  "historical", "19th century", "18th century", "victorian era", "regency",
                  "1920s", "1900s", "aristocracy"]},
    {"id": "guerre", "family": "histoire", "label": "Guerre & conflits",
     "hint": "fronts, soldats, résistance",
     "keywords": ["war", "world war ii", "military", "soldier", "world war i", "vietnam war",
                  "resistance", "nazi", "army"]},
    {"id": "retro", "family": "histoire", "label": "Nostalgie des décennies",
     "hint": "années 70, 80, 90",
     "keywords": ["1970s", "1980s", "1990s", "nostalgic", "1960s", "retro"]},

    # ── Animation & anime ──────────────────────────────────────────────────
    {"id": "anime", "family": "animation", "label": "Anime",
     "hint": "shonen, seinen, isekai, tranches de vie", "genres": [16],
     "keywords": ["anime", "shounen", "seinen", "based on manga", "based on light novel",
                  "anime inspired", "isekai", "slice of life", "shoujo", "based on web novel",
                  "mecha"]},
    {"id": "anim_famille", "family": "animation", "label": "Animation pour tous",
     "hint": "studios, aventures familiales", "genres": [16],
     "keywords": ["3d animation", "pixar", "talking animal", "anthropomorphism", "cartoon",
                  "musical", "family"]},
    {"id": "anim_adulte", "family": "animation", "label": "Animation adulte",
     "hint": "dessin animé pour grands", "genres": [16],
     "keywords": ["adult animation", "adult swim", "mature animation"]},

    # ── Ambiances ──────────────────────────────────────────────────────────
    {"id": "sombre", "family": "ambiance", "label": "Sombre & noir",
     "hint": "atmosphère lourde, morale grise", "need": 2,
     "keywords": ["dark", "gritty", "grim", "neo-noir", "somber", "bleak", "depressing", "noir",
                  "foreboding", "disturbing", "harsh", "brutality", "violence"]},
    {"id": "tendu", "family": "ambiance", "label": "Tendu & haletant",
     "hint": "on retient son souffle", "need": 2,
     "keywords": ["intense", "tense", "suspenseful", "frantic", "thrilling", "anxious",
                  "gripping", "shocking"]},
    {"id": "doux", "family": "ambiance", "label": "Réconfortant & lumineux",
     "hint": "chaleureux, qui fait du bien", "need": 2,
     "keywords": ["comforting", "cheerful", "joyful", "lighthearted", "hopeful", "wholesome",
                  "heartwarming", "uplifting", "whimsical", "wonder", "inspirational", "joyous"]},
    {"id": "emouvant", "family": "ambiance", "label": "Émouvant",
     "hint": "qui touche, qui serre le cœur", "need": 2,
     "keywords": ["heartfelt", "touching", "emotional", "moving", "tearjerker", "bittersweet",
                  "sentimental", "compassionate", "empathetic", "loving", "sincere"]},
    {"id": "reflexif", "family": "ambiance", "label": "Réflexif & lent",
     "hint": "contemplatif, qui laisse penser", "need": 2,
     "keywords": ["philosophical", "reflective", "introspective", "contemplative", "thoughtful",
                  "calm", "melancholy", "wistful", "meditative", "cerebral", "slow burn"]},

    # ── Formats & origines ─────────────────────────────────────────────────
    {"id": "adapt_livre", "family": "format", "label": "Adaptations de romans",
     "hint": "d'après un livre",
     "keywords": ["based on novel or book", "based on young adult novel", "based on short story",
                  "based on children's book"]},
    {"id": "adapt_bd", "family": "format", "label": "Adaptations de BD & comics",
     "hint": "d'après une bande dessinée",
     "keywords": ["based on comic", "based on graphic novel", "based on webcomic or webtoon",
                  "based on comic book"]},
    {"id": "adapt_jeu", "family": "format", "label": "Adaptations de jeux vidéo",
     "hint": "d'après un jeu", "keywords": ["based on video game"]},
    {"id": "miniserie", "family": "format", "label": "Mini-séries",
     "hint": "une histoire, une fin", "keywords": ["miniseries", "limited series", "mini-series"]},
    {"id": "anthologie", "family": "format", "label": "Anthologies",
     "hint": "chaque épisode, une nouvelle histoire", "keywords": ["anthology", "anthology series"]},
    {"id": "univers", "family": "format", "label": "Suites & univers étendus",
     "hint": "franchises, spin-offs",
     "keywords": ["sequel", "spin off", "prequel", "reboot", "remake", "franchise",
                  "cinematic universe", "shared universe"]},
]


# ── Index dérivés (préparés une fois, utilisés par personal.py) ────────────

def _prepare(raw: dict) -> dict:
    taste = dict(raw)
    taste["kw"] = frozenset(k.lower() for k in raw["keywords"])
    taste["genres"] = frozenset(raw.get("genres", []))
    taste.setdefault("need", 1)
    taste.setdefault("show", True)
    return taste


TASTES = [_prepare(t) for t in TASTES]
FAMILY_BY_ID = {f["id"]: f for f in FAMILIES}
TASTE_BY_ID = {t["id"]: t for t in TASTES}
TASTES_BY_FAMILY: dict[str, list[dict]] = {f["id"]: [] for f in FAMILIES}
for _taste in TASTES:
    TASTES_BY_FAMILY[_taste["family"]].append(_taste)

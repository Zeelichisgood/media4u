/* Moteur « pour toi » : port fidèle de personal.py.
 *
 * Pur (aucun accès au DOM) pour pouvoir être testé sous Node : `python3 check_parity.py`
 * compare ses résultats à ceux de Python. Si tu changes une formule ici, change-la aussi
 * dans personal.py (et inversement), puis relance la vérification.
 */
(function (root) {
  "use strict";

  const saturate = x => 1 - Math.exp(-x);

  function intersects(a, b) {
    for (const x of a) if (b.has(x)) return true;
    return false;
  }

  function countIn(a, b) {
    let n = 0;
    for (const x of a) if (b.has(x)) n += 1;
    return n;
  }

  function createEngine(DATA) {
    const cfg = DATA.config;
    const items = new Map();            // "movie:603" -> item
    const documentFrequency = new Map();

    for (const r of DATA.items) {
      const item = {
        ref: r.m + ":" + r.i,
        media: r.m,
        id: r.i,
        title: r.t,
        genres: new Set(r.g),
        keywords: new Set(r.k.map(index => DATA.keywords[index])),
        crew: r.cr,
        cast: r.ca,
        recos: new Set(r.rc),
        period: r.p,
        buzz: r.bz || 0,
        quality: r.q || 0,
        votes: r.n || 0,
        data: r,
        vec: null,
        norm: 1,
      };
      items.set(item.ref, item);
      for (const keyword of item.keywords) {
        documentFrequency.set(keyword, (documentFrequency.get(keyword) || 0) + 1);
      }
    }

    // Vecteurs : genres 1,5 · mots-clés TF-IDF · équipe 2 · casting 0,5 (comme en Python).
    const total = items.size;
    for (const item of items.values()) {
      const vec = new Map();
      for (const g of item.genres) vec.set("g:" + g, 1.5);
      for (const keyword of item.keywords) {
        vec.set("k:" + keyword, Math.log((total + 1) / (documentFrequency.get(keyword) + 1)) + 1.0);
      }
      for (const person of item.crew) vec.set("p:" + person, 2.0);
      for (const person of item.cast) if (!vec.has("p:" + person)) vec.set("p:" + person, 0.5);
      let squares = 0;
      for (const v of vec.values()) squares += v * v;
      item.vec = vec;
      item.norm = Math.sqrt(squares) || 1.0;
    }

    const familiesById = new Map();
    const tastesById = new Map();
    const tastesByFamily = new Map();
    for (const family of DATA.taxonomy.families) {
      familiesById.set(family.id, family);
      tastesByFamily.set(family.id, []);
    }
    for (const raw of DATA.taxonomy.tastes) {
      const taste = Object.assign({}, raw, { kw: new Set(raw.kw), genres: new Set(raw.genres) });
      tastesById.set(taste.id, taste);
      tastesByFamily.get(taste.family).push(taste);
    }

    const pools = new Map();            // "p1|movie" -> items du vivier
    for (const item of items.values()) {
      if (!item.period) continue;
      const key = item.period + "|" + item.media;
      if (!pools.has(key)) pools.set(key, []);
      pools.get(key).push(item);
    }
    const pool = (period, media) => pools.get(period + "|" + media) || [];

    function cosine(a, b) {
      const [small, large] = a.vec.size <= b.vec.size ? [a.vec, b.vec] : [b.vec, a.vec];
      let dot = 0;
      for (const [key, weight] of small) {
        const other = large.get(key);
        if (other !== undefined) dot += weight * other;
      }
      return dot / (a.norm * b.norm);
    }

    function coRecommended(a, b) {
      return a.media === b.media && (a.recos.has(b.id) || b.recos.has(a.id));
    }

    function tasteMatch(item, taste) {
      if (taste.genres.size && !intersects(taste.genres, item.genres)) return 0;
      const hits = countIn(taste.kw, item.keywords);
      return hits ? Math.min(1, hits / taste.need) : 0;
    }

    function tasteWeights(profile) {
      const weights = new Map();
      for (const [familyId, value] of Object.entries(profile.families || {})) {
        for (const taste of tastesByFamily.get(familyId) || []) {
          weights.set(taste.id, cfg.familySpillover * Number(value));
        }
      }
      for (const [tasteId, value] of Object.entries(profile.tastes || {})) {
        weights.set(tasteId, Number(value));
      }
      for (const [key, value] of Array.from(weights)) if (!value) weights.delete(key);
      return weights;
    }

    function genreWeights(profile) {
      const weights = new Map();
      for (const [familyId, value] of Object.entries(profile.families || {})) {
        const family = familiesById.get(familyId);
        for (const genre of (family && family.genres) || []) {
          weights.set(genre, (weights.get(genre) || 0) + cfg.familySpillover * Number(value));
        }
      }
      for (const [key, value] of Array.from(weights)) if (!value) weights.delete(key);
      return weights;
    }

    /* profile : { families, tastes, favorites: [{media,id,level,source}], hidden: ["tv:12"] } */
    function makeMatcher(profile) {
      const tastes = [];
      for (const [tasteId, weight] of tasteWeights(profile)) {
        const taste = tastesById.get(tasteId);
        if (taste) tastes.push([taste, weight]);
      }
      const genreW = genreWeights(profile);
      const liked = [];
      const disliked = [];
      const seen = new Set();             // déjà vus ou masqués : jamais recommandés
      for (const ref of profile.hidden || []) seen.add(ref);
      for (const fav of profile.favorites || []) {
        const ref = fav.media + ":" + fav.id;
        if ((fav.source || "fav") === "fav") seen.add(ref);
        const item = items.get(ref);
        const level = Number(fav.level === undefined ? 1 : fav.level);
        if (!item) continue;
        if (level > 0) liked.push([item, Math.min(1, level / 2)]);
        else if (level < 0) disliked.push([item, Math.min(1, -level)]);
      }
      const active = {
        taste: tastes.length > 0,
        genre: genreW.size > 0,
        fav: liked.length + disliked.length > 0,
      };

      function evaluate(item) {
        let tastePos = 0;
        let tasteNeg = 0;
        const matched = [];
        for (const [taste, weight] of tastes) {
          const m = tasteMatch(item, taste);
          if (!m) continue;
          if (weight > 0) {
            tastePos += weight * m;
            if (taste.show) matched.push([weight * m, taste.label]);
          } else {
            tasteNeg += -weight * m;
          }
        }
        const tasteScore = saturate(tastePos) - saturate(tasteNeg);

        let genrePos = 0;
        let genreNeg = 0;
        for (const [genre, weight] of genreW) {
          if (!item.genres.has(genre)) continue;
          if (weight > 0) genrePos += weight;
          else genreNeg += -weight;
        }
        const genreScore = saturate(genrePos) - saturate(genreNeg);

        const sims = [];
        for (const [fav, strength] of liked) {
          let s = cosine(item, fav) * cfg.simScale;
          if (coRecommended(item, fav)) s += cfg.coRecoBonus;
          sims.push([Math.min(1, s) * strength, fav.title]);
        }
        // Même ordre que Python : score décroissant, puis titre décroissant.
        sims.sort((a, b) => (b[0] - a[0]) || (a[1] < b[1] ? 1 : a[1] > b[1] ? -1 : 0));
        const top = sims.slice(0, 3).map(pair => pair[0]);
        while (top.length < 3) top.push(0);
        const favPos = Math.min(1, top[0] + 0.5 * top[1] + 0.25 * top[2]);
        let favNeg = 0;
        for (const [fav, strength] of disliked) {
          favNeg = Math.max(favNeg, Math.min(1, cosine(item, fav) * cfg.simScale) * strength);
        }
        const favScore = favPos - favNeg;

        const parts = {
          taste: tasteScore, genre: genreScore, fav: favScore,
          buzz: item.buzz, quality: item.quality,
        };
        let numerator = 0;
        let denominator = 0;
        for (const key of Object.keys(parts)) {
          if (key === "buzz" || key === "quality" || active[key]) {
            numerator += parts[key] * cfg.weights[key];
            denominator += cfg.weights[key];
          }
        }

        matched.sort((a, b) => (b[0] - a[0]) || (a[1] < b[1] ? 1 : a[1] > b[1] ? -1 : 0));
        const labels = [];
        for (const pair of matched) if (!labels.includes(pair[1])) labels.push(pair[1]);

        return {
          item,
          score: numerator / denominator,
          titles: sims.filter(pair => pair[0] >= cfg.becauseMin).slice(0, 2).map(pair => pair[1]),
          tastes: labels.slice(0, 2),
          weak: (active.taste || active.fav) &&
                saturate(tastePos) < cfg.weakBelow && favPos < cfg.weakBelow,
        };
      }

      return { seen, evaluate };
    }

    /* Classement personnalisé d'une liste (période × média), titres vus exclus. */
    function rankPersonal(profile, period, media, limit) {
      const matcher = makeMatcher(profile);
      const ranked = [];
      for (const item of pool(period, media)) {
        if (matcher.seen.has(item.ref)) continue;
        ranked.push(matcher.evaluate(item));
      }
      ranked.sort((a, b) => b.score - a.score);
      return limit ? ranked.slice(0, limit) : ranked;
    }

    /* Classement général (buzz), titres vus ou masqués exclus. */
    function rankGeneral(hiddenRefs, period, media, limit) {
      const hidden = new Set(hiddenRefs);
      const ranked = pool(period, media)
        .filter(item => !hidden.has(item.ref))
        .sort((a, b) => (b.buzz - a.buzz) || (b.votes - a.votes))
        .map(item => ({ item, score: item.buzz, titles: [], tastes: [], weak: false }));
      return limit ? ranked.slice(0, limit) : ranked;
    }

    return { items, pool, rankPersonal, rankGeneral, makeMatcher };
  }

  const api = { createEngine };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.Media4uEngine = api;
})(typeof window !== "undefined" ? window : globalThis);

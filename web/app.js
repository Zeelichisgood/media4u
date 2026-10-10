/* Interface de la page : listes par période, « déjà vu », sauvegarde. Aucun serveur :
 * les choix sont gardés dans le navigateur (localStorage) et recalculés à chaque clic. */
(function () {
  "use strict";

  const DATA = JSON.parse(document.getElementById("data").textContent);
  const engine = window.Media4uEngine.createEngine(DATA);
  const POSTER = "https://image.tmdb.org/t/p/w342";
  const LEVEL_CHOICES = [[2, "❤️ Adoré"], [1, "👍 Aimé"], [0, "😐 Bof"], [-1, "👎 Pas aimé"]];
  const LEVEL_LABEL = { "2": "❤️ Adoré", "1": "👍 Aimé", "0": "😐 Bof", "-1": "👎 Pas aimé" };
  const root = document.getElementById("app");
  const toastEl = document.getElementById("toast");

  const esc = value => String(value == null ? "" : value).replace(/[&<>"']/g, c => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  // ── Stockage (jamais bloquant : sans localStorage, tout reste en mémoire) ──
  const memory = {};
  function read(key, fallback) {
    try {
      const raw = window.localStorage.getItem(key);
      return raw ? JSON.parse(raw) : (key in memory ? memory[key] : fallback);
    } catch (e) {
      return key in memory ? memory[key] : fallback;
    }
  }
  function write(key, value) {
    memory[key] = value;
    try { window.localStorage.setItem(key, JSON.stringify(value)); } catch (e) { /* mémoire seule */ }
  }

  // ── État de l'interface ─────────────────────────────────────────────────
  const modes = [{ slug: "general", name: "Général" }]
    .concat(DATA.profiles.map(p => ({ slug: p.slug, name: p.name })));
  const periodKeys = DATA.periods.map(p => p.key);
  const ui = {
    period: periodKeys[0],
    media: "movie",
    mode: DATA.profiles.length ? DATA.profiles[0].slug : "general",
    pending: null,      // ref du titre dont on demande l'avis
    drawer: false,
  };
  const savedUi = read("media4u:ui", {}) || {};
  if (periodKeys.includes(savedUi.period)) ui.period = savedUi.period;
  if (savedUi.media && savedUi.media in DATA.media) ui.media = savedUi.media;
  if (modes.some(m => m.slug === savedUi.mode)) ui.mode = savedUi.mode;
  const fromHash = decodeURIComponent((window.location.hash || "").slice(1));
  if (modes.some(m => m.slug === fromHash)) ui.mode = fromHash;

  // ── Choix de la personne : titres vus (avec un avis) et titres masqués ──
  function userState(slug) {
    const stored = read("media4u:state:" + slug, {}) || {};
    return { seen: stored.seen || {}, hidden: stored.hidden || [] };
  }
  function saveState(slug, state) { write("media4u:state:" + slug, state); }

  function effectiveProfile(slug) {
    const base = DATA.profiles.find(p => p.slug === slug)
      || { families: {}, tastes: {}, favorites: [], hidden: [] };
    const state = userState(slug);
    const favorites = base.favorites.filter(f => !(f.media + ":" + f.id in state.seen));
    for (const [ref, level] of Object.entries(state.seen)) {
      const [media, id] = ref.split(":");
      favorites.push({ media, id: Number(id), level, source: "fav" });
    }
    return {
      families: base.families,
      tastes: base.tastes,
      favorites,
      hidden: (base.hidden || []).concat(state.hidden),
    };
  }

  function currentList() {
    const limit = DATA.config.listSize;
    if (ui.mode === "general") {
      const state = userState("general");
      return engine.rankGeneral(Object.keys(state.seen).concat(state.hidden), ui.period, ui.media, limit);
    }
    return engine.rankPersonal(effectiveProfile(ui.mode), ui.period, ui.media, limit);
  }

  const titleOf = ref => (engine.items.get(ref) || { title: ref }).title;

  // ── Actions ─────────────────────────────────────────────────────────────
  let toastTimer = null;
  function toast(message, undo) {
    toastEl.innerHTML = `<span>${esc(message)}</span>` + (undo ? '<button data-act="undo">Annuler</button>' : "");
    toastEl.hidden = false;
    toast.undo = undo || null;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { toastEl.hidden = true; }, 7000);
  }

  function restore(ref, previous) {
    const state = userState(ui.mode);
    if (previous.seen === undefined) delete state.seen[ref]; else state.seen[ref] = previous.seen;
    state.hidden = state.hidden.filter(r => r !== ref);
    if (previous.hidden) state.hidden.push(ref);
    saveState(ui.mode, state);
    render();
  }

  function snapshot(ref) {
    const state = userState(ui.mode);
    return { seen: state.seen[ref], hidden: state.hidden.includes(ref) };
  }

  function setSeen(ref, level) {
    const before = snapshot(ref);
    const state = userState(ui.mode);
    state.seen[ref] = level;
    state.hidden = state.hidden.filter(r => r !== ref);
    saveState(ui.mode, state);
    ui.pending = null;
    toast(ui.mode === "general" ? "Titre masqué." : "Noté, ta liste est mise à jour.",
      () => restore(ref, before));
    render();
  }

  function hide(ref) {
    const before = snapshot(ref);
    const state = userState(ui.mode);
    if (!state.hidden.includes(ref)) state.hidden.push(ref);
    delete state.seen[ref];
    saveState(ui.mode, state);
    ui.pending = null;
    toast("Titre masqué.", () => restore(ref, before));
    render();
  }

  function download(filename, text) {
    const url = URL.createObjectURL(new Blob([text], { type: "application/json" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  function exportState() {
    const state = userState(ui.mode);
    const payload = {
      app: "media4u", version: 1, profile: ui.mode,
      exported: new Date().toISOString(), seen: state.seen, hidden: state.hidden,
    };
    download("media4u-" + ui.mode + "-" + payload.exported.slice(0, 10) + ".json",
      JSON.stringify(payload, null, 2));
  }

  function importState(file) {
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const payload = JSON.parse(String(reader.result));
        if (payload.app !== "media4u" || typeof payload.seen !== "object") throw new Error("format");
        if (payload.profile && payload.profile !== ui.mode &&
            !window.confirm("Ce fichier vient du profil « " + payload.profile + " ». L'importer dans « " + ui.mode + " » ?")) return;
        saveState(ui.mode, { seen: payload.seen || {}, hidden: payload.hidden || [] });
        toast("Choix restaurés.");
        render();
      } catch (e) {
        toast("Fichier non reconnu.");
      }
    };
    reader.readAsText(file);
  }

  // ── Rendu ───────────────────────────────────────────────────────────────
  function runtime(minutes) {
    const h = Math.floor(minutes / 60);
    const m = minutes % 60;
    if (!h) return m + " min";
    return m ? h + " h " + String(m).padStart(2, "0") : h + " h";
  }

  function cardHTML(rank, entry) {
    const { item } = entry;
    const d = item.data;
    const genres = (DATA.genres[item.media] || {});
    const meta = d.g.map(g => genres[g]).filter(Boolean).slice(0, 3);
    if (d.rt) meta.push(runtime(d.rt) + (item.media === "tv" ? " / épisode" : ""));
    if (item.media === "tv" && d.se) meta.push(d.se + " saison" + (d.se > 1 ? "s" : ""));

    const poster = d.po
      ? `<img src="${POSTER}${esc(d.po)}" alt="" loading="lazy">`
      : '<div class="noposter">Pas d\'affiche</div>';
    const note = Number(d.v).toFixed(1).replace(".", ",");
    const votes = Number(d.n).toLocaleString("fr-FR");

    let because = "";
    if (entry.titles.length) because += `<p class="because"><b>Proche de :</b> ${esc(entry.titles.join(", "))}</p>`;
    if (entry.tastes.length) {
      because += '<div class="chips">' + entry.tastes.map(t => `<span class="chip">${esc(t)}</span>`).join("") + "</div>";
    }
    if (entry.weak) because += '<p class="weak">Peu de rapport avec tes goûts</p>';

    let actions;
    if (ui.pending === item.ref) {
      actions = `<div class="ask"><p>Tu en as pensé quoi ?</p><div class="levels">` +
        LEVEL_CHOICES.map(([level, label]) =>
          `<button class="mini" data-act="level" data-ref="${item.ref}" data-level="${level}">${label}</button>`).join("") +
        `<button class="mini" data-act="cancel">Annuler</button></div></div>`;
    } else {
      actions = `<div class="card-actions">
        <button class="mini primary" data-act="seen" data-ref="${item.ref}">Déjà vu</button>
        <button class="mini" data-act="hide" data-ref="${item.ref}">Pas intéressé</button></div>`;
    }

    return `<li class="card"><span class="rank">${rank}</span>${poster}<div class="body">
      <h3>${esc(d.t)} <span class="year">(${esc(d.y)})</span></h3>
      <p class="meta">${esc(meta.join(" · "))}</p>
      <p class="note"><strong>★ ${note}</strong> · ${votes} votes</p>
      ${d.tg ? `<p class="tagline">« ${esc(d.tg)} »</p>` : ""}${because}
      ${d.ov ? `<details><summary>Voir le synopsis (peut spoiler)</summary><p>${esc(d.ov)}</p></details>` : ""}
      ${actions}</div></li>`;
  }

  function drawerHTML() {
    const state = userState(ui.mode);
    const seenRefs = Object.keys(state.seen);
    const base = DATA.profiles.find(p => p.slug === ui.mode);
    const fromQuiz = base ? base.favorites.filter(f => (f.source || "fav") === "fav").length : 0;

    const seenRows = seenRefs.map(ref => `<div class="row"><span class="t">${esc(titleOf(ref))}</span>
      <span class="levels">${ui.mode === "general" ? "" : LEVEL_CHOICES.map(([level, label]) =>
        `<button class="mini ${state.seen[ref] === level ? "primary" : ""}" data-act="relevel" data-ref="${ref}" data-level="${level}">${label}</button>`).join("")}
      <button class="mini" data-act="forget" data-ref="${ref}">Remettre</button></span></div>`).join("");
    const hiddenRows = state.hidden.map(ref => `<div class="row"><span class="t">${esc(titleOf(ref))}</span>
      <button class="mini" data-act="forget" data-ref="${ref}">Remettre</button></div>`).join("");

    return `<div class="drawer-back" data-act="close"></div>
      <aside class="drawer" role="dialog" aria-label="Mes titres vus">
        <button class="mini" data-act="close" style="float:right">Fermer</button>
        <h2>Mes titres vus</h2>
        <p class="note-small">Chaque titre noté ici affine ta sélection. Tes choix sont gardés sur cet
        appareil${fromQuiz ? ` ; les ${fromQuiz} titres du quiz sont déjà pris en compte` : ""}.</p>
        <h3>Vus (${seenRefs.length})</h3>${seenRows || '<p class="note-small">Aucun pour l\'instant.</p>'}
        <h3>Masqués (${state.hidden.length})</h3>${hiddenRows || '<p class="note-small">Aucun.</p>'}
        <h3>Sauvegarde</h3>
        <p class="note-small">« Sauvegarder » télécharge un fichier avec tes choix : utile pour changer
        d'appareil ou les conserver durablement.</p>
        <div class="tools">
          <button class="mini primary" data-act="export">Sauvegarder mes choix</button>
          <label class="mini" style="cursor:pointer">Restaurer<input type="file" accept="application/json" data-act="import" hidden></label>
          <button class="mini" data-act="reset">Tout effacer</button>
        </div>
      </aside>`;
  }

  function render() {
    const scroll = window.scrollY;
    const period = DATA.periods.find(p => p.key === ui.period);
    const mode = modes.find(m => m.slug === ui.mode);
    const entries = currentList();
    const state = userState(ui.mode);
    const done = Object.keys(state.seen).length;

    const tabs = DATA.periods.map(p => `<button class="tab" role="tab" data-act="period" data-value="${p.key}"
      aria-selected="${p.key === ui.period}"><span class="t">${esc(p.label)}</span><span class="h">${esc(p.hint)}</span></button>`).join("");
    const mediaSwitch = Object.entries(DATA.media).map(([key, label]) =>
      `<button data-act="media" data-value="${key}" aria-pressed="${key === ui.media}">${esc(label)}</button>`).join("");
    const modeSwitch = modes.length > 1 ? '<div class="switch">' + modes.map(m =>
      `<button data-act="mode" data-value="${esc(m.slug)}" aria-pressed="${m.slug === ui.mode}">${esc(m.name)}</button>`).join("") + "</div>" : "";

    const caption = (ui.mode === "general" ? "" : "Classés selon les goûts de " + mode.name + " · ") +
      "sortis du " + period.gte + " au " + period.lte;
    const cards = entries.length
      ? entries.map((entry, i) => cardHTML(i + 1, entry)).join("")
      : '<li class="empty">Plus rien à proposer ici : tout a été vu ou masqué. Reviens après la prochaine mise à jour.</li>';
    const local = ["127.0.0.1", "localhost"].includes(window.location.hostname);

    root.innerHTML = `
      <header class="top">
        <div><h1>Media 4 u</h1>
        <p class="sub">Ce qui est sorti et fait parler de lui. Aucun spoil : les synopsis restent repliés.</p></div>
        <div class="head-actions">
          <button class="pill" data-act="open">Mes titres vus${done ? " (" + done + ")" : ""}</button>
          ${local ? '<a class="pill" href="/">Mes goûts</a>' : ""}
        </div>
      </header>
      <nav class="tabs" role="tablist">${tabs}</nav>
      <div class="switches"><div class="switch">${mediaSwitch}</div>${modeSwitch}</div>
      <p class="window">${esc(caption)}</p>
      <ol class="cards">${cards}</ol>
      <footer>
        <img src="https://www.themoviedb.org/assets/v4/logos/v2/blue_short-8e7b30f73a4020692ccca9c88bafe5dcb6f8a62a4c6bc55cd9ba82bb2cd95f6c.svg" alt="TMDB">
        <span>This product uses the TMDB API but is not endorsed or certified by TMDB.</span>
        <span>Mise à jour : ${esc(DATA.generated)}</span>
      </footer>
      ${ui.drawer ? drawerHTML() : ""}`;
    window.scrollTo(0, scroll);
    write("media4u:ui", { period: ui.period, media: ui.media, mode: ui.mode });
  }

  // ── Événements ──────────────────────────────────────────────────────────
  document.addEventListener("click", event => {
    const target = event.target.closest("[data-act]");
    if (!target) return;
    const { act, value, ref, level } = target.dataset;
    switch (act) {
      case "period": ui.period = value; ui.pending = null; break;
      case "media": ui.media = value; ui.pending = null; break;
      case "mode": ui.mode = value; ui.pending = null; break;
      case "seen":
        if (ui.mode === "general") return setSeen(ref, 0);
        ui.pending = ref; break;
      case "level": return setSeen(ref, Number(level));
      case "cancel": ui.pending = null; break;
      case "hide": return hide(ref);
      case "open": ui.drawer = true; break;
      case "close": ui.drawer = false; break;
      case "relevel": {
        const state = userState(ui.mode);
        state.seen[ref] = Number(level);
        saveState(ui.mode, state);
        break;
      }
      case "forget": restore(ref, { seen: undefined, hidden: false }); return;
      case "export": return exportState();
      case "reset":
        if (!window.confirm("Effacer tous les titres vus et masqués de ce profil ?")) return;
        saveState(ui.mode, { seen: {}, hidden: [] });
        break;
      case "undo":
        if (toast.undo) toast.undo();
        toastEl.hidden = true;
        return;
      case "import": return;
      default: return;
    }
    render();
  });

  document.addEventListener("change", event => {
    const input = event.target.closest('input[data-act="import"]');
    if (input && input.files && input.files[0]) importState(input.files[0]);
  });

  render();
})();

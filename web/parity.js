/* Calcule, avec le moteur de la page, les classements que check_parity.py compare à Python.
 * Entrée (stdin) : { data, cases: [profil…], generalHidden: [ref…] }. Sortie : JSON. */
"use strict";
const fs = require("fs");
const { createEngine } = require("./engine.js");

const input = JSON.parse(fs.readFileSync(0, "utf8"));
const engine = createEngine(input.data);
const limit = input.data.config.listSize;
const out = { general: {}, profiles: {} };

for (const period of input.data.periods) {
  for (const media of Object.keys(input.data.media)) {
    const key = period.key + "|" + media;
    out.general[key] = engine
      .rankGeneral(input.generalHidden || [], period.key, media, limit)
      .map(entry => ({ ref: entry.item.ref }));
    for (const profile of input.cases) {
      out.profiles[profile.slug] = out.profiles[profile.slug] || {};
      out.profiles[profile.slug][key] = engine
        .rankPersonal(profile, period.key, media, limit)
        .map(entry => ({
          ref: entry.item.ref, score: entry.score,
          titles: entry.titles, tastes: entry.tastes, weak: entry.weak,
        }));
    }
  }
}
process.stdout.write(JSON.stringify(out));

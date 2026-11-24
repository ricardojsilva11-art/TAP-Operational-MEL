/* mínimos partilhados (cfg.minima.ap[ICAO][pista] = {best, bd, bv, c1d, c1v}) aplicados sobre os de origem do TAF Monitor */
let MIN_ORIG = null, MIN_KEY = null;
function applyMinima(){
  if (!MIN_ORIG) MIN_ORIG = {m: JSON.parse(JSON.stringify(RWY_MINIMA)), b: JSON.parse(JSON.stringify(RWY_BELOW))};
  const M = (cfg && cfg.minima && cfg.minima.ap) || {}, key = JSON.stringify(M);
  if (key === MIN_KEY) return; MIN_KEY = key;
  for (const k of Object.keys(RWY_MINIMA)) delete RWY_MINIMA[k];
  for (const k of Object.keys(RWY_BELOW)) delete RWY_BELOW[k];
  Object.assign(RWY_MINIMA, JSON.parse(JSON.stringify(MIN_ORIG.m))); Object.assign(RWY_BELOW, JSON.parse(JSON.stringify(MIN_ORIG.b)));
  for (const [ic, R] of Object.entries(M)){
    RWY_MINIMA[ic] = {}; RWY_BELOW[ic] = {};
    for (const [rw, x] of Object.entries(R)){ RWY_MINIMA[ic][rw] = [x.c1d + 200, x.c1v + 1000]; RWY_BELOW[ic][rw] = [x.bd, x.bv]; }
  }
}
/* painel: tabela dos mínimos da carta por pista */
function minimaHtml(icao){
  const R = cfg && cfg.minima && cfg.minima.ap && cfg.minima.ap[icao]; if (!R) return "";
  const rows = Object.entries(R).sort((a, b) => a[0].localeCompare(b[0])).map(([rw, x]) => `<tr><td><b>${esc(rw)}</b></td><td>${esc(x.best)}<small>${x.bd ? x.bd + " ft" : "sem DH"} / ${x.bv} m</small></td><td>${x.bd ? "&lt; " + x.bd + " ft<br>" : ""}&lt; ${x.bv} m</td><td>≤ ${x.c1d + 200} ft<br>≤ ${x.c1v + 1000} m<small>CAT I ${x.c1d} ft / ${x.c1v} m</small></td></tr>`).join("");
  const m = cfg.minima, src = [m.src, m.cat ? "Cat " + m.cat : ""].filter(Boolean).join(" · ");
  return `<div class="minima"><span class="rwy-tag">Mínimos de aproximação${src ? " · " + esc(src) : ""}</span><div class="gtabwrap"><table class="gtab mintab"><thead><tr><th>Pista</th><th>Melhor aproximação</th><th>BELOW MIN</th><th>RVAC</th></tr></thead><tbody>${rows}</tbody></table></div><p class="hint" style="margin:4px 0 0">BELOW MIN: abaixo da melhor aproximação (sem LPV). RVAC: até ao CAT I + 200 ft / + 1000 m. LVO segue a fuel policy.</p></div>`;
}

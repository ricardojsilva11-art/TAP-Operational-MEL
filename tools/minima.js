/* mínimos partilhados (cfg.minima.ap[ICAO][pista] = {best, bd, bv, c1d, c1v}) aplicados sobre os de origem do TAF Monitor */
/* mínimos já incluídos (cartas Lido, Cat C), válidos para todos sem carregar nada; um ficheiro carregado por um
   Administrador nas definições partilhadas (cfg.minima) substitui estes */
const MIN_BUILTIN = {"src": "Lido 23/11/26", "cat": "C", "ap": {"LPPT": {"02": {"best": "ILS CAT IIIB", "bd": 0, "bv": 75, "c1d": 200, "c1v": 750}, "20": {"best": "ILS CAT IIIB", "bd": 0, "bv": 75, "c1d": 200, "c1v": 550}}, "LPPR": {"17": {"best": "ILS CAT II", "bd": 100, "bv": 300, "c1d": 200, "c1v": 550}, "35": {"best": "RNP LNAV/VNAV", "bd": 310, "bv": 700, "c1d": 310, "c1v": 700}}, "LPFR": {"10": {"best": "ILS CAT I", "bd": 200, "bv": 750, "c1d": 200, "c1v": 750}, "28": {"best": "ILS CAT II", "bd": 110, "bv": 300, "c1d": 200, "c1v": 750}}, "LPPD": {"12": {"best": "RNP W LNAV/VNAV", "bd": 520, "bv": 2100, "c1d": 520, "c1v": 2100}, "30": {"best": "ILS CAT I", "bd": 250, "bv": 1000, "c1d": 250, "c1v": 1000}}, "LPLA": {"15": {"best": "ILS CAT I", "bd": 250, "bv": 800, "c1d": 250, "c1v": 800}, "33": {"best": "ILS CAT I (TERPS)", "bd": 380, "bv": 1000, "c1d": 380, "c1v": 1000}}, "LPMA": {"05": {"best": "Circling (RNP A / VOR DME 05)", "bd": 800, "bv": 5000, "c1d": 800, "c1v": 5000}, "23": {"best": "Circling (RNP B / VOR DME 23)", "bd": 1200, "bv": 7000, "c1d": 1200, "c1v": 7000}}, "LEBL": {"02": {"best": "ILS CAT I", "bd": 320, "bv": 700, "c1d": 320, "c1v": 700}, "06L": {"best": "ILS CAT IIIB", "bd": 0, "bv": 75, "c1d": 260, "c1v": 600}, "06R": {"best": "ILS CAT IIIB", "bd": 0, "bv": 75, "c1d": 270, "c1v": 600}, "24L": {"best": "ILS CAT IIIB", "bd": 0, "bv": 75, "c1d": 200, "c1v": 750}, "24R": {"best": "ILS CAT IIIB", "bd": 0, "bv": 75, "c1d": 230, "c1v": 550}}, "LEMD": {"18L": {"best": "ILS CAT IIIB", "bd": 0, "bv": 75, "c1d": 230, "c1v": 550}, "18R": {"best": "ILS CAT IIIB (GA 4.5%)", "bd": 0, "bv": 75, "c1d": 200, "c1v": 550}, "32L": {"best": "ILS CAT IIIB", "bd": 0, "bv": 75, "c1d": 270, "c1v": 600}, "32R": {"best": "ILS CAT IIIB", "bd": 0, "bv": 75, "c1d": 210, "c1v": 550}}, "LEZL": {"09": {"best": "ILS Z CAT I", "bd": 210, "bv": 550, "c1d": 210, "c1v": 550}, "27": {"best": "ILS CAT I", "bd": 220, "bv": 550, "c1d": 220, "c1v": 550}}, "LEMG": {"12": {"best": "ILS CAT I", "bd": 220, "bv": 550, "c1d": 220, "c1v": 550}, "13": {"best": "ILS Z CAT I", "bd": 230, "bv": 550, "c1d": 230, "c1v": 550}, "31": {"best": "ILS Z CAT I (GA 2.5%)", "bd": 770, "bv": 2400, "c1d": 770, "c1v": 2400}}, "LEBB": {"12": {"best": "LOC Z DME", "bd": 790, "bv": 2400, "c1d": 850, "c1v": 2400}, "30": {"best": "ILS Z CAT I", "bd": 320, "bv": 700, "c1d": 320, "c1v": 700}}, "LEVC": {"12": {"best": "ILS CAT I", "bd": 210, "bv": 550, "c1d": 210, "c1v": 550}, "30": {"best": "RNP Y LNAV/VNAV (GA 2.5%)", "bd": 1390, "bv": 2400, "c1d": 1450, "c1v": 2400}}}};
const minCfg = () => (cfg && cfg.minima && cfg.minima.ap) ? cfg.minima : MIN_BUILTIN;
let MIN_ORIG = null, MIN_KEY = null;
function applyMinima(){
  if (!MIN_ORIG) MIN_ORIG = {m: JSON.parse(JSON.stringify(RWY_MINIMA)), b: JSON.parse(JSON.stringify(RWY_BELOW))};
  const M = minCfg().ap || {}, key = JSON.stringify(M);
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
  const R = (minCfg().ap || {})[icao]; if (!R) return "";
  const rows = Object.entries(R).sort((a, b) => a[0].localeCompare(b[0])).map(([rw, x]) => `<tr><td><b>${esc(rw)}</b></td><td>${esc(x.best)}<small>${x.bd ? x.bd + " ft" : "sem DH"} / ${x.bv} m</small></td><td>${x.bd ? "&lt; " + x.bd + " ft<br>" : ""}&lt; ${x.bv} m</td><td>≤ ${x.c1d + 200} ft<br>≤ ${x.c1v + 1000} m<small>CAT I ${x.c1d} ft / ${x.c1v} m</small></td></tr>`).join("");
  const m = minCfg(), src = [m.src, m.cat ? "Cat " + m.cat : ""].filter(Boolean).join(" · ");
  return `<div class="minima"><span class="rwy-tag">Mínimos de aproximação${src ? " · " + esc(src) : ""}</span><div class="gtabwrap"><table class="gtab mintab"><thead><tr><th>Pista</th><th>Melhor aproximação</th><th>BELOW MIN</th><th>RVAC</th></tr></thead><tbody>${rows}</tbody></table></div><p class="hint" style="margin:4px 0 0">BELOW MIN: abaixo da melhor aproximação (sem LPV). RVAC: até ao CAT I + 200 ft / + 1000 m. LVO segue a fuel policy.</p></div>`;
}

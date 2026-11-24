/* layout v2: código curto da categoria para as células e etiquetas */
const CAT_CODE = {lim: "LIM", cig: "LVO", bmin: "BMIN", rvac: "RVAC", conv: "TS", vis: "VA", ice: "SN", wind: "WND", mar: "WND", cig4: "CIG", obsc: "BR", int: "INT", capt: "CAPT"};
const CODE_WORDS = /^(BELOW MIN|LVO|RVAC|OUT OF LIM|LDG NOT ALLOWED|CAPT)$/;
function cellCodeHtml(cat, labs){
  let code = CAT_CODE[cat] || (labs[0] || "").slice(0, 5);
  const rest = labs.filter(s => !CODE_WORDS.test(s) && s !== code).map(s => s.replace(/^WND\s+/, ""));
  if (cat === "ice" && rest[0] && !/SN/.test(rest[0])) code = "ICE";
  let det = rest[0] || "";
  if (code === det) det = rest[1] || "";
  if (labs.length > 2 && det) det += "+";
  return `<span class="cc">${esc(code)}</span>` + (det ? `<span class="cd">${esc(det)}</span>` : "");
}
/* layout v2: uma só barra de controlos — contadores (filtram), zona e categorias em menus, pesquisa */
(function v2Bar(){
  const st = document.querySelector(".strip"), tb = document.querySelector(".toolbar");
  if (!st || !tb || st.dataset.v2) return; st.dataset.v2 = "1";
  st.classList.add("v2bar");
  const areas = document.getElementById("areas");
  const sel = document.createElement("select"); sel.id = "areaSel"; sel.className = "v2sel"; sel.setAttribute("aria-label", "Zona");
  sel.innerHTML = [...areas.querySelectorAll("[data-area]")].map(b => `<option value="${b.dataset.area}">${b.dataset.area ? b.textContent.trim() : "Todas as zonas"}</option>`).join("");
  sel.addEventListener("change", () => { const b = areas.querySelector(`[data-area="${sel.value}"]`); if (b) b.click(); });
  areas.hidden = true;
  const cb = document.createElement("button"); cb.type = "button"; cb.id = "catsBtn"; cb.className = "v2sel"; cb.setAttribute("aria-expanded", "false"); cb.textContent = "Categorias ▾";
  cb.addEventListener("click", () => { ui.catsOpen = !ui.catsOpen; saveUI(); v2Sync(); });
  areas.after(sel); sel.after(cb);
  const sep = document.createElement("span"); sep.className = "v2sep";
  st.append(sep, ...tb.children); tb.remove();
})();
function v2Sync(){
  const sel = document.getElementById("areaSel"); if (sel) sel.value = ui.area || "";
  const cats = document.getElementById("cats"), cb = document.getElementById("catsBtn"); if (!cats || !cb) return;
  const n = cats.querySelectorAll(".cat:not(.zero)").length, open = !!ui.catsOpen || !!ui.cat;
  cats.hidden = !open; cb.setAttribute("aria-expanded", String(open));
  cb.textContent = `Categorias${n ? " (" + n + ")" : ""}${ui.cat ? " · filtro ativo" : ""} ${open ? "▴" : "▾"}`;
  cb.classList.toggle("on", !!ui.cat);
}
/* layout v2: painel do aeroporto por ordem de decisão — resumo do alerta (agora e a seguir) e próximo voo afetado,
   depois pista/mínimos e TAF; METAR, rosa dos ventos, janelas e grupos recolhidos por omissão */
function v2Segs(r, slots){
  const segs = [];
  (r.res || []).forEach((x, k) => {
    const cat = x.level === "red" ? x.cat : null, l = segs[segs.length - 1];
    if (l && l.cat === cat) { l.e = slots[k] + HOUR; if (cat) l.labs.push(...cellLabels(x.hard)); }
    else segs.push({cat, s: slots[k], e: slots[k] + HOUR, labs: cat ? cellLabels(x.hard) : []});
  });
  return segs.filter(g => g.cat);
}
function v2Summary(r, slots){
  if (!r.T || r.T.error || !slots || !slots.length) return "";
  const now = Date.now(), segs = v2Segs(r, slots);
  const cur = segs.find(g => g.s <= now && now < g.e), nxt = segs.find(g => g.s > now && g !== cur);
  const hz = t => pad(new Date(t).getUTCHours()) + "Z";
  const det = g => { const rest = [...new Set(g.labs)].filter(s => !CODE_WORDS.test(s) && s !== CAT_CODE[g.cat]).map(s => s.replace(/^WND\s+/, "")); return rest.slice(0, 2).join(" "); };
  let h = "";
  if (cur) h += `<div class="v2st k-${cur.cat}"><b>${esc(CAT_CODE[cur.cat] || cur.cat)} ${esc(det(cur))}</b> agora até ${hz(cur.e)}`;
  else if (nxt) h += `<div class="v2st ok"><b>Sem alerta agora</b>`;
  else return `<div class="v2st ok"><b>Sem alertas</b> no período do TAF</div>`;
  if (nxt) h += ` <span class="v2nx k-${nxt.cat}">${cur ? "depois" : "a partir das " + hz(nxt.s)} ${esc(CAT_CODE[nxt.cat] || nxt.cat)} ${cur ? hz(nxt.s) + "–" : ""}${hz(nxt.e)}</span>`;
  try { const g = cur || nxt, m = /RWY(\w+)/.exec(g.labs.join(" ")), rw = m && m[1], B = rw && RWY_BELOW[r.icao] && RWY_BELOW[r.icao][rw], V = rw && RWY_MINIMA[r.icao] && RWY_MINIMA[r.icao][rw];
    if (B || V) h += `<div class="v2mn">RWY ${esc(rw)} · ${B ? `BMIN &lt; ${B[0] ? B[0] + " ft / " : ""}${B[1]} m` : ""}${B && V ? " · " : ""}${V ? `RVAC ≤ ${V[0]} ft / ${V[1]} m` : ""}</div>`; } catch(e){}
  try { if (typeof fltCache !== "undefined" && fltCache){ const L = fltCache.P.flights.filter(f => f.dst === r.icao && f.alert && !f.landed).sort((a, b) => (a.eta ?? a.sta) - (b.eta ?? b.sta));
    if (L.length){ const f = L[0], t = f.eta ?? f.sta; h += `<div class="v2fl">✈ ${L.length} ${L.length === 1 ? "voo afetado" : "voos afetados"} · próximo <b>${esc(f.fl)} ${hhmm(t)}Z</b> <span class="v2nx k-${FLT_KEY[f.alert.name] || "int"}">${esc(CAT_CODE[FLT_KEY[f.alert.name]] || f.alert.name)}</span></div>`; } } } catch(e){}
  return h + `</div>`;
}
function v2Panel(el, r, slots){
  const head = el.querySelector(".d-head"); if (!head) return;
  const secs = [...el.querySelectorAll(":scope > .d-sec")], key = s => ((s.querySelector(":scope > h3") || {}).textContent || "").split(/\s[·(]/)[0].trim().toUpperCase();
  const ORDER = ["PISTAS", "TAF", "AGORA", "METAR", "LIMITAÇÕES DE VENTO", "JANELAS DE ALERTA", "GRUPOS"];
  const rank = s => { const k = key(s); const i = ORDER.findIndex(o => k.startsWith(o)); return i < 0 ? ORDER.length : i; };
  let after = head;
  const sm = v2Summary(r, slots);
  if (sm){ const d = document.createElement("div"); d.className = "v2sum"; d.innerHTML = sm; head.after(d); after = d; }
  secs.slice().sort((a, b) => rank(a) - rank(b)).forEach(s => { after.after(s); after = s; });
  ui.secClosed = ui.secClosed || {};
  if (!ui.v2sec){ ui.v2sec = 1; for (const k of ["METAR", "LIMITAÇÕES DE VENTO", "JANELAS DE ALERTA", "GRUPOS"]) if (!(k in ui.secClosed)) ui.secClosed[k] = true; saveUI(); }
}
/* layout v2 — telemóvel: em vez da grelha, cartões dos aeroportos (os mesmos da grelha, pela mesma ordem) com o
   código do alerta, uma barra das próximas horas, o período, a condição e os voos afetados; tocar abre o aeroporto */
function v2Cards(slots){
  let box = document.getElementById("mcards");
  if (!box){ const gw = document.getElementById("gridwrap"); if (!gw) return; box = document.createElement("div"); box.id = "mcards"; box.className = "mcards"; gw.before(box);
    box.addEventListener("click", e => { const c = e.target.closest("[data-mc]"); if (!c) return; const tr = document.querySelector(`#grid tr.row[data-icao="${c.dataset.mc}"]`); if (tr) tr.click(); }); }
  if (!window.matchMedia("(max-width:700px)").matches){ box.innerHTML = ""; return; }
  const ics = [...document.querySelectorAll("#grid tr.row[data-icao]")].map(tr => tr.dataset.icao);
  const N = Math.min(16, (slots || []).length), hz = t => pad(new Date(t).getUTCHours()) + "Z";
  const fl = {}; try { if (fltCache) fltCache.P.flights.filter(f => f.alert && !f.landed).sort((a, b) => (a.eta ?? a.sta) - (b.eta ?? b.sta)).forEach(f => (fl[f.dst] = fl[f.dst] || []).push(f)); } catch(e){}
  const out = []; let hidden = 0;
  for (const ic of ics){
    const r = rowsCache.find(x => x.icao === ic); if (!r) continue;
    if (!ui.mAll && !(r.levels || []).includes("red") && !fl[ic]){ hidden++; continue; }
    const segs = r.T && !r.T.error ? v2Segs(r, slots) : [];
    const g = segs.find(s => s.s <= Date.now() && Date.now() < s.e) || segs[0];
    const bar = (r.res || []).slice(0, N).map(x => `<i class="${x.level === "red" && x.cat ? "k-" + x.cat : x.level}"></i>`).join("");
    const det = g ? [...new Set(g.labs)].filter(s => !CODE_WORDS.test(s) && s !== CAT_CODE[g.cat]).map(s => s.replace(/^WND\s+/, "")).slice(0, 3).join(" ") : "";
    const when = segs.slice(0, 3).map(s => `${CAT_CODE[s.cat] || s.cat} ${hz(s.s)}–${hz(s.e)}`).join(" · ");
    const F = fl[ic] || [];
    out.push(`<button type="button" class="mc${g ? " k-" + g.cat : ""}" data-mc="${ic}"><div class="mt"><b>${ic}</b><span>${esc(iataOf(ic) || "")}</span><span class="sp"></span>${g ? `<span class="mtag">${esc(CAT_CODE[g.cat] || g.cat)}</span>` : `<span class="mok">${r.T ? "sem alerta" : "sem TAF"}</span>`}</div>`
      + `<div class="mb">${bar}</div>${when ? `<div class="mm">${esc(when)}</div>` : ""}${det ? `<div class="mm">${esc(det)}</div>` : ""}`
      + (F.length ? `<div class="mf">✈ ${F.slice(0, 2).map(f => `${esc(f.fl)} ${hhmm(f.eta ?? f.sta)}Z`).join(" · ")}${F.length > 2 ? " · +" + (F.length - 2) : ""}</div>` : "") + `</button>`);
  }
  box.innerHTML = (out.join("") || `<p class="hint" style="padding:12px">Nenhum aeroporto em alerta.</p>`)
    + (hidden || ui.mAll ? `<button type="button" class="v2sel mall" data-mall="1">${ui.mAll ? "Mostrar só os aeroportos em alerta" : `Mostrar também os sem alerta (${hidden})`}</button>` : "");
  const ma = box.querySelector("[data-mall]"); if (ma) ma.onclick = e => { e.stopPropagation(); ui.mAll = !ui.mAll; saveUI(); v2Cards(slots); };
}
let v2rz = null; window.addEventListener("resize", () => { clearTimeout(v2rz); v2rz = setTimeout(() => { try { v2Cards(fltSlots); } catch(e){} }, 200); });

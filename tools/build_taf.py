"""Gera taf/index.html a partir do TAF Monitor original (tools/taf-monitor-original.html).

O conteúdo do monitor fica igual; só se acrescenta:
  - verificação de acesso: só abre dentro do portal, com sessão aprovada (senão vai para o portal);
  - Definições: abrem só para Administradores do portal (deixa de haver PIN) e ficam guardadas no Supabase,
    iguais para todos (o modo ao vivo/exemplo/manual fica só no navegador do Administrador);
  - ponte com o portal: envia o resumo (TAF novos/AMD, destinos em alerta) e aceita "abrir aeroporto" e "filtro".
Para atualizar o monitor: substituir tools/taf-monitor-original.html e correr  python3 tools/build_taf.py
"""
import os, re, sys

WX_H = 8  # horas do resumo do Início (alerta nas próximas WX_H horas)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(ROOT, 'tools', 'taf-monitor-original.html'), encoding='utf-8').read()


def rep(s, old, new, count=1):
    n = s.count(old)
    if n != count:
        sys.exit(f'build_taf: esperava {count}x, encontrei {n}x: {old[:80]!r}')
    return s.replace(old, new)


s = src
# 1) cabeçalho: ícones do portal, sem manifest próprio; esconder até verificar o acesso
s = rep(s, '<link rel="manifest" href="manifest.webmanifest">\n', '')
s = rep(s, '<link rel="icon" type="image/png" sizes="192x192" href="icon-192.png">', '<link rel="icon" type="image/png" sizes="192x192" href="../icon-192.png">')
s = rep(s, '<link rel="apple-touch-icon" href="apple-touch-icon.png">', '<link rel="apple-touch-icon" href="../icon-192.png">\n<style>html.gate body{visibility:hidden}</style>\n<script>document.documentElement.classList.add("gate")</script>')

# 2) Definições só para Administradores do portal (em vez do PIN guardado neste navegador)
s = rep(s, 'let isAdmin = [ADMIN_HASH, ADMIN_HASH_FNV].includes(store.get("tafmon.admin", ""));',
        'let isAdmin = window.__portalRole === "admin"; // portal: Definições só para Administradores')
# definições partilhadas pelo portal (Supabase): iguais para todos; só o modo (ao vivo/exemplo/manual) fica por navegador, e só para Administradores
s = rep(s, 'if (SETTINGS_LOCKED && !isAdmin) cfg = Object.assign({}, DEFAULTS);\nasync function pinHash',
        'function portalCfg(){ const c = Object.assign({}, DEFAULTS, window.__portalTafCfg || {}); c.mode = isAdmin ? store.get("tafmon.mode", DEFAULTS.mode) : DEFAULTS.mode;\n'
        '  /* vento/rajada: o limite passou para 35 kt (definições gravadas antes com 30 kt passam a 35; PDL, TER e FNC continuam acima de 25 kt) */\n'
        '  { const sh = window.__portalTafCfg || {}; if (sh.wind != null && (+sh.windV || 1) < 3 && (+sh.wind === 30 || +sh.wind === 25)) c.wind = 35; c.windV = 3; }\n'
        '  return c; }\n'
        'cfg = portalCfg();\nasync function pinHash')
s = rep(s, '  store.set("tafmon.cfg", cfg);\n  closeSettings(); selected = null; load();',
        '  store.set("tafmon.mode", cfg.mode);\n'
        '  const shared = Object.assign({}, cfg); delete shared.mode;\n'
        '  window.parent.postMessage({type: "taf-cfg-save", cfg: shared}, location.origin);\n'
        '  closeSettings(); selected = null; load();')
s = rep(s, '  dlg.hidden = false; $("#fWorker").focus();\n}',
        '  let pi = $("#portalCfgInfo"); if (!pi){ pi = document.createElement("p"); pi.id = "portalCfgInfo"; pi.className = "muted"; pi.style.cssText = "margin:0 0 10px;font-size:12.5px"; $("#setForm").prepend(pi); }\n'
        '  const m = window.__portalTafMeta; pi.textContent = "Estas definições valem para todos os utilizadores do portal." + (m && m.at ? " Última alteração: " + (m.by || "?") + ", " + new Date(m.at).toLocaleString("pt-PT") + "." : "");\n'
        '  dlg.hidden = false; $("#fWorker").focus();\n}')
s = rep(s, 'paintLock();\n$("#setClose")', 'paintLock();\n$("#setLock").hidden = true; // o acesso vem do portal\n$("#setClose")')
s = rep(s, '$("#btnSettings").addEventListener("click", () => { if (!SETTINGS_LOCKED || isAdmin) openSettings(); else openPin(); });',
        '$("#btnSettings").addEventListener("click", () => { if (!SETTINGS_LOCKED || isAdmin) openSettings(); else portalNotAdmin(); });\n'
        'function portalNotAdmin(){ const b = $("#banner"); b.innerHTML = "<b>Definições bloqueadas.</b> <span>Só um Administrador do portal pode alterar as definições do TAF.</span>"; b.className = "banner"; b.hidden = false; setTimeout(() => { if (b.textContent.startsWith("Definições bloqueadas")) b.hidden = true; }, 6000); }')
s = rep(s, 'b.title = SETTINGS_LOCKED && !isAdmin ? "Bloqueado: precisa de PIN" : "Definições";',
        'b.title = SETTINGS_LOCKED && !isAdmin ? "Só Administradores do portal" : "Definições";')

# 2a) vento/rajada: alerta a partir de 35 kt (PDL, TER e FNC continuam acima de 25 kt)
s = rep(s, 'cig2: 400, wind: 30, windV: 2,', 'cig2: 400, wind: 35, windV: 3,')

# 2b) TAF mais rápidos: o browser não guarda cópia (o Worker já guarda) e, por omissão, atualiza de 2 em 2 minutos
s = rep(s, 'fetch(url, {signal: ctl.signal, headers: {Accept: "application/json, text/plain"}})', 'fetch(url, {signal: ctl.signal, cache: "no-store", headers: {Accept: "application/json, text/plain"}})')
s = rep(s, 'fetch(url, {signal: ctl.signal, headers: {Accept: "application/json"}})', 'fetch(url, {signal: ctl.signal, cache: "no-store", headers: {Accept: "application/json"}})')
s = rep(s, 'intensity: true, hours: 30, refresh: 5};', 'intensity: true, hours: 30, refresh: 2};')

s = rep(s, 'Math.min(60, Math.max(5, +$("#fRefresh").value || 10))', 'Math.min(60, Math.max(1, +$("#fRefresh").value || 2))')
s = rep(s, '<input type="number" id="fRefresh" min="5" max="60" step="5">', '<input type="number" id="fRefresh" min="1" max="60" step="1">')

# 2c) TAF "novo" = emissão mais recente (hora de emissão), não só texto diferente: o mesmo TAF
#     devolvido com outra formatação, ou um TAF mais antigo que reaparece, já não conta como novo
s = rep(s, """  for (const T of list){
    if (!T.icao || T.error) continue;
    const prev = tafSeen[T.icao];
    if (prev && prev.raw !== T.raw) tafChanged[T.icao] = {at: now, prevRaw: prev.raw};
    tafSeen[T.icao] = {raw: T.raw};
  }""", """  const norm = r => String(r || "").replace(/\\s+/g, " ").trim();
  const latest = {};
  for (const T of list){ if (!T.icao || T.error) continue; const L = latest[T.icao]; if (!L || (T.issue || 0) >= (L.issue || 0)) latest[T.icao] = T; }
  for (const T of Object.values(latest)){
    const prev = tafSeen[T.icao], raw = norm(T.raw), iss = T.issue || null;
    if (prev){
      const newer = iss && prev.issue ? iss > prev.issue : raw !== norm(prev.raw);
      if (newer) tafChanged[T.icao] = {at: now, prevRaw: prev.raw, issue: iss};
      else if (iss && prev.issue && iss < prev.issue) continue;   // TAF mais antigo que reapareceu: ignorar
    }
    tafSeen[T.icao] = {raw: T.raw, issue: iss};
  }""")

# 2d) um TAF só conta como novo se foi emitido há pouco (até 2 h): abrir o portal horas depois não marca como novos
#     os TAF emitidos entretanto (ex.: um TAF das 17Z às 22Z)
s = rep(s, 'const isNewTaf = ic => !!tafChanged[ic] && Date.now() - tafChanged[ic].at < NEW_MIN * 60000;',
        'const isNewTaf = ic => { const c = tafChanged[ic]; if (!c || Date.now() - c.at >= NEW_MIN * 60000) return false; return !c.issue || Date.now() - c.issue < 2 * 3600e3; };')

# 3) ponte com o portal: resumo depois de cada render
s = rep(s, '  $("#legendCodes").textContent = ',
        '  try { if (window.parent !== window) window.parent.postMessage({type: "taf-summary", updatedAt: lastFetch || null, total: allRows.length,\n'
        '    now: allRows.filter(r => inList(r.icao, "DST") && r.levels[0] === "red").map(r => ({icao: r.icao, name: nameOf(r.icao)})),\n'
        f'    win: {WX_H}, nextWin: allRows.filter(r => inList(r.icao, "DST") && r.levels.slice(0, {WX_H}).includes("red")).map(r => ({{icao: r.icao, name: nameOf(r.icao)}})),\n'
        '    noTaf: allRows.filter(r => !r.T || r.T.error).length,\n'
        f'    alerts: allRows.filter(r => inList(r.icao, "DST") && r.levels.slice(0, {WX_H}).includes("red")).map(r => {{ const a = r.levels.indexOf("red"); let b = r.levels.slice(0, {WX_H}).lastIndexOf("red"); while (b + 1 < r.levels.length && r.levels[b + 1] === "red") b++; const hard = r.res.slice(0, {WX_H}).filter(x => x.level === "red").flatMap(x => x.hard); const ks = [...new Set(hard.map(h => catOfCode(h.code)))].sort((x, y) => catRank(x) - catRank(y)); return {{icao: r.icao, name: nameOf(r.icao), kc: catColor(worstOf(ks)), rank: ks.length ? catSev(worstOf(ks)) : 99, now: a === 0, from: slots[a], to: slots[b] + HOUR, open: b === r.levels.length - 1, cats: ks.map(k => (CATS.find(c => c.k === k) || {{}}).label || k), cond: cellLabels(hard).slice(0, 10)}}; }}).sort((x, y) => (x.rank - y.rank) || (y.now - x.now) || (x.from - y.from)),\n'
        '    newTafs: allRows.filter(r => r.isNew).map(r => ({icao: r.icao, name: nameOf(r.icao), amd: /\\bAMD\\b/.test((r.T && r.T.raw) || ""), at: (tafChanged[r.icao] || {}).at || null, issue: (r.T && r.T.issue) || null, level: r.levels[0], kc: worstCatColor(r), rank: worstCatRank(r), alert: r.levels.includes("red"), dest: inList(r.icao, "DST")})).sort((a, b) => (a.rank - b.rank) || (b.at || 0) - (a.at || 0)),\n'
        '    error: fetchError || null}, location.origin); } catch(e){}\n'
        '  $("#legendCodes").textContent = ')

# 3b) abrir um aeroporto no painel lateral avisa o portal (esse TAF novo/AMD passa a "visto")
s = rep(s, '  ui.detailClosed = false; saveUI();\n  const t0 = Math.floor(Date.now() / HOUR) * HOUR;',
        '  ui.detailClosed = false; saveUI();\n  try { if (window.parent !== window) window.parent.postMessage({type: "taf-opened", icao: selected}, location.origin); } catch(e){}\n  const t0 = Math.floor(Date.now() / HOUR) * HOUR;')

# 3c) filtro só do portal: alerta nas próximas WX_H horas (o resumo do Início)
s = rep(s, 'if (ui.filter === "next6") return r.levels.slice(0, 6).includes("red");', 'if (ui.filter === "next6") return r.levels.slice(0, 6).includes("red");\n    if (ui.filter === "nextwin") return r.levels.slice(0, %d).includes("red");' % WX_H)

# 3d) aeroportos favoritos (de cada utilizador, guardados pelo portal): estrela na grelha
s = rep(s, '<button type="button" aria-label="Ver TAF ${r.icao}" title="${esc(nameOf(r.icao) || r.icao)}"><span class="dot',
        '<button type="button" aria-label="Ver TAF ${r.icao}" title="${esc(nameOf(r.icao) || r.icao)}">${favStar(r.icao)}<span class="dot')
s = rep(s, 'function buildRows(slots){',
        'const isFavAp = ic => (window.__portalFavs || []).includes(ic);\n'
        'function favStar(ic){ const on = isFavAp(ic); return `<span class="tfav${on ? " on" : ""}" data-fav="${ic}" role="button" tabindex="0" title="${on ? "Retirar dos favoritos" : "Marcar como favorito"}" aria-label="${on ? "Retirar " + ic + " dos favoritos" : "Marcar " + ic + " como favorito"}">${on ? "★" : "☆"}</span>`; }\n'
        'function buildRows(slots){')
s = rep(s, 'th.ap .dot{width:7px;height:7px;border-radius:50%;flex:none;background:var(--line)}', '.tfav{font-size:14px;line-height:1;color:var(--muted,#8a99a8);cursor:pointer;margin-right:-2px;opacity:.55}.tfav:hover{opacity:1}.tfav.on{color:#e0a100;opacity:1}\nth.ap .dot{width:7px;height:7px;border-radius:50%;flex:none;background:var(--line)}')

# 3e) favoritos no topo da grelha: grupo "★ Favoritos" antes das regiões (ou primeiro, na ordenação por alerta)
s = rep(s, """    vis = vis.slice().sort((a, b) => b.score - a.score || a.idx - b.idx);
    h += vis.map(rowHtml).join("");""", """    vis = vis.slice().sort((a, b) => (isFavAp(b.icao) - isFavAp(a.icao)) || b.score - a.score || a.idx - b.idx);
    h += vis.map(rowHtml).join("");""")
s = rep(s, """    const groups = {};
    vis.forEach(r => (groups[r.region] = groups[r.region] || []).push(r));
    const order = REGIONS.map(x => x[0]).concat("Outros");""", """    const groups = {};
    vis.forEach(r => { const gk = isFavAp(r.icao) ? "★ Favoritos" : r.region; (groups[gk] = groups[gk] || []).push(r); });
    const order = ["★ Favoritos"].concat(REGIONS.map(x => x[0]), "Outros");""")

# 3f) colunas das horas mais estreitas (52 px): cabem mais horas no ecrã sem cortar o texto
s = rep(s, '.grid td.c{width:62px;min-width:62px;max-width:62px;height:44px;font-size:12px}', '.grid td.c{width:52px;min-width:52px;max-width:52px;height:42px;font-size:10.5px;padding:1px 1px}')
s = rep(s, '.grid thead tr.hrs th{top:28px;height:26px;font-size:14px;width:62px;min-width:62px}', '.grid thead tr.hrs th{top:28px;height:26px;font-size:13px;width:52px;min-width:52px}')

# 3g) relatório: uma linha por aeroporto, com todas as condições e alertas juntos (cada um por baixo do outro)
s = rep(s, """  for (const k in catSum) delete catSum[k]; icaos.clear();
  for (const B of blocks) for (const r of B.rows){ (catSum[r.name] = catSum[r.name] || new Set()).add(r.icao); icaos.add(r.icao); }""",
"""  /* uma linha por aeroporto: junta as condições e os alertas de todos os tipos (o mais grave primeiro) */
  for (const B of blocks){
    const by = new Map();
    for (const r of B.rows){
      const m = by.get(r.icao);
      if (!m){ by.set(r.icao, Object.assign({}, r, {names: [r.name], wins: r.wins.slice(), conds: r.cond ? [r.cond] : [], fulls: [r.full]})); continue; }
      m.names.push(r.name); m.wins.push(...r.wins);
      if (r.cond && !m.conds.includes(r.cond)) m.conds.push(r.cond);
      if (!m.fulls.includes(r.full)) m.fulls.push(r.full);
    }
    B.rows = [...by.values()].map(m => { m.wins = mergeWins(m.wins); m.cond = m.conds.join("\\n"); m.full = m.fulls.join("\\n"); m.per = m.wins.map(w => fmtWinT(w.s, w.e)).join(", "); m.first = m.wins[0].s; return m; });
  }
  for (const k in catSum) delete catSum[k]; icaos.clear();
  for (const B of blocks) for (const r of B.rows){ for (const n of (r.names || [r.name])) (catSum[n] = catSum[n] || new Set()).add(r.icao); icaos.add(r.icao); }""")
s = rep(s, "const cs = {}; B.rows.forEach(r => (cs[r.name] = cs[r.name] || new Set()).add(r.icao));",
        "const cs = {}; B.rows.forEach(r => (r.names || [r.name]).forEach(n => (cs[n] = cs[n] || new Set()).add(r.icao)));")
s = rep(s, "uma linha por aeroporto e alerta, por zona", "uma linha por aeroporto (condições e alertas juntos), por zona")
# cada condição e alerta numa linha própria dentro da célula (por baixo, para não ficar comprido)
s = rep(s, "const W = REP_COLS.map((h, i) => Math.max(h.length, ...cells.map(c => c[i].length)));",
        "const W = REP_COLS.map((h, i) => Math.max(h.length, ...cells.map(c => Math.max(...String(c[i]).split(\"\\n\").map(x => x.length)))));")
s = rep(s, "out.push(line(cells[k])); }); }", "{ const parts = cells[k].map(x => String(x).split(\"\\n\")), nl = Math.max(...parts.map(q => q.length)); for (let j = 0; j < nl; j++) out.push(line(parts.map(q => q[j] || \"\"))); } }); }")
s = rep(s, '${i === 2 ? ";font-family:Consolas,monospace" : ""}">${esc(c)}</td>`', '${i === 2 ? ";font-family:Consolas,monospace" : ""};vertical-align:top">${esc(c).replace(/\\n/g, "<br>")}</td>`')

# 3h) painel do aeroporto: os dois últimos METAR e o TAF anterior, com o que mudou assinalado; o anterior pode esconder-se
s = rep(s, """    metarStatus = "ok";
    return out;""", """    /* guarda o METAR anterior de cada aeroporto: vem do Worker (vários METAR) ou do que este browser já tinha */
    const hist = store.get("tafmon.mhist", {});
    for (const ic of Object.keys(out)){
      const all = (byIc[ic] || []).sort((a, b) => b.obs - a.obs).filter((m, k, A) => k === 0 || m.obs !== A[k - 1].obs);
      let prev = all[1] || null;
      const H = hist[ic];
      if (!prev && H){ if (H.obs < out[ic].obs) prev = {raw: H.raw, obs: H.obs}; else if (H.obs === out[ic].obs && H.prev) prev = H.prev; }
      out[ic].prev = prev;
      hist[ic] = {raw: out[ic].raw, obs: out[ic].obs, prev};
    }
    store.set("tafmon.mhist", hist);
    metarStatus = "ok";
    return out;""")
s = rep(s, """    const out = {};
    for (const x of arr) if (x.icaoId && x.rawOb){
      const obs = x.obsTime ? x.obsTime * 1000 : Date.parse(x.reportTime || "");""", """    const out = {}, byIc = {};
    for (const x of arr) if (x.icaoId && x.rawOb){
      const obs = x.obsTime ? x.obsTime * 1000 : Date.parse(x.reportTime || "");
      (byIc[x.icaoId] = byIc[x.icaoId] || []).push({raw: x.rawOb, obs});""")
NEW_METAR = r'''/* tokens que mudaram em relação ao outro texto (ignora o tipo, o aeroporto e a hora) */
/* a parte principal compara-se com a parte principal; a tendência / os grupos de mudança com os grupos de mudança */
function diffSegs(raw){ let seg = 0; return String(raw || "").split(/\s+/).map(t => { if (/^(TEMPO|BECMG|NOSIG|RMK|PROB\d{2})$/.test(t) || /^FM\d{6}$/.test(t)) seg = 1; return seg + ":" + t; }); }
function diffIdx(a, b){
  const cnt = {}; diffSegs(b).forEach(k => cnt[k] = (cnt[k] || 0) + 1);
  const out = new Set();
  diffSegs(a).forEach((k, i) => {
    const t = k.slice(2);
    if (/^\d{6}Z$/.test(t) || /^\d{4}\/\d{4}$/.test(t) && i < 5 || (i < 4 && /^(METAR|SPECI|TAF|AMD|COR|AUTO|[A-Z]{4})$/.test(t))) return;
    if (cnt[k]) cnt[k]--; else out.add(i);
  });
  return out;
}
const showPrev = () => store.get("tafmon.showprev", true);
function metarToksHtml(icao, raw, chg){
  let trend = false;
  return String(raw).split(/\s+/).map((t, ix) => {
    let h;
    if (/^(TEMPO|BECMG|NOSIG|RMK)$/.test(t)){ trend = true; h = `<span class="kw">${esc(t)}</span>`; }
    else if (/^(METAR|SPECI|COR|AUTO)$/.test(t)) h = `<span class="kw">${esc(t)}</span>`;
    else { const kc = tokenCat(t, icao); h = kc ? `<span class="${trend ? "ign" : "hit k-" + kc}">${esc(t)}</span>` : esc(t); }
    return chg && chg.has(ix) ? `<mark class="chg">${h}</mark>` : h;
  }).join(" ");
}
const prevTog = () => `<button type="button" class="prevtog" data-prevtog aria-pressed="${showPrev()}">${showPrev() ? "Esconder anterior" : "Mostrar anterior"}</button>`;
function metarHtml(icao){
  const M = metars[icao];
  if (!M){
    const why = metarStatus === "old-worker" ? "Atualize o código do Worker para receber METAR." : metarStatus === "error" ? "Não foi possível obter METAR." : cfg.mode === "manual" ? "Cole também o METAR (linha começada por METAR) para o ver aqui." : "Sem METAR para este aeroporto.";
    return `<div class="d-sec"><h3>METAR</h3><p class="hint" style="margin:0">${why}</p></div>`;
  }
  const age = Math.round((Date.now() - M.obs) / 60000), P = M.prev;
  let h = `<div class="d-sec"><h3>METAR · ${fmtDHZ(M.obs)} · há ${age < 60 ? age + " min" : (age / 60).toFixed(1).replace(".", ",") + " h"}${age > 70 ? ` <span style="color:var(--t-amb)">desatualizado</span>` : ""}</h3>
    <div class="raw">${metarToksHtml(icao, M.raw, P ? diffIdx(M.raw, P.raw) : null)}</div>`;
  if (P && showPrev()) h += `<div class="prevlab">Anterior · ${fmtDHZ(P.obs)}</div><div class="raw prev">${metarToksHtml(icao, P.raw, diffIdx(P.raw, M.raw))}</div>`;
  if (P) h += `<p class="hint chg-hint"><mark class="chg">assinalado</mark> = o que mudou entre os dois METAR ${prevTog()}</p>`;
  return h + `</div>`;
}
'''
a = s.index('function metarHtml(icao){'); b = s.index('\nasync function load(){', a)
s = s[:a] + NEW_METAR + s[b:]
# TAF: assinala o que mudou em relação ao TAF anterior (guardado até 24 h) e mostra o anterior por baixo
s = rep(s, '''    // TAF com destaque
    let raw = "", open = false;''', '''    // TAF com destaque
    let raw = "", open = false;
    const TP = tafChanged[T.icao] && tafChanged[T.icao].prevRaw, tCnt = {};
    if (TP) String(TP).split(/\\s+/).forEach(t => tCnt[t] = (tCnt[t] || 0) + 1);
    const tChg = t => { if (!TP || /^\\d{6}Z$/.test(t)) return false; if (tCnt[t]){ tCnt[t]--; return false; } return true; };''')
s = rep(s, '''      raw += (cls ? `<span class="${cls}">${esc(tk.t)}</span>` : esc(tk.t)) + " ";''', '''      { const ch = tChg(tk.t); raw += (ch ? '<mark class="chg">' : "") + (cls ? `<span class="${cls}">${esc(tk.t)}</span>` : esc(tk.t)) + (ch ? "</mark>" : "") + " "; }''')
s = rep(s, '''    h += `<div class="d-sec"><h3>TAF</h3><div class="raw">${raw}</div></div>`;''', '''    h += `<div class="d-sec"><h3>TAF</h3><div class="raw">${raw}</div>`;
    if (TP && showPrev()) h += `<div class="prevlab">TAF anterior</div><div class="raw prev">${(() => { const tpn = String(TP).replace(/\\s+/g, " ").trim(), dd = diffIdx(tpn, T.raw); return tpn.split(" ").map((t, ix) => dd.has(ix) ? `<mark class="chg">${esc(t)}</mark>` : esc(t)).join(" "); })()}</div>`;
    if (TP) h += `<p class="hint chg-hint"><mark class="chg">assinalado</mark> = o que mudou em relação ao TAF anterior ${prevTog()}</p>`;
    h += `</div>`;''')
s = rep(s, '.raw{font:400 13.5px/1.75 var(--f-mono);', '.raw .chg,.chg-hint .chg{background:rgba(64,170,255,.22);color:inherit;border-radius:3px;box-shadow:0 0 0 1px rgba(64,170,255,.65);padding:0 1px}.raw.prev{opacity:.78;font-size:12.5px;margin-top:4px}.prevlab{font-size:11.5px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.04em;margin:10px 0 2px}.chg-hint{margin:6px 0 0;font-size:12px}.prevtog{margin-left:8px;font-size:11.5px;font-weight:600;padding:2px 8px;border-radius:999px;border:1px solid var(--line2);background:transparent;color:var(--muted);cursor:pointer;text-transform:none;letter-spacing:0}.prevtog:hover{color:inherit}\\n.raw{font:400 13.5px/1.75 var(--f-mono);')

# 3i) Voos: lista de voos tirada de um PDF (ou de texto colado), cruzada com o TAF do destino à chegada e da origem à partida.
#     O PDF é lido só no browser (pdf.js em vendor/) e a lista fica guardada só neste browser (localStorage "tafmon.voos").
#     Na grelha, por baixo de cada aeroporto, aparecem os voos afetados; o resumo vai para o cartão "Voos afetados" do Início.
s = rep(s, '      <button class="btn ghost" id="btnReport" type="button">Relatório</button>',
        '      <button class="btn ghost" id="btnReport" type="button">Relatório</button>\n      <button class="btn ghost" id="btnFlights" type="button">Voos</button>')
s = rep(s, '<div class="modal" id="pinDlg" hidden>', """<div class="modal" id="flights" hidden>
  <div class="dlg wide" role="dialog" aria-modal="true" aria-labelledby="fltTitle">
    <header><h2 id="fltTitle">Voos afetados pela meteorologia no destino</h2><button class="d-close" style="display:block" type="button" id="fltClose" aria-label="Fechar">×</button></header>
    <div class="body">
      <label class="flt-drop" id="fltDrop">
        <input type="file" id="fltFile" accept="application/pdf,.pdf" hidden>
        <b>Carregar PDF dos voos</b><span>ou arraste o ficheiro para aqui · o PDF é lido só neste browser e a lista fica só neste browser</span>
      </label>
      <div class="rep-row flt-tools"><span class="hint" id="fltInfo"></span><button class="btn ghost" type="button" id="fltClear" style="margin-left:auto">Limpar voos</button></div>
      <div class="rep-prev" id="fltOut" aria-label="Voos afetados"></div>
      <details class="flt-raw" id="fltAllBox"><summary>Todos os voos lidos (para conferir)</summary><div class="rep-prev" id="fltAll" style="min-height:0;max-height:40vh"></div></details>
      <details class="flt-raw"><summary>Texto lido do PDF (pode corrigir ou colar a lista à mão)</summary><textarea class="flt-in" id="fltIn" spellcheck="false" placeholder="TP1234   LIS   ZRH   06:15   09:00   06:40   09:25"></textarea><button class="btn ghost" type="button" id="fltGo">Analisar</button></details>
    </div>
    <footer><span class="rep-msg" id="fltMsg" role="status"></span><button class="btn" type="button" id="fltCopy">Copiar tabela</button></footer>
  </div>
</div>

<div class="modal" id="pinDlg" hidden>""")
s = rep(s, '.rep-text{', """.flt-drop{display:flex;flex-direction:column;align-items:center;gap:4px;border:2px dashed var(--line);border-radius:10px;padding:18px;cursor:pointer;background:var(--panel2);text-align:center}
.flt-drop:hover,.flt-drop.over{border-color:var(--accent);background:var(--accent-soft)}
.flt-drop b{font-size:16px;color:var(--accent)} .flt-drop span{font-size:13px;color:var(--muted)}
.flt-in{width:100%;min-height:110px;resize:vertical;border:1px solid var(--line);border-radius:6px;background:var(--panel2);color:var(--ink);padding:8px 10px;font:12.5px/1.5 var(--f-mono);margin:8px 0}
.flt-raw summary{cursor:pointer;color:var(--muted);font-size:13px}
.flt-tools{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
#fltOut{min-height:24vh}
.d-flt{display:flex;flex-direction:column;gap:4px}
.d-fltrow{display:grid;grid-template-columns:62px 82px 86px minmax(0,1fr);gap:8px;align-items:center;font:500 13px/1.3 var(--f-mono);padding:4px 8px;border:1px solid var(--line);border-left:4px solid var(--line);border-radius:6px}
.d-fltrow.al{border-left-color:var(--kc,var(--c-red))}
.d-fltrow .a i{font-style:normal;font-weight:700;color:var(--kc,var(--t-red))} .d-fltrow .a code{font-size:12px;color:var(--muted)} .d-fltrow .ok{color:var(--muted)}
.grid td.c{position:relative}
.grid td.c .fpl{position:absolute;top:1px;right:1px;z-index:3;background:#fff;color:#0f1722;font:800 11px/16px var(--f-mono);border-radius:9px;padding:0 4px;min-width:16px;text-align:center;box-shadow:0 0 0 1.5px #0f1722,0 1px 3px #0008;pointer-events:none}
.d-tabs{display:flex;gap:6px;margin:0 0 10px}
.d-tabs button{border:1px solid var(--accent);background:none;color:var(--accent);border-radius:7px;padding:6px 12px;font-weight:600;font-size:13px;line-height:1;font-family:inherit;cursor:pointer}
.d-tabs button.on{background:var(--accent);color:#fff}
.fd-head{display:flex;align-items:center;gap:10px;margin:0 0 8px}.fd-head h3{margin:0;font-size:15px}.fd-head h3 span{color:var(--muted);font-weight:500}.fd-head .d-close{margin-left:auto}
.fd-cols{display:grid;grid-template-columns:minmax(0,1.15fr) minmax(0,1fr);gap:18px;align-items:start}
@media (max-width:1100px){.fd-cols{grid-template-columns:minmax(0,1fr)}}
.fd-h{margin:0 0 6px;font-size:11.5px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}
.fltab tbody tr{cursor:pointer}.fltab tbody tr:hover td{background:var(--panel2)}.fltab tbody tr.fsel td{background:color-mix(in srgb,var(--kc,var(--accent)) 18%,transparent)}.fltab tbody tr.fsel td:first-child{box-shadow:inset 4px 0 0 var(--kc,var(--accent))}
.fd-sw{font-size:12.5px;color:var(--muted);margin:0 0 8px}.fd-sw button{border:0;background:none;color:var(--accent);font:inherit;font-weight:600;cursor:pointer;padding:0;text-decoration:underline}
.fltab{font-size:13px;width:100%}.fltab td{vertical-align:middle;white-space:nowrap}.fltab td small{display:block;font-size:12px;color:var(--muted);margin-top:2px}.fltab td small b{color:var(--ink)}
.fchip{display:inline-block;background:var(--kc,var(--c-red));color:#fff;font-weight:700;font-size:11.5px;padding:1px 7px;border-radius:5px}
.fraw{font:13px/2.15 var(--f-mono)}
.fraw .dim{opacity:.45}
.fraw u{text-decoration:underline 3px var(--kc,var(--c-red));text-underline-offset:5px;font-weight:700}
.fraw .ftag{display:inline-block;font-weight:700;font-size:11px;line-height:16px;background:var(--kc,var(--c-red));color:#fff;border-radius:4px;padding:0 6px;margin:0 2px 0 4px;vertical-align:1px;font-family:var(--f-mono)}
.ftl2{display:grid;grid-template-columns:64px minmax(0,1fr);row-gap:5px;margin-top:14px;align-items:center}
.ftl-lab{font:700 12px/22px var(--f-mono);color:var(--kc,var(--muted));white-space:nowrap;overflow:hidden}
.ftl-trk{position:relative;height:24px;border-radius:4px;background-color:var(--panel2)}
.ftl-trk > span{position:absolute;box-sizing:border-box}
.ftl-ax{background:none;height:16px}.ftl-ax span{top:0;font:11px/16px var(--f-mono);color:var(--muted);transform:translateX(-50%)}.ftl-ax span:first-child{transform:none}
.ftl-seg{top:2px;height:20px;border-radius:3px;background:var(--kc);color:#fff;font:700 10.5px/20px var(--f-mono);padding:0 5px;overflow:hidden;white-space:nowrap}
.ftl-fy{top:10px;height:4px;border-radius:2px;background:var(--kc,#7d8da0)}
.ftl-fd{top:5px;width:3px;height:14px;border-radius:2px;background:var(--kc,#7d8da0)}
.ftl-fw{top:2px;height:20px;border:2px solid var(--kc,#7d8da0);border-radius:3px;background:color-mix(in srgb,var(--kc,#7d8da0) 40%,transparent)}
.ftl-ft{top:0;font:700 11px/24px var(--f-mono);color:var(--kc,var(--ink));white-space:nowrap}
.ftl-now{top:-2px;bottom:-2px;width:2px;background:var(--accent);z-index:2}
.rep-text{""")
s = rep(s, '  $("#grid").innerHTML = h + "</tbody>";', '  $("#grid").innerHTML = h + "</tbody>";\n  try { decorateFlights(slots); } catch(e){ console.error("Voos:", e); }')
s = rep(s, '  el.innerHTML = h;\n', '  el.innerHTML = h;\n  try { fltDock(r, slots); } catch(e){ console.error("Voos:", e); }\n')
s = rep(s, '  if (!r){ el.innerHTML = ""; el.classList.add("closed");', '  if (!r){ try { fltDock(null, slots); } catch(e){} el.innerHTML = ""; el.classList.add("closed");')
s = rep(s, '<div class="gridwrap" id="gridwrap"><table class="grid" id="grid"></table></div>', '<div class="gridwrap" id="gridwrap"><table class="grid" id="grid"></table></div>\n    <section class="fltdock" id="fltDock" hidden></section>')
s = rep(s, '@media (max-width:1100px){.d-resize{display:none}', '.fltdock{grid-row:2;grid-column:1;background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:0 16px 12px;min-width:0;height:var(--dock-h,380px);overflow:auto;position:relative}\n.fd-resize{position:sticky;top:0;z-index:4;height:12px;margin:0 -16px 2px;cursor:row-resize;display:flex;justify-content:center;align-items:center;background:var(--panel);touch-action:none}\n.fd-resize::before{content:"";width:44px;height:4px;border-radius:2px;background:var(--line)}\n.fd-resize:hover::before,.fd-resize.drag::before{background:var(--accent)}\nbody.resizing-v{cursor:row-resize;user-select:none}\n.layout:has(.fltdock:not([hidden])) .gridwrap{max-height:calc(100vh - 140px - var(--dock-h,380px));min-height:180px}\n.layout:has(.fltdock:not([hidden])) .detail,.layout:has(.fltdock:not([hidden])) .d-resize{grid-row:1 / span 2}\n.layout:has(.fltdock:not([hidden])){grid-template-rows:auto 1fr}.fltdock{align-self:start}\n@media (max-width:1100px){.fltdock{grid-column:auto;grid-row:auto;height:auto}.fd-resize{display:none}.layout:has(.fltdock:not([hidden])) .detail{grid-row:auto}.layout:has(.fltdock:not([hidden])) .gridwrap{max-height:calc(100vh - 230px)}}\n@media (max-width:1100px){.d-resize{display:none}')
FLT_JS = r"""/* ---------- Voos: PDF/texto da lista de voos cruzado com o TAF ---------- */
const IATA2ICAO = Object.fromEntries(Object.entries(AIRPORTS).map(([ic, v]) => [v[0], ic]));
const PDFJS_SRC = "../vendor/pdf.min.js", PDFJS_WORKER = "../vendor/pdf.worker.min.js";
const FLT_RESTR = new Set(["OUT OF LIM", "LDG NOT ALLOWED", "BELOW MIN", "LVO", "RVAC"]);
const FLT_KEY = {"LVO": "cig", "TS": "conv", "LOW CIG": "cig4", "WIND": "wind", "SNOW/ICE": "ice", "OUT OF LIM": "lim", "LDG NOT ALLOWED": "lim", "BELOW MIN": "bmin", "RVAC": "rvac", "WND NEAR LIM": "mar", "MIST": "obsc", "VA": "vis"};
function loadPdfJs(){
  if (window.pdfjsLib) return Promise.resolve(window.pdfjsLib);
  return new Promise((ok, ko) => { const sc = document.createElement("script"); sc.src = PDFJS_SRC; sc.onload = () => { window.pdfjsLib.GlobalWorkerOptions.workerSrc = PDFJS_WORKER; ok(window.pdfjsLib); }; sc.onerror = () => ko(new Error("não foi possível carregar o leitor de PDF")); document.head.appendChild(sc); });
}
/* texto do PDF linha a linha: junta os pedaços com a mesma altura na página, da esquerda para a direita */
async function pdfLines(file){
  const lib = await loadPdfJs();
  const doc = await lib.getDocument({data: await file.arrayBuffer()}).promise;
  const lines = [];
  for (let p = 1; p <= doc.numPages; p++){
    const tc = await (await doc.getPage(p)).getTextContent();
    const rows = [];
    for (const it of tc.items){
      if (!it.str || !it.str.trim()) continue;
      const y = it.transform[5], x = it.transform[4];
      let r = rows.find(q => Math.abs(q.y - y) < 2.5);
      if (!r){ r = {y, parts: []}; rows.push(r); }
      r.parts.push({x, t: it.str.trim()});
    }
    rows.sort((a, b) => b.y - a.y).forEach(r => lines.push(r.parts.sort((a, b) => a.x - b.x).map(q => q.t).join("   ")));
  }
  return lines;
}
/* cada linha com um voo TP: origem e destino (IATA ou ICAO da lista), STD, STA e, se houver, ETD e ETA (UTC) */
/* coordenadas dos aeroportos (OurAirports, domínio público) para estimar o tempo de voo */
const AP_COORD = {"BIKF":[63.99,-22.61],"CYHM":[43.17,-79.93],"CYHZ":[44.88,-63.51],"CYJT":[48.54,-58.55],"CYOW":[45.32,-75.67],"CYQX":[48.94,-54.57],"CYUL":[45.47,-73.74],"CYYR":[53.32,-60.43],"CYYT":[47.62,-52.75],"CYYZ":[43.68,-79.63],"DAAG":[36.69,3.21],"DAAT":[22.81,5.45],"DAUG":[32.38,3.79],"DFFD":[12.35,-1.51],"DGAA":[5.61,-0.17],"DIAP":[5.26,-3.93],"DNKN":[12.05,8.52],"DNMM":[6.58,3.32],"DRRN":[13.48,2.18],"DXXX":[6.17,1.25],"EBBR":[50.9,4.48],"EDDB":[52.36,13.5],"EDDF":[50.03,8.56],"EDDH":[53.63,9.99],"EDDL":[51.29,6.77],"EDDM":[48.35,11.79],"EDDS":[48.69,9.22],"EFHK":[60.32,24.96],"EGCC":[53.35,-2.28],"EGKK":[51.15,-0.19],"EGLL":[51.47,-0.46],"EGPH":[55.95,-3.37],"EHAM":[52.31,4.76],"EIDW":[53.43,-6.26],"EINN":[52.7,-8.92],"EKCH":[55.62,12.66],"ELLX":[49.63,6.21],"ENGM":[60.19,11.1],"EPWA":[52.17,20.97],"ESSA":[59.65,17.93],"FABL":[-29.09,26.3],"FALE":[-29.61,31.12],"FAOR":[-26.14,28.25],"FCBB":[-4.25,15.25],"FCPP":[-4.82,11.89],"FGSL":[3.76,8.71],"FKKD":[4.01,9.72],"FLKK":[-15.33,28.45],"FNBJ":[-9.05,13.5],"FNLU":[-8.86,13.23],"FOOL":[0.46,9.41],"FPST":[0.38,6.71],"FQMA":[-25.92,32.57],"FTTJ":[12.13,15.03],"FZAA":[-4.39,15.44],"FZQA":[-11.59,27.53],"GBYD":[13.34,-16.65],"GCLP":[27.93,-15.39],"GCTS":[28.04,-16.57],"GCXO":[28.48,-16.34],"GGOV":[11.89,-15.65],"GMAD":[30.32,-9.41],"GMFO":[34.79,-1.93],"GMML":[27.14,-13.22],"GMMN":[33.37,-7.59],"GMMX":[31.6,-8.04],"GOBD":[14.67,-17.07],"GUCY":[9.58,-13.61],"GVAC":[16.74,-22.95],"GVBA":[16.14,-22.89],"GVNP":[14.94,-23.48],"GVSV":[16.83,-25.06],"KBGR":[44.81,-68.83],"KBOS":[42.36,-71.01],"KCPR":[42.91,-106.46],"KDTW":[42.21,-83.35],"KEWR":[40.69,-74.17],"KFAR":[46.92,-96.82],"KIAD":[38.94,-77.46],"KJFK":[40.64,-73.78],"KLAS":[36.08,-115.15],"KLAX":[33.94,-118.41],"KMCO":[28.43,-81.31],"KMIA":[25.8,-80.29],"KMSP":[44.88,-93.22],"KOAK":[37.72,-122.22],"KORD":[41.98,-87.9],"KPHL":[39.87,-75.24],"KPSM":[43.08,-70.82],"KSFO":[37.62,-122.37],"KSJC":[37.36,-121.93],"KSLC":[40.79,-111.98],"KSMF":[38.7,-121.59],"LBSF":[42.7,23.42],"LCLK":[34.88,33.62],"LDZA":[45.74,16.07],"LEBB":[43.3,-2.91],"LEBL":[41.3,2.08],"LEMD":[40.49,-3.57],"LEMG":[36.68,-4.5],"LEVC":[39.49,-0.48],"LEVX":[42.23,-8.63],"LEZL":[37.42,-5.89],"LFBD":[44.83,-0.72],"LFBO":[43.63,1.36],"LFLL":[45.73,5.09],"LFML":[43.44,5.21],"LFMN":[43.66,7.22],"LFPG":[49.01,2.55],"LFPO":[48.73,2.36],"LGAV":[37.94,23.94],"LHBP":[47.43,19.26],"LIMC":[45.63,8.73],"LIPE":[44.54,11.29],"LIPZ":[45.51,12.35],"LIRF":[41.8,12.25],"LIRN":[40.89,14.29],"LIRQ":[43.81,11.2],"LJLJ":[46.22,14.46],"LKPR":[50.1,14.26],"LLBG":[32.01,34.89],"LOWW":[48.11,16.57],"LPAZ":[36.97,-25.17],"LPFR":[37.02,-7.97],"LPHR":[38.52,-28.72],"LPLA":[38.76,-27.09],"LPMA":[32.7,-16.77],"LPPD":[37.74,-25.7],"LPPR":[41.25,-8.68],"LPPS":[33.07,-16.35],"LPPT":[38.78,-9.14],"LROP":[44.57,26.1],"LSGG":[46.24,6.11],"LSZH":[47.46,8.55],"MDPC":[18.57,-68.36],"MDSD":[18.43,-69.67],"MMCZ":[20.51,-86.93],"MMMD":[20.93,-89.65],"MMUN":[21.04,-86.87],"MUHA":[22.99,-82.41],"MYNN":[25.04,-77.47],"SBBE":[-1.38,-48.48],"SBBR":[-15.87,-47.92],"SBCF":[-19.64,-43.97],"SBCT":[-25.53,-49.18],"SBFL":[-27.67,-48.55],"SBFZ":[-3.78,-38.53],"SBGL":[-22.81,-43.25],"SBGR":[-23.43,-46.47],"SBKP":[-23.01,-47.13],"SBMO":[-9.51,-35.79],"SBPA":[-29.99,-51.17],"SBRF":[-8.13,-34.92],"SBSG":[-5.77,-35.37],"SBSL":[-2.59,-44.24],"SBSV":[-12.91,-38.32],"SVMC":[10.56,-71.73],"SVMG":[10.91,-63.97],"SVMI":[10.6,-66.99],"SVVA":[10.15,-67.93],"TAPA":[17.14,-61.79],"TFFF":[14.59,-61.0],"TFFR":[16.27,-61.53],"TJSJ":[18.44,-66.0],"TNCA":[12.5,-70.01],"TNCC":[12.19,-68.96],"TXKF":[32.36,-64.68]};
/* tempo de voo (bloco) estimado pela distância: 43 min + distância / 453 kt; para oeste até +6 % (vento de frente) */
function blockMin(o, d){
  const A = AP_COORD[o], B = AP_COORD[d]; if (!A || !B) return null;
  const R = 3440.065, r = Math.PI / 180, p1 = A[0] * r, p2 = B[0] * r, dl = (B[1] - A[1]) * r, dp = p2 - p1;
  const nm = 2 * R * Math.asin(Math.sqrt(Math.sin(dp / 2) ** 2 + Math.cos(p1) * Math.cos(p2) * Math.sin(dl / 2) ** 2));
  const de = ((B[1] - A[1] + 540) % 360) - 180, f = 1 + 0.06 * Math.max(-1, Math.min(1, -de / 30));
  return Math.round(43 + nm * f / 7.55);
}
/* tempos de bloco partilhados (Excel "block_times": voo, DEP, DEST, BLOCK em minutos), carregados por um Administrador
   no Início e guardados nas definições do TAF do portal (Supabase, só utilizadores com sessão): valem para todos */
let fltBlkCache = null;
function fltBlocks(){
  const B = cfg && cfg.blocks;
  if (!B || !Array.isArray(B.rows)) return null;
  if (fltBlkCache && fltBlkCache.at === B.at) return fltBlkCache;
  const byKey = {}, byRoute = {}, byFl = {};
  for (const [fl, o, d, m] of B.rows){ if (!(m > 0)) continue; byKey[fl + "|" + o + "|" + d] = m; (byRoute[o + "|" + d] = byRoute[o + "|" + d] || []).push(m); (byFl[fl] = byFl[fl] || []).push(o + "→" + d); }
  for (const k in byRoute){ const L = byRoute[k].sort((a, b) => a - b); byRoute[k] = L[Math.floor(L.length / 2)]; }
  return fltBlkCache = {at: B.at, byKey, byRoute, byFl, n: B.rows.length, name: B.name || ""};
}
/* tempo de voo: 1) o do voo na tabela de tempos de bloco; 2) o da rota na tabela; 3) estimado pela distância */
function blockFor(fl, o, d){
  const T = fltBlocks(), oI = apIata(o), dI = apIata(d);
  if (T){
    /* só pela rota (origem e destino), sem olhar ao número do voo: vale para voos extra e renumerados;
       se a rota tiver vários voos na tabela, usa o tempo mediano dessa rota */
    if (T.byRoute[oI + "|" + dI]) return {min: T.byRoute[oI + "|" + dI], src: "tabela"};
    const m = blockMin(o, d);
    return {min: m, src: m != null ? "distância" : "", miss: {other: ""}};
  }
  const m = blockMin(o, d);
  return {min: m, src: m != null ? "distância" : ""};
}
const FLT_MON = {JAN: 0, FEB: 1, MAR: 2, APR: 3, MAY: 4, JUN: 5, JUL: 6, AUG: 7, SEP: 8, OCT: 9, NOV: 10, DEC: 11, FEV: 1, ABR: 3, MAI: 4, AGO: 7, SET: 8, OUT: 9, DEZ: 11};
/* data numa linha (22NOV, 22NOV26, 22/11, 22/11/2026, 2026-11-22): devolve o dia em UTC (ms) e o texto sem a data */
function fltDate(line){
  const now = new Date(), Y = now.getUTCFullYear();
  const fix = (dd, mm, yy) => { let y = yy == null ? Y : +yy < 100 ? 2000 + +yy : +yy; let t = Date.UTC(y, mm, dd); if (yy == null && t < Date.now() - 200 * 86400e3) t = Date.UTC(y + 1, mm, dd); if (yy == null && t > Date.now() + 200 * 86400e3) t = Date.UTC(y - 1, mm, dd); return t; };
  let m = /\b(\d{4})-(\d{2})-(\d{2})\b/.exec(line);
  if (m) return {day: Date.UTC(+m[1], +m[2] - 1, +m[3]), rest: line.replace(m[0], " ")};
  /* dd/mm ou dd/mm/aaaa; com pontos só com o ano (dd.mm.aaaa), para não confundir com horas como 10.30 */
  m = /\b(\d{1,2})\/(\d{1,2})(?:\/(\d{2,4}))?\b/.exec(line) || /\b(\d{1,2})\.(\d{1,2})\.(\d{2,4})\b/.exec(line);
  if (m && +m[1] >= 1 && +m[1] <= 31 && +m[2] >= 1 && +m[2] <= 12) return {day: fix(+m[1], +m[2] - 1, m[3]), rest: line.replace(m[0], " ")};
  m = /\b(\d{1,2})[\s-]?(JAN|FEB|FEV|MAR|APR|ABR|MAY|MAI|JUN|JUL|AUG|AGO|SEP|SET|OCT|OUT|NOV|DEC|DEZ)[A-Z]*[\s-]?(\d{2}(?:\d{2})?)?\b/i.exec(line);
  if (m && +m[1] >= 1 && +m[1] <= 31) return {day: fix(+m[1], FLT_MON[m[2].toUpperCase()], m[3]), rest: line.replace(m[0], " ")};
  return null;
}
function parseFlights(txt){
  const now = Date.now(), d = new Date(), day = Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate());
  const out = [], bad = [], outside = new Set(), seen = new Set();
  let curDay = null; /* data do cabeçalho (ex.: "Daily flight list 22NOV26"), para as linhas sem data */
  for (const raw of String(txt || "").split(/\r?\n/)){
    const line0 = raw.trim(); if (!line0) continue;
    const dt = fltDate(line0), line = dt ? dt.rest : line0;
    const fm = /\b(TP|TAP)\s*0*(\d{1,4}[A-Z]?)\b/i.exec(line);
    if (!fm){ if (dt) curDay = dt.day; continue; }
    const fDay = dt ? dt.day : curDay;
    const num = fm[2].replace(/[A-Z]$/i, "");
    const rest = (line.slice(0, fm.index) + " " + line.slice(fm.index + fm[0].length)).replace(new RegExp("(^|[^\\d:])0*" + num + "(?![\\d:])", "g"), "$1 ");
    const aps = [], unk = [];
    for (const t of rest.toUpperCase().split(/[^A-Z0-9]+/)){
      if (/^[A-Z]{4}$/.test(t) && AIRPORTS[t]) aps.push(t);
      else if (/^[A-Z]{3}$/.test(t) && IATA2ICAO[t]) aps.push(IATA2ICAO[t]);
      else if (/^[A-Z]{3}$/.test(t)) unk.push(t);
    }
    /* lista do sistema de operações: STD e ETD em dia-hora-minuto (220850 = dia 22 às 08:50Z; 220945E = ETD estimada).
       Não tem hora de chegada: a ETA é estimada pelo tempo de voo (distância) a partir da ETD ou, sem ETD, da STD. */
    const dhm = [...rest.matchAll(/(?:^|\s)(\d{2})([01]\d|2[0-3])([0-5]\d)(E?)(?=\s|$)/g)];
    if (dhm.length && aps.length >= 2){
      const base = new Date(curDay != null ? curDay : Date.now());
      const mk = m => { const dd = +m[1]; let t = Date.UTC(base.getUTCFullYear(), base.getUTCMonth(), dd, +m[2], +m[3]);
        if (t - now > 15 * 86400e3) t = Date.UTC(base.getUTCFullYear(), base.getUTCMonth() - 1, dd, +m[2], +m[3]);
        if (now - t > 15 * 86400e3) t = Date.UTC(base.getUTCFullYear(), base.getUTCMonth() + 1, dd, +m[2], +m[3]);
        return t; };
      const sM = dhm.find(m => !m[4]) || dhm[0], eM = dhm.find(m => m[4] && m !== sM);
      const fl = "TP" + fm[2].toUpperCase(), std = mk(sM), etd = eM ? mk(eM) : null, bk = blockFor(fl, aps[0], aps[1]), bm = bk.min;
      const key = fl + "|" + aps[0] + "|" + std; if (seen.has(key)) continue; seen.add(key);
      out.push({fl, org: aps[0], dst: aps[1], std, sta: null, etd, eta: bm != null ? (etd ?? std) + bm * 60000 : null, etaEst: true, block: bm, blockSrc: bk.src, miss: bk.miss || null});
      continue;
    }
    /* horas: primeiro as escritas com ":" (07:30); só sem essas se usam as de 4 algarismos (0730) */
    const tc = [...rest.matchAll(/(?:^|[^\d])([01]?\d|2[0-3]):([0-5]\d)(?:Z|UTC)?(?![\d])/g)].map(m => +m[1] * 60 + +m[2]);
    const times = tc.length >= 2 ? tc : [...rest.matchAll(/(?:^|[^\d])([01]\d|2[0-3])([0-5]\d)(?:Z|UTC)?(?![\d])/g)].map(m => +m[1] * 60 + +m[2]);
    const fl = "TP" + fm[2].toUpperCase();
    if (aps.length < 2 || times.length < 2){ if (aps.length === 1 && unk.length) outside.add(fl); else bad.push(line); continue; }
    const near = (min, ref) => { let t = day + min * 60000; while (t < ref - 12 * HOUR) t += 24 * HOUR; while (t > ref + 12 * HOUR) t -= 24 * HOUR; return t; };
    let std, sta;
    if (fDay != null){ std = fDay + times[0] * 60000; sta = fDay + times[1] * 60000; while (sta < std) sta += 24 * HOUR; }
    else {
      /* sem data: a chegada fica entre 6 h atrás e 18 h à frente (uma lista do dia carregada de manhã inclui os voos da madrugada seguinte) */
      sta = day + times[1] * 60000; while (sta < now - 6 * HOUR) sta += 24 * HOUR; while (sta >= now + 18 * HOUR) sta -= 24 * HOUR;
      std = near(times[0], sta); while (std > sta) std -= 24 * HOUR;
    }
    const etd = times.length >= 4 ? near(times[2], std) : null;
    const eta = times.length >= 4 ? near(times[3], sta) : times.length === 3 ? near(times[2], sta) : null;
    const key = fl + "|" + aps[0] + "|" + std; if (seen.has(key)) continue; seen.add(key);
    out.push({fl, org: aps[0], dst: aps[1], std, sta, etd, eta});
  }
  return {flights: out, bad, outside: [...outside]};
}
/* o alerta mais grave de um conjunto de alertas (mesmas regras do relatório) */
function alertOf(its){
  if (!its.length) return null;
  const best = its.map(it => ({name: repCatName(it), cond: repCond(it)})).sort((a, b) => repSev(a.name) - repSev(b.name))[0];
  const toks = its.filter(it => repCatName(it) === best.name).flatMap(it => repCond(it).split(/\s+\/\s+|\s+/)).filter(Boolean);
  let cond = toks[0] || best.cond;
  if (best.name === "LVO"){ let wr = Infinity;
    for (const t of toks){ const v = /^VIS(\d{4})$/.exec(t), c = /^(BKN|OVC|VV)(\d{3}|\/\/\/)/.exec(t);
      const r = v ? +v[1] / (cfg.vis || 850) : c ? (c[2] === "///" ? 0 : +c[2] * 100 / (cfg.cig || 250)) : null;
      if (r != null && r < wr){ wr = r; cond = t; } } }
  else if (best.name !== "TS") cond = [...new Set(toks)].slice(0, 2).join(" ");
  return {name: best.name, cond, full: repFullName(best.name, [cond]), toks};
}
/* o alerta mais grave nesse aeroporto a essa hora */
function alertsAt(all, icao, t){ return alertOf(all.filter(it => it.icao === icao && it.start <= t && t < it.end)); }
/* voos: conta o que o TAF tem entre a ETA e 1 h depois; intensidade (+/−) e MIST não contam como impacto */
const FLT_WIN = 60 * 60000, FLT_SKIP = new Set(["MIST", "INTENSITY"]);
function fltAlertWin(all, icao, a, b){
  const its = all.filter(it => it.icao === icao && it.start < b && it.end > a && !FLT_SKIP.has(repCatName(it)));
  const al = alertOf(its); if (!al) return null;
  const mine = its.filter(it => repCatName(it) === al.name);
  al.from = Math.max(a, Math.min(...mine.map(it => it.start)));
  al.to = Math.min(b, Math.max(...mine.map(it => it.end)));
  return al;
}
const hhmm = t => pad(new Date(t).getUTCHours()) + pad(new Date(t).getUTCMinutes());
/* voos por zona (Portugal, Europa, América do Norte, América do Sul, África) e, em cada zona, por hora de chegada */
const FLT_ZONE_ORDER = [0, 1, 3, 2, 4, 5];
const fltZone = ic => { const z = FLT_ZONE_ORDER.indexOf(repZone(ic)); return z < 0 ? 9 : z; };
/* hora dos voos com o dia (UTC): 24/1030Z */
const hm = t => t == null ? "" : pad(new Date(t).getUTCDate()) + "/" + pad(new Date(t).getUTCHours()) + pad(new Date(t).getUTCMinutes()) + "Z";
const hmE = (t, est) => t == null ? "" : (est ? "~" : "") + hm(t);
const apIata = ic => iataOf(ic) || ic;
const fltStore = {
  get(){ return store.get("tafmon.voos", null); },
  set(v){ try { if (v) store.set("tafmon.voos", v); else localStorage.removeItem("tafmon.voos"); } catch(e){} }
};
/* alertas de todos os aeroportos e de todas as categorias: o cruzamento dos voos não depende das escolhas do Relatório
   (destinos, cenários marcados, "só aeroportos visíveis na grelha") */
function allAlertItems(){
  const keepCats = repUI.cats, keepVis = repUI.onlyVis, keepDest = cfg.destIcao;
  const run = dest => { cfg.destIcao = dest; return reportItems().all || []; };
  try {
    repUI.cats = CATS.map(c => c.k); repUI.onlyVis = false;
    try { return run(""); }
    catch(e){
      /* se um aeroporto der erro, os outros continuam a contar */
      console.warn("Voos: erro nos alertas, a calcular aeroporto a aeroporto", e);
      const out = [];
      for (const ic of Object.keys(AIRPORTS)){ try { out.push(...run(ic)); } catch(e2){ console.warn("Voos: alertas de " + ic + " ignorados", e2); } }
      return out;
    }
  }
  finally { repUI.cats = keepCats; repUI.onlyVis = keepVis; cfg.destIcao = keepDest; }
}
function flightRows(txt){
  const P = parseFlights(txt);
  const all = allAlertItems();
  const rows = [];
  for (const f of P.flights){
    const tA = f.eta ?? f.sta;
    if (tA == null){ f.alert = null; continue; }
    f.landed = tA < Date.now();
    if (f.landed){ f.alert = null; continue; }   /* já aterrou: não conta */
    const a = fltAlertWin(all, f.dst, tA, tA + FLT_WIN);
    f.alert = a;
    if (a) rows.push({f, side: "CHEGADA", ap: f.dst, t: tA, est: !!f.etaEst, name: a.name, cond: a.cond, full: a.full, from: a.from, to: a.to});
  }
  rows.sort((x, y) => fltZone(x.ap) - fltZone(y.ap) || x.t - y.t || repSev(x.name) - repSev(y.name));
  return {P, rows, text: txt, all};
}
let fltCache = null;
const fltEtd = f => f.etd ?? f.std ?? null;
/* período em que um grupo do TAF pode estar em vigor (BECMG: desde o início até ao FM seguinte) */
function fltGroupSpan(T, g){
  const fms = T.groups.filter(x => x.type === "FM");
  const nextFm = t => { const n = fms.find(x => x.from > t); return n ? n.from : T.to; };
  if (g.type === "BASE") return [T.from, fms[0] ? fms[0].from : T.to];
  if (g.type === "FM") return [g.from, g.to ?? T.to];
  if (g.type === "BECMG") return [g.from, g.from != null ? nextFm(g.from) : null];
  return [g.from, g.to];
}
const fltTokMatch = (t, k) => { k = String(k).replace(/\+$/, ""); if (!k) return false; if (t === k) return true;
  const v = /^VIS(\d{4})$/.exec(k); if (v) return t === v[1]; return k.length >= 3 && /\d/.test(k) && /[A-Z]/.test(k) && t.includes(k); };
/* categoria de alerta de um token do TAF (a mesma cor que o painel lateral dá a esse token) */
function fltTokCat(T, g, t){ try { return rvacTok(T, g, t) || tokenCat(t, T.icao) || null; } catch(e){ return null; } }
/* TAF com o que afeta cada voo sublinhado e a etiqueta do voo e da hora */
function fltTafHtml(r, hit){
  const T = r.T; if (!T || T.error || !T.toks) return "";
  const marks = new Map(), tags = {};
  for (const f of hit){
    const a = f.alert, k = FLT_KEY[a.name] || "int", keys = a.toks || [];
    let last = -1;
    for (const g of T.groups){
      const [gs, ge] = fltGroupSpan(T, g); if (gs == null || ge == null || !(gs < a.to && ge > a.from)) continue;
      const idx = []; T.toks.forEach((tk, i) => { if (tk.g === g && tk.role === "el" && (keys.some(kk => fltTokMatch(tk.t, kk)) || fltTokCat(T, g, tk.t) === k)) idx.push(i); });
      if (!idx.length) continue;
      for (const i of idx) if (!marks.has(i)) marks.set(i, {k});
      let gEnd = idx[idx.length - 1]; while (gEnd + 1 < T.toks.length && T.toks[gEnd + 1].g === g && T.toks[gEnd + 1].role !== "kw") gEnd++;
      last = Math.max(last, gEnd);
    }
    if (last >= 0) (tags[last] = tags[last] || []).push({k, t: `${f.fl} ${hhmm(a.from)}–${hhmm(a.to)}Z`});
  }
  const used = new Set([...marks.keys()].map(i => T.toks[i].g));
  let h = "";
  T.toks.forEach((tk, i) => {
    const starts = tk.role === "kw" && tk.g && tk.g.type !== "BASE" && (tk.t.startsWith("FM") || tk.t === "BECMG" || tk.t.startsWith("PROB") || tk.t === "TEMPO");
    if (starts && i) h += "<br>";
    const m = marks.get(i), dim = used.size && tk.g && !used.has(tk.g), tg = tags[i] || [];
    const nx = marks.get(i + 1) && !tg.length && T.toks[i + 1].g === tk.g;
    let t = esc(tk.t);
    if (m) t = `<u class="k-${m.k}">${t}${nx ? " " : ""}</u>`;
    t += tg.map(x => `<span class="ftag k-${x.k}">${esc(x.t)}</span>`).join("");
    h += (dim ? `<span class="dim">${t}</span>` : t) + (m && nx ? "" : " ");
  });
  return `<h4 class="fd-h">TAF · a sublinhado o que afeta cada voo</h4><div class="raw fraw">${h}</div>`;
}
/* linha do tempo do aeroporto: alertas do TAF (com nome e horas) e, por voo, o voo no ar (ETD → ETA) e a hora seguinte à chegada */
function fltTimelineHtml(r, list, slots){
  if (!slots || !slots.length || !fltCache) return "";
  const N = slots.length, s0 = slots[0], s1 = s0 + N * HOUR, cl = t => Math.min(s1, Math.max(s0, t));
  const pc = t => (cl(t) - s0) / (s1 - s0) * 100, x = t => pc(t).toFixed(2) + "%", w = (a, b) => (pc(b) - pc(a)).toFixed(2) + "%";
  const its = (fltCache.all || []).filter(it => it.icao === r.icao && !FLT_SKIP.has(repCatName(it)));
  const segs = []; slots.forEach(t => { const a = alertOf(its.filter(it => it.start <= t && t < it.end)); const n = a ? a.name : "";
    const l = segs[segs.length - 1]; if (l && l.n === n) l.e = t + HOUR; else segs.push({n, k: a ? FLT_KEY[a.name] || "int" : "", s: t, e: t + HOUR}); });
  const grid = `background-image:repeating-linear-gradient(to right,var(--line) 0 1px,transparent 1px calc(100% / ${N / 3}))`;
  const now = Date.now() >= s0 && Date.now() < s1 ? `<span class="ftl-now" style="left:${x(Date.now())}"></span>` : "";
  let h = `<div class="ftl2"><div class="ftl-lab"></div><div class="ftl-trk ftl-ax">${slots.map((t, i) => i % 3 ? "" : `<span style="left:${x(t)}">${pad(new Date(t).getUTCHours())}Z</span>`).join("")}</div>`;
  h += `<div class="ftl-lab">TAF</div><div class="ftl-trk" style="${grid}">${segs.filter(g => g.k).map(g => `<span class="ftl-seg k-${g.k}" style="left:${x(g.s)};width:${w(g.s, g.e)}" title="${esc(g.n)} ${hhmm(g.s)}–${hhmm(g.e)}Z">${pc(g.e) - pc(g.s) > 9 ? esc(g.n) + " " + pad(new Date(g.s).getUTCHours()) + "–" + pad(new Date(g.e).getUTCHours()) + "Z" : ""}</span>`).join("")}${now}</div>`;
  for (const f of list){
    const tA = f.eta ?? f.sta, tD = fltEtd(f), k = f.alert ? "k-" + (FLT_KEY[f.alert.name] || "int") : "";
    if (tA + FLT_WIN <= s0 || (tD ?? tA) >= s1) continue;
    const txt = `ETA ${hhmm(tA)}Z${f.alert ? ` · ${f.alert.name} ${hhmm(f.alert.from)}–${hhmm(f.alert.to)}Z` : ""}`;
    const right = pc(tA + FLT_WIN) > 62;
    h += `<div class="ftl-lab ${k}">${esc(f.fl)}</div><div class="ftl-trk ${k}" style="${grid}">`
      + (tD != null ? `<span class="ftl-fy" style="left:${x(tD)};width:${w(tD, tA)}"></span>` + (tD >= s0 ? `<span class="ftl-fd" style="left:${x(tD)}"></span>` : "") : "")
      + `<span class="ftl-fw" style="left:${x(tA)};width:${w(tA, tA + FLT_WIN)}"></span>`
      + (right ? `<span class="ftl-ft" style="right:${(100 - pc(tD != null ? tD : tA)).toFixed(2)}%;padding-right:6px">${esc(txt)}</span>` : `<span class="ftl-ft" style="left:${x(tA + FLT_WIN)};padding-left:6px">${esc(txt)}</span>`)
      + now + `</div>`;
  }
  return h + `</div><p class="hint" style="margin:6px 0 0">TAF = alertas por hora · linha = voo no ar (ETD → ETA) · caixa = 1 h depois da chegada (o que conta para o alerta)${now ? " · linha azul = agora" : ""}.</p>`;
}
/* voo escolhido no quadro de baixo: o TAF e a linha do tempo mostram só esse voo ("todos" mostra todos) */
let fltSel = {icao: null, key: null};
const fltKey = f => f.fl + "|" + f.std;
function fltPaneHtml(r, list, hit, slots){
  const route = f => `${esc(apIata(f.org))}→${esc(apIata(f.dst))}`;
  if (fltSel.icao !== r.icao || (fltSel.key !== "*" && !hit.some(f => fltKey(f) === fltSel.key))) fltSel = {icao: r.icao, key: hit.length ? fltKey(hit[0]) : null};
  const shown = fltSel.key === "*" ? hit : hit.filter(f => fltKey(f) === fltSel.key), one = fltSel.key !== "*" ? shown[0] : null;
  let h = `<div class="fd-cols"><div class="fd-c">`;
  h += hit.length ? `<div class="gtabwrap"><table class="gtab fltab"><thead><tr><th>Voo</th><th>Rota</th><th>ETD → ETA</th><th>Afetado</th><th>Alerta</th><th>Condição</th></tr></thead><tbody>${hit.map(f => {
      const a = f.alert, tD = fltEtd(f);
      return `<tr class="k-${FLT_KEY[a.name] || "int"}${one && fltKey(f) === fltKey(one) ? " fsel" : ""}" data-fsel="${esc(fltKey(f))}" title="Ver só este voo no TAF e na linha do tempo"><td><b>${esc(f.fl)}</b></td><td>${route(f)}</td><td class="m">${tD != null ? hm(tD) + " → " : ""}<b>${hmE(f.eta ?? f.sta, f.etaEst)}</b></td><td class="m"><b>${hhmm(a.from)}–${hhmm(a.to)}Z</b></td><td><span class="fchip">${esc(a.full || a.name)}</span></td><td class="m">${esc(a.cond)}</td></tr>`;
    }).join("")}</tbody></table></div>` : `<p class="hint" style="margin:0">Nenhum voo com alerta à chegada (da ETA até 1 h depois).</p>`;
  const ok = list.filter(f => !f.alert);
  if (ok.length) h += `<details class="hint" style="margin:8px 0 0"><summary>Sem alerta à chegada (${ok.length})</summary>${ok.map(f => `<b>${esc(f.fl)}</b> ${route(f)} ${hmE(f.eta ?? f.sta, f.etaEst)}`).join(" · ")}</details>`;
  if (list.some(f => f.etaEst)) h += `<p class="hint" style="margin:6px 0 0">~ = ETA estimada: ETD (ou STD) + tempo de voo. Afetado = parte da hora seguinte à chegada em que o TAF tem o alerta.</p>`;
  const sw = hit.length > 1 ? `<div class="fd-sw">${one ? `A mostrar <b>${esc(one.fl)}</b> · <button type="button" data-fsel="*">ver todos (${hit.length})</button>` : `A mostrar todos · escolha um voo na tabela para ver só esse`}</div>` : "";
  return h + `</div><div class="fd-c">` + sw + fltTafHtml(r, shown) + fltTimelineHtml(r, shown, slots) + `</div></div>`;
}
/* por baixo da grelha: voos afetados do aeroporto selecionado (o painel lateral fica só com a meteorologia) */
/* quadro de baixo: fecha e muda de altura independentemente do painel lateral; fica com o aeroporto que mostrava
   quando o painel lateral é fechado; depois de fechado só volta a abrir ao escolher um aeroporto */
let fltDockIc = null, fltDockShut = null;
function fltDock(r, slots){
  const D = document.getElementById("fltDock"); if (!D) return;
  if (!r){ if (D.hidden || !fltDockIc) return; r = rowsCache.find(x => x.icao === fltDockIc); if (!r){ D.hidden = true; return; } }
  if (fltDockShut === r.icao){ D.hidden = true; return; }
  fltDockIc = r.icao;
  const C = fltCache;
  const list = r && C ? C.P.flights.filter(f => f.dst === r.icao && !f.landed && (f.eta ?? f.sta) != null).sort((a, b) => (a.eta ?? a.sta) - (b.eta ?? b.sta)) : [];
  const hit = list.filter(f => f.alert);
  if (!hit.length){ D.hidden = true; D.innerHTML = ""; return; }
  D.innerHTML = `<div class="fd-resize" id="fltDockResize" role="separator" aria-orientation="horizontal" aria-label="Arrastar para mudar a altura" title="Arraste para mudar a altura · duplo clique repõe"></div><div class="fd-head"><h3>Voos afetados · ${esc(r.icao)}${iataOf(r.icao) ? " / " + esc(iataOf(r.icao)) : ""} <span>(${hit.length})</span></h3><button type="button" class="d-close" id="fltDockClose" aria-label="Fechar voos afetados" title="Fechar">×</button></div>` + fltPaneHtml(r, list, hit, slots);
  D.hidden = false;
  D.querySelector("#fltDockClose").addEventListener("click", () => { D.hidden = true; fltDockShut = fltDockIc; });
  D.querySelectorAll("[data-fsel]").forEach(el => el.addEventListener("click", () => { fltSel = {icao: r.icao, key: el.dataset.fsel}; const sc = D.scrollTop; fltDock(r, slots); D.scrollTop = sc; }));
  const hd = D.querySelector("#fltDockResize"), lay = document.querySelector(".layout");
  const setH = h => { h = Math.round(Math.min(window.innerHeight * 0.8, Math.max(160, h))); lay.style.setProperty("--dock-h", h + "px"); return h; };
  let st = null;
  hd.addEventListener("pointerdown", e => { st = {y: e.clientY, h: D.getBoundingClientRect().height}; hd.setPointerCapture(e.pointerId); hd.classList.add("drag"); document.body.classList.add("resizing-v"); e.preventDefault(); });
  hd.addEventListener("pointermove", e => { if (st) ui.dockH = setH(st.h - (e.clientY - st.y)); });
  const end = () => { if (!st) return; st = null; hd.classList.remove("drag"); document.body.classList.remove("resizing-v"); saveUI(); };
  hd.addEventListener("pointerup", end); hd.addEventListener("pointercancel", end);
  hd.addEventListener("dblclick", () => { ui.dockH = null; lay.style.removeProperty("--dock-h"); saveUI(); });
}
try { if (ui.dockH) document.querySelector(".layout").style.setProperty("--dock-h", ui.dockH + "px"); } catch(e){}
/* escolher um aeroporto na grelha volta a permitir o quadro de baixo */
$("#grid").addEventListener("click", e => { if (e.target.closest("tr[data-icao]")) fltDockShut = null; }, true);
/* grelha: um ✈ na célula da hora em que o voo fica afetado (com o número de voos se houver mais de um);
   carregar abre o aeroporto: meteorologia ao lado e voos afetados por baixo da grelha */
let fltSlots = null;
function fltGridRows(slots){
  if (!fltCache || !slots || !slots.length) return;
  const s0 = slots[0], N = slots.length, by = {};
  fltCache.P.flights.forEach(f => {
    const a = f.alert; if (f.landed || !a) return;
    const k = Math.floor((a.from - s0) / HOUR); if (k < 0 || k >= N) return;
    ((by[f.dst] = by[f.dst] || {})[k] = by[f.dst][k] || []).push(f);
  });
  for (const [ic, K] of Object.entries(by)){
    const tr = document.querySelector(`#grid tr.row[data-icao="${ic}"]`); if (!tr) continue;
    for (const [k, L] of Object.entries(K)){
      const td = tr.querySelector(`td[data-k="${k}"]`); if (!td) continue;
      const tip = L.map(f => `${f.fl} ${apIata(f.org)}→${apIata(f.dst)} · ETA ${hmE(f.eta ?? f.sta, f.etaEst)} · afetado ${hhmm(f.alert.from)}–${hhmm(f.alert.to)}Z · ${f.alert.name} ${f.alert.cond}`).join("\n");
      td.insertAdjacentHTML("beforeend", `<span class="fpl">✈${L.length > 1 ? L.length : ""}</span>`);
      td.title = (td.title ? td.title + "\n" : "") + tip;
    }
  }
}
function decorateFlights(slots){
  if (slots) fltSlots = slots;
  const st = fltStore.get();
  fltCache = null;
  if (st && st.text){ try { fltCache = flightRows(st.text); } catch(e){ console.error("Voos:", e); postFlightsError("Erro ao analisar os voos: " + (e && e.message || e)); $("#fltInfo").textContent = "Erro ao analisar os voos: " + (e && e.message || e); return; } }
  try { fltGridRows(fltSlots); } catch(e){ console.error("Voos (grelha):", e); }
  postFlights(st);
  if (!$("#flights").hidden) renderFlights();
}
/* carregar num ✈ abre o aeroporto e mostra os voos afetados por baixo da grelha */
$("#grid").addEventListener("click", e => {
  const td = e.target.closest("td.c"); if (!td || !td.querySelector(".fpl")) return;
  setTimeout(() => { const D = document.getElementById("fltDock"); if (D && !D.hidden) D.scrollIntoView({block: "nearest", behavior: "smooth"}); }, 50);
});
function postFlights(st){
  try {
    if (window.parent === window) return;
    const C = fltCache, fl = new Map();
    if (C) C.rows.forEach(r => { const k = r.f.fl + "|" + r.f.std, w = FLT_RESTR.has(r.name) ? 2 : 1; fl.set(k, Math.max(fl.get(k) || 0, w)); });
    window.parent.postMessage({type: "taf-flights", has: !!(st && st.text), name: (st && st.name) || "", at: (st && st.at) || null,
      total: C ? C.P.flights.length : 0, restr: [...fl.values()].filter(v => v === 2).length, alert: [...fl.values()].filter(v => v === 1).length,
      blocks: (fltBlocks() || {}).n || 0,
      missing: C && fltBlocks() ? C.P.flights.filter(f => f.miss).map(f => ({fl: f.fl, org: apIata(f.org), dst: apIata(f.dst), other: f.miss.other})) : [], blkSrc: C ? C.P.flights.reduce((o, f) => { if (f.blockSrc) o[f.blockSrc] = (o[f.blockSrc] || 0) + 1; return o; }, {}) : {},
      outside: C ? C.P.outside : [], bad: C ? C.P.bad.length : 0, landed: C ? C.P.flights.filter(f => f.landed).length : 0,
      rows: C ? C.rows.map(r => ({fl: r.f.fl, org: apIata(r.f.org), dst: apIata(r.f.dst), side: r.side, t: r.t, est: !!r.est, icao: r.ap, zone: REP_ZONE_NAME[repZone(r.ap)] || "", name: r.name, full: r.full, cond: r.cond, restr: FLT_RESTR.has(r.name)})) : []}, location.origin);
  } catch(e){}
}
let fltLast = null;
function renderFlights(){
  const st = fltStore.get();
  if (st && st.text && !$("#fltIn").value) $("#fltIn").value = st.text;
  const {P, rows} = fltCache || {P: {flights: [], bad: [], outside: []}, rows: []};
  const nAff = new Set(rows.map(r => r.f.fl + r.f.std)).size;
  const parts = [];
  if (st && st.name) parts.push(esc(st.name) + (st.at ? " · carregado às " + hm(st.at) : ""));
  if (P.flights.length) parts.push(`${P.flights.length} voos lidos · ${P.flights.filter(f => f.landed).length} já aterraram · <b>${nAff} afetados</b>`);
  if (P.outside.length) parts.push(`fora da lista do TAF: ${esc(P.outside.join(", "))}`);
  { const mi = P.flights.filter(f => f.miss); if (mi.length) parts.push(`<span style="color:#b26a00;font-weight:700">⚠ ${mi.length} ${mi.length === 1 ? "voo com rota que não está" : "voos com rotas que não estão"} na tabela de tempos de bloco (ETA pela distância): ${mi.map(f => esc(f.fl + " " + apIata(f.org) + "→" + apIata(f.dst))).join(", ")}</span>`); }
  if (P.bad.length) parts.push(`${P.bad.length} linhas com voo não reconhecidas`);
  $("#fltInfo").innerHTML = parts.join(" · ");
  const COLS = ["VOO", "ROTA", "STD", "STA", "ETD", "ETA", "ONDE", "CONDIÇÃO", "ALERTA"];
  const th = h => `<th style="border:1px solid #999;background:#e8e8e8;padding:3px 8px;text-align:left">${esc(h)}</th>`;
  const td = (c, sty) => `<td style="border:1px solid #999;padding:3px 8px;white-space:nowrap${sty || ""}">${esc(c)}</td>`;
  const zs = rows.slice().sort((x, y) => fltZone(x.ap) - fltZone(y.ap) || x.t - y.t || repSev(x.name) - repSev(y.name));
  let html;
  if (zs.length){
    html = `<table style="border-collapse:collapse;font-family:Calibri,Arial,sans-serif;font-size:10.5pt"><tr>${COLS.map(th).join("")}</tr>` + zs.map((r, k) => {
      const z = repZone(r.ap), zh = k === 0 || repZone(zs[k - 1].ap) !== z ? `<tr><td colspan="${COLS.length}" style="border:1px solid #999;background:#d9e7f2;padding:3px 8px;font-weight:bold">${REP_ZONE_NAME[z]}</td></tr>` : "";
      const f = r.f;
      return zh + `<tr>${td(f.fl, ";font-weight:bold")}${td(apIata(f.org) + "→" + apIata(f.dst))}${td(hm(f.std))}${td(hm(f.sta))}${td(hm(f.etd))}${td(hmE(f.eta, f.etaEst), ";font-weight:bold")}${td(r.side + " " + apIata(r.ap))}${td(r.cond, ";font-family:Consolas,monospace")}${td(r.full, ";font-weight:bold")}</tr>`;
    }).join("") + `</table>`;
  } else html = P.flights.length ? `<p style="margin:0">Nenhum voo afetado pelos alertas atuais.</p>` : `<p class="hint" style="margin:0">Carregue o PDF da lista de voos.</p>`;
  $("#fltOut").innerHTML = html;
  $("#fltAll").innerHTML = P.flights.length ? `<table style="border-collapse:collapse;font-size:10.5pt"><tr>${["VOO", "ROTA", "STD", "STA", "ETD", "ETA", "DESTINO À CHEGADA"].map(th).join("")}</tr>` +
    P.flights.slice().sort((a, b) => (a.eta ?? a.sta) - (b.eta ?? b.sta)).map(f => `<tr>${td(f.fl, ";font-weight:bold")}${td(apIata(f.org) + "→" + apIata(f.dst))}${td(fmtDHZ(f.std))}${td(f.sta ? fmtDHZ(f.sta) : "")}${td(f.etd ? fmtDHZ(f.etd) : "")}${td(f.eta ? (f.etaEst ? "~" : "") + fmtDHZ(f.eta) + (f.etaEst && f.block ? " (voo " + Math.floor(f.block / 60) + "h" + pad(f.block % 60) + " · " + (f.blockSrc || "") + ")" : "") : f.etaEst ? "sem estimativa" : "")}${td(f.landed ? "já aterrou" : f.alert ? f.alert.full + " · " + f.alert.cond : "sem alerta", f.alert ? ";font-weight:bold" : f.landed ? ";color:#888" : "")}</tr>`).join("") + `</table>` +
    (P.flights.some(f => f.etaEst) ? `<p class="hint" style="margin:6px 0 0">~ = ETA estimada: ETD (ou STD) + tempo de voo (da tabela de tempos de bloco partilhada, pela rota origem→destino; rota que não está na tabela: pela distância). O alerta no destino conta da ETA até 1 h depois (intensidade e MIST não contam).</p>` : "") : `<p class="hint" style="margin:0">Nenhum voo lido.</p>`;
  fltLast = zs.length ? {html: `<html><head><meta charset="utf-8"></head><body><!--StartFragment-->${html}<p style="margin:0">&nbsp;</p><!--EndFragment--></body></html>`,
    text: zs.map(r => [r.f.fl, apIata(r.f.org) + "-" + apIata(r.f.dst), hm(r.f.std), hm(r.f.sta), hm(r.f.etd), hmE(r.f.eta, r.f.etaEst), r.side + " " + apIata(r.ap), r.cond, r.full].join("\t")).join("\n")} : null;
}
async function fltLoadFile(file){
  if (!file) return;
  $("#fltInfo").textContent = "A ler " + file.name + "…";
  try {
    const lines = await pdfLines(file);
    if (!lines.some(l => /\S/.test(l))){ $("#fltInfo").textContent = "Este PDF não tem texto (parece uma imagem digitalizada)."; postFlightsError("Este PDF não tem texto (parece uma imagem digitalizada)."); return; }
    $("#fltIn").value = lines.join("\n");
    fltStore.set({text: $("#fltIn").value, name: file.name, at: Date.now()});
    try { render(); } catch(e){ console.error("Voos:", e); postFlights(fltStore.get()); }
  } catch(e){ $("#fltInfo").textContent = "Não foi possível ler o PDF: " + e.message; postFlightsError("Não foi possível ler o PDF: " + e.message); }
}
function postFlightsError(msg){ try { if (window.parent !== window) window.parent.postMessage({type: "taf-flights-error", error: msg}, location.origin); } catch(e){} }
function openFlights(){ renderFlights(); $("#fltMsg").textContent = ""; $("#flights").hidden = false; }
$("#btnFlights").addEventListener("click", openFlights);
$("#fltClose").addEventListener("click", () => { $("#flights").hidden = true; $("#btnFlights").focus(); });
$("#flights").addEventListener("click", e => { if (e.target.id === "flights") $("#flights").hidden = true; });
document.addEventListener("keydown", e => { if (e.key === "Escape" && !$("#flights").hidden){ e.stopImmediatePropagation(); $("#flights").hidden = true; } }, true);
$("#fltFile").addEventListener("change", e => { fltLoadFile(e.target.files[0]); e.target.value = ""; });
const fltDropEl = $("#fltDrop");
["dragenter", "dragover"].forEach(ev => fltDropEl.addEventListener(ev, e => { e.preventDefault(); fltDropEl.classList.add("over"); }));
["dragleave", "drop"].forEach(ev => fltDropEl.addEventListener(ev, e => { e.preventDefault(); fltDropEl.classList.remove("over"); }));
fltDropEl.addEventListener("drop", e => fltLoadFile(e.dataTransfer.files[0]));
$("#fltGo").addEventListener("click", () => { const v = $("#fltIn").value; fltStore.set(v.trim() ? {text: v, name: (fltStore.get() || {}).name || "lista colada", at: Date.now()} : null); render(); });
$("#fltClear").addEventListener("click", () => { fltStore.set(null); $("#fltIn").value = ""; render(); renderFlights(); });
$("#fltCopy").addEventListener("click", () => {
  if (!fltLast){ $("#fltMsg").textContent = "Não há voos afetados para copiar."; return; }
  let done = false;
  const onCopy = e => { try { e.clipboardData.setData("text/html", fltLast.html); e.clipboardData.setData("text/plain", fltLast.text); e.preventDefault(); done = true; } catch(err){} };
  document.addEventListener("copy", onCopy, true); try { document.execCommand("copy"); } catch(err){} document.removeEventListener("copy", onCopy, true);
  $("#fltMsg").textContent = done ? "Tabela copiada." : "Selecione a tabela e carregue em Ctrl+C.";
});
/* pedidos do Início: PDF arrastado para o cartão "Voos afetados", abrir a janela, limpar */
window.addEventListener("message", e => {
  if (e.origin !== location.origin || !e.data) return;
  const d = e.data;
  if (d.type === "taf-flights-file" && d.file) fltLoadFile(d.file);
  else if (d.type === "taf-flights-open") openFlights();
  else if (d.type === "taf-flights-clear"){ fltStore.set(null); $("#fltIn").value = ""; render(); }

});
/* outro separador ou janela mudou a lista: atualizar */
window.addEventListener("storage", e => { if (e.key === "tafmon.voos"){ $("#fltIn").value = ""; render(); } });
function closeReport(){"""
s = rep(s, 'function closeReport(){', FLT_JS)

# 3j) Relatório: com uma lista de voos carregada, coluna VOOS na mesma linha do aeroporto (voos por aterrar cuja
#     chegada cai no período do alerta; conta da ETA até 1 h depois)
s = rep(s, 'const REP_COLS = ["AEROPORTO", "PERÍODO (UTC)", "CONDIÇÃO", "ALERTA"];\nconst repCells = r => [icIata(r.icao), r.per, r.cond, r.full];',
        """const REP_COLS_BASE = ["AEROPORTO", "PERÍODO (UTC)", "CONDIÇÃO", "ALERTA"];
let REP_COLS = REP_COLS_BASE;
const repCells = r => { const c = [icIata(r.icao), r.per, r.cond, r.full]; if (REP_COLS.length > 4) c.push(repFlights(r)); return c; };
function fltData(){
  const st = fltStore.get(); if (!st || !st.text) return null;
  let C = fltCache; if (!C || C.text !== st.text){ try { C = flightRows(st.text); } catch(e){ return null; } }
  return C;
}
/* voos que chegam a este aeroporto quando há alerta: conta se a faixa horária do voo (chegada; com ETA estimada,
   da ETA até 1 h depois) apanhar o período do alerta dentro do turno, das 24 H ou da faixa Personalizada.
   Só o número do voo, 4 por linha dentro da célula. */
function repFlights(r){
  const C = fltData(); if (!C) return "";
  return C.P.flights.filter(f => f.dst === r.icao && !f.landed && (f.eta ?? f.sta) != null)
    .map(f => ({f, t: f.eta ?? f.sta}))
    .filter(x => (r.wins || []).some(w => x.t < w.e && x.t + FLT_WIN > w.s))
    .sort((a, b) => a.t - b.t)
    .map(x => x.f.fl).filter((v, k, A) => A.indexOf(v) === k)
    .reduce((L, fl, k) => { if (k % 4 === 0) L.push([]); L[L.length - 1].push(fl); return L; }, []).map(g => g.join(", ")).join("\\n");
}""")
s = rep(s, "function reportText(){", "function reportText(){\n  { const C = fltData(); REP_COLS = C && C.P.flights.length ? REP_COLS_BASE.concat([\"VOOS\"]) : REP_COLS_BASE; }")

# 4) mensagens do portal: abrir aeroporto, atualizar, tipo de acesso
main_end = '\nload();\n</script>'
s = rep(s, main_end,
        '\nwindow.addEventListener("message", e => {\n'
        '  if (e.origin !== location.origin || !e.data) return;\n'
        '  const d = e.data;\n'
        '  if (d.type === "taf-select" && d.icao){\n'
        '    let tr = document.querySelector(`#grid tr[data-icao="${d.icao}"]`);\n'
        '    if (!tr){ ui.filter = "all"; ui.area = ""; ui.list = ""; ui.cat = ""; ui.q = ""; saveUI(); render(); tr = document.querySelector(`#grid tr[data-icao="${d.icao}"]`); }\n'
        '    if (tr){ tr.click(); tr.scrollIntoView({block: "center"}); }\n'
        '  } else if (d.type === "taf-favs"){\n'
        '    window.__portalFavs = d.list || []; render();\n'
        '  } else if (d.type === "taf-filter"){\n'
        '    ui.filter = d.f || "all"; ui.list = d.list || ""; ui.area = ""; ui.cat = ""; ui.q = ""; saveUI(); render();\n'
        '    const g = document.querySelector("#grid"); if (g) g.scrollIntoView({block: "start"});\n'
        '  } else if (d.type === "taf-refresh") load();\n'
        '  else if (d.type === "taf-role"){\n'
        '    isAdmin = d.role === "admin";\n'
        '    cfg = portalCfg();\n'
        '    if (!isAdmin) dlg.hidden = true;\n'
        '    paintLock(); load();\n'
        '  } else if (d.type === "taf-cfg"){\n'
        '    window.__portalTafCfg = d.cfg || null; window.__portalTafMeta = d.meta || null;\n'
        '    if (dlg.hidden){ cfg = portalCfg(); load(); }\n'
        '  } else if (d.type === "taf-cfg-saved" && !d.ok){\n'
        '    cfg = portalCfg(); load();\n'
        '    setTimeout(() => { const b = $("#banner"); b.innerHTML = "<b>As definições não foram guardadas.</b> <span>" + esc(d.error || "Erro desconhecido") + "</span>"; b.className = "banner err"; b.hidden = false; }, 300);\n'
        '  }\n'
        '});\n'
        '$("#detail").addEventListener("click", e => { if (!e.target.closest("[data-prevtog]")) return; e.stopPropagation(); store.set("tafmon.showprev", !showPrev()); const t0 = Math.floor(Date.now() / HOUR) * HOUR; renderDetail(Array.from({length: +cfg.hours || 30}, (_, k) => t0 + k * HOUR)); }, true);\n'
        '/* estrela de favorito na grelha: não abre o painel, avisa o portal */\n'
        '$("#grid").addEventListener("click", e => { const st = e.target.closest(".tfav"); if (!st) return; e.stopPropagation(); e.preventDefault(); const ic = st.dataset.fav; window.parent.postMessage({type: "taf-fav", icao: ic, on: !isFavAp(ic)}, location.origin); }, true);\n'
        '$("#grid").addEventListener("keydown", e => { const st = e.target.closest && e.target.closest(".tfav"); if (st && (e.key === "Enter" || e.key === " ")){ e.preventDefault(); e.stopPropagation(); st.click(); } }, true);\n'
        'load();\n</script>')

# 5) o código do monitor só arranca depois de verificado o acesso
i = s.index('<script>\n', s.index('<main'))
j = s.index('</script>', i)
main_code = s[i + len('<script>\n'):j]
s = s[:i] + '<script type="text/plain" id="tafMain">\n' + main_code + '</script>\n' + s[j + len('</script>'):]

# 6) sem service worker próprio (o do portal guarda esta página)
s = re.sub(r'<script>\s*/\* instalar como aplicação \(Android/Chrome\) \*/.*?</script>\s*', '', s, flags=re.S)

# 7) verificação de acesso
gate = r'''<script>
/* Portal Operational Control: o TAF só abre dentro do portal, com sessão iniciada e conta aprovada. */
(function(){
  if (window.top === window){ location.replace("../#taf"); return; }
  var tries = 0;
  (function wait(){
    var P = null;
    try { P = window.parent.__portal; } catch(e){}
    if (P && P.role && P.cfgReady){
      window.__portalRole = P.role; window.__portalTafCfg = P.cfg || null; window.__portalTafMeta = P.meta || null; window.__portalFavs = P.favs || [];
      var x = document.createElement("script");
      x.textContent = document.getElementById("tafMain").textContent;
      document.documentElement.classList.remove("gate");
      document.body.appendChild(x);
      return;
    }
    if (++tries > 300){ document.body.innerHTML = '<p style="padding:24px;font-family:system-ui,sans-serif">Abre o TAF a partir do portal, com sessão iniciada.</p>'; document.documentElement.classList.remove("gate"); return; }
    setTimeout(wait, 100);
  })();
})();
</script>
'''

# 3k. TAF em janela (Início): o TAF com destaque do painel passa a ser uma função reutilizável (tafRawHtml)
#     e o TAF Monitor responde a pedidos "taf-popup" do portal com o TAF do aeroporto, janelas de alerta e a condição sublinhada
_i = s.index('    // TAF com destaque\n'); _j = s.index('    if (open) raw += "</span>";\n', _i) + len('    if (open) raw += "</span>";\n')
_block = s[_i:_j]
s = s[:_i] + '    let raw = tafRawHtml(T);\n    const TP = tafChanged[T.icao] && tafChanged[T.icao].prevRaw;\n' + s[_j:]
_fn = 'function tafRawHtml(T){\n' + _block.replace('    // TAF com destaque\n', '') + '  return raw;\n}\n' + r"""
/* cor de uma categoria de alerta (a mesma da grelha), para as bolas do Início */
function catColor(k){
  if (!k) return null; const C = catColor.c = catColor.c || {}; if (k in C) return C[k];
  const e = document.createElement("span"); e.className = "k-" + k; e.style.display = "none"; document.body.appendChild(e);
  const v = getComputedStyle(e).getPropertyValue("--kc").trim() || null; e.remove(); return C[k] = v;
}
/* a condição mais penalizante que o TAF prevê (alertas a vermelho em todo o período mostrado) */
/* gravidade de uma categoria: a mesma ordem do relatório (limites/abaixo dos mínimos, LVO, trovoada, teto baixo/RVAC, neve/gelo, vento…) */
const catSev = k => k === "lim" ? 0 : repSev(REP_CAT_NAME[k] || "");
const worstOf = ks => ks.slice().sort((x, y) => catSev(x) - catSev(y) || catRank(x) - catRank(y))[0] || null;
function worstCat(r){ return worstOf([...new Set((r.res || []).filter(x => x.level === "red").flatMap(x => x.hard || []).map(h => catOfCode(h.code)))]); }
function worstCatColor(r){ return catColor(worstCat(r)); }
function worstCatRank(r){ const k = worstCat(r); return k ? catSev(k) : 99; }
/* TAF de um aeroporto para a janela do Início: cores dos alertas passadas para estilos (o portal não tem as classes) */
function tafPopupHtml(icao){
  const r = rowsCache.find(x => x.icao === icao);
  if (!r || !r.T) return {title: icao, html: `<p class="muted">Sem TAF para ${esc(icao)}.</p>`};
  const T = r.T;
  let h = `<div class="tp-meta">${nameOf(icao) ? `<b>${esc(nameOf(icao))}</b> · ` : ""}${esc(r.region || "")}${T.issue ? ` · emitido ${fmtDHZ(T.issue)}` : ""}${T.amd ? ` · <b>AMD</b>` : ""}${r.isNew ? ` · <b>${T.amd ? "emendado" : "novo"}</b>` : ""}</div>`;
  if (T.error) h += `<p class="muted">Não foi possível analisar: ${esc(T.error)}.</p><div class="tp-raw">${esc(T.raw)}</div>`;
  else {
    h += `<div class="tp-raw">${tafRawHtml(T)}</div>`;
  }
  const box = document.createElement("div"); box.style.cssText = "position:absolute;left:-9999px;top:0;visibility:hidden"; box.innerHTML = h; document.body.appendChild(box);
  box.querySelectorAll('[class*="k-"]').forEach(el => { const c = getComputedStyle(el).getPropertyValue("--kc").trim(); if (c) el.style.setProperty("--kc", c); });
  const html = box.innerHTML; box.remove();
  return {title: icao + (iataOf(icao) ? " / " + iataOf(icao) : ""), html};
}
"""
s = rep(s, 'function closeReport(){', _fn + 'function closeReport(){')
s = rep(s, '  } else if (d.type === "taf-favs"){\n', '  } else if (d.type === "taf-popup" && d.icao){\n    const P = tafPopupHtml(d.icao);\n    try { window.parent.postMessage({type: "taf-popup", icao: d.icao, title: P.title, html: P.html}, location.origin); } catch(e){}\n  } else if (d.type === "taf-favs"){\n')


# 3l. tabela do relatório (cópia para Word/Outlook/Teams): largura fixa da página, colunas com larguras definidas,
#     a linha da zona ocupa todas as colunas e os voos quebram linha dentro da coluna VOOS
s = rep(s, '? `<table style="border-collapse:collapse;font-size:10.5pt"><tr>${REP_COLS.map(h => `<th style="border:1px solid #999;background:#e8e8e8;padding:3px 8px;text-align:left">${esc(h)}</th>`).join("")}</tr>` +',
  '? `<table style="border-collapse:collapse;font-size:10.5pt;width:680px;table-layout:fixed">${repColgroup()}<tr>${REP_COLS.map(h => `<th style="border:1px solid #999;background:#e8e8e8;padding:3px 6px;text-align:left;vertical-align:bottom">${esc(h)}</th>`).join("")}</tr>` +')
s = rep(s, '`<tr><td colspan="4" style="border:1px solid #999;background:#d9e7f2;padding:3px 8px;font-weight:bold">${REP_ZONE_NAME[z]}</td></tr>`',
  '`<tr><td colspan="${REP_COLS.length}" style="border:1px solid #999;background:#d9e7f2;padding:3px 6px;font-weight:bold">${REP_ZONE_NAME[z]}</td></tr>`')
s = rep(s, '`<td style="border:1px solid #999;padding:3px 8px;white-space:nowrap${i === 1 || i === 3 ? ";font-weight:bold" : ""}${i === 2 ? ";font-family:Consolas,monospace" : ""};vertical-align:top">${esc(c).replace(/\\n/g, "<br>")}</td>`',
  '`<td style="border:1px solid #999;padding:3px 6px;${i <= 1 ? "white-space:nowrap" : "word-wrap:break-word"}${i === 1 || i === 3 ? ";font-weight:bold" : ""}${i === 2 ? ";font-family:Consolas,monospace;font-size:10pt" : ""}${i === 4 ? ";font-size:9.5pt" : ""};vertical-align:top">${i === 4 ? esc(c).replace(/\\n/g, ", ") : esc(c).replace(/\\n/g, "<br>")}</td>`')
s = rep(s, 'function reportText(){', """/* larguras das colunas da tabela copiada (total 680 px, a largura útil de uma página A4) */
function repColgroup(){
  const W = REP_COLS.length > 4 ? [92, 84, 170, 170, 164] : [110, 100, 235, 235];
  return `<colgroup>${W.map(w => `<col style="width:${w}px" width="${w}">`).join("")}</colgroup>`;
}
function reportText(){""")


# 3m. intensidade fraca no relatório: LIGHT (ex.: LIGHT RAIN AND SNOW) em vez de LOW
s = rep(s, 'const inten = m[1] === "-" ? "LOW" : m[1] === "+" ? "HEAVY" : "";', 'const inten = m[1] === "-" ? "LIGHT" : m[1] === "+" ? "HEAVY" : "";')


# 3n. filtro "✈ Com voos": só os aeroportos com voos afetados (os do ✈ na grelha)
s = rep(s, '      <button type="button" data-f="now">Alerta agora</button>\n', '      <button type="button" data-f="now">Alerta agora</button>\n      <button type="button" data-f="flt" id="fFlt" hidden title="Só aeroportos com voos afetados (✈)">✈ Com voos</button>\n')
s = rep(s, '    if (ui.filter === "new") return r.isNew;\n', '    if (ui.filter === "new") return r.isNew;\n    if (ui.filter === "flt") return fltIcaos().has(r.icao);\n')
s = rep(s, 'function decorateFlights(slots){', """/* aeroportos com voos afetados (da última análise dos voos) */
let fltFilterKey = "";
function fltIcaos(){ return new Set(fltCache ? fltCache.P.flights.filter(f => f.alert && !f.landed).map(f => f.dst) : []); }
function decorateFlights(slots){""")
s = rep(s, '  try { fltGridRows(fltSlots); } catch(e){ console.error("Voos (grelha):", e); }\n', """  try { fltGridRows(fltSlots); } catch(e){ console.error("Voos (grelha):", e); }
  { const set = fltIcaos(), b = document.getElementById("fFlt");
    if (b){ b.hidden = !fltCache; b.textContent = `✈ Com voos (${set.size})`; }
    if (!fltCache && ui.filter === "flt"){ ui.filter = "all"; saveUI(); setTimeout(render, 0); }
    const key = [...set].sort().join(",");
    if (ui.filter === "flt" && key !== fltFilterKey){ fltFilterKey = key; setTimeout(render, 0); } else fltFilterKey = key; }
""")


# 3o. mínimos de aproximação das cartas Lido (definições partilhadas: cfg.minima, carregados por um Administrador)
#     por pista: melhor aproximação (sem LPV) -> BELOW MIN abaixo de DH/RVR; ILS CAT I + 200 ft / + 1000 m -> RVAC
s = rep(s, 'function render(){\n', 'function render(){\n  try { applyMinima(); } catch(e){ console.error("Mínimos:", e); }\n')
_pistas = '    h += `<div class="d-sec"><h3>Pistas</h3><div class="rwys">${RW.map(x => `<span class="rwy"><b>${esc(x[0])}</b>${x[1] ? ` ${x[1]} m` : ""}</span>`).join("")}</div>`;\n'
s = rep(s, _pistas, _pistas + '    try { h += minimaHtml(r.icao); } catch(e){}\n')
s = rep(s, 'function closeReport(){', open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'minima.js'), encoding='utf-8').read() + 'function closeReport(){')
s = rep(s, ".fltab{font-size:13px;width:100%}", ".minima{margin-top:10px}.mintab{font-size:12.5px;width:100%}.mintab td{vertical-align:top}.mintab td small{display:block;color:var(--muted);font-size:11.5px;margin-top:1px}\n.fltab{font-size:13px;width:100%}")

k = s.rindex('</body>')
s = s[:k] + gate + s[k:]

out = os.path.join(ROOT, 'taf', 'index.html')
open(out, 'w', encoding='utf-8').write(s)
print('taf/index.html gerado:', len(s), 'caracteres')

# o portal pede taf/?v=<versão>, para os browsers não usarem uma cópia antiga guardada em cache
import hashlib
ver = hashlib.sha256(s.encode('utf-8')).hexdigest()[:10]
ip = os.path.join(ROOT, 'index.html')
idx = open(ip, encoding='utf-8').read()
new_idx = re.sub(r"f\.src='taf/[^']*'", f"f.src='taf/?v={ver}'", idx)
if new_idx.count(f"f.src='taf/?v={ver}'") != 1:
    sys.exit('build_taf: não encontrei o iframe do TAF no index.html')
open(ip, 'w', encoding='utf-8').write(new_idx)
print('index.html: TAF versão', ver)

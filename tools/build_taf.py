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
        'function portalCfg(){ const c = Object.assign({}, DEFAULTS, window.__portalTafCfg || {}); c.mode = isAdmin ? store.get("tafmon.mode", DEFAULTS.mode) : DEFAULTS.mode; return c; }\n'
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
        f'    alerts: allRows.filter(r => inList(r.icao, "DST") && r.levels.slice(0, {WX_H}).includes("red")).map(r => {{ const a = r.levels.indexOf("red"); let b = r.levels.slice(0, {WX_H}).lastIndexOf("red"); while (b + 1 < r.levels.length && r.levels[b + 1] === "red") b++; const hard = r.res.slice(0, {WX_H}).filter(x => x.level === "red").flatMap(x => x.hard); const ks = [...new Set(hard.map(h => catOfCode(h.code)))].sort((x, y) => catRank(x) - catRank(y)); return {{icao: r.icao, name: nameOf(r.icao), now: a === 0, from: slots[a], to: slots[b] + HOUR, open: b === r.levels.length - 1, cats: ks.map(k => (CATS.find(c => c.k === k) || {{}}).label || k), cond: cellLabels(hard).slice(0, 10)}}; }}).sort((x, y) => (y.now - x.now) || (x.from - y.from)),\n'
        '    newTafs: allRows.filter(r => r.isNew).map(r => ({icao: r.icao, name: nameOf(r.icao), amd: /\\bAMD\\b/.test((r.T && r.T.raw) || ""), at: (tafChanged[r.icao] || {}).at || null, issue: (r.T && r.T.issue) || null, level: r.levels[0], alert: r.levels.includes("red"), dest: inList(r.icao, "DST")})).sort((a, b) => (b.at || 0) - (a.at || 0)),\n'
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
    <header><h2 id="fltTitle">Voos afetados pela meteorologia</h2><button class="d-close" style="display:block" type="button" id="fltClose" aria-label="Fechar">×</button></header>
    <div class="body">
      <label class="flt-drop" id="fltDrop">
        <input type="file" id="fltFile" accept="application/pdf,.pdf" hidden>
        <b>Carregar PDF dos voos</b><span>ou arraste o ficheiro para aqui · o PDF é lido só neste browser e a lista fica só neste browser</span>
      </label>
      <div class="rep-row flt-tools"><span class="hint" id="fltInfo"></span><button class="btn ghost" type="button" id="fltClear" style="margin-left:auto">Limpar voos</button></div>
      <div class="rep-prev" id="fltOut" aria-label="Voos afetados"></div>
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
.grid th.ap .ap-flt{display:flex;flex-direction:column;gap:1px;padding:0 0 5px 22px;margin-top:-4px}
.grid th.ap .ap-flt span{font:500 11.5px/1.25 var(--f-mono);color:var(--muted);white-space:nowrap}
.grid th.ap .ap-flt b{color:var(--ink);font-weight:700}
.grid th.ap .ap-flt i{font-style:normal;font-weight:700;color:var(--kc,var(--t-red))}
.rep-text{""")
s = rep(s, '  $("#grid").innerHTML = h + "</tbody>";', '  $("#grid").innerHTML = h + "</tbody>";\n  try { decorateFlights(); } catch(e){}')
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
  m = /\b(\d{1,2})\s?(JAN|FEB|FEV|MAR|APR|ABR|MAY|MAI|JUN|JUL|AUG|AGO|SEP|SET|OCT|OUT|NOV|DEC|DEZ)[A-Z]*\s?(\d{2}(?:\d{2})?)?\b/i.exec(line);
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
    const fm = /\b(TP|TAP)\s?0*(\d{1,4}[A-Z]?)\b/i.exec(line);
    if (!fm){ if (dt) curDay = dt.day; continue; }
    const fDay = dt ? dt.day : curDay;
    const rest = line.slice(0, fm.index) + " " + line.slice(fm.index + fm[0].length);
    const aps = [], unk = [];
    for (const t of rest.toUpperCase().split(/[^A-Z0-9]+/)){
      if (/^[A-Z]{4}$/.test(t) && AIRPORTS[t]) aps.push(t);
      else if (/^[A-Z]{3}$/.test(t) && IATA2ICAO[t]) aps.push(IATA2ICAO[t]);
      else if (/^[A-Z]{3}$/.test(t)) unk.push(t);
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
/* o alerta mais grave nesse aeroporto a essa hora (mesmas regras do relatório) */
function alertsAt(all, icao, t){
  const its = all.filter(it => it.icao === icao && it.start <= t && t < it.end);
  if (!its.length) return null;
  const best = its.map(it => ({name: repCatName(it), cond: repCond(it)})).sort((a, b) => repSev(a.name) - repSev(b.name))[0];
  const toks = its.filter(it => repCatName(it) === best.name).flatMap(it => repCond(it).split(/\s+\/\s+|\s+/)).filter(Boolean);
  let cond = toks[0] || best.cond;
  if (best.name === "LVO"){ let wr = Infinity;
    for (const t of toks){ const v = /^VIS(\d{4})$/.exec(t), c = /^(BKN|OVC|VV)(\d{3}|\/\/\/)/.exec(t);
      const r = v ? +v[1] / (cfg.vis || 850) : c ? (c[2] === "///" ? 0 : +c[2] * 100 / (cfg.cig || 250)) : null;
      if (r != null && r < wr){ wr = r; cond = t; } } }
  else if (best.name !== "TS") cond = [...new Set(toks)].slice(0, 2).join(" ");
  return {name: best.name, cond, full: repFullName(best.name, [cond])};
}
const hm = t => t == null ? "" : pad(new Date(t).getUTCHours()) + pad(new Date(t).getUTCMinutes()) + "Z";
const apIata = ic => iataOf(ic) || ic;
const fltStore = {
  get(){ return store.get("tafmon.voos", null); },
  set(v){ try { if (v) store.set("tafmon.voos", v); else localStorage.removeItem("tafmon.voos"); } catch(e){} }
};
/* alertas de todos os aeroportos e de todas as categorias: o cruzamento dos voos não depende das escolhas do Relatório
   (destinos, cenários marcados, "só aeroportos visíveis na grelha") */
function allAlertItems(){
  const keepCats = repUI.cats, keepVis = repUI.onlyVis, keepDest = cfg.destIcao;
  try { repUI.cats = CATS.map(c => c.k); repUI.onlyVis = false; cfg.destIcao = ""; return reportItems().all; }
  finally { repUI.cats = keepCats; repUI.onlyVis = keepVis; cfg.destIcao = keepDest; }
}
function flightRows(txt){
  const P = parseFlights(txt);
  const all = allAlertItems();
  const rows = [];
  for (const f of P.flights){
    const a = alertsAt(all, f.dst, f.eta ?? f.sta), dp = alertsAt(all, f.org, f.etd ?? f.std);
    if (a) rows.push(Object.assign({f, side: "CHEGADA", ap: f.dst, t: f.eta ?? f.sta}, a));
    if (dp) rows.push(Object.assign({f, side: "PARTIDA", ap: f.org, t: f.etd ?? f.std}, dp));
  }
  rows.sort((x, y) => repSev(x.name) - repSev(y.name) || x.t - y.t);
  return {P, rows};
}
let fltCache = null;
/* por baixo de cada aeroporto na grelha: voos afetados (↓ chegada, ↑ partida), hora e alerta; e o resumo para o Início */
function decorateFlights(){
  const st = fltStore.get();
  fltCache = st && st.text ? flightRows(st.text) : null;
  if (fltCache){
    const by = {};
    fltCache.rows.forEach(r => (by[r.ap] = by[r.ap] || []).push(r));
    for (const [ic, list] of Object.entries(by)){
      const th = document.querySelector(`#grid tr[data-icao="${ic}"] th.ap`); if (!th) continue;
      const L = list.slice().sort((a, b) => a.t - b.t);
      const show = L.slice(0, 3).map(r => {
        const tip = `${r.f.fl} ${apIata(r.f.org)}-${apIata(r.f.dst)} · ${r.side === "CHEGADA" ? "chegada" : "partida"} ${hm(r.t)} · ${r.cond} · ${r.full}`;
        return `<span class="k-${FLT_KEY[r.name] || "int"}" title="${esc(tip)}">${r.side === "CHEGADA" ? "↓" : "↑"} <b>${r.f.fl}</b> ${hm(r.t)} <i>${esc(r.name)}</i></span>`;
      });
      if (L.length > 3) show.push(`<span>+${L.length - 3} voos</span>`);
      th.insertAdjacentHTML("beforeend", `<div class="ap-flt">${show.join("")}</div>`);
    }
  }
  postFlights(st);
  if (!$("#flights").hidden) renderFlights();
}
function postFlights(st){
  try {
    if (window.parent === window) return;
    const C = fltCache, fl = new Map();
    if (C) C.rows.forEach(r => { const k = r.f.fl + "|" + r.f.std, w = FLT_RESTR.has(r.name) ? 2 : 1; fl.set(k, Math.max(fl.get(k) || 0, w)); });
    window.parent.postMessage({type: "taf-flights", has: !!(st && st.text), name: (st && st.name) || "", at: (st && st.at) || null,
      total: C ? C.P.flights.length : 0, restr: [...fl.values()].filter(v => v === 2).length, alert: [...fl.values()].filter(v => v === 1).length,
      outside: C ? C.P.outside : [], bad: C ? C.P.bad.length : 0,
      rows: C ? C.rows.map(r => ({fl: r.f.fl, org: apIata(r.f.org), dst: apIata(r.f.dst), side: r.side, t: r.t, icao: r.ap, name: r.name, full: r.full, cond: r.cond, restr: FLT_RESTR.has(r.name)})) : []}, location.origin);
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
  if (P.flights.length) parts.push(`${P.flights.length} voos lidos · <b>${nAff} afetados</b>`);
  if (P.outside.length) parts.push(`fora da lista do TAF: ${esc(P.outside.join(", "))}`);
  if (P.bad.length) parts.push(`${P.bad.length} linhas com voo não reconhecidas`);
  $("#fltInfo").innerHTML = parts.join(" · ");
  const COLS = ["VOO", "ROTA", "STD", "STA", "ETD", "ETA", "ONDE", "CONDIÇÃO", "ALERTA"];
  const th = h => `<th style="border:1px solid #999;background:#e8e8e8;padding:3px 8px;text-align:left">${esc(h)}</th>`;
  const td = (c, sty) => `<td style="border:1px solid #999;padding:3px 8px;white-space:nowrap${sty || ""}">${esc(c)}</td>`;
  const zs = rows.slice().sort((x, y) => repZone(x.ap) - repZone(y.ap) || repSev(x.name) - repSev(y.name) || x.t - y.t);
  let html;
  if (zs.length){
    html = `<table style="border-collapse:collapse;font-family:Calibri,Arial,sans-serif;font-size:10.5pt"><tr>${COLS.map(th).join("")}</tr>` + zs.map((r, k) => {
      const z = repZone(r.ap), zh = k === 0 || repZone(zs[k - 1].ap) !== z ? `<tr><td colspan="${COLS.length}" style="border:1px solid #999;background:#d9e7f2;padding:3px 8px;font-weight:bold">${REP_ZONE_NAME[z]}</td></tr>` : "";
      const f = r.f;
      return zh + `<tr>${td(f.fl, ";font-weight:bold")}${td(apIata(f.org) + "→" + apIata(f.dst))}${td(hm(f.std))}${td(hm(f.sta))}${td(hm(f.etd))}${td(hm(f.eta), ";font-weight:bold")}${td(r.side + " " + apIata(r.ap))}${td(r.cond, ";font-family:Consolas,monospace")}${td(r.full, ";font-weight:bold")}</tr>`;
    }).join("") + `</table>`;
  } else html = P.flights.length ? `<p style="margin:0">Nenhum voo afetado pelos alertas atuais.</p>` : `<p class="hint" style="margin:0">Carregue o PDF da lista de voos.</p>`;
  $("#fltOut").innerHTML = html;
  fltLast = zs.length ? {html: `<html><head><meta charset="utf-8"></head><body><!--StartFragment-->${html}<p style="margin:0">&nbsp;</p><!--EndFragment--></body></html>`,
    text: zs.map(r => [r.f.fl, apIata(r.f.org) + "-" + apIata(r.f.dst), hm(r.f.std), hm(r.f.sta), hm(r.f.etd), hm(r.f.eta), r.side + " " + apIata(r.ap), r.cond, r.full].join("\t")).join("\n")} : null;
}
async function fltLoadFile(file){
  if (!file) return;
  $("#fltInfo").textContent = "A ler " + file.name + "…";
  try {
    const lines = await pdfLines(file);
    if (!lines.some(l => /\S/.test(l))){ $("#fltInfo").textContent = "Este PDF não tem texto (parece uma imagem digitalizada)."; postFlightsError("Este PDF não tem texto (parece uma imagem digitalizada)."); return; }
    $("#fltIn").value = lines.join("\n");
    fltStore.set({text: $("#fltIn").value, name: file.name, at: Date.now()});
    render();
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

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

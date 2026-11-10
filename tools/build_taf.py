"""Gera taf/index.html a partir do TAF Monitor original (tools/taf-monitor-original.html).

O conteúdo do monitor fica igual; só se acrescenta:
  - verificação de acesso: só abre dentro do portal, com sessão aprovada (senão vai para o portal);
  - Definições: abrem só para Administradores do portal (deixa de haver PIN);
  - ponte com o portal: envia o resumo (TAF novos/AMD, alertas) e aceita "abrir aeroporto".
Para atualizar o monitor: substituir tools/taf-monitor-original.html e correr  python3 tools/build_taf.py
"""
import os, re, sys

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
s = rep(s, '$("#btnSettings").addEventListener("click", () => { if (!SETTINGS_LOCKED || isAdmin) openSettings(); else openPin(); });',
        '$("#btnSettings").addEventListener("click", () => { if (!SETTINGS_LOCKED || isAdmin) openSettings(); else portalNotAdmin(); });\n'
        'function portalNotAdmin(){ const b = $("#banner"); b.innerHTML = "<b>Definições bloqueadas.</b> <span>Só um Administrador do portal pode alterar as definições do TAF.</span>"; b.className = "banner"; b.hidden = false; setTimeout(() => { if (b.textContent.startsWith("Definições bloqueadas")) b.hidden = true; }, 6000); }')
s = rep(s, 'b.title = SETTINGS_LOCKED && !isAdmin ? "Bloqueado: precisa de PIN" : "Definições";',
        'b.title = SETTINGS_LOCKED && !isAdmin ? "Só Administradores do portal" : "Definições";')

# 3) ponte com o portal: resumo depois de cada render
s = rep(s, '  $("#legendCodes").textContent = ',
        '  try { if (window.parent !== window) window.parent.postMessage({type: "taf-summary", updatedAt: lastFetch || null, total: allRows.length,\n'
        '    now: allRows.filter(r => r.levels[0] === "red").map(r => ({icao: r.icao, name: nameOf(r.icao)})),\n'
        '    next6: allRows.filter(r => r.levels.slice(0, 6).includes("red")).map(r => ({icao: r.icao, name: nameOf(r.icao)})),\n'
        '    noTaf: allRows.filter(r => !r.T || r.T.error).length,\n'
        '    newTafs: allRows.filter(r => r.isNew).map(r => ({icao: r.icao, name: nameOf(r.icao), amd: /\\bAMD\\b/.test((r.T && r.T.raw) || ""), at: (tafChanged[r.icao] || {}).at || null, level: r.levels[0]})).sort((a, b) => (b.at || 0) - (a.at || 0)),\n'
        '    error: fetchError || null}, location.origin); } catch(e){}\n'
        '  $("#legendCodes").textContent = ')

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
        '  } else if (d.type === "taf-refresh") load();\n'
        '  else if (d.type === "taf-role"){\n'
        '    isAdmin = d.role === "admin";\n'
        '    cfg = SETTINGS_LOCKED && !isAdmin ? Object.assign({}, DEFAULTS) : Object.assign({}, DEFAULTS, store.get("tafmon.cfg", {}));\n'
        '    if (!isAdmin) dlg.hidden = true;\n'
        '    paintLock(); load();\n'
        '  }\n'
        '});\n'
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
    if (P && P.role){
      window.__portalRole = P.role;
      var x = document.createElement("script");
      x.textContent = document.getElementById("tafMain").textContent;
      document.documentElement.classList.remove("gate");
      document.body.appendChild(x);
      return;
    }
    if (++tries > 100){ document.body.innerHTML = '<p style="padding:24px;font-family:system-ui,sans-serif">Abre o TAF a partir do portal, com sessão iniciada.</p>'; document.documentElement.classList.remove("gate"); return; }
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

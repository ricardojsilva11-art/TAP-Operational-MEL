"""Portal Operational Control: Início, separador TAF (TAF Monitor dentro da app) e ligação entre os dois."""
from harness import UID, logged_in, open_app, visible

SUMMARY = ("{type:'taf-summary',updatedAt:Date.UTC(2026,10,10,9,30),total:42,"
           "now:[{icao:'LPPT',name:'Lisboa'}],next6:[{icao:'LPPT',name:'Lisboa'},{icao:'LPPR',name:'Porto'}],noTaf:0,error:null,"
           "alerts:[{icao:'LPPT',name:'Lisboa',now:true,from:Date.UTC(2026,10,10,9),to:Date.UTC(2026,10,10,14),open:false,cats:['LVO','Wind / gust'],cond:['VIS400m','FG','BKN002','G35']},"
           "{icao:'LPPR',name:'Porto',now:false,from:Date.UTC(2026,10,10,12),to:Date.UTC(2026,10,10,16),open:false,cats:['Thunderstorm'],cond:['TSRA']}],"
           "newTafs:[{icao:'LPFR',name:'Faro',amd:true,at:Date.UTC(2026,10,10,9,12),level:'amber',alert:true},"
           "{icao:'LEMD',name:'Madrid',amd:false,at:Date.UTC(2026,10,10,9,5),level:'green',alert:true},"
           "{icao:'LEBL',name:'Barcelona',amd:true,at:Date.UTC(2026,10,10,9,20),level:'green',alert:false}]}")
NEW_LPMA = "newTafs:[{icao:'LPMA',name:'Madeira',amd:true,at:Date.UTC(2026,10,10,9,40),level:'red',alert:true},"


def taf_frame(page):
    page.wait_for_function("!!document.getElementById('tafFrame')", timeout=10000)
    page.wait_for_function("(()=>{try{const d=document.getElementById('tafFrame').contentDocument;"
                           "return d&&!d.documentElement.classList.contains('gate')&&!!d.getElementById('grid')}catch(e){return false}})()",
                           timeout=20000)
    return next(f for f in page.frames if '/taf/' in f.url)


def test_inicio_por_omissao_e_ordem_do_menu(browser, server, mock):
    ctx, page, errors = open_app(browser, server, mock, logged_in(), view='portal')
    assert visible(page, '#portalView') and not visible(page, '#homeView')
    navs = page.evaluate("[...document.querySelectorAll('#nav [data-nav]')].map(b=>b.dataset.nav)")
    assert navs[:3] == ['portal', 'taf', 'home']
    assert page.inner_text('.brand h1') == 'OPERATIONAL CONTROL'
    assert page.inner_text('.brand small') == 'TAF · MEL'
    assert page.inner_text('#pMelTotal').startswith('3 MEL ativas')
    assert 'A320' in page.inner_text('#pTabs')
    assert not errors
    ctx.close()


def test_taf_abre_dentro_do_portal(browser, server, mock):
    ctx, page, errors = open_app(browser, server, mock, logged_in(), view='portal')
    f = taf_frame(page)
    assert f.evaluate('window.__portalRole') == 'operator'
    page.click('[data-nav="taf"]')
    assert visible(page, '#tafView') and page.evaluate("document.body.classList.contains('taf-mode')")
    box = page.evaluate("document.getElementById('tafFrame').getBoundingClientRect().height")
    assert box > 500  # ocupa o ecrã todo
    # o resumo chega ao portal (mesmo sem rede para os TAF)
    page.wait_for_function("tafSum!==null", timeout=15000)
    page.click('[data-nav="portal"]')
    assert not page.evaluate("document.body.classList.contains('taf-mode')")
    assert not errors
    ctx.close()


def test_resumo_taf_no_inicio_e_alerta_no_separador(browser, server, mock):
    ctx, page, errors = open_app(browser, server, mock, logged_in(), view='portal')
    f = taf_frame(page)
    f.evaluate("parent.postMessage(%s,location.origin)" % SUMMARY)
    page.wait_for_function("document.getElementById('pNew').textContent==='2'")
    assert page.inner_text('#tafBadge') == '2' and visible(page, '#tafBadge')
    assert page.inner_text('#pNow') == '1' and page.inner_text('#pNext') == '2'  # LPPT já em alerta conta também nas 6 h
    lst = page.inner_text('#pNewList')
    assert 'LPFR' in lst and 'AMD' in lst and 'NOVO' in lst and '09:12Z' in lst
    assert 'LEBL' not in lst  # TAF emendado sem alerta não conta
    assert 'LPPT' in page.inner_text('#pAlertList') and 'LPPR' in page.inner_text('#pAlertList')
    assert '42 aeroportos' in page.inner_text('#pTafUpd')
    # mensagens de outra origem/janela são ignoradas
    page.evaluate("window.postMessage({type:'taf-summary',newTafs:[],now:[],next6:[]},location.origin)")
    page.wait_for_timeout(200)
    assert page.inner_text('#tafBadge') == '2'
    # sem TAF novos, o alerta desaparece
    f.evaluate("parent.postMessage({type:'taf-summary',total:42,now:[],next6:[],newTafs:[]},location.origin)")
    page.wait_for_function("document.getElementById('tafBadge').classList.contains('hidden')")
    assert 'Nenhum destino' in page.inner_text('#pAlertList')
    assert not errors
    ctx.close()


def test_clicar_aeroporto_abre_painel_no_taf(browser, server, mock):
    ctx, page, _ = open_app(browser, server, mock, logged_in(), view='portal')
    f = taf_frame(page)
    f.evaluate("window.__sel=[];addEventListener('message',e=>{if(e.data&&e.data.type==='taf-select')__sel.push(e.data.icao)})")
    f.evaluate("parent.postMessage(%s,location.origin)" % SUMMARY)
    page.wait_for_selector('#pAlertList [data-icao="LPPT"]')
    page.click('#pAlertList [data-icao="LPPT"]')
    assert visible(page, '#tafView')
    page.wait_for_timeout(300)
    assert f.evaluate('__sel') == ['LPPT']
    ctx.close()


def test_definicoes_do_taf_so_para_administrador(browser, server, mock):
    ctx, page, _ = open_app(browser, server, mock, logged_in(), view='portal')
    f = taf_frame(page)
    page.click('[data-nav="taf"]')
    f.click('#btnSettings')
    assert 'Só um Administrador' in f.inner_text('#banner')
    assert f.evaluate("document.getElementById('settings').hidden")
    assert f.evaluate("document.getElementById('btnSettings').title") == 'Só Administradores do portal'
    # passa a Administrador em tempo real: as definições abrem
    page.evaluate("onProfileChange({eventType:'UPDATE',new:{...profile,role:'admin'},old:{user_id:'%s'}})" % UID)
    page.wait_for_function("(()=>{try{return document.getElementById('tafFrame').contentWindow.isAdmin===true}catch(e){return false}})()"
                           "||document.getElementById('tafFrame').contentWindow.eval('isAdmin')===true", timeout=5000)
    f.click('#btnSettings')
    assert not f.evaluate("document.getElementById('settings').hidden")
    ctx.close()


def test_link_direto_do_taf_vai_para_o_portal(browser, server, mock):
    ctx, page, _ = open_app(browser, server, mock, logged_in(), view='portal')
    page.goto(server.url + 'taf/')
    page.wait_for_function("location.pathname==='/'&&!document.getElementById('appPanel').classList.contains('hidden')", timeout=20000)
    page.wait_for_timeout(300)
    assert visible(page, '#tafView')
    assert location_hash(page) == ''
    ctx.close()


def test_taf_sem_sessao_mostra_login(browser, server, mock):
    ctx, page, _ = open_app(browser, server, mock, {}, view='portal')
    page.goto(server.url + 'taf/')
    page.wait_for_timeout(2500)
    assert visible(page, '#loginPanel') and not visible(page, '#appPanel')
    assert not page.evaluate("!!document.getElementById('tafFrame')")
    ctx.close()


def test_alteracoes_das_ultimas_24h_no_inicio(browser, server, mock):
    from datetime import datetime, timedelta, timezone
    iso = lambda h: (datetime.now(timezone.utc) - timedelta(hours=h)).strftime('%Y-%m-%dT%H:%M:%SZ')
    long = 'Linha 1<br>' + '<br>'.join(f'Linha {i} do impacto operacional' for i in range(2, 30))
    mock.rows[0].update(operational_impact_html=long, notes='Nota importante', updated_at=iso(2), updated_by_name='Ana')  # alterada
    mock.rows[2].update(created_at=iso(1), created_by_name='Rui')                                                         # nova (A330)
    mock.rows[1].update(updated_at=iso(30))                                                                               # há mais de 24 h
    mock.rows.append(dict(mock.rows[1], id='r9', mel_item='M-30-11-01', is_active=False, updated_at=iso(3)))              # apagada
    ctx, page, errors = open_app(browser, server, mock, logged_in(), view='portal')
    page.wait_for_timeout(400)
    items = page.evaluate("[...document.querySelectorAll('#pMelList .p-mel .code')].map(e=>e.textContent)")
    assert items == ['M-21-28-03A', 'M-21-26-01', 'M-30-11-01']  # mais recente primeiro, sem a de há 30 h
    txt = page.inner_text('#pMelList')
    assert 'Linha 29 do impacto operacional' in txt and 'Nota importante' in txt  # texto todo
    assert 'Nova' in txt and 'Alterada' in txt and 'Apagada' in txt and 'Ana' in txt
    assert '3 alterações nas últimas 24 h' in page.inner_text('#pMelTotal')
    page.click('[data-ptab="A330"]')
    assert page.evaluate("document.querySelectorAll('#pMelList .p-mel').length") == 1
    page.click('[data-ptab=""]')
    page.fill('#pSearch', '26-01')
    page.wait_for_timeout(400)
    assert page.evaluate("document.querySelectorAll('#pMelList .p-mel').length") == 1
    page.click('#pMelList [data-mel="M-21-26-01"]')
    assert visible(page, '#homeView') and page.input_value('#search') == 'M-21-26-01'
    assert not errors
    ctx.close()


def test_sem_alteracoes_nas_ultimas_24h(browser, server, mock):
    ctx, page, _ = open_app(browser, server, mock, logged_in(), view='portal')
    assert 'Nenhuma MEL foi adicionada, alterada ou apagada' in page.inner_text('#pMelList')
    ctx.close()


def test_abrir_taf_limpa_o_alerta(browser, server, mock):
    ctx, page, _ = open_app(browser, server, mock, logged_in(), view='portal')
    f = taf_frame(page)
    f.evaluate("parent.postMessage(%s,location.origin)" % SUMMARY)
    page.wait_for_function("document.getElementById('tafBadge').textContent==='2'")
    page.click('[data-nav="taf"]')
    assert not visible(page, '#tafBadge')
    page.click('[data-nav="portal"]')
    f.evaluate("parent.postMessage(%s,location.origin)" % SUMMARY)  # os mesmos TAF: continua limpo
    page.wait_for_timeout(300)
    assert not visible(page, '#tafBadge')
    assert 'LPFR' not in page.inner_text('#pNewList')  # depois de abrir o TAF, sai também do Início
    assert page.inner_text('#pNew') == '0' and 'por ver' in page.inner_text('#pNewList')
    # um TAF novo volta a acender o alerta (só esse)
    f.evaluate("parent.postMessage(%s,location.origin)" % SUMMARY.replace("newTafs:[", NEW_LPMA))
    page.wait_for_function("document.getElementById('tafBadge').textContent==='1'")
    ctx.close()


def location_hash(page):
    return page.evaluate('location.hash')


def test_definicoes_do_taf_partilhadas(browser, server, mock):
    mock.taf_cfg.update(cfg={'vis': 600, 'wind': 35, 'mode': 'sample'}, updated_at='2026-11-10T09:00:00Z', updated_by_name='Ana')
    ctx, page, errors = open_app(browser, server, mock, logged_in(), view='portal')
    f = taf_frame(page)
    # quem não é Administrador usa as definições partilhadas, mas sempre no modo ao vivo
    assert f.evaluate('cfg.vis') == 600 and f.evaluate('cfg.wind') == 35 and f.evaluate('cfg.mode') == 'live'
    # o Administrador muda em tempo real e todos recebem
    mock.taf_cfg['cfg'] = {'vis': 700}
    page.evaluate('loadTafCfg()')
    page.wait_for_function("document.getElementById('tafFrame').contentWindow.eval('cfg.vis')===700", timeout=5000)
    # quem não é Administrador não grava, mesmo que a página do TAF o tente
    f.evaluate("parent.postMessage({type:'taf-cfg-save',cfg:{vis:1}},location.origin)")
    page.wait_for_timeout(500)
    assert not any('taf_settings' in p for m, p, _ in mock.requests)
    assert 'não foram guardadas' in f.inner_text('#banner')
    assert not errors
    ctx.close()


def test_administrador_grava_definicoes_do_taf(browser, server, mock):
    mock.profile['role'] = 'admin'
    ctx, page, errors = open_app(browser, server, mock, logged_in(), view='portal')
    f = taf_frame(page)
    page.click('[data-nav="taf"]')
    f.click('#btnSettings')
    assert 'valem para todos' in f.inner_text('#portalCfgInfo')
    f.fill('#fVis', '900')
    f.click('#mSample')
    f.evaluate("document.getElementById('setForm').requestSubmit()")
    page.wait_for_function("window.__portal.cfg&&window.__portal.cfg.vis===900", timeout=5000)
    body = next(b for m, p, b in mock.requests if m == 'PATCH' and 'taf_settings' in p)
    assert '"vis":900' in body and '"mode"' not in body  # o modo fica só neste navegador
    assert f.evaluate('cfg.mode') == 'sample'
    assert not errors
    ctx.close()


def test_sem_tabela_de_definicoes_avisa(browser, server, mock):
    mock.profile['role'] = 'admin'
    mock.taf_missing = True
    ctx, page, _ = open_app(browser, server, mock, logged_in(), view='portal')
    f = taf_frame(page)
    assert f.evaluate('cfg.vis') == f.evaluate('DEFAULTS.vis')
    f.evaluate("parent.postMessage({type:'taf-cfg-save',cfg:{vis:1}},location.origin)")
    page.wait_for_timeout(600)
    assert '014_definicoes_taf.sql' in f.inner_text('#banner')
    ctx.close()


def test_importa_definicoes_do_site_antigo(browser, server, mock):
    import base64, json
    mock.profile['role'] = 'admin'
    raw = base64.urlsafe_b64encode(json.dumps({'vis': 1234, 'icao': 'LPPT LPPR', 'mode': 'manual'}).encode()).decode().rstrip('=')
    ctx, page, _ = open_app(browser, server, mock, logged_in(), view='portal')
    page.goto(server.url + '#taf&taf-import=' + raw)
    page.reload()  # só mudar o # não recarrega a página
    page.wait_for_function("window.__portal&&window.__portal.cfg&&window.__portal.cfg.vis===1234", timeout=15000)
    assert mock.taf_cfg['cfg'] == {'vis': 1234, 'icao': 'LPPT LPPR'}
    assert visible(page, '#tafView') and page.evaluate('location.hash') == ''
    ctx.close()


def test_versao_do_taf_atualizada():
    """O portal pede taf/?v=<versão>; se isto falhar, correr python3 tools/build_taf.py."""
    import hashlib, os
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    taf = open(os.path.join(root, 'taf', 'index.html'), encoding='utf-8').read()
    ver = hashlib.sha256(taf.encode('utf-8')).hexdigest()[:10]
    assert f"f.src='taf/?v={ver}'" in open(os.path.join(root, 'index.html'), encoding='utf-8').read()


def test_numeros_do_taf_abrem_o_filtro_certo(browser, server, mock):
    ctx, page, _ = open_app(browser, server, mock, logged_in(), view='portal')
    f = taf_frame(page)
    f.evaluate("parent.postMessage(%s,location.origin)" % SUMMARY)
    page.wait_for_function("document.getElementById('pNew').textContent==='2'")
    for tf, lst in (('now', 'DST'), ('next6', 'DST'), ('new', '')):
        page.click('[data-nav="portal"]')
        page.click(f'[data-tf="{tf}"]')
        assert visible(page, '#tafView')
        page.wait_for_timeout(300)
        assert f.evaluate('ui.filter') == tf and f.evaluate('ui.list') == lst
    ctx.close()


def test_resumo_do_taf_so_com_destinos(browser, server, mock):
    mock.profile['role'] = 'admin'
    ctx, page, _ = open_app(browser, server, mock, logged_in({'tafmon.mode': '"sample"'}), view='portal')
    taf_frame(page)
    page.wait_for_function("tafSum!==null&&tafSum.total>0", timeout=20000)
    f = next(x for x in page.frames if '/taf/' in x.url)
    icaos = page.evaluate("tafSum.now.concat(tafSum.next6).map(a=>a.icao)")
    assert icaos and all(f.evaluate(f"inList('{ic}','DST')") for ic in icaos)
    ctx.close()


def test_texto_escuro_fica_legivel_no_tom_escuro(browser, server, mock):
    mock.rows[0]['operational_impact_html'] = '<span style="color:#000000">preto</span> <span style="color:rgb(31,31,31)">quase</span> <font color="#000080">azul</font> <span style="color:#d62f37">vermelho</span>'
    ctx, page, errors = open_app(browser, server, mock, logged_in({'mel-theme': 'dark'}))
    marked = page.evaluate("[...document.querySelectorAll('#rows td.impact .dk')].map(e=>e.textContent)")
    assert marked == ['preto', 'quase', 'azul']
    col = page.evaluate("getComputedStyle(document.querySelector('#rows td.impact .dk')).color")
    assert col != 'rgb(0, 0, 0)'
    assert not errors
    ctx.close()


def test_larguras_guardadas_cabem_na_pagina(browser, server, mock):
    # larguras antigas, maiores do que o ecrã e com a coluna Ações estreita
    ctx, page, _ = open_app(browser, server, mock, logged_in({'mel-colw': '[400,1400,300,300,120]'}), view='portal')
    page.set_viewport_size({'width': 1400, 'height': 900})
    page.click('[data-nav="home"]')
    page.wait_for_timeout(400)
    r = page.evaluate("(()=>{const w=document.querySelector('.tablewrap'),t=document.getElementById('melTable'),a=t.querySelector('thead th:last-child');"
                      "return {sw:w.scrollWidth,cw:w.clientWidth,act:a.getBoundingClientRect().width,doc:document.documentElement.scrollWidth,vw:innerWidth}})()")
    assert r['sw'] <= r['cw'] + 2 and r['act'] >= 205 and r['doc'] <= r['vw']
    ctx.close()


def test_aviso_diz_qual_o_aeroporto(browser, server, mock):
    ctx, page, _ = open_app(browser, server, mock, logged_in(), view='portal')
    f = taf_frame(page)
    f.evaluate("parent.postMessage(%s,location.origin)" % SUMMARY)
    page.wait_for_selector('.taf-toast')
    t = page.inner_text('.taf-toast')
    assert '2 TAF novos ou emendados' in t and 'LPFR' in t and 'LEMD' in t
    assert 'LPFR (AMD)' in page.get_attribute('#tafBadge', 'title')
    assert page.evaluate("document.querySelectorAll('#pNewList .p-item.unseen').length") == 2
    page.evaluate("document.querySelectorAll('.taf-toast').forEach(x=>x.remove())")
    # chega um TAF novo: o aviso diz qual, e carregar abre esse aeroporto no TAF
    f.evaluate("window.__sel=[];addEventListener('message',e=>{if(e.data&&e.data.type==='taf-select')__sel.push(e.data.icao)})")
    f.evaluate("parent.postMessage(%s,location.origin)" % SUMMARY.replace("newTafs:[", NEW_LPMA))
    page.wait_for_selector('.taf-toast')
    t = page.inner_text('.taf-toast')
    assert 'TAF emendado (AMD): LPMA Madeira' in t and '09:40Z' in t
    page.click('.taf-toast')
    assert visible(page, '#tafView')
    page.wait_for_timeout(300)
    assert f.evaluate('__sel') == ['LPMA']
    assert page.evaluate("document.querySelectorAll('#pNewList .p-item.unseen').length") == 0
    ctx.close()


def test_taf_atualiza_ao_voltar_a_janela(browser, server, mock):
    ctx, page, _ = open_app(browser, server, mock, logged_in(), view='portal')
    f = taf_frame(page)
    assert f.evaluate('DEFAULTS.refresh') == 2
    f.evaluate("window.__ref=0;addEventListener('message',e=>{if(e.data&&e.data.type==='taf-refresh')__ref++})")
    page.evaluate("tafRefAt=Date.now()-120000;dispatchEvent(new Event('focus'))")
    page.wait_for_timeout(300)
    page.evaluate("dispatchEvent(new Event('focus'))")  # logo a seguir não repete
    page.wait_for_timeout(300)
    assert f.evaluate('__ref') == 1
    ctx.close()



def test_so_tafs_com_alerta_contam(browser, server, mock):
    ctx, page, _ = open_app(browser, server, mock, logged_in(), view='portal')
    f = taf_frame(page)
    f.evaluate("parent.postMessage({type:'taf-summary',total:42,now:[],next6:[],alerts:[],newTafs:[{icao:'LEBL',name:'Barcelona',amd:true,at:1,level:'green',alert:false}]},location.origin)")
    page.wait_for_timeout(500)
    assert not visible(page, '#tafBadge') and page.evaluate("document.querySelectorAll('.taf-toast').length") == 0
    assert page.inner_text('#pNew') == '0'
    ctx.close()


def test_meteorologia_nos_destinos(browser, server, mock):
    ctx, page, _ = open_app(browser, server, mock, logged_in(), view='portal')
    f = taf_frame(page)
    many = SUMMARY.replace("alerts:[", "alerts:[" + ",".join(
        "{icao:'X%03d',name:'N',now:false,from:Date.UTC(2026,10,10,13),to:Date.UTC(2026,10,10,15),open:true,cats:['MIST'],cond:['BR']}" % i for i in range(6)) + ",")
    f.evaluate("parent.postMessage(%s,location.origin)" % SUMMARY)
    page.wait_for_selector('#pAlertList .p-wxrow')
    rows = page.evaluate("[...document.querySelectorAll('#pAlertList .p-wxrow')].map(e=>e.innerText.replace(/\\s+/g,' '))")
    assert rows[0].startswith('LPPT Agora–14Z LVO VIS400m FG BKN002')  # só a categoria mais grave e até 3 valores
    assert 'Wind / gust' not in rows[0] and 'G35' not in rows[0]
    assert rows[1].startswith('LPPR 12Z–16Z Thunderstorm TSRA')
    assert 'Wind / gust' in page.get_attribute('#pAlertList [data-icao="LPPT"]', 'title')
    f.evaluate("parent.postMessage(%s,location.origin)" % many)
    page.wait_for_function("document.querySelectorAll('#pAlertList .p-wxrow').length===6")
    assert 'Ver todos (8)' in page.inner_text('#pAlertList')
    page.click('.p-wxall')
    assert visible(page, '#tafView')
    page.wait_for_timeout(300)
    assert f.evaluate('ui.filter') == 'next6' and f.evaluate('ui.list') == 'DST'
    ctx.close()


def test_resumo_traz_meteorologia_real(browser, server, mock):
    mock.profile['role'] = 'admin'
    ctx, page, _ = open_app(browser, server, mock, logged_in({'tafmon.mode': '"sample"'}), view='portal')
    taf_frame(page)
    page.wait_for_function("tafSum!==null&&tafSum.total>0", timeout=20000)
    al = page.evaluate("tafSum.alerts")
    assert al and all(a['cats'] and a['cond'] and a['to'] > a['from'] for a in al)
    assert all(isinstance(t.get('alert'), bool) for t in page.evaluate("tafSum.newTafs"))
    ctx.close()


def test_carregar_no_alerta_do_inicio_faz_desaparecer(browser, server, mock):
    ctx, page, _ = open_app(browser, server, mock, logged_in(), view='portal')
    f = taf_frame(page)
    f.evaluate("parent.postMessage(%s,location.origin)" % SUMMARY)
    page.wait_for_selector('#pNewList [data-icao="LPFR"]')
    page.evaluate("document.querySelectorAll('.taf-toast').forEach(x=>x.remove())")
    page.click('#pNewList [data-icao="LPFR"]')
    assert visible(page, '#tafView')
    page.click('[data-nav="portal"]')
    assert page.evaluate("document.querySelectorAll('#pNewList [data-icao]').length") == 0
    assert page.inner_text('#pNew') == '0' and not visible(page, '#tafBadge')
    page.reload()  # e continua assim depois de recarregar
    page.wait_for_selector('#appPanel:not(.hidden)')
    f = taf_frame(page)
    f.evaluate("parent.postMessage(%s,location.origin)" % SUMMARY)
    page.wait_for_timeout(500)
    assert page.inner_text('#pNew') == '0' and not visible(page, '#tafBadge')
    assert page.evaluate("document.querySelectorAll('.taf-toast').length") == 0
    ctx.close()

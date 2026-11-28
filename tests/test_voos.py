import re
"""Voos: PDF da lista de voos lido no browser e cruzado com o TAF (Início, janela Voos e grelha do TAF)."""
import json
import os
import time

from harness import logged_in, open_app, visible
from test_portal import taf_frame

PDF = os.path.join(os.path.dirname(__file__), 'fixtures', 'voos-exemplo.pdf')
WORKER = 'https://taf.ricardo-j-silva11.workers.dev/**'


def _taf_json(route):
    """TAF de teste: Lisboa com nevoeiro (LVO) nas próximas 24 h; Londres sem alertas."""
    if 'type=metar' in route.request.url:
        return route.fulfill(status=200, content_type='application/json', body='[]')
    t0 = int(time.time() // 3600 * 3600) - 3600
    g = lambda t: time.strftime('%d%H', time.gmtime(t))
    iss = time.strftime('%d%H%MZ', time.gmtime(t0))
    per = f'{g(t0)}/{g(t0 + 30 * 3600)}'
    tafs = [{'icaoId': 'LPPT', 'issueTime': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(t0)), 'rawTAF': f'TAF LPPT {iss} {per} VRB02KT 0300 FG VV001'},
            {'icaoId': 'EGLL', 'issueTime': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(t0)), 'rawTAF': f'TAF EGLL {iss} {per} 24008KT 9999 SCT030'}]
    return route.fulfill(status=200, content_type='application/json', headers={'Access-Control-Allow-Origin': '*'}, body=json.dumps(tafs))


def _hhmm(t):
    return time.strftime('%H:%M', time.gmtime(t))


def test_pdf_arrastado_no_inicio(browser, server, mock):
    ctx, page, errors = open_app(browser, server, mock, logged_in(), view='portal')
    taf_frame(page)
    page.wait_for_function("tafSum!==null", timeout=15000)
    assert 'Sem lista de voos' in page.inner_text('#pFltInfo')
    page.set_input_files('#pFltFile', PDF)
    page.wait_for_function("document.getElementById('pFltTotal').textContent==='6'", timeout=20000)
    info = page.inner_text('#pFltInfo')
    assert 'voos-exemplo.pdf' in info and '6 voos' in info
    assert '1 fora da lista' in page.inner_text('#pFltOk')  # TP9999 para XYZ
    saved = json.loads(page.evaluate("localStorage.getItem('tafmon.voos')"))
    assert 'TP1350' in saved['text'] and saved['name'] == 'voos-exemplo.pdf'
    assert 'substitui a lista atual' in page.inner_text('#pFltDrop')
    assert not errors
    ctx.close()


def test_voos_afetados_no_inicio_na_janela_e_na_grelha(browser, server, mock):
    ctx, page, errors = open_app(browser, server, mock, logged_in(), view='portal')
    ctx.route(WORKER, _taf_json)
    f = taf_frame(page)
    now = time.time()
    lista = (f'TP1350  LIS  LHR  {_hhmm(now + 3600)}  {_hhmm(now + 3 * 3600)}\n'
             f'TP1351  LHR  LIS  {_hhmm(now + 4 * 3600)}  {_hhmm(now + 6 * 3600)}\n'
             f'TP2001  LHR  CDG  {_hhmm(now + 2 * 3600)}  {_hhmm(now + 3 * 3600)}')
    f.evaluate("t=>{localStorage.setItem('tafmon.voos',JSON.stringify({text:t,name:'lista.pdf',at:Date.now()}))}", lista)
    f.evaluate("parent.postMessage({type:'x'},location.origin)")
    page.evaluate("postTaf({type:'taf-refresh'})")
    page.wait_for_function("fltSum&&fltSum.has&&fltSum.restr===1", timeout=20000)
    # Início: só conta o destino: chegada a LIS com LVO; a partida de LIS (TP1350) e o LHR-CDG não contam
    assert page.inner_text('#pFltRestr') == '1' and page.inner_text('#pFltAlert') == '0' and page.inner_text('#pFltTotal') == '3'
    lst = page.inner_text('#pFltList')
    assert 'TP1351' in lst and 'LVO' in lst and 'TP1350' not in lst and 'TP2001' not in lst
    assert '↓' in lst and '↑' not in lst
    # grelha do TAF: o voo por baixo de LPPT
    assert f.locator('#grid tr.row[data-icao="LPPT"] .fpl').count() == 1          # ✈ na hora em que o voo fica afetado
    tip = f.evaluate("document.querySelector('#grid tr.row[data-icao=LPPT] .fpl').parentElement.title")
    assert 'TP1351' in tip and 'LVO' in tip and 'TP1350' not in tip
    # clicar num voo abre o aeroporto no TAF
    page.click('#pFltList [data-icao="LPPT"] >> nth=0')
    assert visible(page, '#tafView')
    # janela Voos
    page.click('[data-nav="portal"]')
    page.click('#pFltOpen')
    f.wait_for_selector('#flights:not([hidden])')
    tab = f.inner_text('#fltOut')
    assert 'TP1351' in tab and 'CHEGADA LIS' in tab and 'PARTIDA' not in tab
    f.click('#fltAllBox summary')
    todos = f.inner_text('#fltAll')
    assert 'TP1350' in todos and 'TP2001' in todos and 'sem alerta' in todos
    # limpar
    f.click('#fltClear')
    page.wait_for_function("fltSum&&!fltSum.has", timeout=10000)
    assert page.evaluate("localStorage.getItem('tafmon.voos')") is None
    assert not errors
    ctx.close()


def test_sair_apaga_a_lista_de_voos(browser, server, mock):
    ctx, page, _ = open_app(browser, server, mock, logged_in({'tafmon.voos': json.dumps({'text': 'TP1 LIS OPO 10:00 11:00', 'name': 'x.pdf', 'at': 1})}), view='portal')
    assert page.evaluate("localStorage.getItem('tafmon.voos')") is not None
    page.evaluate("document.getElementById('logout').click()")
    page.wait_for_timeout(800)
    assert page.evaluate("localStorage.getItem('tafmon.voos')") is None
    ctx.close()


def _frame_ready(browser, server, mock):
    ctx, page, errors = open_app(browser, server, mock, logged_in(), view='portal')
    return ctx, page, errors, taf_frame(page)


def test_leitura_de_datas_e_horas(browser, server, mock):
    ctx, page, errors, f = _frame_ready(browser, server, mock)
    r = f.evaluate("""() => {
      const iso = t => new Date(t).toISOString().slice(0, 16);
      const a = parseFlights('Daily flight list 22NOV26 (UTC)\\nTP1350  LIS  BRU  22:10  01:05\\nTP1352  23/11/2026  LIS  BRU  06:00  08:45');
      const b = parseFlights('TP777 LIS BRU 2026 07:30 10:15');   // um ano solto não é hora
      const c = parseFlights('TP1703  1703  OPO  FNC  1430  1605');   // número do voo repetido noutra coluna não é hora
      return {a: a.flights.map(x => [x.fl, iso(x.std), iso(x.sta)]), b: b.flights.map(x => [iso(x.std).slice(11), iso(x.sta).slice(11)]), c: c.flights.map(x => [iso(x.std).slice(11), iso(x.sta).slice(11)])};
    }""")
    assert r['a'][0] == ['TP1350', '2026-11-22T22:10', '2026-11-23T01:05']   # data do cabeçalho; chegada no dia seguinte
    assert r['a'][1] == ['TP1352', '2026-11-23T06:00', '2026-11-23T08:45']   # data na própria linha
    assert r['b'] == [['07:30', '10:15']]
    assert r['c'] == [['14:30', '16:05']]
    # sem data: um voo da madrugada seguinte não fica no passado
    nxt = f.evaluate("""() => { const t = Date.now() + 14 * 3600e3, d = new Date(t), hh = String(d.getUTCHours()).padStart(2,'0') + ':' + String(d.getUTCMinutes()).padStart(2,'0');
      const s = new Date(t - 2 * 3600e3), sh = String(s.getUTCHours()).padStart(2,'0') + ':' + String(s.getUTCMinutes()).padStart(2,'0');
      return parseFlights(`TP9 LIS BRU ${sh} ${hh}`).flights[0].sta - Date.now(); }""")
    assert 13 * 3600e3 < nxt < 15 * 3600e3
    assert not errors
    ctx.close()


def test_cruzamento_nao_depende_das_escolhas_do_relatorio(browser, server, mock):
    """Aeroporto fora dos destinos, cenário LVO desmarcado no Relatório e "só visíveis" ligado: o voo continua afetado."""
    ctx, page, errors = open_app(browser, server, mock, logged_in(), view='portal')
    ctx.route(WORKER, _taf_json)
    f = taf_frame(page)
    f.evaluate("()=>{repUI.cats=repUI.cats.filter(c=>c!=='cig');repUI.onlyVis=true;visibleIcaos=new Set(['EGLL']);window.__portalTafCfg=Object.assign({},window.__portalTafCfg||{},{destIcao:'EGLL'});cfg.destIcao='EGLL'}")
    now = time.time()
    f.evaluate("t=>localStorage.setItem('tafmon.voos',JSON.stringify({text:t,name:'l.pdf',at:Date.now()}))",
               f'TP1350  LHR  LIS  {_hhmm(now + 3600)}  {_hhmm(now + 3 * 3600)}')
    page.evaluate("postTaf({type:'taf-refresh'})")
    page.wait_for_function("fltSum&&fltSum.has&&fltSum.restr===1", timeout=20000)
    assert 'LVO' in page.inner_text('#pFltList')
    assert f.evaluate("repUI.cats.includes('cig')") is False and f.evaluate("cfg.destIcao") == 'EGLL'  # escolhas do Relatório intactas
    assert not errors
    ctx.close()


def test_lista_do_sistema_de_operacoes_std_em_dia_hora_minuto(browser, server, mock):
    """Formato da Flight List (Time/Team/User/AL/FLT/.../DEP/DEST/ACFT/STD/ETD/AIR/CTOT): sem hora de chegada,
    STD/ETD em dia-hora-minuto, "TP" separado do número por vários espaços; a ETA é estimada pelo tempo de voo."""
    ctx, page, errors, f = _frame_ready(browser, server, mock)
    txt = ('ALL FLIGHT 22-NOV-2026 0600 22-NOV-2026 2359 User defined\n'
           'Time Team User AL FLT ATC C/S Day DEP DEST ACFT STD ETD AIR CTOT Status\n'
           '0550 -   LM   TP   016 TAP016   22   REC LIS       CSXXA 220850           0903   .... FP:3 B:0\n'
           '0645 -   RM   TP 1527 TAP1527 22     LIS ACC       CSXXB 220935 220945E 0952     .... FP:3 B:0\n'
           '1700 -   -    TP   646 TAP46RU 22    LIS BRU       CSXXC 222000           .... FP:0 B:0')
    r = f.evaluate("""t => parseFlights(t).flights.map(x => [x.fl, x.org, x.dst, new Date(x.std).toISOString().slice(0, 16),
        x.etd ? new Date(x.etd).toISOString().slice(11, 16) : '', x.etaEst, Math.round((x.eta - (x.etd || x.std)) / 60000)])""", txt)
    assert [x[:5] for x in r] == [['TP16', 'SBRF', 'LPPT', '2026-11-22T08:50', ''],
                                  ['TP1527', 'LPPT', 'DGAA', '2026-11-22T09:35', '09:45'],
                                  ['TP646', 'LPPT', 'EBBR', '2026-11-22T20:00', '']]
    assert all(x[5] for x in r)
    assert 140 <= r[2][6] <= 185      # LIS-BRU: cerca de 2h40
    assert 400 <= r[0][6] <= 480      # REC-LIS: cerca de 7h30
    assert not errors
    ctx.close()


def test_alerta_conta_da_eta_ate_1_hora_depois(browser, server, mock):
    ctx, page, errors, f = _frame_ready(browser, server, mock)
    r = f.evaluate("""() => {
      const t0 = Math.floor(Date.now() / HOUR) * HOUR + 5 * HOUR;
      allAlertItems = () => [{icao: 'EBBR', start: t0, end: t0 + HOUR, code: 'CIG', cat: 'cig', raw: 'VV001', lab0: ''}];
      const d = new Date(t0 - 162 * 60000 - 55 * 60000);   // ETA estimada 55 min antes do LVO
      const dd = String(d.getUTCDate()).padStart(2,'0'), hh = String(d.getUTCHours()).padStart(2,'0'), mm = String(d.getUTCMinutes()).padStart(2,'0');
      const in59 = flightRows(`TP646 22 LIS BRU CSXXC ${dd}${hh}${mm} ....`).rows.length;
      const d2 = new Date(d.getTime() - 10 * 60000), dd2 = String(d2.getUTCDate()).padStart(2,'0'), h2 = String(d2.getUTCHours()).padStart(2,'0'), m2 = String(d2.getUTCMinutes()).padStart(2,'0');
      const out = flightRows(`TP646 22 LIS BRU CSXXC ${dd2}${h2}${m2} ....`).rows.length;   // 65 min antes: fora
      const d3 = new Date(t0 + HOUR + 20 * 60000 - 162 * 60000), dd3 = String(d3.getUTCDate()).padStart(2,'0'), h3 = String(d3.getUTCHours()).padStart(2,'0'), m3 = String(d3.getUTCMinutes()).padStart(2,'0');
      const after = flightRows(`TP646 22 LIS BRU CSXXC ${dd3}${h3}${m3} ....`).rows.length;   // chega 20 min depois do fim do LVO: não conta
      const d4 = new Date(t0 + 30 * 60000 - 162 * 60000), dd4 = String(d4.getUTCDate()).padStart(2,'0'), h4 = String(d4.getUTCHours()).padStart(2,'0'), m4 = String(d4.getUTCMinutes()).padStart(2,'0');
      const R = flightRows(`TP646 22 LIS BRU CSXXC ${dd4}${h4}${m4} ....`).rows[0];   // chega a meio do LVO: afetado até ao fim do LVO
      return [in59, out, after, R.to - R.from, R.to === t0 + HOUR];
    }""")
    assert r == [1, 0, 0, 30 * 60000, True]
    assert not errors
    ctx.close()


def test_voos_ja_aterrados_saem_e_painel_mostra_as_chegadas(browser, server, mock):
    ctx, page, errors = open_app(browser, server, mock, logged_in(), view='portal')
    ctx.route(WORKER, _taf_json)
    f = taf_frame(page)
    now = time.time()
    lista = (f'TP1351  LHR  LIS  {_hhmm(now - 4 * 3600)}  {_hhmm(now - 3600)}\n'      # já aterrou
             f'TP1353  LHR  LIS  {_hhmm(now + 3600)}  {_hhmm(now + 3 * 3600)}\n'
             f'TP1355  LHR  LIS  {_hhmm(now + 2 * 3600)}  {_hhmm(now + 4 * 3600)}')
    f.evaluate("t=>localStorage.setItem('tafmon.voos',JSON.stringify({text:t,name:'l.pdf',at:Date.now()}))", lista)
    page.evaluate("postTaf({type:'taf-refresh'})")
    page.wait_for_function("fltSum&&fltSum.has&&fltSum.restr===2", timeout=20000)
    lst = page.inner_text('#pFltList')
    assert 'TP1353' in lst and 'TP1355' in lst and 'TP1351' not in lst
    assert page.evaluate("fltSum.landed") == 1
    # painel lateral de LPPT: as chegadas por aterrar, com o alerta
    page.evaluate("tafSelect('LPPT')")
    f.wait_for_selector('#fltDock:not([hidden])')
    pan = f.inner_text('#fltDock')                                 # voos afetados por baixo da grelha
    assert 'TP1353' in pan and 'TP1355' in pan and 'TP1351' not in pan and 'LVO' in pan
    assert 'Voos afetados · LPPT' in pan and '(2)' in pan
    assert f.locator('#fltDock .fraw u').count() >= 1                                       # TAF sublinhado
    assert f.locator('#detail .d-tabs').count() == 0 and 'Voos afetados' not in f.inner_text('#detail')   # o painel lateral fica só com a meteorologia
    # um voo de cada vez: por omissão o primeiro; escolher outro mostra só esse no TAF e na linha do tempo
    assert 'TP1353' in f.inner_text('#fltDock .fraw') and 'TP1355' not in f.inner_text('#fltDock .fraw')
    f.click('#fltDock tr[data-fsel^="TP1355"]')
    assert 'TP1355' in f.inner_text('#fltDock .fraw') and 'TP1353' not in f.inner_text('#fltDock .fraw')
    assert f.locator('#fltDock .ftl-lab', has_text='TP13').count() == 1
    f.click('#fltDock [data-fsel="*"]')
    assert 'TP1353' in f.inner_text('#fltDock .fraw') and 'TP1355' in f.inner_text('#fltDock .fraw')
    # fechar o painel lateral não fecha o quadro de baixo
    f.click('#dClose')
    assert f.locator('#fltDock').is_visible() and 'Voos afetados · LPPT' in f.inner_text('#fltDock')
    # altura do quadro: arrastar a pega para cima aumenta
    h0 = f.evaluate("document.getElementById('fltDock').getBoundingClientRect().height")
    box = f.locator('#fltDockResize').bounding_box()
    page.mouse.move(box['x'] + box['width'] / 2, box['y'] + 5); page.mouse.down()
    page.mouse.move(box['x'] + box['width'] / 2, box['y'] - 60, steps=5); page.mouse.up()
    h1 = f.evaluate("document.getElementById('fltDock').getBoundingClientRect().height")
    assert h1 > h0 + 40
    # fechar o quadro de baixo não fecha o painel lateral e não volta a abrir na atualização
    page.evaluate("tafSelect('LPPT')")
    f.wait_for_selector('#detail .d-head')
    f.click('#fltDockClose')
    assert f.locator('#fltDock').is_hidden() and f.locator('#detail .d-head').is_visible()
    f.evaluate("render()")
    assert f.locator('#fltDock').is_hidden()
    assert not errors
    ctx.close()


def test_vento_rajada_a_partir_de_35_kt(browser, server, mock):
    ctx, page, errors, f = _frame_ready(browser, server, mock)
    r = f.evaluate("""() => { const t = (ic, tok) => evaluate(apply(EMPTY, parseEl([tok])), ic).map(x => x.code).join(",") || "-";
      return {wind: cfg.wind, g34: t('EGLL', '24020G34KT'), g35: t('EGLL', '24020G35KT'), w35: t('EGLL', '24035KT'), pdl26: t('LPPD', '24020G26KT'),
              old: (() => { window.__portalTafCfg = {wind: 30}; return portalCfg().wind; })(), mine: (() => { window.__portalTafCfg = {wind: 40, windV: 3}; return portalCfg().wind; })()}; }""")
    assert r['wind'] == 35
    assert r['g34'] == '-' and r['g35'] != '-' and r['w35'] != '-'
    assert r['pdl26'] != '-'                       # Açores/Madeira continuam acima de 25 kt
    assert r['old'] == 35 and r['mine'] == 40      # definições antigas (30 kt) passam a 35; um valor escolhido depois mantém-se
    assert not errors
    ctx.close()


def test_relatorio_mostra_os_voos_na_linha_do_aeroporto(browser, server, mock):
    ctx, page, errors = open_app(browser, server, mock, logged_in(), view='portal')
    ctx.route(WORKER, _taf_json)
    f = taf_frame(page)
    now = time.time()
    f.evaluate("t=>localStorage.setItem('tafmon.voos',JSON.stringify({text:t,name:'l.pdf',at:Date.now()}))",
               f'TP1353  LHR  LIS  {_hhmm(now + 3600)}  {_hhmm(now + 3 * 3600)}\nTP1355  LHR  LIS  {_hhmm(now + 2 * 3600)}  {_hhmm(now + 4 * 3600)}')
    page.evaluate("postTaf({type:'taf-refresh'})")
    page.wait_for_function("fltSum&&fltSum.has&&fltSum.restr===2", timeout=20000)
    page.click('[data-nav="taf"]')
    f.click('#btnReport')
    f.click('#repBlk [data-blk="2"]')   # 24 H
    txt = f.input_value('#repText')
    assert 'VOOS' in txt
    lis = [l for l in txt.splitlines() if l.startswith('LPPT/LIS')][0]
    assert lis.rstrip().endswith('TP1353, TP1355')           # na mesma linha do aeroporto, só o número do voo
    assert 'TP1353' in f.inner_text('#repPrev')              # tabela (Outlook/Teams)
    # Personalizado: conta o voo cuja faixa horária apanha a faixa escolhida
    h = lambda t: time.strftime('%H', time.gmtime(t))
    f.click('#repBlk [data-blk="3"]')
    ini = (int((now + 3 * 3600) // 3600) + 2) * 3600       # começa depois da chegada do TP1353 + 1 h
    f.fill('#repWinFrom', h(ini)); f.fill('#repWinTo', h(ini + 3 * 3600))
    f.press('#repWinTo', 'Enter')
    txt = f.input_value('#repText')
    lis = [l for l in txt.splitlines() if l.startswith('LPPT/LIS')][0]
    assert 'TP1355' in lis and 'TP1353' not in lis
    assert not errors
    ctx.close()


def test_tempos_de_bloco_do_excel(browser, server, mock):
    """Administrador arrasta o Excel dos tempos de bloco: fica nas definições partilhadas (para todos) e a ETA usa o tempo
    do voo da tabela; voos do PDF que não estão na tabela (extra/renumerados) dão aviso."""
    mock.profile['role'] = 'admin'
    ctx, page, errors = open_app(browser, server, mock, logged_in(), view='portal')
    f = taf_frame(page)
    page.wait_for_function("tafSum!==null", timeout=15000)
    assert 'sem tabela' in page.inner_text('#pFltBlk')
    page.set_input_files('#pFltFile', os.path.join(os.path.dirname(__file__), 'fixtures', 'tempos-bloco-exemplo.xlsx'))
    page.wait_for_function("document.getElementById('pFltBlk').innerText.includes('4 voos')", timeout=15000)
    assert len(mock.taf_cfg['cfg']['blocks']['rows']) == 4          # guardado no servidor, não no browser
    assert page.evaluate("localStorage.getItem('tafmon.blocks')") is None
    f.wait_for_function("fltBlocks() && fltBlocks().n === 4", timeout=15000)
    r = f.evaluate("""() => { const P = parseFlights('TP   646 TAP46RU 22 LIS BRU CSXXC 222000   ....\\nTP 1527 TAP1527 22 LIS ACC CSXXB 220935 220945E 0952 ....\\nTP 9999 X 22 LIS OPO CSXXD 221000 ....');
      return P.flights.map(x => [x.fl, x.block, x.blockSrc, !!x.miss]); }""")
    assert r[0] == ['TP646', 170, 'tabela', False]
    assert r[1] == ['TP1527', 360, 'tabela', False]                  # número diferente, mesma rota LIS-ACC: usa a tabela
    assert f.evaluate("blockFor('TP109','LPPT','SBFL').min") == 660   # linha da tabela sem número de voo conta pela rota
    assert r[2] == ['TP9999', f.evaluate("blockMin('LPPT','LPPR')"), 'distância', True]
    # aviso no Início ao carregar o PDF do dia
    now = time.time()
    f.evaluate("t=>{localStorage.setItem('tafmon.voos',JSON.stringify({text:t,name:'d.pdf',at:Date.now()}))}",
               f'TP 9999 X {time.strftime("%d", time.gmtime(now))} LIS OPO CSXXD {time.strftime("%d%H%M", time.gmtime(now + 1800))} ....')
    page.evaluate("postTaf({type:'taf-refresh'})")
    page.wait_for_function("!document.getElementById('pFltMiss').classList.contains('hidden')", timeout=20000)
    assert 'TP9999' in page.inner_text('#pFltMiss') and 'não estão na tabela' in page.inner_text('#pFltMiss') or 'não está na tabela' in page.inner_text('#pFltMiss')
    assert not errors
    ctx.close()


def test_tempos_de_bloco_so_admin(browser, server, mock):
    """Operador não pode substituir a tabela partilhada, mas usa a que o Administrador carregou."""
    mock.taf_cfg['cfg'] = {'blocks': {'rows': [['TP646', 'LIS', 'BRU', 170]], 'name': 'bt.xlsx', 'at': 1, 'by': 'Ricardo'}}
    ctx, page, errors = open_app(browser, server, mock, logged_in(), view='portal')
    f = taf_frame(page)
    page.wait_for_function("document.getElementById('pFltBlk').innerText.includes('1 voos')", timeout=15000)
    f.wait_for_function("fltBlocks() && fltBlocks().n === 1", timeout=15000)
    page.set_input_files('#pFltFile', os.path.join(os.path.dirname(__file__), 'fixtures', 'tempos-bloco-exemplo.xlsx'))
    page.wait_for_function("!document.getElementById('pFltErr').classList.contains('hidden')")
    assert 'Administrador' in page.inner_text('#pFltErr')
    assert len(mock.taf_cfg['cfg']['blocks']['rows']) == 1
    assert not errors
    ctx.close()


def test_grelha_aviao_so_nos_voos_com_alerta(browser, server, mock):
    """Base com muitas chegadas: o ✈ só aparece nos voos com alerta, na célula da hora em que ficam afetados, com o número de voos."""
    ctx, page, errors = open_app(browser, server, mock, logged_in(), view='portal')
    ctx.route(WORKER, _taf_json)
    f = taf_frame(page)
    now = time.time()
    t = int(now // 3600 * 3600) + 2 * 3600 + 600                                     # todas a chegar na mesma hora
    lis = '\n'.join(f'TP{1400 + k}  LHR  LIS  {_hhmm(now + 600)}  {_hhmm(t + k * 60)}' for k in range(8))   # 8 chegadas a LIS com LVO
    lhr = '\n'.join(f'TP{1500 + k}  LIS  LHR  {_hhmm(now + 600)}  {_hhmm(now + 3600 + k * 600)}' for k in range(5))   # LHR sem alerta
    f.evaluate("t=>localStorage.setItem('tafmon.voos',JSON.stringify({text:t,name:'l.pdf',at:Date.now()}))", lis + '\n' + lhr)
    page.evaluate("postTaf({type:'taf-refresh'})")
    page.wait_for_function("fltSum&&fltSum.has&&fltSum.restr===8", timeout=20000)
    assert f.locator('#grid tr.row[data-icao="EGLL"] .fpl').count() == 0            # sem alerta: sem ✈
    assert f.locator('#grid tr.row[data-icao="LPPT"] .fpl').count() == 1
    assert f.inner_text('#grid tr.row[data-icao="LPPT"] .fpl') == '✈8'
    # carregar na célula abre o aeroporto com os voos afetados por baixo da grelha
    f.evaluate("document.querySelector('#grid tr.row[data-icao=LPPT] .fpl').parentElement.click()")
    f.wait_for_selector('#fltDock:not([hidden])')
    assert '(8)' in f.inner_text('#fltDock .fd-head')
    assert not errors
    ctx.close()


def test_filtro_com_voos(browser, server, mock):
    """Filtro "✈ Com voos": só os aeroportos com voos afetados; sem voos carregados o botão não aparece."""
    ctx, page, errors = open_app(browser, server, mock, logged_in(), view='portal')
    ctx.route(WORKER, _taf_json)
    f = taf_frame(page)
    page.wait_for_function("tafSum!==null", timeout=15000)
    assert f.locator('#fFlt').is_hidden()
    now = time.time()
    f.evaluate("t=>localStorage.setItem('tafmon.voos',JSON.stringify({text:t,name:'l.pdf',at:Date.now()}))",
               f'TP1351  LHR  LIS  {_hhmm(now + 600)}  {_hhmm(now + 3 * 3600)}\nTP1352  LIS  LHR  {_hhmm(now + 600)}  {_hhmm(now + 3 * 3600)}')
    page.evaluate("postTaf({type:'taf-refresh'})")
    page.wait_for_function("fltSum&&fltSum.has", timeout=20000)
    page.click('[data-nav="taf"]')
    f.wait_for_selector('#fFlt:not([hidden])')
    assert '(1)' in f.inner_text('#fFlt')
    f.click('#fFlt')
    f.wait_for_function("document.querySelectorAll('#grid tr.row').length === 1")
    assert f.locator('#grid tr.row[data-icao="LPPT"]').count() == 1
    assert not errors
    ctx.close()


def test_minimos_de_aproximacao_partilhados(browser, server, mock):
    """Administrador carrega o ficheiro de mínimos (.json): ficam nas definições partilhadas, aparecem no painel do
    aeroporto e o BELOW MIN/RVAC passa a usar esses valores; um operador não pode carregar."""
    mock.profile['role'] = 'admin'
    ctx, page, errors = open_app(browser, server, mock, logged_in(), view='portal')
    f = taf_frame(page)
    page.wait_for_function("tafSum!==null", timeout=15000)
    page.set_input_files('#pFltFile', os.path.join(os.path.dirname(__file__), 'fixtures', 'minimos-exemplo.json'))
    page.wait_for_function("document.getElementById('pFltBlk').innerText.includes('Exemplo · carregados por')", timeout=15000)
    assert mock.taf_cfg['cfg']['minima']['ap']['LPPT']['02']['bv'] == 200
    f.wait_for_function("RWY_BELOW.LPPT && RWY_BELOW.LPPT['02'][1] === 200", timeout=15000)
    assert f.evaluate("[RWY_MINIMA.LPPT['02'], RWY_MINIMA.LPPT['20']]") == [[400, 1750], [400, 1550]]
    assert f.evaluate("rvacCheck('LPPT', {wind: {dir: 20, spd: 10}, vis: 150, clouds: []}).code") == 'BMIN'
    assert f.evaluate("rvacCheck('LPPT', {wind: {dir: 20, spd: 10}, vis: 1500, clouds: []}).code") == 'RVAC'
    page.evaluate("tafSelect('LPPT')")
    f.wait_for_selector('#detail .mintab')
    assert 'ILS CAT IIIA' in f.inner_text('#detail .mintab')
    assert not errors
    ctx.close()


def test_minimos_incluidos_sem_carregar(browser, server, mock):
    """Sem nada carregado, os mínimos das cartas já estão em vigor para todos (LIS em CAT IIIB, FNC por circling)."""
    ctx, page, errors = open_app(browser, server, mock, logged_in(), view='portal')
    f = taf_frame(page)
    page.wait_for_function("tafSum!==null", timeout=15000)
    assert 'incluídos no site' in page.inner_text('#pFltBlk')
    f.wait_for_function("RWY_BELOW.LPPT && RWY_BELOW.LPPT['02'][1] === 75", timeout=15000)
    assert f.evaluate("[RWY_BELOW.LPMA['23'], RWY_MINIMA.LPMA['23'], RWY_BELOW.LPPD['12'], RWY_MINIMA.LPPD['12']]") == [[1200, 7000], [1400, 8000], [520, 2100], [720, 3100]]
    assert f.evaluate("[RWY_BELOW.LEMD['18L'], RWY_BELOW.LEBB['12'], RWY_MINIMA.LEBB['12'], RWY_MINIMA.LEMG['31']]") == [[0, 75], [790, 2400], [1050, 3400], [970, 3400]]
    # pistas paralelas: usa a de mínimos mais baixos na mesma direção (32L/32R → 32R)
    assert f.evaluate("minimaRwy('LEMD', {tok: '32015KT', spd: 15}).rw") == '32R'
    assert not errors
    ctx.close()



def test_resumo_dos_destinos_com_as_horas_do_taf(browser, server, mock):
    """Alerta em curso: o resumo do Início mostra o início real (antes de agora) e o fim como a última hora (igual ao TAF)."""
    H = 3600
    t0 = int(time.time() // H * H)
    g = lambda t: time.strftime('%d%H', time.gmtime(t))

    def tafs(route):
        if 'type=metar' in route.request.url:
            return route.fulfill(status=200, content_type='application/json', body='[]')
        iss = time.strftime('%d%H%MZ', time.gmtime(t0 - 4 * H))
        raw = f'TAF DGAA {iss} {g(t0 - 4 * H)}/{g(t0 + 24 * H)} 18013KT 9999 SCT020 PROB30 TEMPO {g(t0 - 2 * H)}/{g(t0 + 2 * H)} 7000 -TSRA BKN010CB'
        return route.fulfill(status=200, content_type='application/json', headers={'Access-Control-Allow-Origin': '*'},
                             body=json.dumps([{'icaoId': 'DGAA', 'issueTime': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(t0 - 4 * H)), 'rawTAF': raw}]))
    ctx, page, errors = open_app(browser, server, mock, logged_in(), view='portal')
    ctx.route(WORKER, tafs)
    taf_frame(page)
    page.evaluate("postTaf({type:'taf-refresh'})")
    page.wait_for_function("tafSum && (tafSum.alerts||[]).some(a=>a.icao==='DGAA')", timeout=20000)
    a = page.evaluate("tafSum.alerts.find(a=>a.icao==='DGAA')")
    assert a['now'] and a['from'] == (t0 - 2 * H) * 1000 and a['to'] == (t0 + 2 * H) * 1000
    page.wait_for_selector('#pAlertList [data-icao="DGAA"]')
    txt = page.inner_text('#pAlertList [data-icao="DGAA"]')
    assert f'{g(t0 - 2 * H)}/{g(t0 + 2 * H)}' in txt and 'AGORA' not in txt
    assert not errors
    ctx.close()


def test_voo_no_ar_conta_o_metar_em_todo_o_lado(browser, server, mock):
    ctx, page, errors = open_app(browser, server, mock, logged_in(), view='portal')
    ctx.route(WORKER, _taf_json)
    f = taf_frame(page)
    now = time.time()
    lista = f'TP1357  LHR  LIS  {_hhmm(now - 1800)}  {_hhmm(now + 3600)}'          # já saiu; chega dentro de 1 h
    f.evaluate("t=>localStorage.setItem('tafmon.voos',JSON.stringify({text:t,name:'l.pdf',at:Date.now()}))", lista)
    page.evaluate("postTaf({type:'taf-refresh'})")
    page.wait_for_function("fltSum&&fltSum.has&&fltSum.restr===1", timeout=20000)
    # METAR limpo: o voo já saiu, por isso conta o METAR e deixa de estar afetado (grelha e Início também)
    f.evaluate("metars.LPPT={obs:Date.now()-600000,raw:'METAR LPPT 270800Z 00000KT CAVOK 10/05 Q1020'};render()")
    page.wait_for_function("fltSum.restr===0&&fltSum.alert===0", timeout=10000)
    assert f.locator('#grid tr.row[data-icao="LPPT"] .fpl').count() == 0
    # METAR com nevoeiro: volta a estar afetado, com fonte METAR
    f.evaluate("metars.LPPT={obs:Date.now()-600000,raw:'METAR LPPT 270800Z 00000KT 0200 FG VV001 10/10 Q1020'};render()")
    page.wait_for_function("fltSum.restr===1", timeout=10000)
    page.evaluate("tafSelect('LPPT')")
    f.wait_for_selector('#fltDock:not([hidden])')
    txt = f.inner_text('#fltDock')
    assert 'TP1357' in txt and 'METAR' in txt
    assert f.locator('#grid tr.row[data-icao="LPPT"] .fpl').count() == 1
    assert not errors
    ctx.close()


def test_relatorio_so_destinos_com_voos_afetados(browser, server, mock):
    ctx, page, errors = open_app(browser, server, mock, logged_in(), view='portal')
    def taf2(route):            # Lisboa e Porto com nevoeiro; só Lisboa tem voos
        if 'type=metar' in route.request.url:
            return route.fulfill(status=200, content_type='application/json', body='[]')
        t0 = int(time.time() // 3600 * 3600) - 3600
        g = lambda t: time.strftime('%d%H', time.gmtime(t))
        iss, per, it = time.strftime('%d%H%MZ', time.gmtime(t0)), f'{g(t0)}/{g(t0 + 30 * 3600)}', time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(t0))
        tafs = [{'icaoId': ic, 'issueTime': it, 'rawTAF': f'TAF {ic} {iss} {per} VRB02KT 0300 FG VV001'} for ic in ('LPPT', 'LPPR')]
        return route.fulfill(status=200, content_type='application/json', headers={'Access-Control-Allow-Origin': '*'}, body=json.dumps(tafs))
    ctx.route(WORKER, taf2)
    f = taf_frame(page)
    now = time.time()
    f.evaluate("t=>localStorage.setItem('tafmon.voos',JSON.stringify({text:t,name:'l.pdf',at:Date.now()}))",
               f'TP1353  LHR  LIS  {_hhmm(now + 3600)}  {_hhmm(now + 3 * 3600)}')
    page.evaluate("postTaf({type:'taf-refresh'})")
    page.wait_for_function("fltSum&&fltSum.has&&fltSum.restr===1", timeout=20000)
    page.click('[data-nav="taf"]')
    f.click('#btnReport')
    f.click('#repBlk [data-blk="2"]')   # 24 H
    linhas = lambda: [l for l in f.input_value('#repText').splitlines() if re.match(r'^[A-Z]{4}/', l)]
    antes = linhas()
    assert any('TP1353' not in l for l in antes)               # há destinos com alerta mas sem voos
    assert f.locator('#repFltLab').is_visible()
    f.check('#repFlt')
    depois = linhas()
    assert depois and all('TP1353' in l for l in depois) and all(l.startswith('LPPT/LIS') for l in depois)
    assert 'SÓ VOOS AFETADOS' in f.input_value('#repText')
    html = f.evaluate('reportText().copyHtml')                  # tabela copiada sem larguras fixas (o Word ajusta)
    assert 'table-layout' not in html and 'width:' not in html and 'TP1353' in html
    assert f.evaluate("repFltLines('TP1, TP2, TP3, TP4, TP5')") == 'TP1, TP2, TP3,<br>TP4, TP5'
    f.uncheck('#repFlt')
    assert len(linhas()) == len(antes)
    assert not errors
    ctx.close()


def test_voos_afetados_mostra_minimos_a_chegada(browser, server, mock):
    ctx, page, errors = open_app(browser, server, mock, logged_in(), view='portal')
    def taf3(route):            # Lisboa 300 m (acima do CAT IIIB) e Porto 150 m VV001 (abaixo do CAT II)
        if 'type=metar' in route.request.url:
            return route.fulfill(status=200, content_type='application/json', body='[]')
        t0 = int(time.time() // 3600 * 3600) - 3600
        g = lambda t: time.strftime('%d%H', time.gmtime(t))
        iss, per, it = time.strftime('%d%H%MZ', time.gmtime(t0)), f'{g(t0)}/{g(t0 + 30 * 3600)}', time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(t0))
        tafs = [{'icaoId': 'LPPT', 'issueTime': it, 'rawTAF': f'TAF LPPT {iss} {per} VRB02KT 0300 FG VV001'},
                {'icaoId': 'LPPR', 'issueTime': it, 'rawTAF': f'TAF LPPR {iss} {per} 18005KT 0150 FG VV001'}]
        return route.fulfill(status=200, content_type='application/json', headers={'Access-Control-Allow-Origin': '*'}, body=json.dumps(tafs))
    ctx.route(WORKER, taf3)
    page.set_viewport_size({'width': 1900, 'height': 1000})
    f = taf_frame(page)
    now = time.time()
    f.evaluate("t=>localStorage.setItem('tafmon.voos',JSON.stringify({text:t,name:'l.pdf',at:Date.now()}))",
               f'TP1353  LHR  LIS  {_hhmm(now + 3600)}  {_hhmm(now + 3 * 3600)}\nTP1940  LIS  OPO  {_hhmm(now + 3600)}  {_hhmm(now + 2 * 3600)}')
    page.evaluate("postTaf({type:'taf-refresh'})")
    page.wait_for_function("fltSum&&fltSum.has&&fltSum.restr===2", timeout=20000)
    page.evaluate("tafSelect('LPPT')")
    f.wait_for_selector('#fltDock:not([hidden]) .fmin')
    assert 'MINIMA' in f.inner_text('#fltDock thead').upper() and f.inner_text('#fltDock .fmin').startswith('ABOVE MIN')
    page.evaluate("tafSelect('LPPR')")
    f.wait_for_function("document.querySelector('#fltDock h3').textContent.includes('LPPR')")
    assert f.inner_text('#fltDock .fmin').startswith('BELOW MIN')
    assert 'CAT II 100/300' in f.inner_text('#fltDock .fmn')
    assert not errors
    ctx.close()


def test_limites_vento_lpma_carta_lido(browser, server, mock):
    ctx, page, errors = open_app(browser, server, mock, logged_in(), view='portal')
    f = taf_frame(page)
    lim = f.evaluate("[300,5,30,125,150,190,215,90,null].map(d=>{const l=ldgLimit('LPMA',d);return l?[l.spd,l.gust]:null})")
    # 120–190: RWY 05 em uso (vento até 135°) 20/30; RWY 23 em uso 15/25; VRB → o mais restritivo
    assert lim == [[15, 25], [15, 25], [20, 30], [20, 30], [15, 25], [15, 25], [25, 25], None, [15, 25]]
    assert 'RWY 23' in f.evaluate("ldgLimit('LPMA',160).label") and 'RWY 05' in f.evaluate("ldgLimit('LPMA',125).label")
    assert not errors
    ctx.close()

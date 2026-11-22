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
    sub = f.inner_text('#grid tr[data-icao="LPPT"] .ap-flt')
    assert 'TP1351' in sub and 'TP1350' not in sub
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


def test_eta_estimada_conta_59_min_antes_e_depois(browser, server, mock):
    ctx, page, errors, f = _frame_ready(browser, server, mock)
    r = f.evaluate("""() => {
      const t0 = Math.floor(Date.now() / HOUR) * HOUR + 5 * HOUR;
      allAlertItems = () => [{icao: 'EBBR', start: t0, end: t0 + HOUR, code: 'CIG', cat: 'cig', raw: 'VV001', lab0: ''}];
      const d = new Date(t0 - 162 * 60000 - 55 * 60000);   // ETA estimada 55 min antes do LVO
      const dd = String(d.getUTCDate()).padStart(2,'0'), hh = String(d.getUTCHours()).padStart(2,'0'), mm = String(d.getUTCMinutes()).padStart(2,'0');
      const in59 = flightRows(`TP646 22 LIS BRU CSXXC ${dd}${hh}${mm} ....`).rows.length;
      const d2 = new Date(d.getTime() - 10 * 60000), dd2 = String(d2.getUTCDate()).padStart(2,'0'), h2 = String(d2.getUTCHours()).padStart(2,'0'), m2 = String(d2.getUTCMinutes()).padStart(2,'0');
      const out = flightRows(`TP646 22 LIS BRU CSXXC ${dd2}${h2}${m2} ....`).rows.length;   // 65 min antes: fora
      return [in59, out];
    }""")
    assert r == [1, 0]
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
    f.wait_for_selector('#detail .d-flt')
    pan = f.inner_text('#detail .d-flt')
    assert 'TP1353' in pan and 'TP1355' in pan and 'TP1351' not in pan and 'LVO' in pan
    assert 'VOOS · CHEGADAS (2, 2 COM ALERTA)' in f.inner_text('#detail').upper()
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
    ini = (int((now + 3 * 3600) // 3600) + 1) * 3600       # começa depois da chegada do TP1353 (STA real, sem margem)
    f.fill('#repWinFrom', h(ini)); f.fill('#repWinTo', h(ini + 3 * 3600))
    f.press('#repWinTo', 'Enter')
    txt = f.input_value('#repText')
    lis = [l for l in txt.splitlines() if l.startswith('LPPT/LIS')][0]
    assert 'TP1355' in lis and 'TP1353' not in lis
    assert not errors
    ctx.close()

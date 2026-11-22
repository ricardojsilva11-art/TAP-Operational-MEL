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
    page.wait_for_function("fltSum&&fltSum.has&&fltSum.restr===2", timeout=20000)
    # Início: partida de LIS e chegada a LIS com LVO; o voo LHR-CDG não tem alerta
    assert page.inner_text('#pFltRestr') == '2' and page.inner_text('#pFltAlert') == '0' and page.inner_text('#pFltTotal') == '3'
    lst = page.inner_text('#pFltList')
    assert 'TP1350' in lst and 'TP1351' in lst and 'LVO' in lst and 'TP2001' not in lst
    assert '↑' in lst and '↓' in lst
    # grelha do TAF: os voos por baixo de LPPT
    sub = f.inner_text('#grid tr[data-icao="LPPT"] .ap-flt')
    assert 'TP1350' in sub and 'TP1351' in sub
    # clicar num voo abre o aeroporto no TAF
    page.click('#pFltList [data-icao="LPPT"] >> nth=0')
    assert visible(page, '#tafView')
    # janela Voos
    page.click('[data-nav="portal"]')
    page.click('#pFltOpen')
    f.wait_for_selector('#flights:not([hidden])')
    tab = f.inner_text('#fltOut')
    assert 'TP1350' in tab and 'PARTIDA LIS' in tab and 'CHEGADA LIS' in tab
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

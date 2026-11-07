"""Consulta offline: última cópia guardada no dispositivo, só leitura."""
from harness import SKEY, logged_in, open_app, visible


def state(page):
    return page.evaluate("""()=>({banner:!document.getElementById('offBanner').classList.contains('hidden'),
      app:!document.getElementById('appPanel').classList.contains('hidden'),
      add:!document.getElementById('add').classList.contains('hidden'),
      rows:document.querySelectorAll('#rows tr[data-id]').length,
      session:Object.keys(localStorage).some(k=>k.startsWith('sb-')),
      cache:!!localStorage.getItem('mel_offline_v1'),
      loginError:document.getElementById('loginError').textContent})""")


def get_cache(browser, server, mock):
    ctx, page, _ = open_app(browser, server, mock, logged_in())
    cache = page.evaluate("localStorage.getItem('mel_offline_v1')")
    ctx.close()
    assert cache
    return cache


def test_online_guarda_copia(browser, server, mock):
    ctx, page, errors = open_app(browser, server, mock, logged_in())
    s = state(page)
    assert s['app'] and not s['banner'] and s['rows'] == 3 and s['cache'] and s['add']
    assert not errors
    ctx.close()


def test_ligacao_cai_e_volta(browser, server, mock):
    ctx, page, _ = open_app(browser, server, mock, logged_in())
    mock.up = False
    page.click('#refresh')
    page.wait_for_selector('#offBanner:not(.hidden)', timeout=40000)
    s = state(page)
    assert s['rows'] == 3 and not s['add']
    assert 'Sem ligação ao servidor' in page.inner_text('#offText')
    mock.up = True
    page.click('#offRetry')
    page.wait_for_selector('#offBanner.hidden', state='attached', timeout=20000)
    assert state(page)['add']
    ctx.close()


def test_arranque_sem_servidor_com_sessao_mostra_copia(browser, server, mock):
    cache = get_cache(browser, server, mock)
    mock.up = False
    ctx, page, errors = open_app(browser, server, mock, logged_in({'mel_offline_v1': cache}))
    s = state(page)
    assert s['banner'] and s['app'] and s['rows'] == 3 and s['session'] and not s['add']
    assert not errors
    ctx.close()


def test_arranque_sem_servidor_sem_sessao_mostra_copia(browser, server, mock):
    cache = get_cache(browser, server, mock)
    mock.up = False
    ctx, page, _ = open_app(browser, server, mock, {'mel_offline_v1': cache})
    s = state(page)
    assert s['banner'] and s['app'] and s['rows'] == 3
    ctx.close()


def test_sem_copia_nao_termina_sessao(browser, server, mock):
    mock.up = False
    ctx, page, _ = open_app(browser, server, mock, logged_in())
    s = state(page)
    assert not s['app'] and s['session'] and 'Sem ligação' in s['loginError']
    ctx.close()


def test_servidor_ok_sem_sessao_apaga_copia(browser, server, mock):
    cache = get_cache(browser, server, mock)
    ctx, page, _ = open_app(browser, server, mock, {'mel_offline_v1': cache})
    s = state(page)
    assert not s['app'] and not s['cache']
    ctx.close()


def test_service_worker_abre_sem_rede(browser, server, mock):
    ctx, page, _ = open_app(browser, server, mock, logged_in(), service_workers='allow')
    page.evaluate('navigator.serviceWorker.ready')
    page.wait_for_function("navigator.serviceWorker.controller!==null||performance.now()>8000", timeout=15000)
    page.reload()
    page.wait_for_timeout(1500)
    ctx.set_offline(True)
    page.reload()
    page.wait_for_selector('#offBanner:not(.hidden)', timeout=20000)
    assert state(page)['rows'] == 3
    ctx.close()


def test_terminar_sessao_apaga_copia(browser, server, mock):
    ctx, page, _ = open_app(browser, server, mock, logged_in())
    page.click('#logout')
    page.wait_for_timeout(1200)
    s = state(page)
    assert not s['cache'] and not s['session'] and not s['app']
    ctx.close()

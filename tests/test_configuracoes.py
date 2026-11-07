"""Página Configurações (administradores)."""
import time

import openpyxl
import pytest

from harness import OTHER, logged_in, open_app, rec, visible


@pytest.fixture
def admin(mock):
    mock.profile['role'] = 'admin'
    mock.revisions[0].update(revision='45', effective_date='2026-10-01', updated_at='2026-10-02T10:00:00Z', updated_by_name='Ricardo')
    mock.audit = [{'id': 5, 'record_id': 'r1', 'action': 'UPDATE', 'changed_by': OTHER, 'changed_at': '2026-11-07T09:00:00Z',
                   'old_record': rec('r1', 'A320', 'M-21-26-01', 'a'), 'new_record': rec('r1', 'A320', 'M-21-26-01', 'b', updated_by_name='Ana Silva')},
                  {'id': 4, 'record_id': 'r2', 'action': 'DEACTIVATE', 'changed_by': OTHER, 'changed_at': '2026-11-06T09:00:00Z',
                   'old_record': rec('r2', 'A320', 'M-21-26-02'), 'new_record': rec('r2', 'A320', 'M-21-26-02', active=False, updated_by_name='Rui')}]
    return mock


def open_settings(browser, server, mock):
    ctx, page, errors = open_app(browser, server, mock, logged_in())
    page.on('dialog', lambda d: d.accept())
    page.click('#navSettings')
    page.wait_for_timeout(600)
    return ctx, page, errors


def patches(mock, table):
    return [b for m, p, b in mock.requests if m == 'PATCH' and table in p]


def test_revisao_no_cartao_da_frota(browser, server, admin):
    ctx, page, _ = open_app(browser, server, admin, logged_in())
    assert page.inner_text('.fleet-card[data-f="A320"] .revtag') == 'Rev. 45 · desde 01/10/2026'
    assert not visible(page, '.fleet-card[data-f="A330"] .revtag')
    ctx.close()


def test_definicoes_gravam(browser, server, admin):
    ctx, page, errors = open_settings(browser, server, admin)
    assert visible(page, '#settingsView') and page.inner_text('#setSignupsTxt') == 'Abertos'
    page.click('.switch')
    page.wait_for_timeout(400)
    page.select_option('#setSession', '8')
    page.wait_for_timeout(400)
    assert '{"signups_open":false}' in patches(admin, 'app_settings')
    assert '{"session_hours":8}' in patches(admin, 'app_settings')
    assert page.inner_text('#setSignupsTxt') == 'Fechados'
    assert not errors
    ctx.close()


def test_revisoes_guardar_e_apagar(browser, server, admin):
    ctx, page, _ = open_settings(browser, server, admin)
    page.fill('#revRows tr[data-fleet="A330"] [data-k="revision"]', '12')
    page.fill('#revRows tr[data-fleet="A330"] [data-k="effective_date"]', '2026-11-01')
    page.click('#revSave')
    page.wait_for_timeout(600)
    assert '{"revision":"12","effective_date":"2026-11-01"}' in patches(admin, 'fleet_revisions')
    page.click('[data-revdel="A320"]')
    page.wait_for_timeout(600)
    assert '{"revision":"","effective_date":null}' in patches(admin, 'fleet_revisions')
    assert not visible(page, '.fleet-card[data-f="A320"] .revtag')
    ctx.close()


def test_atividade_recente(browser, server, admin):
    ctx, page, _ = open_settings(browser, server, admin)
    assert page.input_value('#actPeriod') == '1'
    assert page.evaluate("document.querySelectorAll('#actRows tr').length") == 2
    page.select_option('#actPerson', 'Rui')
    assert page.evaluate("document.querySelectorAll('#actRows tr').length") == 1
    page.select_option('#actPerson', '')
    page.click('#actRows tr[data-rec="r1"]')
    page.wait_for_selector('#auditModal.show')
    ctx.close()


def test_copia_de_seguranca(browser, server, admin, tmp_path):
    admin.rows = [rec('r1', 'A320', 'M-21-26-01', html='<div>Linha 1</div><div>Linha 2</div>'), rec('r9', 'A330', 'C-21-01', 'apagada', active=False)]
    ctx, page, _ = open_settings(browser, server, admin)
    with page.expect_download() as d:
        page.click('#setBackupBtn')
    path = tmp_path / 'backup.xlsx'
    d.value.save_as(path)
    page.wait_for_timeout(500)
    wb = openpyxl.load_workbook(path)
    assert wb.sheetnames == ['MEL ativas', 'Histórico (apagadas)', 'Revisões', 'Informação']
    assert wb['MEL ativas'].cell(2, 4).value == 'Linha 1\nLinha 2'
    assert wb['MEL ativas'].cell(2, 4).alignment.wrap_text
    assert wb['Histórico (apagadas)'].cell(2, 2).value == 'C-21-01'
    assert any('last_backup_at' in (b or '') for b in patches(admin, 'app_settings'))
    assert 'Ricardo' in page.inner_text('#setBackupInfo')
    ctx.close()


def test_sessao_termina_por_inatividade(browser, server, mock):
    mock.settings['session_hours'] = 1
    two_hours_ago = str(int(time.time() * 1000) - 2 * 3600 * 1000)
    ctx, page, _ = open_app(browser, server, mock, logged_in({'mel_last_activity': two_hours_ago}))
    page.wait_for_timeout(1200)
    assert not visible(page, '#appPanel')
    assert 'sem atividade' in page.inner_text('#loginInfo')
    assert not page.evaluate("Object.keys(localStorage).some(k=>k.startsWith('sb-'))")
    ctx.close()


def test_sessao_com_atividade_recente_continua(browser, server, mock):
    mock.settings['session_hours'] = 1
    ten_min_ago = str(int(time.time() * 1000) - 10 * 60 * 1000)
    ctx, page, _ = open_app(browser, server, mock, logged_in({'mel_last_activity': ten_min_ago}))
    assert visible(page, '#appPanel')
    ctx.close()


def test_registos_fechados_escondem_criar_conta(browser, server, mock):
    mock.settings['signups_open'] = False
    ctx, page, _ = open_app(browser, server, mock, {})
    page.wait_for_timeout(500)
    assert not visible(page, '[data-auth="signup"]')
    ctx.close()


def test_sem_sql_010_a_app_continua(browser, server, admin):
    admin.tables_missing = True
    ctx, page, errors = open_settings(browser, server, admin)
    assert 'Falta correr' in page.inner_text('#setNote')
    assert page.evaluate("document.getElementById('setSignups').disabled")
    assert page.evaluate("document.querySelectorAll('#rows tr[data-id]').length") == 3
    assert not errors
    ctx.close()

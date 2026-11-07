"""MEL: validações, histórico de alterações, avisos em tempo real e exportação Excel."""
import json

import openpyxl

from harness import OTHER, UID, logged_in, open_app, rec


def accept_dialogs(page, store=None):
    page.on('dialog', lambda d: ((store.append(d.message) if store is not None else None), d.accept()))


def test_formato_recusado_pela_base_de_dados(browser, server, mock):
    mock.fail_format = True
    ctx, page, _ = open_app(browser, server, mock, logged_in())
    page.click('#rows tr[data-id="r3"] [data-edit]')
    page.click('#recordForm button.primary')
    page.wait_for_timeout(800)
    assert 'tem de seguir o formato' in page.inner_text('#recordError')
    ctx.close()


def test_formato_validado_na_app(browser, server, mock):
    ctx, page, _ = open_app(browser, server, mock, logged_in())
    ok = page.evaluate("['M-34-50','M-21-26-01A','M-21-51-00-A','M-23-51-00-03-B','C-21','C-21-01'].every(v=>MEL_RE.test(v))")
    bad = page.evaluate("['M-21','M-21-2','M-34-50-09F (ver MEL)','m-21-26-01','M-21-26-01ABC'].some(v=>MEL_RE.test(v))")
    assert ok and not bad
    ctx.close()


def test_duplicado_bloqueado_antes_de_gravar(browser, server, mock):
    ctx, page, _ = open_app(browser, server, mock, logged_in())
    page.click('#add')
    page.fill('#melItem', 'M-21-26-01')
    page.evaluate("document.querySelector('#fleetPick input[value=\"A320\"]').click()")
    page.evaluate("document.getElementById('editor').innerText='Impacto 1'")
    page.click('#recordForm button.primary')
    page.wait_for_timeout(400)
    assert 'Já existe uma MEL ativa' in page.inner_text('#recordError')
    assert not any(m == 'POST' and 'mel_records' in p for m, p, _ in mock.requests)
    ctx.close()


def test_historico_de_alteracoes_e_repor(browser, server, mock):
    v0 = rec('r1', 'A320', 'M-21-26-01', 'May be inoperative provided that the blower fan is operative.')
    v1 = dict(v0, operational_impact='May be inoperative provided that the blower and extract fans are operative.', updated_by=OTHER, updated_by_name='Ana Silva')
    v2 = dict(v1, notes='Confirmar com MCC', updated_by=UID, updated_by_name='Ricardo')
    mock.rows = [dict(v2), rec('r2', 'A330', 'M-21-28-03A', 'x')]
    mock.audit = [{'id': 3, 'action': 'UPDATE', 'changed_by': UID, 'changed_at': '2026-11-07T10:00:00Z', 'old_record': v1, 'new_record': v2},
                  {'id': 2, 'action': 'UPDATE', 'changed_by': OTHER, 'changed_at': '2026-11-06T09:00:00Z', 'old_record': v0, 'new_record': v1},
                  {'id': 1, 'action': 'INSERT', 'changed_by': None, 'changed_at': '2026-11-01T10:00:00Z', 'old_record': None, 'new_record': v0}]
    ctx, page, errors = open_app(browser, server, mock, logged_in())
    accept_dialogs(page)
    page.click('#rows tr[data-id="r1"] [data-audit]')
    page.wait_for_selector('.aud-item')
    assert page.evaluate("document.querySelectorAll('.aud-item').length") == 3
    diff = page.evaluate("[...document.querySelectorAll('.aud-diff ins,.aud-diff del')].map(x=>x.tagName+':'+x.textContent)")
    assert 'DEL:fan is' in diff and 'INS:and extract fans are' in diff
    assert 'Importado' in page.inner_text('.aud-item:last-child')
    assert page.evaluate("document.querySelectorAll('[data-audrestore]').length") == 2
    page.click('[data-audrestore="2"]')
    page.wait_for_timeout(800)
    body = next(b for m, p, b in mock.requests if m == 'PATCH' and 'mel_records' in p)
    assert 'blower and extract fans' in json.loads(body)['operational_impact']
    assert not errors
    ctx.close()


def test_avisos_de_alteracoes_de_outros(browser, server, mock):
    ctx, page, _ = open_app(browser, server, mock, logged_in())
    page.evaluate("""()=>{const r2=rows.find(r=>r.id==='r2');
      notifyChange({eventType:'UPDATE',new:{...r2,updated_by:'%s',updated_by_name:'Ana Silva'},old:{id:'r2'}});
      notifyChange({eventType:'UPDATE',new:{...r2,updated_by:'%s',updated_by_name:'Eu'},old:{id:'r2'}});
      notifyChange({eventType:'INSERT',new:{id:'r9',fleet:'E190/E195',mel_item:'C-05-01',created_by:'%s',created_by_name:'Marta'},old:{}});}""" % (OTHER, UID, OTHER))
    toasts = page.evaluate("[...document.querySelectorAll('.live-toast')].map(t=>t.innerText)")
    assert any('Ana Silva alterou M-21-26-02 (A320)' in t for t in toasts)
    assert any('Marta adicionou C-05-01' in t for t in toasts)
    assert not any('Eu ' in t for t in toasts)
    ctx.close()


def test_exportar_excel_ordenado_e_formatado(browser, server, mock, tmp_path):
    mock.rows = [rec('a', 'E190/E195', 'C-05-01', html='Linha 1<br>Linha 2'),
                 rec('b', 'A330', 'M-21-21-01B', 'Cabin Fan:\n- The fuel consumption'),
                 rec('c', 'A320', 'M-21-26-10A', 'x'),
                 rec('d', 'A320', 'M-21-3-01', 'y'),
                 rec('e', 'A320', 'M-21-26-02A', html='<div>VENT AVNCS SYS FAULT not displayed</div><div>May be inoperative provided that:</div><ol><li>The blower fan</li><li>The EXTRACT fan</li></ol>')]
    mock.revisions[0].update(revision='45', effective_date='2026-10-01')
    ctx, page, _ = open_app(browser, server, mock, logged_in())
    with page.expect_download() as d:
        page.click('#export')
    path = tmp_path / 'export.xlsx'
    d.value.save_as(path)
    ws = openpyxl.load_workbook(path).active
    rows = [[c.value for c in r] for r in ws.iter_rows(min_row=2)]
    assert [(r[0], r[1]) for r in rows] == [('A320', 'M-21-3-01'), ('A320', 'M-21-26-02A'), ('A320', 'M-21-26-10A'), ('A330', 'M-21-21-01B'), ('E190/E195', 'C-05-01')]
    assert rows[1][3] == 'VENT AVNCS SYS FAULT not displayed\nMay be inoperative provided that:\n1) The blower fan\n2) The EXTRACT fan'
    assert rows[4][3] == 'Linha 1\nLinha 2'
    assert ws.cell(2, 4).alignment.wrap_text
    assert rows[0][6] == 'Rev. 45 · desde 01/10/2026'
    ctx.close()

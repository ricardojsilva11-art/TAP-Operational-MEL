"""Anexos PDF nas MEL."""
from harness import logged_in, open_app, visible

PDF = b'%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n'


def att(i, rid, name, path):
    return {'id': i, 'record_id': rid, 'file_name': name, 'storage_path': path, 'size_bytes': 2048,
            'uploaded_by_name': 'Ana', 'uploaded_at': '2026-11-08T10:00:00Z'}


def test_contador_e_lista(browser, server, mock):
    mock.attachments = [att('a1', 'r1', 'MEL 21-26.pdf', 'r1/a.pdf'), att('a2', 'r1', 'Boletim.pdf', 'r1/b.pdf')]
    ctx, page, errors = open_app(browser, server, mock, logged_in())
    page.wait_for_selector('#rows tr[data-id="r1"] [data-att] .n')
    assert page.inner_text('#rows tr[data-id="r1"] [data-att] .n') == '2'
    assert page.evaluate("document.querySelector('#rows tr[data-id=\"r2\"] [data-att] .n')") is None
    page.click('#rows tr[data-id="r1"] [data-att]')
    page.wait_for_selector('.att-item')
    names = page.evaluate("[...document.querySelectorAll('.att-meta b')].map(b=>b.textContent)")
    assert set(names) == {'MEL 21-26.pdf', 'Boletim.pdf'}
    assert visible(page, '#attDrop')
    assert not errors
    ctx.close()


def test_anexar_e_apagar(browser, server, mock, tmp_path):
    ctx, page, errors = open_app(browser, server, mock, logged_in())
    page.on('dialog', lambda d: d.accept())
    page.wait_for_selector('#rows tr[data-id="r2"] [data-att]')
    page.click('#rows tr[data-id="r2"] [data-att]')
    page.wait_for_timeout(300)
    f = tmp_path / 'Manual A320.pdf'
    f.write_bytes(PDF)
    page.set_input_files('#attFile', str(f))
    page.wait_for_selector('.att-item')
    assert page.inner_text('.att-meta b') == 'Manual A320.pdf'
    assert len(mock.storage) == 1 and list(mock.storage)[0].startswith('r2/')
    assert mock.attachments[0]['record_id'] == 'r2'
    page.click('#attClose')
    assert page.inner_text('#rows tr[data-id="r2"] [data-att] .n') == '1'
    page.click('#rows tr[data-id="r2"] [data-att]')
    page.wait_for_selector('[data-attdel]')
    page.click('[data-attdel]')
    page.wait_for_timeout(600)
    assert mock.attachments == [] and mock.storage == {}
    assert page.evaluate("document.querySelectorAll('.att-item').length") == 0
    assert not errors
    ctx.close()


def test_recusa_ficheiro_que_nao_e_pdf(browser, server, mock, tmp_path):
    ctx, page, _ = open_app(browser, server, mock, logged_in())
    msgs = []
    page.on('dialog', lambda d: (msgs.append(d.message), d.accept()))
    page.wait_for_selector('#rows tr[data-id="r1"] [data-att]')
    page.click('#rows tr[data-id="r1"] [data-att]')
    f = tmp_path / 'foto.png'
    f.write_bytes(b'\x89PNG')
    page.set_input_files('#attFile', str(f))
    page.wait_for_timeout(500)
    assert mock.storage == {} and any('não é um PDF' in m for m in msgs)
    ctx.close()


def test_abrir_gera_link_temporario(browser, server, mock):
    mock.attachments = [att('a1', 'r1', 'MEL.pdf', 'r1/a.pdf')]
    ctx, page, _ = open_app(browser, server, mock, logged_in())
    page.wait_for_selector('#rows tr[data-id="r1"] [data-att]')
    page.click('#rows tr[data-id="r1"] [data-att]')
    page.wait_for_selector('[data-attopen]')
    with ctx.expect_page() as newp:
        page.click('[data-attopen]')
    p2 = newp.value
    p2.wait_for_url('**/object/sign/mel-pdfs/r1/a.pdf**', timeout=10000)
    ctx.close()


def test_so_consulta_ve_mas_nao_anexa(browser, server, mock):
    mock.profile['role'] = 'reader'
    mock.attachments = [att('a1', 'r1', 'MEL.pdf', 'r1/a.pdf')]
    ctx, page, _ = open_app(browser, server, mock, logged_in())
    page.wait_for_selector('#rows tr[data-id="r1"] [data-att]')
    page.click('#rows tr[data-id="r1"] [data-att]')
    page.wait_for_selector('.att-item')
    assert not visible(page, '#attDrop')
    assert page.evaluate("document.querySelectorAll('[data-attdel]').length") == 0
    assert page.evaluate("document.querySelectorAll('[data-attopen]').length") == 1
    ctx.close()


def test_sem_sql_011_nao_mostra_botao(browser, server, mock):
    mock.attach_missing = True
    ctx, page, errors = open_app(browser, server, mock, logged_in())
    page.wait_for_timeout(600)
    assert page.evaluate("document.querySelectorAll('[data-att]').length") == 0
    assert page.evaluate("document.querySelectorAll('#rows tr[data-id]').length") == 3
    assert not errors
    ctx.close()


def test_formulario_adicionar_com_anexos_em_varias_frotas(browser, server, mock, tmp_path):
    ctx, page, errors = open_app(browser, server, mock, logged_in())
    page.wait_for_selector('#rows tr[data-id="r1"] [data-att]')
    page.click('#add')
    assert visible(page, '#fAttWrap')
    page.fill('#melItem', 'M-21-99-01')
    page.dispatch_event('#melItem', 'input')
    page.evaluate("['A320','A330'].forEach(v=>document.querySelector(`#fleetPick input[value=\"${v}\"]`).click())")
    page.evaluate("document.getElementById('editor').innerText='Novo impacto'")
    f = tmp_path / 'Procedimento.pdf'
    f.write_bytes(PDF)
    page.set_input_files('#fAttFile', str(f))
    assert page.inner_text('#fAttList .fatt-item b') == 'Procedimento.pdf'
    assert mock.storage == {}  # só envia ao guardar
    page.click('#recordForm button.primary')
    page.wait_for_selector('#modal:not(.show)', state='attached', timeout=10000)
    page.wait_for_timeout(300)
    assert sorted(a['record_id'] for a in mock.attachments) == ['new1', 'new2']
    assert len(mock.storage) == 2
    assert not errors
    ctx.close()


def test_formulario_editar_retirar_e_juntar(browser, server, mock, tmp_path):
    mock.attachments = [att('a1', 'r1', 'Antigo.pdf', 'r1/a.pdf'), att('a2', 'r1', 'Fica.pdf', 'r1/b.pdf')]
    mock.storage = {'r1/a.pdf': 1, 'r1/b.pdf': 1}
    ctx, page, errors = open_app(browser, server, mock, logged_in())
    page.wait_for_selector('#rows tr[data-id="r1"] [data-att] .n')
    page.click('#rows tr[data-id="r1"] [data-edit]')
    page.wait_for_selector('#fAttList .fatt-item')
    assert page.evaluate("document.querySelectorAll('#fAttList .fatt-item').length") == 2
    page.click('[data-fattrm="a1"]')
    assert 'Vai ser apagado' in page.inner_text('#fAttList')
    page.click('[data-fattundo="a1"]')
    page.click('[data-fattrm="a1"]')
    f = tmp_path / 'Novo.pdf'
    f.write_bytes(PDF)
    page.set_input_files('#fAttFile', str(f))
    page.click('#recordForm button.primary')
    page.wait_for_selector('#modal:not(.show)', state='attached', timeout=10000)
    page.wait_for_timeout(300)
    assert sorted(a['file_name'] for a in mock.attachments) == ['Fica.pdf', 'Novo.pdf']
    assert 'r1/a.pdf' not in mock.storage and 'r1/b.pdf' in mock.storage
    assert not errors
    ctx.close()


def test_formulario_cancelar_nao_envia(browser, server, mock, tmp_path):
    mock.attachments = [att('a1', 'r1', 'Antigo.pdf', 'r1/a.pdf')]
    ctx, page, _ = open_app(browser, server, mock, logged_in())
    page.wait_for_selector('#rows tr[data-id="r1"] [data-att] .n')
    page.click('#rows tr[data-id="r1"] [data-edit]')
    page.wait_for_selector('[data-fattrm="a1"]')
    page.click('[data-fattrm="a1"]')
    f = tmp_path / 'X.pdf'
    f.write_bytes(PDF)
    page.set_input_files('#fAttFile', str(f))
    page.click('#cancel')
    page.wait_for_timeout(300)
    assert [a['id'] for a in mock.attachments] == ['a1'] and mock.storage == {}
    ctx.close()

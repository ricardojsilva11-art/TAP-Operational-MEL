"""Contas: palavra-passe temporária, tipos de acesso, página Utilizadores e nomes."""
from harness import OTHER, UID, logged_in, open_app, visible


def test_palavra_passe_temporaria_obriga_a_mudar(browser, server, mock):
    mock.profile['must_change_password'] = True
    ctx, page, errors = open_app(browser, server, mock, logged_in())
    assert page.evaluate("document.getElementById('pwModal').classList.contains('show')")
    assert not visible(page, '#appPanel')
    assert page.inner_text('#pwCancel') == 'Terminar sessão'
    page.fill('#pw1', 'novapass123')
    page.fill('#pw2', 'novapass123')
    page.click('#pwForm button.primary')
    page.wait_for_selector('#appPanel:not(.hidden)', timeout=10000)
    assert any(m == 'PUT' and '/auth/v1/user' in p for m, p, _ in mock.requests)
    assert not errors
    ctx.close()


def test_palavra_passe_temporaria_terminar_sessao(browser, server, mock):
    mock.profile['must_change_password'] = True
    ctx, page, _ = open_app(browser, server, mock, logged_in())
    page.click('#pwCancel')
    page.wait_for_timeout(1200)
    assert not visible(page, '#appPanel')
    assert not page.evaluate("Object.keys(localStorage).some(k=>k.startsWith('sb-'))")
    ctx.close()


def test_separadores_de_administrador(browser, server, mock):
    for role, admin in (('reader', False), ('operator', False), ('admin', True)):
        mock.profile['role'] = role
        ctx, page, _ = open_app(browser, server, mock, logged_in())
        assert visible(page, '#navUsers') is admin
        assert visible(page, '#navSettings') is admin
        page.evaluate("document.getElementById('navUsers').click()")
        assert visible(page, '#usersView') is admin
        ctx.close()


def test_so_consulta_sem_botoes_de_edicao(browser, server, mock):
    mock.profile['role'] = 'reader'
    ctx, page, _ = open_app(browser, server, mock, logged_in())
    assert not visible(page, '#add')
    assert page.evaluate("document.querySelectorAll('#rows [data-edit],#rows [data-delete]').length") == 0
    assert visible(page, '#roBanner')
    ctx.close()


def test_tipo_de_acesso_muda_em_tempo_real(browser, server, mock):
    ctx, page, _ = open_app(browser, server, mock, logged_in())
    page.evaluate("onProfileChange({eventType:'UPDATE',new:{...profile,role:'reader'},old:{user_id:'%s'}})" % UID)
    assert page.inner_text('#roleLabel') == 'Só consulta'
    assert page.evaluate("document.querySelectorAll('#rows [data-edit]').length") == 0
    page.evaluate("onProfileChange({eventType:'UPDATE',new:{...profile,role:'admin'},old:{user_id:'%s'}})" % UID)
    assert visible(page, '#navUsers') and visible(page, '#navSettings')
    page.evaluate("onProfileChange({eventType:'UPDATE',new:{user_id:'%s',role:'reader'},old:{user_id:'%s'}})" % (OTHER, OTHER))
    assert page.inner_text('#roleLabel') == 'Administrador'
    ctx.close()


def test_conta_desativada_termina_sessao(browser, server, mock):
    ctx, page, _ = open_app(browser, server, mock, logged_in())
    page.on('dialog', lambda d: d.accept())
    page.evaluate("onProfileChange({eventType:'UPDATE',new:{...profile,active:false},old:{user_id:'%s'}})" % UID)
    page.wait_for_timeout(1500)
    assert not visible(page, '#appPanel')
    ctx.close()


def test_editar_nome_de_utilizador(browser, server, mock):
    mock.profile['role'] = 'admin'
    mock.users = [{'user_id': UID, 'email': 'r@x.pt', 'display_name': 'Ricardo', 'role': 'admin', 'active': True, 'approved_before': True,
                   'reset_requested': False, 'created_at': '2026-11-01T10:00:00Z', 'last_sign_in_at': None},
                  {'user_id': OTHER, 'email': 'ana@x.pt', 'display_name': 'ana', 'role': 'operator', 'active': True, 'approved_before': True,
                   'reset_requested': False, 'created_at': '2026-11-01T10:00:00Z', 'last_sign_in_at': None}]
    ctx, page, errors = open_app(browser, server, mock, logged_in())
    page.click('#navUsers')
    page.wait_for_timeout(500)
    page.click(f'[data-uname="{OTHER}"]')
    page.fill(f'[data-ucell="{OTHER}"] input', '  Ana   Silva ')
    page.keyboard.press('Enter')
    page.wait_for_timeout(600)
    assert page.inner_text(f'[data-ucell="{OTHER}"] b') == 'Ana Silva'
    assert any(m == 'PATCH' and f'user_id=eq.{OTHER}' in p and '"display_name":"Ana Silva"' in (b or '') for m, p, b in mock.requests)
    # cancelar com Esc não grava
    n = len(mock.requests)
    page.click(f'[data-uname="{OTHER}"]')
    page.fill(f'[data-ucell="{OTHER}"] input', 'Outro')
    page.keyboard.press('Escape')
    assert page.inner_text(f'[data-ucell="{OTHER}"] b') == 'Ana Silva' and len(mock.requests) == n
    # o próprio nome atualiza o topo
    page.click(f'[data-uname="{UID}"]')
    page.fill(f'[data-ucell="{UID}"] input', 'Ricardo Silva')
    page.click(f'[data-unsave="{UID}"]')
    page.wait_for_timeout(600)
    assert page.inner_text('#userLabel') == 'Ricardo Silva'
    assert not errors
    ctx.close()

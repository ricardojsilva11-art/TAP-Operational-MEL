"""Registo e entrada: emails com caracteres escondidos ou símbolos estranhos."""
import json

from harness import open_app


def signups(mock):
    return [json.loads(b)['email'] for m, p, b in mock.requests if m == 'POST' and '/auth/v1/signup' in p]


def fill_signup(page, email):
    page.click('[data-auth="signup"]')
    page.fill('#suName', 'Joao Lemos')
    page.fill('#suEmail', email) if '◘' not in email else page.evaluate("v=>document.getElementById('suEmail').value=v", email)
    page.fill('#suPass', 'segredo123')
    page.fill('#suPass2', 'segredo123')
    page.click('#signupForm button.primary')
    page.wait_for_timeout(500)


def test_recusa_simbolo_estranho_no_dominio(browser, server, mock):
    ctx, page, _ = open_app(browser, server, mock, {})
    fill_signup(page, 'jplemos@◘tap.pt')
    assert 'caracteres inválidos' in page.inner_text('#loginError')
    assert signups(mock) == []
    ctx.close()


def test_limpa_espacos_e_caracteres_invisiveis(browser, server, mock):
    ctx, page, _ = open_app(browser, server, mock, {})
    page.click('[data-auth="signup"]')
    page.evaluate("document.getElementById('suEmail').value=' JPLemos@tap.pt\\u200b '")
    page.fill('#suName', 'Joao Lemos')
    page.fill('#suPass', 'segredo123')
    page.fill('#suPass2', 'segredo123')
    page.click('#signupForm button.primary')
    page.wait_for_timeout(600)
    assert signups(mock) == ['jplemos@tap.pt']
    ctx.close()


def test_recusa_email_incompleto(browser, server, mock):
    ctx, page, _ = open_app(browser, server, mock, {})
    page.click('[data-auth="signup"]')
    page.evaluate("document.getElementById('suEmail').value='jplemos@tap'")
    page.fill('#suName', 'Joao Lemos')
    page.fill('#suPass', 'segredo123')
    page.fill('#suPass2', 'segredo123')
    page.click('#signupForm button.primary')
    page.wait_for_timeout(400)
    assert 'não parece válido' in page.inner_text('#loginError') and signups(mock) == []
    ctx.close()


def test_entrada_usa_email_limpo(browser, server, mock):
    ctx, page, _ = open_app(browser, server, mock, {})
    page.evaluate("document.getElementById('email').value='JPLEMOS@tap.pt\\u200b'")
    page.fill('#password', 'x')
    page.click('#loginForm button.primary')
    page.wait_for_timeout(600)
    sent = [json.loads(b)['email'] for m, p, b in mock.requests if '/auth/v1/token' in p]
    assert sent == ['jplemos@tap.pt']
    assert 'errados' in page.inner_text('#loginError')
    ctx.close()

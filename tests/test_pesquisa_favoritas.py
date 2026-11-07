"""Pesquisa tolerante, realce, atalho / e favoritas."""
import pytest

from harness import logged_in, open_app, rec, visible

ITEMS = [rec('r0', 'A320', 'M-21-26-01', 'Perda da pressão da cabine'), rec('r1', 'A320', 'M-21-26-02', 'Ventilação avionics'),
         rec('r2', 'A320', 'M-32-12-60', 'Trem de aterragem'), rec('r3', 'A330', 'C-21-01', 'Item de cabine'),
         rec('r4', 'A320', 'M-21-26-01A', 'Variante A'), rec('r5', 'A320', 'M-34-11-05', 'Sem pressão estática'),
         rec('r6', 'E190/E195', 'M-21-51-00-A', 'Embraer')]


def codes(page, q):
    page.fill('#search', q)
    page.wait_for_timeout(150)
    return page.evaluate("[...document.querySelectorAll('#rows tr[data-id] .code')].map(c=>c.textContent)")


@pytest.fixture
def app(browser, server, mock):
    mock.rows = [dict(r) for r in ITEMS]
    ctx, page, errors = open_app(browser, server, mock, logged_in())
    yield page, mock, errors
    ctx.close()


@pytest.mark.parametrize('q,expected', [
    ('212601', {'M-21-26-01', 'M-21-26-01A'}),
    ('21-26', {'M-21-26-01', 'M-21-26-02', 'M-21-26-01A'}),
    ('m212601', {'M-21-26-01', 'M-21-26-01A'}),
    ('c21', {'C-21-01'}),
    ('pressao', {'M-21-26-01', 'M-34-11-05'}),
    ('2126 cabine', {'M-21-26-01'}),
    ('215100a', {'M-21-51-00-A'}),
    ('xyz', set()),
])
def test_pesquisa_tolerante(app, q, expected):
    page, _, errors = app
    assert set(codes(page, q)) == expected
    assert not errors


def test_nao_confunde_grupos(app):
    page, _, _ = app
    assert 'M-32-12-60' not in codes(page, '2126')


def test_realce_do_termo(app):
    page, _, _ = app
    codes(page, 'pressao')
    marks = page.evaluate("[...document.querySelectorAll('#rows mark.hl')].map(m=>m.textContent)")
    assert 'pressão' in marks


def test_atalho_barra_e_esc(app):
    page, _, _ = app
    page.evaluate('document.activeElement.blur()')
    page.keyboard.press('/')
    assert page.evaluate('document.activeElement.id') == 'search'
    page.keyboard.type('c21')
    page.keyboard.press('Escape')
    assert page.input_value('#search') == ''


def test_favoritas(app):
    page, mock, _ = app
    codes(page, '')
    assert not visible(page, '#clearFav')
    page.click('#rows tr[data-id="r2"] [data-fav]')
    page.wait_for_timeout(300)
    page.select_option('#showFilter', 'fav')
    page.wait_for_timeout(150)
    assert codes(page, '') == ['M-32-12-60']
    assert 'Favoritas (1)' in page.inner_text('#showFilter')
    assert any(m == 'POST' and 'mel_user_prefs' in p for m, p, _ in mock.requests)
    assert visible(page, '#clearFav')


def test_limpar_favoritas(browser, server, mock):
    mock.prefs = [{'record_id': 'r1', 'is_favorite': True, 'last_used_at': None}, {'record_id': 'r2', 'is_favorite': True, 'last_used_at': None}]
    ctx, page, _ = open_app(browser, server, mock, logged_in())
    page.on('dialog', lambda d: d.accept())
    page.wait_for_timeout(400)
    assert page.evaluate("document.querySelectorAll('.act.fav.on').length") == 2
    page.click('#clearFav')
    page.wait_for_timeout(600)
    assert page.evaluate("document.querySelectorAll('.act.fav.on').length") == 0
    assert not visible(page, '#clearFav')
    assert any(m == 'DELETE' and 'user_id=eq.' in p for m, p, _ in mock.requests)
    ctx.close()

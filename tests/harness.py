"""Ambiente de teste da TAP Operational MEL.

Serve a app localmente e substitui o Supabase por um servidor falso (MockSupabase),
para testar a app num browser sem tocar na base de dados real.
"""
import base64
import functools
import http.server
import json
import os
import threading
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UID = '11111111-1111-1111-1111-111111111111'
OTHER = '22222222-2222-2222-2222-222222222222'
SKEY = 'sb-hojypgcmqkikcxlhbjyr-auth-token'
XLSX_URL = 'https://cdn.sheetjs.com/xlsx-0.20.3/package/dist/xlsx.full.min.js'


def _b64(d):
    return base64.urlsafe_b64encode(json.dumps(d).encode()).decode().rstrip('=')


def session():
    exp = int(time.time()) + 3600
    jwt = _b64({'alg': 'HS256', 'typ': 'JWT'}) + '.' + _b64({'sub': UID, 'exp': exp, 'role': 'authenticated', 'email': 'r@x.pt'}) + '.sig'
    return {'access_token': jwt, 'refresh_token': 'rt', 'expires_at': exp, 'expires_in': 3600, 'token_type': 'bearer',
            'user': {'id': UID, 'email': 'r@x.pt', 'aud': 'authenticated'}}


def logged_in(extra=None):
    d = {SKEY: json.dumps(session())}
    d.update(extra or {})
    return d


def rec(i, fleet, item, impact='', html='', notes='', active=True, **kw):
    r = {'id': i, 'fleet': fleet, 'mel_item': item, 'operational_impact': impact, 'operational_impact_html': html,
         'notes': notes, 'is_active': active, 'created_by': None, 'created_by_name': 'Importado', 'updated_by': None,
         'updated_by_name': None, 'updated_at': None, 'created_at': '2026-11-01T10:00:00Z', 'legacy_id': None}
    r.update(kw)
    return r


class Server:
    def __init__(self, port=8765):
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT)
        handler.log_message = lambda *a: None
        self.httpd = http.server.ThreadingHTTPServer(('127.0.0.1', port), handler)
        self.url = f'http://127.0.0.1:{port}/'
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def close(self):
        self.httpd.shutdown()


class MockSupabase:
    """Responde aos pedidos que a app faz ao Supabase (REST e Auth)."""

    def __init__(self):
        self.up = True
        self.profile = {'user_id': UID, 'display_name': 'Ricardo', 'role': 'operator', 'active': True, 'must_change_password': False}
        self.rows = [rec('r1', 'A320', 'M-21-26-01', 'Impacto 1'), rec('r2', 'A320', 'M-21-26-02', 'Impacto 2'), rec('r3', 'A330', 'M-21-28-03A', 'Impacto 3')]
        self.prefs = []
        self.audit = []
        self.users = []
        self.settings = {'id': 1, 'signups_open': True, 'session_hours': 12, 'last_backup_at': None, 'last_backup_by': None, 'updated_at': None, 'updated_by': None}
        self.revisions = [{'fleet': f, 'revision': '', 'effective_date': None, 'updated_at': None, 'updated_by_name': None} for f in ('A320', 'A330', 'E190/E195')]
        self.attachments = []
        self.taf_cfg = {'id': 1, 'cfg': None, 'updated_at': None, 'updated_by_name': None}
        self.taf_missing = False
        self.storage = {}
        self.attach_missing = False
        self.tables_missing = False
        self.fail_format = False
        self.requests = []  # (método, caminho, corpo) dos pedidos que alteram dados

    def _json(self, route, data, status=200):
        return route.fulfill(status=status, content_type='application/json', body=json.dumps(data))

    def handle(self, route):
        if not self.up:
            return route.abort()
        req = route.request
        u, m = req.url, req.method
        path = u.split('.supabase.co', 1)[1]
        if m in ('POST', 'PATCH', 'PUT', 'DELETE'):
            self.requests.append((m, path, req.post_data))
        obj = 'vnd.pgrst.object' in (req.headers.get('accept') or '')
        one = lambda d: self._json(route, d if obj else [d])

        if '/storage/v1/object/sign/mel-pdfs/' in u:
            path = u.split('/object/sign/mel-pdfs/')[1].split('?')[0]
            return self._json(route, {'signedURL': f'/object/sign/mel-pdfs/{path}?token=t'})
        if '/storage/v1/object/mel-pdfs' in u:
            if m == 'DELETE':
                for pth in json.loads(req.post_data or '{}').get('prefixes', []):
                    self.storage.pop(pth, None)
                return self._json(route, [])
            if m == 'POST':
                path = u.split('/object/mel-pdfs/')[1].split('?')[0]
                self.storage[path] = len(req.post_data_buffer or b'')
                return self._json(route, {'Key': 'mel-pdfs/' + path})
        if '/rest/v1/taf_settings' in u:
            if self.taf_missing:
                return self._json(route, {'code': '42P01', 'message': 'relation "public.taf_settings" does not exist'}, 404)
            if m == 'PATCH':
                self.taf_cfg.update(json.loads(req.post_data), updated_at='2026-11-10T10:40:00Z', updated_by_name=self.profile['display_name'])
                return self._json(route, [self.taf_cfg])
            return one(self.taf_cfg)
        if '/rest/v1/mel_attachments' in u:
            if self.attach_missing:
                return self._json(route, {'code': '42P01', 'message': 'relation does not exist'}, 404)
            if m == 'POST':
                d = json.loads(req.post_data)
                d.update(id='att%d' % (len(self.attachments) + 1), uploaded_by=UID, uploaded_by_name='Ricardo', uploaded_at='2026-11-09T10:00:00Z')
                self.attachments.append(d)
                return route.fulfill(status=201, body='')
            if m == 'DELETE':
                aid = u.split('id=eq.')[1].split('&')[0]
                self.attachments = [a for a in self.attachments if a['id'] != aid]
                return route.fulfill(status=204, body='')
            if 'record_id=eq.' in u:
                rid = u.split('record_id=eq.')[1].split('&')[0]
                return self._json(route, [a for a in self.attachments if a['record_id'] == rid])
            return self._json(route, self.attachments)
        if '/auth/v1/signup' in u:
            return self._json(route, {'user': {'id': 'nu1', 'email': json.loads(req.post_data)['email'], 'identities': [{'id': 'i1'}]}, 'session': None})
        if '/auth/v1/token' in u:
            return self._json(route, {'error': 'invalid_grant', 'error_description': 'Invalid login credentials', 'msg': 'Invalid login credentials'}, 400)
        if '/auth/v1/health' in u:
            return self._json(route, {})
        if '/auth/v1/user' in u and m == 'PUT':
            self.profile['must_change_password'] = False
            return self._json(route, session()['user'])
        if '/auth/v1/logout' in u:
            return route.fulfill(status=204, body='')
        if '/rpc/signups_open' in u:
            return self._json(route, bool(self.settings['signups_open']))
        if '/rpc/admin_delete_user' in u:
            uid = json.loads(req.post_data)['p_user']
            self.users = [x for x in self.users if x['user_id'] != uid]
            return route.fulfill(status=204, body='')
        if '/rpc/admin_list_users' in u:
            return self._json(route, self.users)
        if '/rest/v1/user_profiles' in u:
            if m == 'PATCH':
                d = json.loads(req.post_data)
                uid = u.split('user_id=eq.')[1].split('&')[0]
                for x in self.users:
                    if x['user_id'] == uid:
                        x.update(d)
                return self._json(route, [{'user_id': uid}])
            return one(self.profile)
        if '/rest/v1/mel_records' in u:
            if m in ('PATCH', 'POST'):
                if self.fail_format:
                    return self._json(route, {'code': '23514', 'message': 'violates check constraint "mel_item_format"'}, 400)
                if m == 'POST' and 'return=representation' in (req.headers.get('prefer') or ''):
                    body = json.loads(req.post_data)
                    body = body if isinstance(body, list) else [body]
                    return self._json(route, [{'id': 'new%d' % (i + 1)} for i in range(len(body))], 201)
                return route.fulfill(status=204, body='')
            return self._json(route, self.rows)
        if '/rest/v1/mel_user_prefs' in u:
            if m == 'DELETE':
                self.prefs.clear()
                return route.fulfill(status=204, body='')
            if m == 'POST':
                return route.fulfill(status=201, body='')
            return self._json(route, self.prefs)
        if '/rest/v1/mel_audit_log' in u:
            return self._json(route, self.audit)
        if '/rest/v1/app_settings' in u or '/rest/v1/fleet_revisions' in u:
            if self.tables_missing:
                return self._json(route, {'code': '42P01', 'message': 'relation does not exist'}, 404)
            if m == 'PATCH':
                d = json.loads(req.post_data)
                if 'app_settings' in u:
                    self.settings.update(d)
                    if 'last_backup_at' in d:
                        self.settings['last_backup_by'] = 'Ricardo'
                else:
                    f = u.split('fleet=eq.')[1].split('&')[0].replace('%2F', '/')
                    for x in self.revisions:
                        if x['fleet'] == f:
                            x.update(d)
                return route.fulfill(status=204, body='')
            if 'app_settings' in u:
                return one(self.settings)
            return self._json(route, self.revisions)
        return self._json(route, [])


def open_app(browser, server, mock, local_storage=None, service_workers='block', wait=True, view='mel'):
    """Abre a app com o Supabase falso e o localStorage indicado. Devolve (context, page, errors).

    view='mel' passa logo para o separador MEL (a maior parte dos testes); view='portal' fica no Início."""
    ctx = browser.new_context(service_workers=service_workers)
    xlsx_local = os.environ.get('XLSX_LOCAL')  # sem internet: usar uma cópia local do SheetJS
    if xlsx_local:
        ctx.route(XLSX_URL, lambda r: r.fulfill(path=xlsx_local, content_type='text/javascript'))
    ctx.route('**/*.supabase.co/**', mock.handle)
    ctx.route('https://taf.ricardo-j-silva11.workers.dev/**', lambda r: r.abort())  # TAF: sem rede nos testes
    page = ctx.new_page()
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.goto(server.url)
    page.evaluate('d=>{localStorage.clear();for(const k in d)localStorage.setItem(k,d[k])}', local_storage or {})
    page.reload()
    if wait:
        page.wait_for_function("!document.getElementById('appPanel').classList.contains('hidden')"
                               "||document.getElementById('loginError').textContent"
                               "||document.getElementById('pwModal').classList.contains('show')"
                               "||performance.now()>4000", timeout=40000)
        page.wait_for_timeout(400)
        if view == 'mel':
            page.evaluate("()=>{if(!document.getElementById('appPanel').classList.contains('hidden'))document.querySelector('[data-nav=\"home\"]').click()}")
    return ctx, page, errors


def visible(page, sel):
    return page.evaluate("s=>{const e=document.querySelector(s);return !!e&&!e.classList.contains('hidden')}", sel)

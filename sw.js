// Service worker da TAP Operational MEL: guarda a "casca" da app para abrir sem ligação.
// Os dados das MEL NÃO passam por aqui: a app guarda a última cópia no próprio browser.
const CACHE = 'mel-shell-v4';
const SHELL = ['./', './index.html', './config.js', './manifest.webmanifest', './icon-192.png', './icon-512.png',
               './img/a320.webp', './img/a330.webp', './img/e190.webp',
               './vendor/supabase-js-2.119.0.js'];
const CDN = [
  'https://cdn.sheetjs.com/xlsx-0.20.3/package/dist/xlsx.full.min.js'
];

self.addEventListener('install', e => {
  e.waitUntil((async () => {
    const c = await caches.open(CACHE);
    await c.addAll(SHELL);
    await Promise.all(CDN.map(async u => {
      try { const r = await fetch(u, { mode: 'no-cors' }); await c.put(u, r); } catch (_) {}
    }));
    self.skipWaiting();
  })());
});

self.addEventListener('activate', e => {
  e.waitUntil((async () => {
    for (const k of await caches.keys()) if (k !== CACHE) await caches.delete(k);
    await self.clients.claim();
  })());
});

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.hostname.endsWith('.supabase.co')) return;          // dados e login: sempre direto ao servidor

  if (url.origin === location.origin) {                          // app: primeiro a rede, senão a cópia
    e.respondWith((async () => {
      const c = await caches.open(CACHE);
      try {
        const ctl = new AbortController(); const t = setTimeout(() => ctl.abort(), 5000);
        const r = await fetch(req, { signal: ctl.signal }); clearTimeout(t);
        if (r.ok) c.put(req.mode === 'navigate' ? './index.html' : req, r.clone());
        return r;
      } catch (_) {
        return (await c.match(req, { ignoreSearch: true })) ||
               (req.mode === 'navigate' ? await c.match('./index.html') : undefined) ||
               Response.error();
      }
    })());
    return;
  }

  if (url.hostname === 'cdn.sheetjs.com') {                    // bibliotecas: cópia, atualizada em segundo plano
    e.respondWith((async () => {
      const c = await caches.open(CACHE);
      const hit = await c.match(req.url);
      const net = fetch(req).then(r => { if (r.ok || r.type === 'opaque') c.put(req.url, r.clone()); return r; }).catch(() => null);
      return hit || (await net) || Response.error();
    })());
  }
});

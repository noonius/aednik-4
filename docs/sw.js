'use strict';
const CACHE = 'aednik-offline-v1';
const SHELL = ['./', 'index.html', 'style.css', 'taimed.js', 'study.js', 'app.js', 'icon.svg', 'manifest.webmanifest'];
self.addEventListener('install', event => {
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE);
    for (const path of SHELL) {
      const response = await fetch(new URL(path, self.registration.scope));
      if (!response.ok || response.redirected) throw new Error('App shell did not load');
      await cache.put(new URL(path, self.registration.scope), response);
    }
    await self.skipWaiting();
  })());
});
self.addEventListener('activate', event => { event.waitUntil(self.clients.claim()); });
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);
  if (event.request.method !== 'GET' || url.origin !== self.location.origin || !url.href.startsWith(self.registration.scope) || url.pathname.includes('/api/')) return;
  event.respondWith((async () => {
    const cache = await caches.open(CACHE);
    const cached = await cache.match(event.request);
    if (cached) return cached;
    try {
      const response = await fetch(event.request);
      if (response.ok && !response.redirected && url.pathname.match(/\.(jpg|js|css|svg|json|webmanifest)$/)) await cache.put(event.request, response.clone());
      return response;
    } catch (error) {
      if (event.request.mode === 'navigate') {
        const shell = await cache.match(new URL('index.html', self.registration.scope));
        if (shell) return shell;
      }
      throw error;
    }
  })());
});

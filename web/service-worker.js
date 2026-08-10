const CACHE_NAME = 'spec-voice-shell-v2';
const APP_SHELL = [
    '/',
    '/manifest.json',
    '/icons/icon-192.png',
    '/icons/icon-512.png',
];

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_SHELL))
    );
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((names) =>
            Promise.all(names.filter((name) => name !== CACHE_NAME).map((name) => caches.delete(name)))
        )
    );
    self.clients.claim();
});

self.addEventListener('fetch', (event) => {
    const url = new URL(event.request.url);

    // Never cache API calls - always go to the network for live answers
    if (url.pathname.startsWith('/api/')) {
        return;
    }

    if (event.request.method !== 'GET') {
        return;
    }

    // Network-first: always prefer the live deployed version so updates (like this
    // one) show up immediately. Cache is only a fallback for offline/flaky signal,
    // not the primary source - a cache-first app shell kept phones stuck on
    // whatever was cached on their very first visit, with no way to self-heal.
    event.respondWith(
        fetch(event.request)
            .then((response) => {
                const copy = response.clone();
                caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copy));
                return response;
            })
            .catch(() => caches.match(event.request))
    );
});

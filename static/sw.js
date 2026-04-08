/* Easy NodeOne — PWA + /static/: red primero (JS/CSS siempre actuales), caché si offline. */
var CACHE = 'nodeone-offline-v1';
var STATIC_CACHE = 'nodeone-static-v2';
var OFFLINE_URL = '/static/offline.html';

self.addEventListener('install', function (event) {
  event.waitUntil(
    caches.open(CACHE).then(function (cache) {
      return cache.add(OFFLINE_URL);
    }).then(function () {
      return self.skipWaiting();
    })
  );
});

self.addEventListener('activate', function (event) {
  event.waitUntil(
    caches
      .keys()
      .then(function (keys) {
        return Promise.all(
          keys.map(function (k) {
            if (k === 'nodeone-static-v1') return caches.delete(k);
            return Promise.resolve();
          })
        );
      })
      .then(function () {
        return self.clients.claim();
      })
  );
});

function isSameOriginStaticGet(request) {
  if (request.method !== 'GET') return false;
  try {
    var u = new URL(request.url);
    if (u.origin !== self.location.origin) return false;
    return u.pathname.indexOf('/static/') === 0;
  } catch (e) {
    return false;
  }
}

self.addEventListener('fetch', function (event) {
  var req = event.request;
  if (req.mode === 'navigate') {
    event.respondWith(
      fetch(req).catch(function () {
        return caches.match(OFFLINE_URL).then(function (r) {
          return r || new Response('Offline', { status: 503, statusText: 'Offline' });
        });
      })
    );
    return;
  }
  if (isSameOriginStaticGet(req)) {
    event.respondWith(
      caches.open(STATIC_CACHE).then(function (cache) {
        return fetch(req)
          .then(function (res) {
            if (res && res.ok && res.type === 'basic') {
              cache.put(req, res.clone());
            }
            return res;
          })
          .catch(function () {
            return cache.match(req).then(function (cached) {
              return cached || new Response('', { status: 504, statusText: 'Offline' });
            });
          });
      })
    );
    return;
  }
});

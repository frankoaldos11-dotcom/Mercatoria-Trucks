const CACHE_NAME = "mercatoria-v1";

const STATIC_ASSETS = [
  "/",
  "/static/css/admin.css",
  "/static/css/layout.css",
  "/static/style.css",
  "/static/icons/icon-192.png",
  "/static/icons/icon-512.png",
  "/static/manifest.json"
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))
      )
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const { request } = event;

  // Never intercept non-GET or API/POST routes
  if (request.method !== "GET") return;

  const url = new URL(request.url);

  // Skip cross-origin requests (CDN, fonts, etc.)
  if (url.origin !== self.location.origin) return;

  // Skip admin data routes — always fetch fresh from network
  const BYPASS_PREFIXES = [
    "/admin/viaje",
    "/admin/viajes",
    "/admin/camioneros",
    "/admin/clientes",
    "/admin/comercial",
    "/admin/reportes",
    "/admin/exportar",
    "/admin/importar",
    "/admin/catalogos",
    "/logout",
    "/login",
    "/cliente",
  ];
  if (BYPASS_PREFIXES.some((p) => url.pathname.startsWith(p))) return;

  // For static assets: cache-first
  if (url.pathname.startsWith("/static/")) {
    event.respondWith(
      caches.match(request).then(
        (cached) => cached || fetch(request).then((response) => {
          if (response && response.status === 200) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
          }
          return response;
        })
      )
    );
    return;
  }

  // For the homepage only: network-first, fall back to cache
  if (url.pathname === "/") {
    event.respondWith(
      fetch(request)
        .then((response) => {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
          return response;
        })
        .catch(() => caches.match(request))
    );
  }
});

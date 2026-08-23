const UI_LANGUAGE = "__UI_LANGUAGE__";
const CACHE_NAME = `print-scan-hub-shell-v2-${UI_LANGUAGE}`;
const STATIC_FILES = [
  "/manifest.webmanifest",
  "/static/css/app.css",
  "/static/js/drawers.js",
  "/static/js/i18n.js",
  "/static/js/pwa.js",
  "/static/js/theme.js",
  "/static/vendor/bootstrap.bundle.min.js",
  "/static/vendor/bootstrap.min.css",
  "/static/vendor/fontawesome/css/all.min.css",
  "/static/icons/icon-192.png",
  "/static/icons/icon-512.png",
  `/static/offline-${UI_LANGUAGE}.html`
];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_FILES)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((names) => Promise.all(
      names
        .filter((name) => name.startsWith("print-scan-hub-") && name !== CACHE_NAME)
        .map((name) => caches.delete(name))
    ))
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  const url = new URL(request.url);

  if (request.method !== "GET" || url.origin !== self.location.origin) {
    return;
  }

  if (url.pathname.includes("/api/") || url.pathname === "/health") {
    event.respondWith(fetch(request));
    return;
  }

  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request).catch(() => caches.match(`/static/offline-${UI_LANGUAGE}.html`))
    );
    return;
  }

  if (url.pathname.startsWith("/static/")) {
    event.respondWith(
      caches.match(request, {ignoreSearch: true}).then((cached) => cached || fetch(request))
    );
  }
});

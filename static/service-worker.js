const CACHE_NAME = "api-model-manager-v1";
const URLS_TO_CACHE = [
    "./",
    "./index.html",
    "./manifest.json",
    "./icons/icon-192.png",
    "./icons/icon-512.png"
];

self.addEventListener("install", (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => cache.addAll(URLS_TO_CACHE))
    );
});

self.addEventListener("activate", (event) => {
    event.waitUntil(
        caches.keys().then((keys) =>
            Promise.all(keys.map((key) => key !== CACHE_NAME && caches.delete(key)))
        )
    );
});

self.addEventListener("fetch", (event) => {
    event.respondWith(
        caches.match(event.request).then((resp) => resp || fetch(event.request))
    );
});

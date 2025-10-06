// service-worker.js
// Nombre de la caché (versión)
const CACHE_NAME = 'rifas-cache-v1';

// Recursos estáticos que queremos cachear
const urlsToCache = [
    '/',
    '/rifas',
    '/static/css/main.css',
    '/static/js/base.js',
    // URLs de Bootstrap, Tailwind y FontAwesome (se asume que se cachean por ser CDN,
    // pero incluirlos aquí si queremos control total)
    // '/static/img/icon-192x192.png',
    // '/static/img/icon-512x512.png'
];

// Instalar el Service Worker y guardar el contenido estático
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => {
                console.log('Opened cache');
                // Agregar las URLs a la caché (falla si alguna URL no está disponible)
                return cache.addAll(urlsToCache); 
            })
            .catch((error) => {
                console.error('Failed to cache resources:', error);
            })
    );
});

// Interceptamos peticiones para servir desde la caché si está disponible (Estrategia Cache-First)
self.addEventListener('fetch', (event) => {
    // Solo manejar peticiones GET
    if (event.request.method !== 'GET') return;
    
    event.respondWith(
        caches.match(event.request)
            .then((response) => {
                // Si encontramos la respuesta en la caché, la servimos
                if (response) {
                    return response;
                }
                
                // Si no está en la caché, vamos a la red
                return fetch(event.request)
                    .then((networkResponse) => {
                        // Verificamos si la respuesta de la red es válida
                        if (!networkResponse || networkResponse.status !== 200 || networkResponse.type !== 'basic') {
                            return networkResponse;
                        }
                        
                        // Clonamos la respuesta porque el stream solo se puede consumir una vez
                        const responseToCache = networkResponse.clone();
                        
                        // Abrimos la caché y guardamos la nueva respuesta
                        caches.open(CACHE_NAME)
                            .then((cache) => {
                                // Evitamos guardar peticiones de terceros que podrían ser problemáticas (ej. Google Analytics)
                                if (event.request.url.startsWith(self.location.origin)) {
                                    cache.put(event.request, responseToCache);
                                }
                            });

                        return networkResponse;
                    })
                    .catch((error) => {
                        console.error('Fetch failed: ', error);
                        // Esto podría ser un buen punto para servir una página offline
                        // return caches.match('/offline.html');
                    });
            })
    );
});

// Limpiar cachés viejas
self.addEventListener('activate', (event) => {
    const cacheWhitelist = [CACHE_NAME];
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames.map((cacheName) => {
                    if (cacheWhitelist.indexOf(cacheName) === -1) {
                        return caches.delete(cacheName);
                    }
                })
            );
        })
    );
});

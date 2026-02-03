/* 
 * NEET BRO PWA Service Worker
 * Handles offline caching and app installation
 * DO NOT modify API calls - they must always go to the Django backend
 */

const CACHE_VERSION = 'v1';
const CACHE_NAME = `neetbro-pwa-${CACHE_VERSION}`;

// Assets to cache immediately on install
const PRECACHE_ASSETS = [
  '/',
  '/index.html',
  '/manifest.json'
];

// Assets to cache on first request (runtime caching)
const RUNTIME_CACHE = [
  '/static/',
  '/assets/',
  '/icons/'
];

// API endpoints to NEVER cache (always fetch from network)
const NETWORK_ONLY_PATTERNS = [
  '/api/',
  '/admin/',
  '/auth/'
];

// ============================================================================
// INSTALL EVENT - Cache essential assets
// ============================================================================
self.addEventListener('install', (event) => {
  console.log('[SW] Installing service worker...');
  
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.log('[SW] Precaching static assets');
        return cache.addAll(PRECACHE_ASSETS);
      })
      .then(() => {
        console.log('[SW] Service worker installed successfully');
        // Force the waiting service worker to become the active service worker
        return self.skipWaiting();
      })
      .catch((error) => {
        console.error('[SW] Precache failed:', error);
      })
  );
});

// ============================================================================
// ACTIVATE EVENT - Clean up old caches
// ============================================================================
self.addEventListener('activate', (event) => {
  console.log('[SW] Activating service worker...');
  
  event.waitUntil(
    caches.keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames.map((cacheName) => {
            // Delete old cache versions
            if (cacheName !== CACHE_NAME) {
              console.log('[SW] Deleting old cache:', cacheName);
              return caches.delete(cacheName);
            }
          })
        );
      })
      .then(() => {
        console.log('[SW] Service worker activated');
        // Take control of all pages immediately
        return self.clients.claim();
      })
  );
});

// ============================================================================
// FETCH EVENT - Intercept network requests
// ============================================================================
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // CRITICAL: Never cache API requests - always fetch from network
  if (NETWORK_ONLY_PATTERNS.some(pattern => url.pathname.startsWith(pattern))) {
    event.respondWith(
      fetch(request).catch((error) => {
        console.error('[SW] Network request failed:', url.pathname, error);
        // Return a custom offline response for API failures
        return new Response(
          JSON.stringify({ 
            error: 'Network unavailable', 
            message: 'Please check your internet connection' 
          }),
          {
            status: 503,
            headers: { 'Content-Type': 'application/json' }
          }
        );
      })
    );
    return;
  }

  // For navigation requests (HTML pages)
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request)
        .catch(() => {
          // If offline, serve cached index.html for SPA routing
          return caches.match('/index.html');
        })
    );
    return;
  }

  // For static assets (JS, CSS, images, fonts)
  // Strategy: Cache First, fallback to Network
  if (RUNTIME_CACHE.some(pattern => url.pathname.includes(pattern))) {
    event.respondWith(
      caches.match(request)
        .then((cachedResponse) => {
          if (cachedResponse) {
            console.log('[SW] Serving from cache:', url.pathname);
            return cachedResponse;
          }

          // Not in cache, fetch from network and cache it
          return fetch(request)
            .then((networkResponse) => {
              // Only cache successful responses
              if (networkResponse && networkResponse.status === 200) {
                const responseClone = networkResponse.clone();
                caches.open(CACHE_NAME)
                  .then((cache) => {
                    cache.put(request, responseClone);
                  });
              }
              return networkResponse;
            })
            .catch((error) => {
              console.error('[SW] Fetch failed for:', url.pathname, error);
              // Return offline fallback if available
              return caches.match('/index.html');
            });
        })
    );
    return;
  }

  // For all other requests, try network first
  event.respondWith(
    fetch(request).catch(() => {
      return caches.match(request);
    })
  );
});

// ============================================================================
// MESSAGE EVENT - Handle messages from the app
// ============================================================================
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    console.log('[SW] Received SKIP_WAITING message');
    self.skipWaiting();
  }

  if (event.data && event.data.type === 'CLEAR_CACHE') {
    console.log('[SW] Clearing all caches');
    event.waitUntil(
      caches.keys().then((cacheNames) => {
        return Promise.all(
          cacheNames.map((cacheName) => caches.delete(cacheName))
        );
      })
    );
  }
});

// ============================================================================
// PUSH NOTIFICATION (Optional - for future use)
// ============================================================================
self.addEventListener('push', (event) => {
  if (event.data) {
    const data = event.data.json();
    const options = {
      body: data.body || 'You have a new notification',
      icon: '/icons/icon-192.png',
      badge: '/icons/icon-72.png',
      vibrate: [200, 100, 200],
      data: data.url || '/'
    };

    event.waitUntil(
      self.registration.showNotification(data.title || 'InzightEd', options)
    );
  }
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  event.waitUntil(
    clients.openWindow(event.notification.data || '/')
  );
});

console.log('[SW] Service worker script loaded');

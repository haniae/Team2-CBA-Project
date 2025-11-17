// CFI Dashboard Service Worker
// Provides offline support and caching for better performance

const CACHE_NAME = 'cfi-dashboard-v2';
const ASSETS_TO_CACHE = [
  'cfi_dashboard.html',
  'cfi_dashboard.css',
  'cfi_dashboard.js',
  'styles.css',
  'app.js',
  'favicon.svg',
  'https://cdn.plot.ly/plotly-2.32.0.min.js',
  'https://fonts.googleapis.com/css2?family=Inter:wght@500;600;700&display=swap'
];

// Install event - cache assets
self.addEventListener('install', (event) => {
  console.log('[ServiceWorker] Installing...');
  
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.log('[ServiceWorker] Caching assets');
        return cache.addAll(ASSETS_TO_CACHE);
      })
      .then(() => {
        console.log('[ServiceWorker] Installation complete');
        return self.skipWaiting();
      })
      .catch((error) => {
        console.error('[ServiceWorker] Installation failed:', error);
      })
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
  console.log('[ServiceWorker] Activating...');
  
  event.waitUntil(
    caches.keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames
            .filter((cacheName) => cacheName !== CACHE_NAME)
            .map((cacheName) => {
              console.log('[ServiceWorker] Deleting old cache:', cacheName);
              return caches.delete(cacheName);
            })
        );
      })
      .then(() => {
        console.log('[ServiceWorker] Activation complete');
        return self.clients.claim();
      })
  );
});

// Fetch event - serve from cache, fallback to network
self.addEventListener('fetch', (event) => {
  const { request } = event;
  
  // Skip cross-origin requests
  if (!request.url.startsWith(self.location.origin) && 
      !request.url.startsWith('https://cdn.plot.ly') &&
      !request.url.startsWith('https://fonts.googleapis.com')) {
    return;
  }

  // Network first for API requests, cache first for assets
  if (request.url.includes('/api/') || request.url.includes('companyfacts')) {
    event.respondWith(networkFirst(request));
  } else {
    event.respondWith(cacheFirst(request));
  }
});

// Cache first strategy (for static assets)
async function cacheFirst(request) {
  try {
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      console.log('[ServiceWorker] Serving from cache:', request.url);
      return cachedResponse;
    }

    console.log('[ServiceWorker] Fetching from network:', request.url);
    const networkResponse = await fetch(request);
    
    // Cache successful responses
    if (networkResponse && networkResponse.status === 200) {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, networkResponse.clone());
    }
    
    return networkResponse;
  } catch (error) {
    console.error('[ServiceWorker] Fetch failed:', error);
    
    // Return offline page if available
    const offlineResponse = await caches.match('/offline.html');
    if (offlineResponse) {
      return offlineResponse;
    }
    
    // Return basic offline response
    return new Response('Offline - Please check your connection', {
      status: 503,
      statusText: 'Service Unavailable',
      headers: new Headers({
        'Content-Type': 'text/plain'
      })
    });
  }
}

// Network first strategy (for API requests)
async function networkFirst(request) {
  try {
    console.log('[ServiceWorker] Network first for:', request.url);
    const networkResponse = await fetch(request);
    
    // Cache successful responses
    if (networkResponse && networkResponse.status === 200) {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, networkResponse.clone());
    }
    
    return networkResponse;
  } catch (error) {
    console.log('[ServiceWorker] Network failed, trying cache:', request.url);
    const cachedResponse = await caches.match(request);
    
    if (cachedResponse) {
      console.log('[ServiceWorker] Serving stale data from cache');
      return cachedResponse;
    }
    
    throw error;
  }
}

// Background sync for offline actions
self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-dashboard-data') {
    console.log('[ServiceWorker] Background sync triggered');
    event.waitUntil(syncDashboardData());
  }
});

async function syncDashboardData() {
  try {
    // In a real implementation, sync any pending data changes
    console.log('[ServiceWorker] Syncing dashboard data...');
    return Promise.resolve();
  } catch (error) {
    console.error('[ServiceWorker] Sync failed:', error);
    throw error;
  }
}

// Push notifications support
self.addEventListener('push', (event) => {
  const options = {
    body: event.data ? event.data.text() : 'New update available',
    icon: '/favicon.svg',
    badge: '/favicon.svg',
    vibrate: [200, 100, 200],
    tag: 'dashboard-notification',
    requireInteraction: false,
    actions: [
      {
        action: 'view',
        title: 'View Dashboard'
      },
      {
        action: 'dismiss',
        title: 'Dismiss'
      }
    ]
  };

  event.waitUntil(
    self.registration.showNotification('CFI Dashboard', options)
  );
});

// Notification click handler
self.addEventListener('notificationclick', (event) => {
  event.notification.close();

  if (event.action === 'view') {
    event.waitUntil(
      clients.openWindow('/')
    );
  }
});

// Message handler for communication with main thread
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
  
  if (event.data && event.data.type === 'CLEAR_CACHE') {
    event.waitUntil(
      caches.delete(CACHE_NAME).then(() => {
        console.log('[ServiceWorker] Cache cleared');
      })
    );
  }
});

console.log('[ServiceWorker] Service Worker loaded');


// Clawverse Service Worker — Push Notifications
self.addEventListener('push', event => {
  let data = { title: 'Clawverse', body: 'Something happened on your island!', url: '/' };
  try {
    data = event.data.json();
  } catch (e) {
    data.body = event.data ? event.data.text() : data.body;
  }

  const options = {
    body: data.body,
    icon: '/api/island/default/thumbnail',
    badge: '/api/island/default/thumbnail',
    tag: data.event_type || 'clawverse',
    renotify: true,
    data: { url: data.url || '/' },
    actions: [{ action: 'open', title: 'View Island' }]
  };

  event.waitUntil(self.registration.showNotification(data.title, options));
});

self.addEventListener('notificationclick', event => {
  event.notification.close();
  const url = event.notification.data?.url || '/';
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then(list => {
      for (const client of list) {
        if (client.url.includes(self.location.origin) && 'focus' in client) {
          client.navigate(url);
          return client.focus();
        }
      }
      return clients.openWindow(url);
    })
  );
});

// Minimal service worker for the Notification Hub PWA shell.
// No caching/offline strategy -- just enough for push delivery and
// "add to home screen" installability (see plan.md's frontend design).

self.addEventListener('push', (event) => {
  const data = event.data ? event.data.json() : {}
  const title = data.title || 'Dojo Admin'
  const options = { body: data.body || '' }
  event.waitUntil(self.registration.showNotification(title, options))
})

self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clients) => {
      for (const client of clients) {
        if (client.url.includes('/notifications') && 'focus' in client) {
          return client.focus()
        }
      }
      if (self.clients.openWindow) {
        return self.clients.openWindow('/notifications')
      }
    })
  )
})

import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { VitePWA } from 'vite-plugin-pwa';

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      // autoUpdate + skipWaiting: a new deploy replaces the cached app on the
      // next load (the old 'prompt' mode had no prompt UI, so admins stayed on
      // stale builds and never saw new pages).
      registerType: 'autoUpdate',
      manifest: {
        name: 'AgrowAI Admin Control Centre',
        short_name: 'AgrowAI Admin',
        description: 'Secure operations portal for authorised AgrowAI team members.',
        theme_color: '#123c2d',
        background_color: '#f4f1e8',
        display: 'standalone',
        start_url: '/',
        scope: '/',
        icons: [
          { src: '/pwa-192.svg', sizes: '192x192', type: 'image/svg+xml', purpose: 'any' },
          { src: '/pwa-512.svg', sizes: '512x512', type: 'image/svg+xml', purpose: 'any maskable' }
        ]
      },
      workbox: {
        navigateFallbackDenylist: [/^\/api\//, /^\/admin\/api\//],
        skipWaiting: true,
        clientsClaim: true,
        cleanupOutdatedCaches: true,
        runtimeCaching: []
      }
    })
  ],
  server: { port: 4173, strictPort: true }
});

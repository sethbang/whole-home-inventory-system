import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'
import fs from 'fs'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  server: {
    host: true,
    port: 5173,
    strictPort: true,
    https: {
      key: fs.readFileSync(path.resolve(__dirname, 'certs/key.pem')),
      cert: fs.readFileSync(path.resolve(__dirname, 'certs/cert.pem')),
    },
    proxy: {
      '/api': {
        target: 'https://backend:27182',
        secure: false,
        changeOrigin: true
      },
      '/uploads': {
        target: 'https://backend:27182',
        secure: false,
        changeOrigin: true
      }
    }
  },
  plugins: [
    react(),
    VitePWA({
      devOptions: {
        enabled: true,
        type: 'module'
      },
      registerType: 'autoUpdate',
      includeAssets: ['apple-touch-icon.png', 'apple-touch-icon-192x192.png', 'apple-touch-icon-512x512.png'],
      injectRegister: 'auto',
      strategies: 'generateSW',
      disable: false,
      selfDestroying: false,
      manifestFilename: 'manifest.webmanifest',
      manifest: {
        name: 'WHIS',
        short_name: 'WHIS',
        description: 'Track and manage your home inventory',
        theme_color: '#ffffff',
        background_color: '#ffffff',
        display: 'standalone',
        start_url: '/',
        scope: '/',
        icons: [
          {
            src: 'apple-touch-icon-192x192.png',
            sizes: '192x192',
            type: 'image/png',
            purpose: 'any'
          },
          {
            src: 'apple-touch-icon-192x192.png',
            sizes: '192x192',
            type: 'image/png',
            purpose: 'maskable'
          },
          {
            src: 'apple-touch-icon-512x512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'any'
          },
          {
            src: 'apple-touch-icon-512x512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'maskable'
          }
        ]
      },
      workbox: {
        globPatterns: ['**/*.{js,css,html,png}'],
        runtimeCaching: [
          {
            urlPattern: /^https:\/\/api\.*/i,
            handler: 'NetworkFirst',
            options: {
              cacheName: 'api-cache',
              networkTimeoutSeconds: 10,
              cacheableResponse: {
                statuses: [0, 200]
              }
            }
          }
        ],
        cleanupOutdatedCaches: true
      }
    })
  ]
})

import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'

import { VitePWA } from 'vite-plugin-pwa'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      registerType: 'autoUpdate',
      manifest: {
        name: 'RetroWeb Emulator',
        short_name: 'RetroWeb',
        description: 'A WASM-based retro game emulator in your browser',
        theme_color: '#09090b',
        background_color: '#09090b',
        display: 'standalone',
        orientation: 'landscape',
        icons: [
          {
            src: '/pwa-192x192.png',
            sizes: '192x192',
            type: 'image/png'
          },
          {
            src: '/pwa-512x512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'any maskable'
          }
        ]
      },
      workbox: {
        globPatterns: ['**/*.{js,css,html,ico,png,svg,wasm,json}'],
        maximumFileSizeToCacheInBytes: 50 * 1024 * 1024,
        runtimeCaching: [
          {
            urlPattern: /^https:\/\/raw\.githubusercontent\.com\/.*/i,
            handler: 'CacheFirst',
            options: {
              cacheName: 'github-thumbnails',
              expiration: { maxEntries: 200, maxAgeSeconds: 60 * 60 * 24 * 7 },
            },
          },
        ],
      }
    }),
    {
      name: 'configure-response-headers',
      configureServer: (server) => {
        server.middlewares.use((_req, res, next) => {
          res.setHeader('Cross-Origin-Opener-Policy', 'same-origin')
          res.setHeader('Cross-Origin-Embedder-Policy', 'require-corp')
          next()
        })
      },
      configurePreviewServer: (server) => {
        server.middlewares.use((_req, res, next) => {
          res.setHeader('Cross-Origin-Opener-Policy', 'same-origin')
          res.setHeader('Cross-Origin-Embedder-Policy', 'require-corp')
          next()
        })
      }
    }
  ],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  build: {
    target: 'esnext',
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor-react': ['react', 'react-dom', 'react-router'],
          'vendor-ui': ['lucide-react', 'sonner', 'clsx', 'tailwind-merge', 'class-variance-authority'],
          'vendor-data': ['dexie', 'zustand', 'date-fns'],
          'vendor-zip': ['@zip.js/zip.js'],
          'emulator': ['nostalgist'],
        },
      },
    },
  },
})

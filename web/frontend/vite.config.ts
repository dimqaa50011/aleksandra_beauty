import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { VitePWA } from 'vite-plugin-pwa'
import legacy from '@vitejs/plugin-legacy'
import path from 'path'

export default defineConfig({
  base: '/cabinet/', 

  plugins: [
    vue(),
    legacy({
      targets: ['defaults', 'not IE 11', 'Android >= 6', 'iOS >= 12'],
    }),
    VitePWA({
      strategies: 'injectManifest',
      srcDir: 'src',
      filename: 'sw.ts',
      registerType: 'autoUpdate',
      devOptions: { enabled: true },
      injectManifest: {
        globPatterns: ['**/*.{js,css,html,ico,png,svg}']
      },
      manifest: {
        name: 'Sasha Sugar | Личный кабинет',
        short_name: 'Sasha Sugar',
        description: 'Запись, бонусы и сертификаты',
        theme_color: '#f2a6b0',
        background_color: '#fef9f7',
        display: 'standalone',
        start_url: '/cabinet/', 
        scope: '/cabinet/',
        icons: [
          { src: 'icons/icon-192x192.png', sizes: '192x192', type: 'image/png' },
          { src: 'icons/icon-512x512.png', sizes: '512x512', type: 'image/png' },
          { src: 'icons/icon-512x512.png', sizes: '512x512', type: 'image/png', purpose: 'any maskable' }
        ]
      }
    })
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  build: {
    target: 'es2015',      // <-- Ключевой параметр для старых WebView
    cssTarget: 'chrome61', // <-- Для совместимости CSS
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
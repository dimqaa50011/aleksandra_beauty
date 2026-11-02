import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { VitePWA } from 'vite-plugin-pwa'
import path from 'path'

export default defineConfig({
  // 1. Указываем базовый путь для всего проекта
  base: '/cabinet/', 

  plugins: [
    vue(),
    VitePWA({
      strategies: 'injectManifest',
      srcDir: 'src',           // <-- Где искать sw.ts
      filename: 'sw.ts',       // <-- Имя нашего файла Service Worker
      registerType: 'autoUpdate',
      
      // Настройки для работы в dev-режиме (чтобы SW работал при npm run dev)
      devOptions: { 
        enabled: true,
        type: 'module'
      },

      // Указываем, какие файлы Workbox должен предварительно кэшировать (precache)
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
        
        // Пути для PWA
        start_url: '/cabinet/', 
        scope: '/cabinet/',
        
        icons: [
          {
            src: 'icons/icon-192x192.png',
            sizes: '192x192',
            type: 'image/png'
          },
          {
            src: 'icons/icon-512x512.png',
            sizes: '512x512',
            type: 'image/png'
          },
          {
            src: 'icons/icon-512x512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'any maskable'
          }
        ]
      }
    })
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
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
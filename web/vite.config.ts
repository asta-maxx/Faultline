import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // Proxy /api/* to the FastAPI backend (dev: port 8000; FAULTLINE_API overrides)
      '/api': {
        target: process.env.FAULTLINE_API ?? 'http://localhost:8000',
        changeOrigin: true,
        // No rewrite — FastAPI routes are at /api/*
      },
    },
  },
  build: {
    // Warn on chunks > 1 MB
    chunkSizeWarningLimit: 1000,
  },
})

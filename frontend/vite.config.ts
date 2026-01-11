import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8151',
        changeOrigin: true
      }
    }
  },
  preview: {
    port: 8150,
    host: true,
    allowedHosts: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8151',
        changeOrigin: true
      }
    }
  }
})

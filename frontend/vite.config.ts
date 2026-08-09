import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from "path"

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(import.meta.dirname, "./src"),
    },
  },
  server: {
    allowedHosts: ["tipoff-violation-bleep.ngrok-free.dev"],
    headers: {
      "ngrok-skip-browser-warning": "true",
      "Access-Control-Allow-Origin": "*",
    },
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8080',
        changeOrigin: true,
        secure: false,
      },
      '/ws': {
        target: 'ws://127.0.0.1:8080',
        ws: true,
        changeOrigin: true,
      },
      '/webhook': {
        target: 'http://127.0.0.1:8080',
        changeOrigin: true,
        secure: false,
      },
      '/webhooks': {
        target: 'http://127.0.0.1:8080',
        changeOrigin: true,
        secure: false,
      },
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('node_modules')) {
            if (id.includes('react') || id.includes('react-dom') || id.includes('react-router-dom') || id.includes('@tanstack/react-query')) {
              return 'vendor';
            }
            if (id.includes('lucide-react') || id.includes('date-fns') || id.includes('framer-motion')) {
              return 'ui';
            }
            return 'modules';
          }
        }
      }
    }
  }
})
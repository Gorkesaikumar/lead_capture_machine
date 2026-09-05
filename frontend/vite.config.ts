import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import path from "path"

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const backendTarget = env.VITE_BACKEND_TARGET || env.BACKEND_URL || 'http://127.0.0.1:8002';
  const wsTarget = backendTarget.replace(/^http/, 'ws');

  return {
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
          target: backendTarget,
          changeOrigin: true,
          secure: false,
        },
        '/ws': {
          target: wsTarget,
          ws: true,
          changeOrigin: true,
        },
        '/webhook': {
          target: backendTarget,
          changeOrigin: true,
          secure: false,
        },
        '/webhooks': {
          target: backendTarget,
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
  };
})
import path from 'node:path'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    // shadcn/ui convention — every component import in this project uses `@/`.
    alias: { '@': path.resolve(__dirname, './src') },
  },
  server: {
    // The FastAPI backend runs on :8000. Proxying in dev lets the app call
    // same-origin `/api/...` paths, so there is no CORS round-trip in dev and
    // no hardcoded host to swap at deploy time.
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/api/, ''),
      },
    },
  },
})

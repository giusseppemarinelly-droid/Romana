/// <reference types="vitest/config" />
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Misma variable que ya usa la GUI de escritorio para ubicar el backend
// (config.py → API_BASE_URL / ROMANA_API_URL). Default 127.0.0.1, NO
// "localhost": confirmado en planta que resolver "localhost" le suma ~2s
// a cada request (Windows intenta IPv6 primero y el backend solo escucha
// IPv4) -- ver el comentario de API_BASE_URL en config.py.
const backend = process.env.ROMANA_API_URL ?? 'http://127.0.0.1:8000'

// https://vite.dev/config/
export default defineConfig({
  // El backend sirve la web bajo /supervision/ (no en la raíz, para no
  // pisar las respuestas de error de la API -- ver montar_web_supervision
  // en backend/main.py). Mismo base en dev y en build, para que las rutas
  // se comporten igual en los dos.
  base: '/supervision/',
  plugins: [react(), tailwindcss()],
  server: {
    // Solo para `npm run dev`. En producción la SPA la sirve el propio
    // FastAPI (mismo origen), así que no hace falta proxy.
    proxy: {
      '/api': { target: backend, changeOrigin: true },
      '/ws': { target: backend, ws: true, changeOrigin: true },
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: './src/test-setup.ts',
  },
})

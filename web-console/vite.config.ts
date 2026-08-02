import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  base: '/',
  build: {
    outDir: path.resolve(__dirname, '../agent/web-console-dist'),
    emptyOutDir: true,
  },
  server: {
    port: 3000,
    host: true,
  },
})

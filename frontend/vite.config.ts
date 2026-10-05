import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  build: { chunkSizeWarningLimit: 1000 }, // single-page dashboard; charts + waveform are one chunk
  server: {
    proxy: { '/api': 'http://127.0.0.1:8000' },
  },
})

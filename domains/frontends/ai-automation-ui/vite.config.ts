import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  test: {
    globals: true,
    environment: 'happy-dom',
    setupFiles: './src/test/setup.ts',
  },
  plugins: [
    react(),
  ],
  server: {
    host: '0.0.0.0',
    port: 3001,
    strictPort: true
  },
  preview: {
    host: '0.0.0.0',
    port: 3001,
    strictPort: true
  },
  optimizeDeps: {
    include: ['react-force-graph', 'three']
  },
  define: {
    // Provide AFRAME as a global for modules that check for it
    // Only define in non-test environments
    ...(process.env.NODE_ENV !== 'test' && {
      'global.AFRAME': 'window.AFRAME'
    })
  }
})


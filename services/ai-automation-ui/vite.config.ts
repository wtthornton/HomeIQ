import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [
    react(),
    // Plugin to inject AFRAME stub and THREE.js preload before any modules load
    {
      name: 'aframe-stub',
      transformIndexHtml(html) {
        return html.replace(
          '<script type="module" src="/src/main.tsx"></script>',
          `<script>
            // Global AFRAME stub to prevent errors from react-force-graph
            if (typeof window !== 'undefined' && !window.AFRAME) {
              window.AFRAME = {
                registerComponent: function() {},
                registerSystem: function() {},
                registerPrimitive: function() {},
                scenes: [],
                version: '1.0.0'
              };
            }
          </script>
          <script type="module">
            // Preload THREE.js to ensure it's available globally for react-force-graph
            import * as THREE from 'three';
            if (typeof window !== 'undefined') {
              window.THREE = THREE;
            }
          </script>
          <script type="module" src="/src/main.tsx"></script>`
        );
      }
    }
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
    'global.AFRAME': 'window.AFRAME'
  }
})


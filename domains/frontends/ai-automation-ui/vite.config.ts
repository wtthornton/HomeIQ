import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  test: {
    globals: true,
    environment: 'happy-dom',
    setupFiles: './src/test/setup.ts',
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html', 'lcov'],
      reportsDirectory: './coverage',
      exclude: [
        'node_modules/',
        'src/test/',
        'src/mocks/',
        '**/*.test.ts',
        '**/*.test.tsx',
        '**/*.d.ts',
        'vite.config.ts',
      ],
      thresholds: {
        statements: 30,
        branches: 25,
        functions: 25,
        lines: 30,
      },
    },
  },
  plugins: [
    react({
      babel: {
        plugins: ['babel-plugin-react-compiler'],
      },
    }),
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


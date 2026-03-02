import { loadEnv } from 'vite';
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig(({ mode }) => ({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'happy-dom',
    setupFiles: ['./src/tests/setup.ts'],
    // Context7 recommended: Load all env vars, not just VITE_ prefixed
    env: loadEnv(mode, process.cwd(), ''),
    // Context7 pattern: Enable automatic environment reset
    unstubEnvs: true,
    css: false,
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html', 'lcov'],
      thresholds: {
        statements: 40,
        branches: 35,
        functions: 35,
        lines: 40,
      },
      exclude: [
        'node_modules/',
        'src/tests/',
        'src/mocks/',
        '**/*.test.ts',
        '**/*.test.tsx',
        '**/*.d.ts',
        'src/vite-env.d.ts',
      ],
    },
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
}));


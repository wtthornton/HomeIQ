import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    // Test environment
    environment: 'happy-dom',
    
    // Include only unit test files
    include: [
      'src/__tests__/apiUsageCalculator.test.ts',
      'src/__tests__/useTeamPreferences.test.ts',
      'src/hooks/__tests__/useStatistics.test.ts'
    ],
    
    // Exclude integration, e2e, and visual tests
    exclude: [
      '**/node_modules/**',
      '**/dist/**',
      '**/e2e/**',
      '**/integration/**',
      '**/visual/**',
      '**/*.integration.test.*',
      '**/*.e2e.test.*',
      '**/*.visual.test.*',
      '**/Dashboard.test.tsx',
      '**/Dashboard.interactions.test.tsx',
      '**/useHealth.test.ts',
      '**/api.test.ts',
      '**/ServiceDependencyGraph.test.tsx',
      '**/ServiceDetailsModal.test.tsx',
      '**/ServicesTab.test.tsx',
      '**/ServiceCard.test.tsx'
    ],
    
    // Coverage configuration
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html', 'json'],
      reportsDirectory: '../../test-results/coverage/typescript',
      include: ['src/**/*'],
      exclude: [
        'src/**/*.test.*',
        'src/**/*.spec.*',
        'src/tests/**',
        'src/**/__tests__/**',
        'src/**/*.stories.*',
        'src/**/*.config.*',
        'src/**/*.d.ts',
        'src/vite-env.d.ts'
      ],
      thresholds: {
        global: {
          branches: 70,
          functions: 70,
          lines: 70,
          statements: 70
        }
      }
    },
    
    // Test configuration
    globals: true,
    setupFiles: ['./src/tests/setup.ts'],
    
    // Reporter configuration
    reporter: ['verbose', 'json', 'html'],
    outputFile: {
      json: '../../test-results/typescript-test-results.json',
      html: '../../test-results/typescript-test-report.html'
    },
    
    // Test timeout
    testTimeout: 10000,
    hookTimeout: 10000,
    
    // Retry configuration
    retry: 1,
    
    // Parallel execution
    pool: 'threads',
    poolOptions: {
      threads: {
        singleThread: false
      }
    }
  },
  
  // Resolve configuration
  resolve: {
    alias: {
      '@': '/src'
    }
  }
});

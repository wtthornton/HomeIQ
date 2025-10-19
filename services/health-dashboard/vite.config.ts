import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve } from 'path'

// https://vitejs.dev/config/
export default defineConfig(({ command, mode }) => {
  // Load env file based on `mode` in the current working directory.
  const env = loadEnv(mode, process.cwd(), '')
  
  const isProduction = mode === 'production'
  const isDevelopment = mode === 'development'
  
  return {
    plugins: [
      react({
        // Enable React Fast Refresh
        fastRefresh: true,
        // Optimize JSX runtime
        jsxRuntime: 'automatic',
      }),
    ],
    
    // Base URL for the application
    base: env.VITE_BASE_URL || '/',
    
    // Resolve configuration
    resolve: {
      alias: {
        '@': resolve(__dirname, 'src'),
        '@components': resolve(__dirname, 'src/components'),
        '@hooks': resolve(__dirname, 'src/hooks'),
        '@services': resolve(__dirname, 'src/services'),
        '@types': resolve(__dirname, 'src/types'),
      },
    },
    
    // Development server configuration
    server: {
      port: parseInt(env.VITE_PORT || '3000'),
      host: true,
      open: true,
      cors: true,
      proxy: {
        // WebSocket proxy
        '/ws': {
          target: 'ws://homeiq-admin-dev:8004',
          ws: true,
          changeOrigin: true,
          secure: false,
        },
        // Sports API proxy
        '/api/sports': {
          target: 'http://localhost:8005',
          changeOrigin: true,
          secure: false,
          rewrite: (path) => path.replace(/^\/api\/sports/, '/api/v1'),
        },
        // General API proxy
        '/api': {
          target: 'http://homeiq-admin-dev:8004',
          changeOrigin: true,
          secure: false,
          rewrite: (path) => path.replace(/^\/api/, '/api/v1'),
        },
      },
    },
    
    // Preview server configuration
    preview: {
      port: parseInt(env.VITE_PREVIEW_PORT || '4173'),
      host: true,
      cors: true,
    },
    
    // Build configuration
    build: {
      outDir: 'dist',
      sourcemap: isDevelopment,
      minify: isProduction ? 'esbuild' : false,
      
      // Rollup options
      rollupOptions: {
        input: {
          main: resolve(__dirname, 'index.html'),
        },
        output: {
          // Code splitting
          manualChunks: {
            vendor: ['react', 'react-dom'],
          },
          // Asset naming
          chunkFileNames: 'assets/js/[name]-[hash].js',
          entryFileNames: 'assets/js/[name]-[hash].js',
          assetFileNames: (assetInfo) => {
            const extType = assetInfo.name?.split('.').at(1)
            if (/png|jpe?g|svg|gif|tiff|bmp|ico/i.test(extType ?? '')) {
              return `assets/images/[name]-[hash][extname]`
            }
            if (/css/i.test(extType ?? '')) {
              return `assets/css/[name]-[hash][extname]`
            }
            return `assets/[name]-[hash][extname]`
          },
        },
      },
      
      // Build optimization
      target: 'esnext',
      cssCodeSplit: true,
      reportCompressedSize: true,
      chunkSizeWarningLimit: 1000,
    },
    
    // CSS configuration
    css: {
      devSourcemap: isDevelopment,
    },
    
    // Environment variables
    define: {
      __APP_VERSION__: JSON.stringify(process.env.npm_package_version || '1.0.0'),
      __BUILD_TIME__: JSON.stringify(new Date().toISOString()),
      __ENVIRONMENT__: JSON.stringify(mode),
    },
    
    // Optimize dependencies
    optimizeDeps: {
      include: [
        'react',
        'react-dom',
      ],
    },
  }
})
/**
 * Global AFRAME stub to prevent errors from react-force-graph
 * react-force-graph checks for AFRAME globally but we only use 2D graphs
 * (THREE.js is preloaded in index.html via Vite plugin)
 * 
 * SECURITY: Only add stubs in browser environment, never in SSR
 */
if (typeof window !== 'undefined' && !(window as any).AFRAME) {
  (window as any).AFRAME = {
    registerComponent: () => {},
    registerSystem: () => {},
    registerPrimitive: () => {},
    scenes: [],
    version: '1.0.0'
  };
}

/**
 * Fallback: Ensure THREE.js is available globally if not already loaded
 * (Primary loading happens in index.html via Vite plugin)
 * 
 * SECURITY: Use dynamic import with error handling to prevent XSS
 */
if (typeof window !== 'undefined' && !(window as any).THREE) {
  import('three')
    .then((THREE) => {
      (window as any).THREE = THREE;
    })
    .catch((err: Error) => {
      // Log error but don't expose sensitive information
      console.warn('Failed to load THREE.js in main.tsx (fallback):', err.message);
    });
}

import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import App from './App.tsx'
import './index.css'
import './styles/design-system.css'

const queryClient = new QueryClient()

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>,
)


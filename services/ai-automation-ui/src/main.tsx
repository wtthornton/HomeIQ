// Global AFRAME stub to prevent errors from react-force-graph
// react-force-graph checks for AFRAME globally but we only use 2D graphs
if (typeof window !== 'undefined' && !(window as any).AFRAME) {
  (window as any).AFRAME = {
    registerComponent: () => {},
    registerSystem: () => {},
    registerPrimitive: () => {},
    scenes: [],
    version: '1.0.0'
  };
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


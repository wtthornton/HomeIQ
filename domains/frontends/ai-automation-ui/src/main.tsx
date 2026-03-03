// AFRAME stub loaded via /aframe-stub.js in index.html (runs before modules)
// THREE.js preload for react-force-graph - must run before any graph component
import './three-global';
import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import App from './App.tsx'
import './index.css'
import './styles/design-system.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30 * 1000,     // 30s before data considered stale
      retry: 2,                  // 2 retries on failure
      refetchOnWindowFocus: false,
    },
  },
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>,
)


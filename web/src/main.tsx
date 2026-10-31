import { lazy, StrictMode, Suspense } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import './styles.css'

const root = document.getElementById('root')
if (!root) throw new Error('Application root is missing')

const Tour = lazy(() => import('./CinematicTour'))
const isTour = new URLSearchParams(location.search).has('tour')
createRoot(root).render(<StrictMode>{isTour
  ? <Suspense fallback={<p role="status">Preparing your house film...</p>}><Tour /></Suspense>
  : <App />}</StrictMode>)

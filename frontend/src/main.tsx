import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { RepoContextProvider } from './contexts/RepoContext.tsx'
import { TourProvider } from './components/tours/TourProvider.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <RepoContextProvider>
      <TourProvider>
        <App />
      </TourProvider>
    </RepoContextProvider>
  </StrictMode>,
)

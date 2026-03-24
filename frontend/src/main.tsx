import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { RepoContextProvider } from './contexts/RepoContext.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <RepoContextProvider>
      <App />
    </RepoContextProvider>
  </StrictMode>,
)

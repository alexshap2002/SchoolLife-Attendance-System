import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App.tsx'
import './index.css'

// Initialize Telegram WebApp
declare global {
  interface Window {
    Telegram: any;
  }
}

if (window.Telegram?.WebApp) {
  const webApp = window.Telegram.WebApp;
  webApp.ready();
  webApp.expand();
  
  // Enable haptic feedback
  webApp.HapticFeedback?.impactOccurred('medium');
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>,
)

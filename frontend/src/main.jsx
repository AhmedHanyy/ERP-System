import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: '#131C2E',
            color: '#F1F5F9',
            border: '1px solid #1E2D47',
            borderRadius: '12px',
          },
          success: { iconTheme: { primary: '#10B981', secondary: '#131C2E' } },
          error: { iconTheme: { primary: '#F43F5E', secondary: '#131C2E' } },
        }}
      />
    </BrowserRouter>
  </React.StrictMode>
)

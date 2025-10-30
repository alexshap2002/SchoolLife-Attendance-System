import { Routes, Route } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { useEffect } from 'react'
import { useTelegramStore } from './stores/telegramStore'
import GroupsPage from './pages/GroupsPage'
import AttendancePage from './pages/AttendancePage'
import LoadingPage from './pages/LoadingPage'

function App() {
  const { initWebApp, isInitialized } = useTelegramStore()

  useEffect(() => {
    initWebApp()
  }, [initWebApp])

  if (!isInitialized) {
    return <LoadingPage />
  }

  return (
    <div className="h-screen overflow-hidden bg-telegram-bg text-telegram-text">
      <Routes>
        <Route path="/" element={<GroupsPage />} />
        <Route path="/groups" element={<GroupsPage />} />
        <Route path="/attendance/:groupId" element={<AttendancePage />} />
      </Routes>
      
      <Toaster
        position="top-center"
        toastOptions={{
          duration: 3000,
          style: {
            background: 'var(--tg-theme-button-color, #3390ec)',
            color: 'var(--tg-theme-button-text-color, #ffffff)',
            border: 'none',
            borderRadius: '12px',
            fontSize: '16px',
            fontWeight: '500',
            padding: '12px 16px',
          },
        }}
      />
    </div>
  )
}

export default App

import { BrowserRouter, Navigate, Outlet, Route, Routes } from 'react-router-dom'
import { Toaster } from 'sonner'
import { AuthProvider } from '@/context/AuthContext.jsx'
import AppHeader from '@/components/AppHeader.jsx'
import WatchlistPage from '@/pages/WatchlistPage.jsx'
import LoginPage from '@/pages/LoginPage.jsx'
import RegisterPage from '@/pages/RegisterPage.jsx'
import AccountPage from '@/pages/AccountPage.jsx'
import AdminPage from '@/pages/AdminPage.jsx'
import './App.css'

function Layout() {
  return (
    <div className="min-h-screen bg-background">
      <AppHeader />
      <Outlet />
    </div>
  )
}

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Toaster />
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<WatchlistPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/account" element={<AccountPage />} />
            <Route path="/admin" element={<AdminPage />} />
            <Route path="/:username" element={<WatchlistPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}

export default App

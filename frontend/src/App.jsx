import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './context/AuthContext'
import AppLayout from './components/layout/AppLayout'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import GoogleCallbackPage from './pages/Googlecallbackpage'
import DashboardPage from './pages/DashboardPage'
import ExpensesPage from './pages/ExpensesPage'
import AddExpensePage from './pages/AddExpensePage'
import EditExpensePage from './pages/EditExpensePage'
import ReceiptsPage from './pages/ReceiptsPage'
import BudgetsPage from './pages/BudgetsPage'
import InsightsPage from './pages/InsightsPage'
import ReportsPage from './pages/ReportsPage'
import ProfilePage from './pages/ProfilePage'
import ChatbotPage from './pages/ChatbotPage'
import NotFoundPage from './pages/NotFoundPage'
import ThemeToggle from './components/ui/ThemeToggle'

function PrivateRoute({ children }) {
  const { user, loading } = useAuth()
  if (loading) return (
    <div className="flex items-center justify-center h-screen" style={{ background: 'var(--bg-base)' }}>
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#1E3A5F]" />
    </div>
  )
  return user ? children : <Navigate to="/login" replace />
}

function PublicRoute({ children }) {
  const { user, loading } = useAuth()
  if (loading) return null
  return !user ? children : <Navigate to="/dashboard" replace />
}

export default function App() {
  return (
    <>
      <Routes>
        {/* Public routes */}
        <Route path="/login" element={<PublicRoute><LoginPage /></PublicRoute>} />
        <Route path="/register" element={<PublicRoute><RegisterPage /></PublicRoute>} />

        {/* Google OAuth callback — always accessible */}
        <Route path="/auth/google/success" element={<GoogleCallbackPage />} />

        {/* Protected routes */}
        <Route path="/" element={<PrivateRoute><AppLayout /></PrivateRoute>}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="expenses" element={<ExpensesPage />} />
          <Route path="expenses/add" element={<AddExpensePage />} />
          <Route path="expenses/:id/edit" element={<EditExpensePage />} />
          <Route path="receipts" element={<ReceiptsPage />} />
          <Route path="budgets" element={<BudgetsPage />} />
          <Route path="insights" element={<InsightsPage />} />
          <Route path="reports" element={<ReportsPage />} />
          <Route path="profile" element={<ProfilePage />} />
          <Route path="chatbot" element={<ChatbotPage />} />
        </Route>

        <Route path="*" element={<NotFoundPage />} />
      </Routes>
      <ThemeToggle />
    </>
  )
}
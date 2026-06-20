import { useNavigate } from 'react-router-dom'
import Button from '../components/ui/Button'

export default function NotFoundPage() {
  const navigate = useNavigate()
  return (
    <div className="min-h-screen flex flex-col items-center justify-center text-center p-4">
      <div className="text-8xl mb-4">💸</div>
      <h1 className="text-4xl font-bold text-primary mb-2">404</h1>
      <p className="text-gray-500 mb-6">Oops! This page doesn't exist.</p>
      <Button onClick={() => navigate('/dashboard')}>Back to Dashboard</Button>
    </div>
  )
}

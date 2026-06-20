import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard, Receipt, PlusCircle, Wallet,
  Lightbulb, FileText, User, X, TrendingUp, Upload, MessageCircle
} from 'lucide-react'

const links = [
  { to: '/dashboard',   label: 'Dashboard',       icon: LayoutDashboard },
  { to: '/expenses',    label: 'Expenses',         icon: Receipt },
  { to: '/expenses/add',label: 'Add Expense',      icon: PlusCircle },
  { to: '/receipts',    label: 'Receipts Upload',  icon: Upload },
  { to: '/budgets',     label: 'Budgets',          icon: Wallet },
  { to: '/insights',    label: 'AI Insights',      icon: Lightbulb },
  { to: '/chatbot',     label: 'Expense Assistant',icon: MessageCircle },
  { to: '/reports',     label: 'Reports',          icon: FileText },
  { to: '/profile',     label: 'Profile',          icon: User },
]

export default function Sidebar({ open, onClose }) {
  return (
    <>
      {open && <div className="fixed inset-0 bg-black/40 z-20 lg:hidden" onClick={onClose} />}
      <aside className={`
        fixed lg:static inset-y-0 left-0 z-30 w-64 flex flex-col
        transform transition-transform duration-200
        ${open ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
      `} style={{ background: 'var(--bg-sidebar)' }}>

        {/* Logo — "Expense Manager" */}
        <div className="flex items-center justify-between px-6 py-5 border-b border-white/10">
          <div>
            <h1 className="text-white font-bold text-lg leading-tight">💰 SmartTracker</h1>
            <p className="text-blue-200 text-xs">Expense Manager</p>
          </div>
          <button onClick={onClose} className="lg:hidden text-white/70 hover:text-white">
            <X size={20} />
          </button>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
          {links.map(({ to, label, icon: Icon }) => (
            <NavLink key={to} to={to} onClick={onClose}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive ? 'bg-white/20 text-white' : 'text-blue-100 hover:bg-white/10 hover:text-white'
                }`
              }>
              <Icon size={17} />
              {label}
            </NavLink>
          ))}
        </nav>
        {/* Bottom text removed as per requirement */}
      </aside>
    </>
  )
}

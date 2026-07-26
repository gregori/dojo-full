import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import {
  LogOut,
  Users,
  Calendar,
  Home,
  Award,
  QrCode,
  Settings,
  Wallet,
  FileText,
  BarChart3,
} from 'lucide-react'

interface LayoutProps {
  children: React.ReactNode
}

export default function Layout({ children }: LayoutProps) {
  const { user, logout, isAdmin } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const navItems = [
    { path: '/', label: 'Dashboard', icon: Home },
    { path: '/students', label: 'Alunos', icon: Users },
    { path: '/events', label: 'Eventos', icon: Calendar },
    { path: '/exams', label: 'Exames', icon: Award },
    { path: '/reports', label: 'Relatórios', icon: BarChart3 },
    ...(isAdmin
      ? [
          { path: '/plans', label: 'Planos', icon: Wallet },
          { path: '/contract-templates', label: 'Modelo de Contrato', icon: FileText },
          { path: '/event-types', label: 'Tipos de Evento', icon: Calendar },
          { path: '/belts', label: 'Faixas', icon: Award },
          { path: '/dojos', label: 'Dojos', icon: Settings },
          { path: '/belt-requirements', label: 'Requisitos', icon: Settings },
        ]
      : []),
  ]

  return (
    <div className="min-h-screen bg-gray-50 flex">
      {/* Sidebar */}
      <aside className="w-64 bg-white shadow-md">
        <div className="p-6">
          <h1 className="text-2xl font-bold text-gray-800">Dojo Admin</h1>
          <p className="text-sm text-gray-500 mt-1">{user?.full_name}</p>
          <span className="inline-block mt-2 px-2 py-1 text-xs rounded bg-blue-100 text-blue-800">
            {user?.role === 'admin' ? 'Administrador' : 'Instrutor'}
          </span>
        </div>
        <nav className="mt-6">
          {navItems.map((item) => {
            const Icon = item.icon
            const isActive = location.pathname === item.path
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center px-6 py-3 text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-blue-50 text-blue-600 border-r-2 border-blue-600'
                    : 'text-gray-600 hover:bg-gray-50'
                }`}
              >
                <Icon className="w-5 h-5 mr-3" />
                {item.label}
              </Link>
            )
          })}
          <div className="mt-4 px-6">
            <Link
              to="/checkin"
              target="_blank"
              className="flex items-center px-4 py-2 text-sm font-medium text-white bg-green-600 rounded hover:bg-green-700"
            >
              <QrCode className="w-4 h-4 mr-2" />
              Tela de Check-in
            </Link>
          </div>
        </nav>
        <div className="absolute bottom-0 w-64 p-6">
          <button
            onClick={handleLogout}
            className="flex items-center text-sm text-gray-600 hover:text-red-600 transition-colors"
          >
            <LogOut className="w-4 h-4 mr-2" />
            Sair
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 p-8 overflow-auto">{children}</main>
    </div>
  )
}

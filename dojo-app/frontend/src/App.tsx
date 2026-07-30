import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider, useAuth } from './hooks/useAuth'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import StudentsPage from './pages/StudentsPage'
import EventsPage from './pages/EventsPage'
import EventSeriesPage from './pages/EventSeriesPage'
import CheckInPage from './pages/CheckInPage'
import CheckInPrintPage from './pages/CheckInPrintPage'
import PreCheckInPage from './pages/PreCheckInPage'
import MedicalExamPage from './pages/MedicalExamPage'
import ExamsPage from './pages/ExamsPage'
import PlansPage from './pages/PlansPage'
import ContractTemplatesPage from './pages/ContractTemplatesPage'
import BeltRequirementsPage from './pages/BeltRequirementsPage'
import BeltsPage from './pages/BeltsPage'
import DojosPage from './pages/DojosPage'
import EventTypesPage from './pages/EventTypesPage'
import ReportsPage from './pages/ReportsPage'
import UsersPage from './pages/UsersPage'
import Layout from './components/Layout'
import { ToastContainer } from './components/Toast'

const queryClient = new QueryClient()

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const { user } = useAuth()
  return user ? <Layout>{children}</Layout> : <Navigate to="/login" />
}

function AdminRoute({ children }: { children: React.ReactNode }) {
  const { user, isAdmin } = useAuth()
  if (!user) return <Navigate to="/login" />
  if (!isAdmin) return <Navigate to="/" />
  return <Layout>{children}</Layout>
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <ToastContainer />
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/checkin" element={<CheckInPage />} />
            <Route path="/precheckin" element={<PreCheckInPage />} />
            <Route path="/medical-exam" element={<MedicalExamPage />} />
            <Route
              path="/"
              element={
                <PrivateRoute>
                  <DashboardPage />
                </PrivateRoute>
              }
            />
            <Route
              path="/students"
              element={
                <PrivateRoute>
                  <StudentsPage />
                </PrivateRoute>
              }
            />
            <Route
              path="/events"
              element={
                <PrivateRoute>
                  <EventsPage />
                </PrivateRoute>
              }
            />
            <Route
              path="/event-series"
              element={
                <PrivateRoute>
                  <EventSeriesPage />
                </PrivateRoute>
              }
            />
            <Route
              path="/checkin-print"
              element={
                <PrivateRoute>
                  <CheckInPrintPage />
                </PrivateRoute>
              }
            />
            <Route
              path="/exams"
              element={
                <PrivateRoute>
                  <ExamsPage />
                </PrivateRoute>
              }
            />
            <Route
              path="/reports"
              element={
                <PrivateRoute>
                  <ReportsPage />
                </PrivateRoute>
              }
            />
            <Route
              path="/belt-requirements"
              element={
                <AdminRoute>
                  <BeltRequirementsPage />
                </AdminRoute>
              }
            />
            <Route
              path="/plans"
              element={
                <AdminRoute>
                  <PlansPage />
                </AdminRoute>
              }
            />
            <Route
              path="/contract-templates"
              element={
                <AdminRoute>
                  <ContractTemplatesPage />
                </AdminRoute>
              }
            />
            <Route
              path="/event-types"
              element={
                <AdminRoute>
                  <EventTypesPage />
                </AdminRoute>
              }
            />
            <Route
              path="/belts"
              element={
                <AdminRoute>
                  <BeltsPage />
                </AdminRoute>
              }
            />
            <Route
              path="/dojos"
              element={
                <AdminRoute>
                  <DojosPage />
                </AdminRoute>
              }
            />
            <Route
              path="/users"
              element={
                <AdminRoute>
                  <UsersPage />
                </AdminRoute>
              }
            />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  )
}

export default App

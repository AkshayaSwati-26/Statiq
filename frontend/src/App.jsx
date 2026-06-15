import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useTheme } from './hooks/useTheme'
import AppLayout        from './components/layout/AppLayout'
import LoginPage        from './pages/LoginPage'
import DashboardHome    from './pages/DashboardHome'
import DataIngestion    from './pages/DataIngestion'
import QueryWorkspace   from './pages/QueryWorkspace'
import ResultsDashboard from './pages/ResultsDashboard'
import QueryHistory     from './pages/QueryHistory'
import ExportsPage      from './pages/ExportsPage'
import SettingsPage     from './pages/SettingsPage'

export default function App() {
  const { isDark } = useTheme()
  return (
    <div data-theme={isDark ? 'dark' : 'light'} style={{ minHeight:'100vh' }}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route element={<AppLayout />}>
            <Route path="/"          element={<Navigate to="/dashboard" />} />
            <Route path="/dashboard" element={<DashboardHome />} />
            <Route path="/ingest"    element={<DataIngestion />} />
            <Route path="/query"     element={<QueryWorkspace />} />
            <Route path="/results"   element={<ResultsDashboard />} />
            <Route path="/history"   element={<QueryHistory />} />
            <Route path="/exports"   element={<ExportsPage />} />
            <Route path="/settings"  element={<SettingsPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </div>
  )
}
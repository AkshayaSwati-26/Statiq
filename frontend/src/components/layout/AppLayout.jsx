import { Outlet, Navigate } from 'react-router-dom'
import Sidebar from './Sidebar'
import TopNavbar from './TopNavbar'
import { useSession } from '../../hooks/useSession'

export default function AppLayout() {
  const user = useSession(state => state.user)

  if (!user) {
    return <Navigate to="/login" replace />
  }

  return (
    <div style={{ display:'flex', height:'100vh', overflow:'hidden', background:'var(--ink)' }}>
      <Sidebar />
      <div style={{ flex:1, display:'flex', flexDirection:'column', overflow:'hidden' }}>
        <TopNavbar />
        <main className="iris-grid" style={{ flex:1, overflowY:'auto', padding:24 }}>
          <Outlet />
        </main>
      </div>
    </div>
  )
}
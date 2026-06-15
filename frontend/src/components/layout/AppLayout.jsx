import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import TopNavbar from './TopNavbar'

export default function AppLayout() {
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
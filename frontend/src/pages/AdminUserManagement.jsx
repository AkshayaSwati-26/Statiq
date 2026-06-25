import { useState, useEffect } from 'react'
import { useSession } from '../hooks/useSession'
import axios from 'axios'

export default function AdminUserManagement() {
  const { user } = useSession()
  useEffect(() => {
    // No-op since we removed pending registrations
  }, [])

  const handleExport = () => {
    window.location.href = '/v1/admin/users/export'
  }

  if (user?.scope !== 'admin') {
    return (
      <div style={{ padding: 40, fontFamily: "'Space Mono',monospace", color: '#ef4444' }}>
        // ERROR: UNAUTHORIZED ACCESS
      </div>
    )
  }

  return (
    <div style={{ padding: '40px', maxWidth: 1200, margin: '0 auto', fontFamily: "'Inter', sans-serif", color: '#f1f5f9' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 32 }}>
        <div>
          <h1 style={{ fontFamily: "'Syne', sans-serif", fontSize: 28, margin: '0 0 8px 0' }}>User Management</h1>
          <p style={{ margin: 0, color: 'rgba(148,163,184,1)', fontSize: 14 }}>Manage user accounts.</p>
        </div>
        <button
          onClick={handleExport}
          style={{
            background: 'rgba(245,158,11,0.1)', border: '1px solid rgba(245,158,11,0.4)',
            color: '#f59e0b', padding: '10px 16px', borderRadius: 4, cursor: 'pointer',
            fontFamily: "'Space Mono', monospace", fontSize: 12, display: 'flex', alignItems: 'center', gap: 8
          }}
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="16" height="16">
            <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/>
          </svg>
          EXPORT USERS CSV
        </button>
      </div>


    </div>
  )
}

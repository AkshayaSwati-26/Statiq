import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useSession } from '../hooks/useSession'
import { USE_MOCK_UPLOAD } from '../utils/mockData'
import { getErrorMessage } from '../utils/errors'
import axios from 'axios'

/* ── Animated canvas: radar + floating data particles ── */
function HeroCanvas() {
  const ref = useRef()
  useEffect(() => {
    const canvas = ref.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    let raf, t = 0

    const resize = () => {
      canvas.width  = canvas.offsetWidth  * window.devicePixelRatio
      canvas.height = canvas.offsetHeight * window.devicePixelRatio
      ctx.scale(window.devicePixelRatio, window.devicePixelRatio)
    }
    resize()
    window.addEventListener('resize', resize)

    // data particles
    const particles = Array.from({ length: 60 }, () => ({
      x: Math.random() * 600,
      y: Math.random() * 600,
      vx: (Math.random() - 0.5) * 0.3,
      vy: (Math.random() - 0.5) * 0.3,
      r:  Math.random() * 1.5 + 0.5,
      o:  Math.random(),
      label: Math.random() > 0.7 ? ['PLFS','HCES','NSSO','2024','SQL','GOV','IN','TN','UR','M/F'][Math.floor(Math.random()*10)] : null,
    }))

    // grid lines
    const gridLines = Array.from({ length: 6 }, (_, i) => ({
      x1: 0, y1: i * 100, x2: 600, y2: i * 100,
    }))

    const draw = () => {
      const W = canvas.offsetWidth
      const H = canvas.offsetHeight
      ctx.clearRect(0, 0, W, H)
      t += 0.008

      // background gradient
      const bg = ctx.createRadialGradient(W/2, H/2, 0, W/2, H/2, Math.max(W,H)/1.5)
      bg.addColorStop(0,   'rgba(3,25,65,1)')
      bg.addColorStop(0.5, 'rgba(2,15,40,1)')
      bg.addColorStop(1,   'rgba(1,8,20,1)')
      ctx.fillStyle = bg
      ctx.fillRect(0, 0, W, H)

      // grid
      ctx.strokeStyle = 'rgba(34,211,238,0.05)'
      ctx.lineWidth = 1
      for (let x = 0; x < W; x += 32) {
        ctx.beginPath(); ctx.moveTo(x,0); ctx.lineTo(x,H); ctx.stroke()
      }
      for (let y = 0; y < H; y += 32) {
        ctx.beginPath(); ctx.moveTo(0,y); ctx.lineTo(W,y); ctx.stroke()
      }

      // radar circle (centred right side)
      const cx = W * 0.62, cy = H * 0.5
      const maxR = Math.min(W, H) * 0.38

      // concentric rings
      for (let i = 1; i <= 4; i++) {
        const r = maxR * i / 4
        ctx.beginPath()
        ctx.arc(cx, cy, r, 0, Math.PI * 2)
        ctx.strokeStyle = `rgba(34,211,238,${0.06 + i * 0.02})`
        ctx.lineWidth = 1
        ctx.stroke()
      }

      // cross hairs
      ctx.strokeStyle = 'rgba(34,211,238,0.08)'
      ctx.lineWidth = 1
      ctx.setLineDash([4, 8])
      ctx.beginPath(); ctx.moveTo(cx - maxR - 20, cy); ctx.lineTo(cx + maxR + 20, cy); ctx.stroke()
      ctx.beginPath(); ctx.moveTo(cx, cy - maxR - 20); ctx.lineTo(cx, cy + maxR + 20); ctx.stroke()
      ctx.setLineDash([])

      // rotating radar sweep
      const sweepAngle = t * 1.2
      const grad = ctx.createConicalGradient
        ? null
        : (() => {
            const g = ctx.createLinearGradient(cx, cy, cx + maxR, cy)
            g.addColorStop(0, 'rgba(245,158,11,0.5)')
            g.addColorStop(1, 'rgba(245,158,11,0)')
            return g
          })()

      // sweep sector
      ctx.save()
      ctx.translate(cx, cy)
      ctx.rotate(sweepAngle)
      ctx.beginPath()
      ctx.moveTo(0, 0)
      ctx.arc(0, 0, maxR, -0.5, 0.1)
      ctx.closePath()
      const sweepGrad = ctx.createLinearGradient(0, 0, maxR, 0)
      sweepGrad.addColorStop(0, 'rgba(245,158,11,0.35)')
      sweepGrad.addColorStop(1, 'rgba(245,158,11,0)')
      ctx.fillStyle = sweepGrad
      ctx.fill()
      // sweep line
      ctx.beginPath()
      ctx.moveTo(0, 0)
      ctx.lineTo(maxR, 0)
      ctx.strokeStyle = 'rgba(245,158,11,0.8)'
      ctx.lineWidth = 1.5
      ctx.stroke()
      ctx.restore()

      // blip dots on radar
      const blips = [
        { angle: 0.8, dist: 0.6 }, { angle: 2.1, dist: 0.4 },
        { angle: 3.7, dist: 0.75 }, { angle: 5.0, dist: 0.3 },
        { angle: 1.4, dist: 0.85 },
      ]
      blips.forEach(b => {
        const bx = cx + Math.cos(b.angle) * maxR * b.dist
        const by = cy + Math.sin(b.angle) * maxR * b.dist
        const pulse = (Math.sin(t * 3 + b.angle) + 1) / 2
        ctx.beginPath()
        ctx.arc(bx, by, 3, 0, Math.PI * 2)
        ctx.fillStyle = `rgba(34,211,238,${0.5 + pulse * 0.5})`
        ctx.fill()
        // ripple
        ctx.beginPath()
        ctx.arc(bx, by, 3 + pulse * 8, 0, Math.PI * 2)
        ctx.strokeStyle = `rgba(34,211,238,${0.3 - pulse * 0.3})`
        ctx.lineWidth = 1
        ctx.stroke()
      })

      // centre dot
      ctx.beginPath()
      ctx.arc(cx, cy, 4, 0, Math.PI * 2)
      ctx.fillStyle = 'var(--amber, #f59e0b)'
      ctx.fill()
      ctx.beginPath()
      ctx.arc(cx, cy, 8 + Math.sin(t*3)*3, 0, Math.PI * 2)
      ctx.strokeStyle = 'rgba(245,158,11,0.4)'
      ctx.lineWidth = 1
      ctx.stroke()

      // floating particles + labels
      particles.forEach(p => {
        p.x += p.vx; p.y += p.vy
        if (p.x < 0) p.x = W; if (p.x > W) p.x = 0
        if (p.y < 0) p.y = H; if (p.y > H) p.y = 0
        p.o = 0.3 + Math.sin(t * 2 + p.x) * 0.3

        ctx.beginPath()
        ctx.arc(p.x, p.y, p.r, 0, Math.PI*2)
        ctx.fillStyle = `rgba(34,211,238,${p.o})`
        ctx.fill()

        if (p.label) {
          ctx.font = '8px "Space Mono", monospace'
          ctx.fillStyle = `rgba(34,211,238,${p.o * 0.7})`
          ctx.fillText(p.label, p.x + 4, p.y - 4)
        }
      })

      // connection lines between nearby particles
      for (let i = 0; i < particles.length; i++) {
        for (let j = i+1; j < particles.length; j++) {
          const dx = particles[i].x - particles[j].x
          const dy = particles[i].y - particles[j].y
          const dist = Math.sqrt(dx*dx + dy*dy)
          if (dist < 80) {
            ctx.beginPath()
            ctx.moveTo(particles[i].x, particles[i].y)
            ctx.lineTo(particles[j].x, particles[j].y)
            ctx.strokeStyle = `rgba(34,211,238,${0.07 * (1 - dist/80)})`
            ctx.lineWidth = 0.5
            ctx.stroke()
          }
        }
      }

      // scan line overlay
      const scanY = ((t * 80) % (H + 40)) - 20
      const scanGrad = ctx.createLinearGradient(0, scanY - 10, 0, scanY + 10)
      scanGrad.addColorStop(0,   'transparent')
      scanGrad.addColorStop(0.5, 'rgba(34,211,238,0.04)')
      scanGrad.addColorStop(1,   'transparent')
      ctx.fillStyle = scanGrad
      ctx.fillRect(0, scanY - 10, W, 20)

      raf = requestAnimationFrame(draw)
    }

    draw()
    return () => { cancelAnimationFrame(raf); window.removeEventListener('resize', resize) }
  }, [])

  return <canvas ref={ref} style={{ position:'absolute', inset:0, width:'100%', height:'100%' }} />
}

/* ── Typewriter effect ── */
function Typewriter({ texts, speed = 60 }) {
  const [display, setDisplay] = useState('')
  const [idx,     setIdx]     = useState(0)
  const [charIdx, setCharIdx] = useState(0)
  const [deleting, setDeleting] = useState(false)

  useEffect(() => {
    const current = texts[idx]
    const timer = setTimeout(() => {
      if (!deleting) {
        setDisplay(current.slice(0, charIdx + 1))
        if (charIdx + 1 === current.length) {
          setTimeout(() => setDeleting(true), 1800)
        } else {
          setCharIdx(c => c + 1)
        }
      } else {
        setDisplay(current.slice(0, charIdx - 1))
        if (charIdx - 1 === 0) {
          setDeleting(false)
          setIdx(i => (i + 1) % texts.length)
          setCharIdx(0)
        } else {
          setCharIdx(c => c - 1)
        }
      }
    }, deleting ? 30 : speed)
    return () => clearTimeout(timer)
  }, [charIdx, deleting, idx, texts, speed])

  return (
    <span style={{ color:'var(--amber, #f59e0b)', fontFamily:"'Space Mono',monospace" }}>
      {display}<span style={{ animation:'blink 1s step-end infinite', opacity:1 }}>█</span>
    </span>
  )
}

const TYPEWRITER_TEXTS = [
  'TRANSFORMING SURVEY MICRODATA',
  'NATURAL LANGUAGE TO SQL ENGINE',
  'PLFS · HCES · NSSO ANALYTICS',
  'PRIVACY-SAFE POLICY INTELLIGENCE',
  'DPDP ACT 2023 COMPLIANT',
]

export default function LoginPage() {
  const navigate  = useNavigate()
  const [email,    setEmail]    = useState('')
  const [password, setPassword] = useState('')
  const [loading,  setLoading]  = useState(false)
  const [error,    setError]    = useState('')
  const [success,  setSuccess]  = useState('')
  const [phase,    setPhase]    = useState(0) // 0=loading 1=ready
  const [isSignup, setIsSignup] = useState(false)
  const [role,     setRole]     = useState('public')
  const [adminPasscode, setAdminPasscode] = useState('')
  const [name, setFullName] = useState('')
  const [institution, setInstitution] = useState('')
  const [purpose, setPurpose] = useState('')
  const [otpMode, setOtpMode] = useState(false)
  const [otp, setOtp] = useState('')

  useEffect(() => {
    // simulate system boot sequence
    const t = setTimeout(() => setPhase(1), 2200)
    return () => clearTimeout(t)
  }, [])

  const loginUser = useSession(state => state.loginUser)

  const handleLogin = async (e) => {
    e.preventDefault()
    if (!email || !password) { setError('// ERROR: credentials required'); return }
    setError(''); setLoading(true)
    
    // Extract userId from email
    const userId = email.includes('@') ? email.split('@')[0].toLowerCase().trim() : email.toLowerCase().trim()
    const cleanEmail = email.includes('@') ? email.trim() : `${userId}@mospi.gov.in`

    if (isSignup) {
      try {
        let scope = role

        if (!USE_MOCK_UPLOAD) {
          try {
            const res = await axios.post(
              '/v1/auth/register',
              {
                email: email.trim(),
                password: password,
                scope: role,
                admin_passcode: role === 'admin' ? adminPasscode : null,
                name: name,
                institution: institution,
                purpose: purpose
              },
              { withCredentials: true }
            )
            scope = res.data.scope
          } catch (err) {
            setError(getErrorMessage(err, '// ERROR: Registration failed'))
            setLoading(false)
            return
          }
        } else {
          // Mock registration
          await new Promise(r => setTimeout(r, 1300))
          if (role === 'admin' && adminPasscode !== 'MoSPIAdmin2026') {
            setError('// ERROR: Invalid admin passcode')
            setLoading(false)
            return
          }
          scope = role === 'admin' ? 'admin' : 'public'
        }

        loginUser({
          userId,
          email: email.trim(),
          scope
        })

        setLoading(false)
        navigate('/dashboard')
      } catch (err) {
        setError('// ERROR: Registration process failed')
        setLoading(false)
      }
      return
    }

    try {
      let scope = 'public'

      if (!USE_MOCK_UPLOAD) {
        // Real backend authentication — sets HttpOnly cookie automatically
        try {
          const res = await axios.post(
            '/v1/auth/login',
            { user_id: email.trim().toLowerCase(), password: password },
            { withCredentials: true }   // must be true to receive HttpOnly cookies
          )
          scope = res.data.scope
        } catch (err) {
          setError(getErrorMessage(err, '// ERROR: Invalid credentials'))
          setLoading(false)
          return
        }
      } else {
        // Mock authentication (USE_MOCK_UPLOAD = true)
        await new Promise(r => setTimeout(r, 1300))
        if (userId === 'admin' && password === 'AdminPassword123!') {
          scope = 'admin'
        } else if (userId === 'analyst' && password === 'AdminPassword123!') {
          scope = 'research'
        } else if (userId === 'student' && password === 'AdminPassword123!') {
          scope = 'public'
        } else {
          setError('// ERROR: Invalid credentials')
          setLoading(false)
          return
        }
      }

      loginUser({
        userId,
        email: cleanEmail,
        scope
      })

      setLoading(false)
      navigate('/dashboard')
    } catch (err) {
      setError('// ERROR: Authentication process failed')
      setLoading(false)
    }
  }

  const handleOtpVerify = async (e) => {
    e.preventDefault()
    if (!otp) { setError('// ERROR: OTP required'); return }
    setError(''); setLoading(true)

    try {
      let scope = 'public'
      const userId = email.includes('@') ? email.split('@')[0].toLowerCase().trim() : email.toLowerCase().trim()
      const cleanEmail = email.includes('@') ? email.trim() : `${userId}@mospi.gov.in`

      if (!USE_MOCK_UPLOAD) {
        try {
          const res = await axios.post(
            '/v1/auth/verify-otp',
            { email: email.trim(), otp: otp },
            { withCredentials: true }
          )
          scope = res.data.scope
        } catch (err) {
          setError(getErrorMessage(err, '// ERROR: Invalid OTP'))
          setLoading(false)
          return
        }
      } else {
        await new Promise(r => setTimeout(r, 1300))
      }

      loginUser({
        userId,
        email: cleanEmail,
        scope
      })

      setLoading(false)
      navigate('/dashboard')
    } catch (err) {
      setError('// ERROR: OTP verification failed')
      setLoading(false)
    }
  }

  // ── BOOT SCREEN ──
  if (phase === 0) {
    return (
      <div style={{
        minHeight:'100vh', background:'#010812',
        display:'flex', flexDirection:'column',
        alignItems:'center', justifyContent:'center', gap:32,
        fontFamily:"'Space Mono',monospace",
      }}>
        <div style={{ textAlign:'center' }}>
          <div style={{
            width:80, height:80, margin:'0 auto 24px',
            border:'2px solid rgba(245,158,11,0.4)',
            borderRadius:'50%', display:'flex',
            alignItems:'center', justifyContent:'center',
            position:'relative',
          }}>
            <div style={{
              position:'absolute', inset:-2,
              border:'2px solid transparent',
              borderTopColor:'#f59e0b',
              borderRadius:'50%',
              animation:'spin 1s linear infinite',
            }}></div>
            <svg viewBox="0 0 32 32" fill="none" width="36" height="36">
              <circle cx="16" cy="16" r="6" fill="#f59e0b"/>
              <circle cx="16" cy="16" r="12" stroke="rgba(245,158,11,0.4)" strokeWidth="1"/>
              <line x1="16" y1="4"  x2="16" y2="0"  stroke="#f59e0b" strokeWidth="2"/>
              <line x1="16" y1="32" x2="16" y2="28" stroke="#f59e0b" strokeWidth="2"/>
              <line x1="4"  y1="16" x2="0"  y2="16" stroke="#f59e0b" strokeWidth="2"/>
              <line x1="32" y1="16" x2="28" y2="16" stroke="#f59e0b" strokeWidth="2"/>
            </svg>
          </div>

          <div style={{ fontSize:28, fontFamily:"'Syne',sans-serif", fontWeight:800, color:'#f1f5f9', letterSpacing:'0.12em', marginBottom:6 }}>
            STATIQ
          </div>
          <div style={{ fontSize:10, color:'rgba(100,116,139,1)', letterSpacing:'0.25em' }}>
            INTELLIGENCE &amp; RESEARCH INTERFACE SYSTEM
          </div>
        </div>

        {/* Boot log */}
        <div style={{
          width:380, background:'rgba(255,255,255,0.02)',
          border:'1px solid rgba(255,255,255,0.06)',
          padding:'16px 20px',
        }}>
          {[
            { text:'SYSTEM INITIALISING...', done:true,  delay:0    },
            { text:'LOADING SECURITY MODULES', done:true,  delay:300  },
            { text:'CONNECTING TO MoSPI VAULT', done:true,  delay:700  },
            { text:'ENCRYPTION LAYER ACTIVE', done:true,  delay:1100 },
            { text:'READY FOR AUTHENTICATION', done:false, delay:1700 },
          ].map((line, i) => (
            <BootLine key={i} text={line.text} done={line.done} delay={line.delay} />
          ))}
        </div>
        <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
      </div>
    )
  }

  // ── MAIN LOGIN ──
  return (
    <div style={{ minHeight:'100vh', display:'flex', overflow:'hidden', position:'relative', background:'#010812' }}>

      {/* Animated canvas background */}
      <HeroCanvas />

      {/* Left — hero text */}
      <div style={{
        flex:1, display:'flex', flexDirection:'column',
        justifyContent:'space-between', padding:52,
        position:'relative', zIndex:2,
      }}>
        <div style={{ display:'flex', alignItems:'center', gap:12 }} className="a-iris">
          <div style={{
            width:44, height:44, background:'#f59e0b',
            display:'flex', alignItems:'center', justifyContent:'center',
          }} className="a-pulse-a">
            <svg viewBox="0 0 20 20" fill="#010812" width="22" height="22">
              <circle cx="10" cy="10" r="4"/>
              <circle cx="10" cy="10" r="8" fill="none" stroke="#010812" strokeWidth="1.5"/>
              <line x1="10" y1="2"  x2="10" y2="0"  stroke="#010812" strokeWidth="2"/>
              <line x1="10" y1="20" x2="10" y2="18" stroke="#010812" strokeWidth="2"/>
              <line x1="2"  y1="10" x2="0"  y2="10" stroke="#010812" strokeWidth="2"/>
              <line x1="20" y1="10" x2="18" y2="10" stroke="#010812" strokeWidth="2"/>
            </svg>
          </div>
          <div>
            <div style={{ fontFamily:"'Syne',sans-serif", fontWeight:800, fontSize:20, color:'#f1f5f9', letterSpacing:'0.12em' }} className="a-flicker">
              STATIQ
            </div>
            <div style={{ fontFamily:"'Space Mono',monospace", fontSize:9, color:'rgba(148,163,184,0.8)', letterSpacing:'0.2em', textTransform:'uppercase' }}>
              Intelligence &amp; Research Interface System
            </div>
          </div>
        </div>

        <div>
          <div style={{ fontFamily:"'Space Mono',monospace", fontSize:10, color:'rgba(245,158,11,0.8)', letterSpacing:'0.15em', textTransform:'uppercase', marginBottom:16 }} className="a-slide d2">
            // MISSION
          </div>
          <h1 style={{
            fontFamily:"'Syne',sans-serif", fontWeight:800,
            fontSize:48, color:'#f1f5f9', lineHeight:1.05,
            marginBottom:20, letterSpacing:'0.02em',
          }} className="a-slide d3">
            Survey Data<br />
            <span style={{ color:'#f59e0b' }}>Intelligence</span><br />
            Platform
          </h1>

          {/* Typewriter */}
          <div style={{
            fontFamily:"'Space Mono',monospace", fontSize:13,
            minHeight:22, marginBottom:40,
          }} className="a-slide d4">
            <Typewriter texts={TYPEWRITER_TEXTS} speed={55} />
          </div>

          {/* Feature grid */}
          <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:10, maxWidth:480 }}>
            {[
              ['NL-QUERY',   'Natural language to SQL'],
              ['DYN-SCOPE',  'Active dataset constraint'],
              ['TRANSPRNCY', 'Formula + traceability'],
              ['PRIV-SAFE',  'DPDP Act 2023 compliant'],
            ].map(([code, desc], i) => (
              <div key={code} className={`a-slide d${i+5}`} style={{
                display:'flex', alignItems:'center', gap:10,
                background:'rgba(255,255,255,0.03)',
                border:'1px solid rgba(255,255,255,0.06)',
                padding:'10px 14px',
              }}>
                <span style={{
                  fontFamily:"'Space Mono',monospace", fontSize:9,
                  color:'#f59e0b', letterSpacing:'0.1em',
                  background:'rgba(245,158,11,0.1)',
                  border:'1px solid rgba(245,158,11,0.3)',
                  padding:'2px 6px', whiteSpace:'nowrap',
                }}>
                  {code}
                </span>
                <span style={{ fontFamily:"'Space Mono',monospace", fontSize:11, color:'rgba(203,213,225,1)', lineHeight:1.4 }}>
                  {desc}
                </span>
              </div>
            ))}
          </div>
        </div>

        <div>
          <div style={{ borderTop:'1px solid rgba(255,255,255,0.07)', paddingTop:16 }}>
            <div style={{ fontFamily:"'Space Mono',monospace", fontSize:9, color:'rgba(100,116,139,0.8)', letterSpacing:'0.08em' }}>
              GOV-IN // StatIQ // STATATHON-2025 // TEAM-NEXUS
            </div>
            <div style={{ fontFamily:"'Space Mono',monospace", fontSize:9, color:'rgba(100,116,139,0.5)', marginTop:4, letterSpacing:'0.08em' }}>
              CLASSIFICATION: OFFICIAL USE ONLY
            </div>
          </div>
        </div>
      </div>

      {/* Right — login form */}
      <div style={{
        width:460, display:'flex', alignItems:'center',
        justifyContent:'center', padding:48,
        background:'rgba(1,8,18,0.7)',
        backdropFilter:'blur(20px)',
        borderLeft:'1px solid rgba(255,255,255,0.06)',
        position:'relative', zIndex:2,
      }}>
        <div style={{ width:'100%' }} className="a-iris d3">

          <div style={{ marginBottom:32 }}>
            <div style={{ fontFamily:"'Space Mono',monospace", fontSize:9, color:'rgba(245,158,11,0.9)', letterSpacing:'0.15em', textTransform:'uppercase', marginBottom:10 }}>
              {isSignup ? "REGISTER NEW ACCOUNT" : "AUTHENTICATION REQUIRED"}
            </div>
            <h2 style={{ fontFamily:"'Syne',sans-serif", fontWeight:700, fontSize:24, color:'#f1f5f9' }}>
              {isSignup ? "Create Account" : "Secure Sign In"}
            </h2>
            <div style={{ fontFamily:"'Space Mono',monospace", fontSize:11, color:'rgba(148,163,184,0.9)', marginTop:6 }}>
              StatIQ - Real-time Analytics
            </div>
          </div>

          {/* Form card */}
          <div style={{
            background:'rgba(15,31,53,0.95)',
            border:'1px solid rgba(245,158,11,0.3)',
            padding:28, position:'relative',
          }}>
            {/* corner brackets */}
            {[
              { top:-1,    left:-1,  borderWidth:'1px 0 0 1px' },
              { bottom:-1, right:-1, borderWidth:'0 1px 1px 0' },
            ].map((b, i) => (
              <div key={i} style={{
                position:'absolute', width:12, height:12,
                borderColor:'#22d3ee', borderStyle:'solid',
                opacity:0.6, ...b,
              }}/>
            ))}

            {otpMode ? (
              <form onSubmit={handleOtpVerify}>
                <div style={{ marginBottom:24 }}>
                  <label style={{ display:'block', fontFamily:"'Space Mono',monospace", fontSize:10, color:'rgba(148,163,184,1)', letterSpacing:'0.15em', textTransform:'uppercase', marginBottom:8 }}>
                    OTP Verification
                  </label>
                  <input
                    type="text" value={otp}
                    onChange={e => setOtp(e.target.value)}
                    placeholder="Enter 6-digit OTP"
                    style={{
                      width:'100%', padding:'10px 14px',
                      background:'rgba(0,0,0,0.4)',
                      border:'1px solid rgba(255,255,255,0.12)',
                      color:'#f1f5f9', fontFamily:"'Space Mono',monospace",
                      fontSize:12, outline:'none', borderRadius:2,
                      transition:'border-color 0.15s',
                    }}
                    onFocus={e => e.target.style.borderColor = 'rgba(245,158,11,0.6)'}
                    onBlur={e  => e.target.style.borderColor = 'rgba(255,255,255,0.12)'}
                  />
                </div>
                
                {error && (
                  <div style={{
                    fontFamily:"'Space Mono',monospace", fontSize:11,
                    color:'#ef4444', background:'rgba(239,68,68,0.08)',
                    border:'1px solid rgba(239,68,68,0.25)',
                    padding:'8px 12px', marginBottom:16,
                    wordBreak:'break-word',
                  }}>
                    {error}
                  </div>
                )}
                
                <button
                  type="submit" disabled={loading}
                  style={{
                    width:'100%', padding:'12px', background:'rgba(245,158,11,0.9)',
                    color:'#010812', border:'none', fontFamily:"'Space Mono',monospace",
                    fontSize:12, fontWeight:700, letterSpacing:'0.1em',
                    cursor:loading ? 'wait' : 'pointer',
                    transition:'background 0.2s', borderRadius:2,
                  }}
                  onMouseOver={e => !loading && (e.target.style.background = '#f59e0b')}
                  onMouseOut={e  => !loading && (e.target.style.background = 'rgba(245,158,11,0.9)')}
                >
                  <div style={{ display:'flex', alignItems:'center', justifyContent:'center', gap:8 }}>
                    {loading ? (
                      <>
                        <div style={{ width:12, height:12, border:'2px solid rgba(1,8,18,0.2)', borderTopColor:'#010812', borderRadius:'50%', animation:'spin 1s linear infinite' }}></div>
                        VERIFYING...
                      </>
                    ) : (
                      <>
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="16" height="16">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M11 16l-4-4m0 0l4-4m-4 4h14m-5 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h7a3 3 0 013 3v1"/>
                        </svg>
                        <span className="cursor">VERIFY OTP</span>
                      </>
                    )}
                  </div>
                </button>
              </form>
            ) : (
            <form onSubmit={handleLogin}>
              <div style={{ marginBottom:16 }}>
                <label style={{ display:'block', fontFamily:"'Space Mono',monospace", fontSize:10, color:'rgba(148,163,184,1)', letterSpacing:'0.15em', textTransform:'uppercase', marginBottom:8 }}>
                  Official Email
                </label>
                <input
                  type="email" value={email}
                  onChange={e => setEmail(e.target.value)}
                  placeholder="analyst@mospi.gov.in"
                  style={{
                    width:'100%', padding:'10px 14px',
                    background:'rgba(0,0,0,0.4)',
                    border:'1px solid rgba(255,255,255,0.12)',
                    color:'#f1f5f9', fontFamily:"'Space Mono',monospace",
                    fontSize:12, outline:'none', borderRadius:2,
                    transition:'border-color 0.15s',
                  }}
                  onFocus={e => e.target.style.borderColor = 'rgba(245,158,11,0.6)'}
                  onBlur={e  => e.target.style.borderColor = 'rgba(255,255,255,0.12)'}
                />
              </div>

              <div style={{ marginBottom:isSignup ? 16 : 24 }}>
                <label style={{ display:'block', fontFamily:"'Space Mono',monospace", fontSize:10, color:'rgba(148,163,184,1)', letterSpacing:'0.15em', textTransform:'uppercase', marginBottom:8 }}>
                  Passphrase
                </label>
                <input
                  type="password" value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  style={{
                    width:'100%', padding:'10px 14px',
                    background:'rgba(0,0,0,0.4)',
                    border:'1px solid rgba(255,255,255,0.12)',
                    color:'#f1f5f9', fontFamily:"'Space Mono',monospace",
                    fontSize:12, outline:'none', borderRadius:2,
                    transition:'border-color 0.15s',
                  }}
                  onFocus={e => e.target.style.borderColor = 'rgba(245,158,11,0.6)'}
                  onBlur={e  => e.target.style.borderColor = 'rgba(255,255,255,0.12)'}
                />
              </div>

              {isSignup && (
                <div style={{ marginBottom: role === 'admin' ? 16 : 24 }}>
                  <label style={{ display:'block', fontFamily:"'Space Mono',monospace", fontSize:10, color:'rgba(148,163,184,1)', letterSpacing:'0.15em', textTransform:'uppercase', marginBottom:8 }}>
                    User Role
                  </label>
                  <select
                    value={role}
                    onChange={e => setRole(e.target.value)}
                    style={{
                      width:'100%', padding:'10px 14px',
                      background:'rgba(0,0,0,0.4)',
                      border:'1px solid rgba(255,255,255,0.12)',
                      color:'#f1f5f9', fontFamily:"'Space Mono',monospace",
                      fontSize:12, outline:'none', borderRadius:2,
                      transition:'border-color 0.15s',
                      cursor:'pointer',
                    }}
                    onFocus={e => e.target.style.borderColor = 'rgba(245,158,11,0.6)'}
                    onBlur={e  => e.target.style.borderColor = 'rgba(255,255,255,0.12)'}
                  >
                    <option value="public" style={{ background: '#0f1f35' }}>Student / Researcher</option>
                    <option value="admin" style={{ background: '#0f1f35' }}>Administrator</option>
                  </select>
                </div>
              )}

              {isSignup && role === 'admin' && (
                <div style={{ marginBottom: 24 }}>
                  <label style={{ display:'block', fontFamily:"'Space Mono',monospace", fontSize:10, color:'rgba(148,163,184,1)', letterSpacing:'0.15em', textTransform:'uppercase', marginBottom:8 }}>
                    Admin Invite Passcode
                  </label>
                  <input
                    type="password" value={adminPasscode}
                    onChange={e => setAdminPasscode(e.target.value)}
                    placeholder="MoSPIAdmin2026"
                    style={{
                      width:'100%', padding:'10px 14px',
                      background:'rgba(0,0,0,0.4)',
                      border:'1px solid rgba(255,255,255,0.12)',
                      color:'#f1f5f9', fontFamily:"'Space Mono',monospace",
                      fontSize:12, outline:'none', borderRadius:2,
                      transition:'border-color 0.15s',
                    }}
                    onFocus={e => e.target.style.borderColor = 'rgba(245,158,11,0.6)'}
                    onBlur={e  => e.target.style.borderColor = 'rgba(255,255,255,0.12)'}
                  />
                </div>
              )}

              {isSignup && role === 'public' && (
                <>
                  <div style={{ marginBottom: 16 }}>
                    <label style={{ display:'block', fontFamily:"'Space Mono',monospace", fontSize:10, color:'rgba(148,163,184,1)', letterSpacing:'0.15em', textTransform:'uppercase', marginBottom:8 }}>
                      Full Name
                    </label>
                    <input
                      type="text" value={name}
                      onChange={e => setFullName(e.target.value)}
                      placeholder="Jane Doe"
                      style={{
                        width:'100%', padding:'10px 14px',
                        background:'rgba(0,0,0,0.4)',
                        border:'1px solid rgba(255,255,255,0.12)',
                        color:'#f1f5f9', fontFamily:"'Space Mono',monospace",
                        fontSize:12, outline:'none', borderRadius:2,
                        transition:'border-color 0.15s',
                      }}
                      onFocus={e => e.target.style.borderColor = 'rgba(245,158,11,0.6)'}
                      onBlur={e  => e.target.style.borderColor = 'rgba(255,255,255,0.12)'}
                    />
                  </div>
                  <div style={{ marginBottom: 16 }}>
                    <label style={{ display:'block', fontFamily:"'Space Mono',monospace", fontSize:10, color:'rgba(148,163,184,1)', letterSpacing:'0.15em', textTransform:'uppercase', marginBottom:8 }}>
                      Institution / Organization
                    </label>
                    <input
                      type="text" value={institution}
                      onChange={e => setInstitution(e.target.value)}
                      placeholder="University or Company Name"
                      style={{
                        width:'100%', padding:'10px 14px',
                        background:'rgba(0,0,0,0.4)',
                        border:'1px solid rgba(255,255,255,0.12)',
                        color:'#f1f5f9', fontFamily:"'Space Mono',monospace",
                        fontSize:12, outline:'none', borderRadius:2,
                        transition:'border-color 0.15s',
                      }}
                      onFocus={e => e.target.style.borderColor = 'rgba(245,158,11,0.6)'}
                      onBlur={e  => e.target.style.borderColor = 'rgba(255,255,255,0.12)'}
                    />
                  </div>
                  <div style={{ marginBottom: 24 }}>
                    <label style={{ display:'block', fontFamily:"'Space Mono',monospace", fontSize:10, color:'rgba(148,163,184,1)', letterSpacing:'0.15em', textTransform:'uppercase', marginBottom:8 }}>
                      Purpose of Registration
                    </label>
                    <input
                      type="text" value={purpose}
                      onChange={e => setPurpose(e.target.value)}
                      placeholder="E.g., Research on education metrics"
                      style={{
                        width:'100%', padding:'10px 14px',
                        background:'rgba(0,0,0,0.4)',
                        border:'1px solid rgba(255,255,255,0.12)',
                        color:'#f1f5f9', fontFamily:"'Space Mono',monospace",
                        fontSize:12, outline:'none', borderRadius:2,
                        transition:'border-color 0.15s',
                      }}
                      onFocus={e => e.target.style.borderColor = 'rgba(245,158,11,0.6)'}
                      onBlur={e  => e.target.style.borderColor = 'rgba(255,255,255,0.12)'}
                    />
                  </div>
                </>
              )}

              {error && (
                <div style={{
                  fontFamily:"'Space Mono',monospace", fontSize:11,
                  color:'#ef4444', background:'rgba(239,68,68,0.08)',
                  border:'1px solid rgba(239,68,68,0.25)',
                  padding:'8px 12px', marginBottom:16,
                  wordBreak:'break-word',
                }}>
                  {error}
                </div>
              )}

              {success && (
                <div style={{
                  fontFamily:"'Space Mono',monospace", fontSize:11,
                  color:'#10b981', background:'rgba(16,185,129,0.08)',
                  border:'1px solid rgba(16,185,129,0.25)',
                  padding:'8px 12px', marginBottom:16,
                  wordBreak:'break-word',
                }}>
                  {success}
                </div>
              )}

              <button
                type="submit" disabled={loading}
                style={{
                  width:'100%', padding:'12px',
                  background: loading ? 'rgba(245,158,11,0.5)' : '#f59e0b',
                  border:'none', cursor: loading ? 'not-allowed' : 'pointer',
                  fontFamily:"'Space Mono',monospace", fontWeight:700,
                  fontSize:12, letterSpacing:'0.12em', textTransform:'uppercase',
                  color:'#010812', transition:'all 0.15s',
                  display:'flex', alignItems:'center', justifyContent:'center', gap:8,
                }}
                onMouseEnter={e => { if(!loading) e.target.style.boxShadow='0 0 20px rgba(245,158,11,0.5)' }}
                onMouseLeave={e => e.target.style.boxShadow='none'}
              >
                {loading ? (
                  <>
                    <div style={{ width:12, height:12, border:'2px solid rgba(0,0,0,0.3)', borderTopColor:'#010812', borderRadius:'50%', animation:'spin 0.7s linear infinite' }}></div>
                    {isSignup ? "REGISTERING..." : "AUTHENTICATING..."}
                  </>
                ) : (
                  <span className="cursor">{isSignup ? "CREATE ACCOUNT" : "ENTER PLATFORM"}</span>
                )}
              </button>

              <div style={{ marginTop:20, textAlign:'center' }}>
                <button
                  type="button"
                  onClick={() => {
                    setIsSignup(!isSignup); 
                    setError(''); 
                    setSuccess('');
                    setOtpMode(false);
                  }}
                  style={{
                    background:'none', border:'none',
                    fontFamily:"'Space Mono',monospace", fontSize:11,
                    color:'rgba(148,163,184,1)', cursor:'pointer',
                    textDecoration:'underline', textUnderlineOffset:4,
                    transition:'color 0.2s'
                  }}
                  onMouseOver={e => e.target.style.color = '#f1f5f9'}
                  onMouseOut={e  => e.target.style.color = 'rgba(148,163,184,1)'}
                >
                  {isSignup ? "◄ Back to Secure Sign In" : "Don't have an account? Create one ►"}
                </button>
              </div>
            </form>
            )}
          </div>

          <div style={{ marginTop:20, textAlign:'center', fontFamily:"'Space Mono',monospace", fontSize:9, color:'rgba(100,116,139,0.7)', letterSpacing:'0.08em' }}>
            CLEARANCE LEVEL 3 // AUTHORISED ACCESS ONLY
          </div>
        </div>
      </div>

      <style>{`@keyframes spin{to{transform:rotate(360deg)}} @keyframes blink{0%,100%{opacity:1}50%{opacity:0}}`}</style>
    </div>
  )
}

function BootLine({ text, done, delay }) {
  const [show, setShow] = useState(false)
  useEffect(() => {
    const t = setTimeout(() => setShow(true), delay)
    return () => clearTimeout(t)
  }, [delay])
  if (!show) return null
  return (
    <div style={{
      display:'flex', alignItems:'center', gap:10,
      fontFamily:"'Space Mono',monospace", fontSize:11,
      color: done ? 'rgba(100,116,139,0.9)' : 'rgba(245,158,11,0.9)',
      padding:'3px 0',
      animation:'iris-in 0.3s ease both',
    }}>
      <span style={{ color: done ? 'rgba(16,185,129,0.9)' : 'rgba(245,158,11,0.9)' }}>
        {done ? '✓' : '►'}
      </span>
      {text}
      {!done && <span style={{ animation:'blink 1s step-end infinite' }}>█</span>}
    </div>
  )
}
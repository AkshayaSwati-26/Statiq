import { useState, useEffect } from 'react'
import { useSession } from '../../hooks/useSession'
import axios from 'axios'
import { USE_MOCK_UPLOAD } from '../../utils/mockData'
import { getErrorMessage } from '../../utils/errors'

export default function PremiumUpgradeModal({ isOpen, onClose }) {
  const user = useSession(state => state.user)
  const loginUser = useSession(state => state.loginUser)
  
  const [step, setStep] = useState(0) // 0 = comparison, 1 = upgrading (logs), 2 = success, 3 = checkout
  const [logs, setLogs] = useState([])
  const [error, setError] = useState('')

  // Payment mock states
  const [paymentMethod, setPaymentMethod] = useState('card')
  const [cardNo, setCardNo] = useState('')
  const [expiry, setExpiry] = useState('')
  const [cvv, setCvv] = useState('')
  const [cardName, setCardName] = useState('')
  const [selectedBank, setSelectedBank] = useState('')
  const [isProcessingPayment, setIsProcessingPayment] = useState(false)
  const [paymentError, setPaymentError] = useState('')

  useEffect(() => {
    if (!isOpen) {
      setStep(0)
      setLogs([])
      setError('')
      setPaymentMethod('card')
      setCardNo('')
      setExpiry('')
      setCvv('')
      setCardName('')
      setSelectedBank('')
      setIsProcessingPayment(false)
      setPaymentError('')
    }
  }, [isOpen])

  if (!isOpen) return null

  const handlePaymentSubmit = async () => {
    setPaymentError('')
    setIsProcessingPayment(true)

    // Basic Validation simulation
    if (paymentMethod === 'card') {
      if (!cardName.trim() || !cardNo.trim() || !expiry.trim() || !cvv.trim()) {
        setPaymentError('// ERROR: All credit card details are required.')
        setIsProcessingPayment(false)
        return
      }
      if (cardNo.replace(/\s/g, '').length < 16) {
        setPaymentError('// ERROR: Invalid card number.')
        setIsProcessingPayment(false)
        return
      }
      if (expiry.length < 5) {
        setPaymentError('// ERROR: Invalid expiry format (MM/YY).')
        setIsProcessingPayment(false)
        return
      }
      if (cvv.length < 3) {
        setPaymentError('// ERROR: CVV must be 3 digits.')
        setIsProcessingPayment(false)
        return
      }
    }

    // Process payment simulation
    await new Promise(r => setTimeout(r, 1500))
    setIsProcessingPayment(false)
    runUpgrade()
  }

  const runUpgrade = async () => {
    setStep(1)
    setError('')
    
    const steps = [
      '// DECRYPTING TRANSACTION SECURE BLOCK...',
      '// CONNECTING TO MoSPI SECURE VAULT...',
      '// GENERATING RESEARCHER CERTIFICATE...',
      '// UPDATING DATABASE PRIVILEGES (PUBLIC -> RESEARCH)...',
      '// ROTATING JWT ACCESS CREDENTIALS...',
    ]

    for (let i = 0; i < steps.length; i++) {
      setLogs(prev => [...prev, steps[i]])
      await new Promise(r => setTimeout(r, 600))
    }

    try {
      let scope = 'research'

      if (!USE_MOCK_UPLOAD) {
        try {
          const res = await axios.post(
            '/v1/auth/upgrade',
            {},
            { withCredentials: true }
          )
          scope = res.data.scope
        } catch (err) {
          setError(getErrorMessage(err, '// ERROR: Privilege escalation rejected by server'))
          setStep(0)
          setLogs([])
          return
        }
      } else {
        // Mock upgrade
        await new Promise(r => setTimeout(r, 800))
      }

      // Update session
      loginUser({
        ...user,
        scope: scope,
        isSimulatedPremium: USE_MOCK_UPLOAD
      })

      setStep(2)
    } catch (err) {
      setError('// ERROR: Upgrade connection failed')
      setStep(0)
      setLogs([])
    }
  }

  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      background: 'rgba(1, 8, 18, 0.85)',
      backdropFilter: 'blur(12px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 9999,
      fontFamily: "'Space Mono', monospace",
    }}>
      <div style={{
        width: 580,
        background: 'rgba(15, 31, 53, 0.98)',
        border: '1px solid rgba(34, 211, 238, 0.4)',
        boxShadow: '0 0 40px rgba(34, 211, 238, 0.15)',
        padding: 32,
        position: 'relative',
        animation: 'modalFadeIn 0.3s ease both',
      }}>
        {/* corner brackets */}
        {[
          { top: -1, left: -1, borderWidth: '1px 0 0 1px' },
          { top: -1, right: -1, borderWidth: '1px 1px 0 0' },
          { bottom: -1, left: -1, borderWidth: '0 0 1px 1px' },
          { bottom: -1, right: -1, borderWidth: '0 1px 1px 0' },
        ].map((b, i) => (
          <div key={i} style={{
            position: 'absolute',
            width: 16,
            height: 16,
            borderColor: '#22d3ee',
            borderStyle: 'solid',
            opacity: 0.8,
            ...b,
          }} />
        ))}

        {step === 0 && (
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
              <div>
                <div style={{ fontSize: 9, color: 'rgba(34, 211, 238, 0.9)', letterSpacing: '0.15em', textTransform: 'uppercase', marginBottom: 6 }}>
                  // ESCALATION MODULE
                </div>
                <h3 style={{ fontFamily: "'Syne', sans-serif", fontWeight: 800, fontSize: 20, color: '#f1f5f9', margin: 0 }}>
                  Elevate Clearance Level
                </h3>
              </div>
              <button 
                onClick={onClose} 
                style={{ background: 'none', border: 'none', color: 'rgba(255,255,255,0.4)', cursor: 'pointer', fontSize: 16 }}
              >
                ✕
              </button>
            </div>

            {error && (
              <div style={{
                fontSize: 11,
                color: '#ef4444',
                background: 'rgba(239, 68, 68, 0.08)',
                border: '1px solid rgba(239, 68, 68, 0.25)',
                padding: '8px 12px',
                marginBottom: 20,
              }}>
                {error}
              </div>
            )}

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 28 }}>
              {/* Free tier */}
              <div style={{
                background: 'rgba(0, 0, 0, 0.2)',
                border: '1px solid rgba(255, 255, 255, 0.06)',
                padding: 20,
                borderRadius: 2,
              }}>
                <div style={{ fontSize: 10, color: 'rgba(148, 163, 184, 0.8)', letterSpacing: '0.1em', marginBottom: 4 }}>
                  CURRENT LEVEL
                </div>
                <div style={{ fontSize: 16, fontWeight: 700, color: '#f1f5f9', marginBottom: 16 }}>
                  Free User
                </div>
                <ul style={{ paddingLeft: 16, margin: 0, fontSize: 11, color: 'rgba(148, 163, 184, 0.9)', lineHeight: '1.8em' }}>
                  <li>Standard dashboard views</li>
                  <li>Aggregate survey tables</li>
                  <li>Basic filters only</li>
                  <li>Strict API rate limits</li>
                </ul>
              </div>

              {/* Premium tier */}
              <div style={{
                background: 'rgba(34, 211, 238, 0.03)',
                border: '1px solid rgba(34, 211, 238, 0.25)',
                padding: 20,
                borderRadius: 2,
                position: 'relative',
              }}>
                <div style={{
                  position: 'absolute',
                  top: 10,
                  right: 10,
                  fontSize: 8,
                  background: 'rgba(34, 211, 238, 0.15)',
                  color: '#22d3ee',
                  padding: '2px 6px',
                  borderRadius: 2,
                  fontWeight: 700,
                }}>
                  RECOMMENDED
                </div>
                <div style={{ fontSize: 10, color: '#22d3ee', letterSpacing: '0.1em', marginBottom: 4 }}>
                  TARGET LEVEL
                </div>
                <div style={{ fontSize: 16, fontWeight: 700, color: '#22d3ee', marginBottom: 16 }}>
                  Premium Analyst
                </div>
                <ul style={{ paddingLeft: 16, margin: 0, fontSize: 11, color: '#f1f5f9', lineHeight: '1.8em' }}>
                  <li style={{ color: '#22d3ee', fontWeight: 700 }}>✦ NL Query (Text-to-SQL)</li>
                  <li>✦ Custom SQL workspace</li>
                  <li>✦ Developer API key access</li>
                  <li>✦ Detailed data dictionary</li>
                  <li>✦ Increased API rate limits</li>
                </ul>
              </div>
            </div>

            <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end' }}>
              <button
                onClick={onClose}
                style={{
                  padding: '10px 20px',
                  background: 'transparent',
                  border: '1px solid rgba(255,255,255,0.15)',
                  color: 'rgba(255,255,255,0.7)',
                  cursor: 'pointer',
                  fontSize: 11,
                  fontWeight: 700,
                  textTransform: 'uppercase',
                }}
              >
                Cancel
              </button>
              <button
                onClick={() => setStep(3)}
                style={{
                  padding: '10px 24px',
                  background: 'linear-gradient(90deg, #22d3ee, #0891b2)',
                  border: 'none',
                  color: '#010812',
                  cursor: 'pointer',
                  fontSize: 11,
                  fontWeight: 700,
                  textTransform: 'uppercase',
                  boxShadow: '0 0 15px rgba(34, 211, 238, 0.3)',
                  transition: 'all 0.15s',
                }}
                onMouseEnter={e => e.target.style.boxShadow = '0 0 25px rgba(34, 211, 238, 0.5)'}
                onMouseLeave={e => e.target.style.boxShadow = '0 0 15px rgba(34, 211, 238, 0.3)'}
              >
                Activate Premium clearance
              </button>
            </div>
          </div>
        )}

        {step === 3 && (
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
              <div>
                <div style={{ fontSize: 9, color: 'rgba(34, 211, 238, 0.9)', letterSpacing: '0.15em', textTransform: 'uppercase', marginBottom: 6 }}>
                  // SECURE GATEWAY PROTOCOL
                </div>
                <h3 style={{ fontFamily: "'Syne', sans-serif", fontWeight: 800, fontSize: 20, color: '#f1f5f9', margin: 0 }}>
                  Escrow Checkout
                </h3>
              </div>
              <button 
                onClick={onClose} 
                style={{ background: 'none', border: 'none', color: 'rgba(255,255,255,0.4)', cursor: 'pointer', fontSize: 16 }}
              >
                ✕
              </button>
            </div>

            {/* Price banner */}
            <div style={{
              background: 'rgba(34, 211, 238, 0.05)',
              border: '1px solid rgba(34, 211, 238, 0.2)',
              padding: '16px 20px',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: 20,
            }}>
              <div>
                <div style={{ fontSize: 11, color: '#f1f5f9', fontWeight: 700 }}>Premium Analyst Clearance</div>
                <div style={{ fontSize: 9, color: 'rgba(34, 211, 238, 0.7)', marginTop: 4 }}>Annual Cryptographic License</div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: 18, fontWeight: 700, color: '#22d3ee' }}>₹2,499 / yr</div>
                <div style={{ fontSize: 8, color: 'rgba(255,255,255,0.4)', marginTop: 2 }}>inclusive of all taxes</div>
              </div>
            </div>

            {/* Payment tab buttons */}
            <div style={{ display: 'flex', gap: 2, background: 'rgba(0,0,0,0.2)', padding: 3, marginBottom: 20 }}>
              {[
                { id: 'card', label: '💳 Credit/Debit' },
                { id: 'upi', label: '📱 UPI QR' }
              ].map(method => (
                <button
                  key={method.id}
                  onClick={() => {
                    setPaymentMethod(method.id)
                    setPaymentError('')
                  }}
                  style={{
                    flex: 1,
                    padding: '8px 12px',
                    fontSize: 10,
                    fontFamily: "'Space Mono', monospace",
                    background: paymentMethod === method.id ? 'rgba(34, 211, 238, 0.1)' : 'transparent',
                    border: '1px solid ' + (paymentMethod === method.id ? 'rgba(34, 211, 238, 0.3)' : 'transparent'),
                    color: paymentMethod === method.id ? '#22d3ee' : 'rgba(148, 163, 184, 0.8)',
                    cursor: 'pointer',
                    fontWeight: 700,
                  }}
                >
                  {method.label}
                </button>
              ))}
            </div>

            {paymentError && (
              <div style={{
                fontSize: 11,
                color: '#ef4444',
                background: 'rgba(239, 68, 68, 0.08)',
                border: '1px solid rgba(239, 68, 68, 0.25)',
                padding: '8px 12px',
                marginBottom: 16,
              }}>
                {paymentError}
              </div>
            )}

            {/* Tab contents */}
            <div style={{ minHeight: 180, marginBottom: 24 }}>
              {paymentMethod === 'card' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                  <div>
                    <label style={{ fontSize: 9, color: 'rgba(255,255,255,0.5)', display: 'block', marginBottom: 6 }}>CARDHOLDER NAME</label>
                    <input 
                      value={cardName}
                      onChange={e => setCardName(e.target.value)}
                      placeholder="Anant R." 
                      className="iris-input" 
                      style={{ width: '100%', fontSize: 12, padding: '8px 12px' }}
                    />
                  </div>
                  <div>
                    <label style={{ fontSize: 9, color: 'rgba(255,255,255,0.5)', display: 'block', marginBottom: 6 }}>CARD NUMBER</label>
                    <input 
                      value={cardNo}
                      onChange={e => setCardNo(e.target.value.replace(/\D/g, '').replace(/(\d{4})/g, '$1 ').trim().substring(0, 19))}
                      placeholder="4111 2222 3333 4444" 
                      className="iris-input" 
                      style={{ width: '100%', fontSize: 12, padding: '8px 12px' }}
                    />
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                    <div>
                      <label style={{ fontSize: 9, color: 'rgba(255,255,255,0.5)', display: 'block', marginBottom: 6 }}>EXPIRY DATE</label>
                      <input 
                        value={expiry}
                        onChange={e => setExpiry(e.target.value.replace(/\D/g, '').replace(/(\d{2})/, '$1/').substring(0, 5))}
                        placeholder="MM/YY" 
                        className="iris-input" 
                        style={{ width: '100%', fontSize: 12, padding: '8px 12px' }}
                      />
                    </div>
                    <div>
                      <label style={{ fontSize: 9, color: 'rgba(255,255,255,0.5)', display: 'block', marginBottom: 6 }}>CVV</label>
                      <input 
                        type="password"
                        value={cvv}
                        onChange={e => setCvv(e.target.value.replace(/\D/g, '').substring(0, 3))}
                        placeholder="***" 
                        className="iris-input" 
                        style={{ width: '100%', fontSize: 12, padding: '8px 12px' }}
                      />
                    </div>
                  </div>
                </div>
              )}

              {paymentMethod === 'upi' && (
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '10px 0', background: '#f4f6fb', borderRadius: 8 }}>
                  <div style={{
                    background: '#fff',
                    padding: 16,
                    borderRadius: 16,
                    boxShadow: '0 4px 20px rgba(0,0,0,0.05)',
                    marginBottom: 16,
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                  }}>
                    <div style={{ position: 'relative', width: 140, height: 140, marginBottom: 12 }}>
                      <img 
                        src="https://api.qrserver.com/v1/create-qr-code/?size=140x140&data=upi://pay?pa=sanjanasenthilkumar15@oksbi" 
                        alt="UPI QR Code" 
                        style={{ width: '100%', height: '100%' }}
                      />
                      <div style={{ 
                        position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)',
                        background: '#fff', padding: 3, borderRadius: '50%', width: 32, height: 32,
                        display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
                      }}>
                        <svg viewBox="0 0 24 24" width="18" height="18">
                          <path fill="#4285F4" d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8z"/>
                          <path fill="#34A853" d="M11 16.5l-4.5-4.5 1.41-1.41L11 13.67l6.09-6.09L18.5 9l-7.5 7.5z"/>
                        </svg>
                      </div>
                    </div>
                    <div style={{ fontSize: 13, color: '#475569', letterSpacing: '0.02em' }}>
                      UPI ID: sanjanasenthilkumar15@oksbi
                    </div>
                  </div>
                  
                  <div style={{ fontSize: 14, color: '#475569', textAlign: 'center', marginBottom: 8 }}>
                    Scan to pay with any UPI app
                  </div>
                </div>
              )}
            </div>

            {/* Checkout actions */}
            <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end' }}>
              <button
                onClick={() => setStep(0)}
                style={{
                  padding: '10px 20px',
                  background: 'transparent',
                  border: '1px solid rgba(255,255,255,0.15)',
                  color: 'rgba(255,255,255,0.7)',
                  cursor: 'pointer',
                  fontSize: 11,
                  fontWeight: 700,
                  textTransform: 'uppercase',
                }}
              >
                Back
              </button>
              <button
                onClick={handlePaymentSubmit}
                disabled={isProcessingPayment}
                style={{
                  padding: '10px 24px',
                  background: 'linear-gradient(90deg, #22d3ee, #0891b2)',
                  border: 'none',
                  color: '#010812',
                  cursor: 'pointer',
                  fontSize: 11,
                  fontWeight: 700,
                  textTransform: 'uppercase',
                  boxShadow: '0 0 15px rgba(34, 211, 238, 0.3)',
                  transition: 'all 0.15s',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                }}
              >
                {isProcessingPayment ? (
                  <>
                    <div style={{ width: 12, height: 12, border: '2px solid rgba(1, 8, 18, 0.2)', borderTopColor: '#010812', borderRadius: '50%', animation: 'spin 0.6s linear infinite' }}></div>
                    Authorizing...
                  </>
                ) : (
                  'Confirm Payment & Proceed'
                )}
              </button>
            </div>
          </div>
        )}

        {step === 1 && (
          <div style={{ padding: '20px 0' }}>
            <div style={{ fontSize: 10, color: '#22d3ee', letterSpacing: '0.15em', marginBottom: 24, textTransform: 'uppercase' }}>
              // DECRYPTING PRIVILEGE LAYERS...
            </div>
            
            <div style={{
              background: 'rgba(0,0,0,0.4)',
              border: '1px solid rgba(255,255,255,0.06)',
              padding: 20,
              minHeight: 140,
              marginBottom: 28,
            }}>
              {logs.map((log, index) => (
                <div 
                  key={index} 
                  style={{ 
                    fontSize: 11, 
                    color: index === logs.length - 1 ? '#22d3ee' : 'rgba(148, 163, 184, 0.8)',
                    marginBottom: 8,
                    animation: 'iris-in 0.2s ease both',
                  }}
                >
                  {log}
                </div>
              ))}
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 12 }}>
                <div style={{ width: 10, height: 10, border: '2px solid rgba(34, 211, 238, 0.2)', borderTopColor: '#22d3ee', borderRadius: '50%', animation: 'spin 0.6s linear infinite' }}></div>
                <span style={{ fontSize: 10, color: '#22d3ee' }}>PROCESSING ESCALATION SCHEME...</span>
              </div>
            </div>
          </div>
        )}

        {step === 2 && (
          <div style={{ textAlign: 'center', padding: '30px 0' }}>
            <div style={{
              width: 50,
              height: 50,
              borderRadius: '50%',
              background: 'rgba(16, 185, 129, 0.1)',
              border: '2px solid #10b981',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 20px',
              animation: 'pulseGreen 1.5s infinite',
            }}>
              <svg viewBox="0 0 20 20" fill="none" stroke="#10b981" strokeWidth="2.5" width="24" height="24">
                <path d="M5 10l3 3 7-7" />
              </svg>
            </div>
            
            <h3 style={{ fontFamily: "'Syne', sans-serif", fontWeight: 800, fontSize: 22, color: '#10b981', marginBottom: 10, marginTop: 0 }}>
              Clearance Upgraded
            </h3>
            
            <p style={{ fontSize: 12, color: 'rgba(148, 163, 184, 0.9)', marginBottom: 28, lineHeight: '1.6em', maxWidth: 420, margin: '0 auto 28px' }}>
              Your account clearance level has successfully been escalated to <span style={{ color: '#22d3ee', fontWeight: 700 }}>Premium Analyst</span>. All restricted features (Query Workspace, custom SQL tools) are now fully unlocked.
            </p>

            <button
              onClick={onClose}
              style={{
                padding: '10px 32px',
                background: '#10b981',
                border: 'none',
                color: '#010812',
                cursor: 'pointer',
                fontSize: 11,
                fontWeight: 700,
                textTransform: 'uppercase',
                boxShadow: '0 0 15px rgba(16, 185, 129, 0.3)',
                transition: 'all 0.15s',
              }}
              onMouseEnter={e => e.target.style.boxShadow = '0 0 25px rgba(16, 185, 129, 0.5)'}
              onMouseLeave={e => e.target.style.boxShadow = '0 0 15px rgba(16, 185, 129, 0.3)'}
            >
              Acknowledge &amp; Return
            </button>
          </div>
        )}

      </div>

      <style>{`
        @keyframes modalFadeIn {
          from { opacity: 0; transform: scale(0.97); }
          to { opacity: 1; transform: scale(1); }
        }
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
        @keyframes pulseGreen {
          0% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.4); }
          70% { box-shadow: 0 0 0 10px rgba(16, 185, 129, 0); }
          100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
        }
      `}</style>
    </div>
  )
}

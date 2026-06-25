import { useState, useRef } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useSession } from '../hooks/useSession'
import { useLang } from '../hooks/useLang'
import { uploadDataset } from '../services/api'

const ACCEPTED = ['.csv','.xlsx','.xls','.sav','.dta','.txt','.zip']

export default function DataIngestion() {
  const navigate = useNavigate()
  const { setDataset, clearDataset, datasetReady, filename, rowCount,
          columns, uploadTime, datasetId, fileType, previewRows } = useSession()
  const user = useSession(state => state.user)
  const { t } = useLang()

  const inputRef = useRef()
  const [dragging,  setDragging]  = useState(false)
  const [uploading, setUploading] = useState(false)
  const [progress,  setProgress]  = useState(0)
  const [error,     setError]     = useState('')
  const [done,      setDone]      = useState(datasetReady)

  // ZIP multi-file state
  const [zipMode,   setZipMode]   = useState(false)
  const [zipFiles,  setZipFiles]  = useState([]) // { name, status, rows, message }

  if (!user || user.scope !== 'admin') {
    return (
      <div style={{ maxWidth:600, padding:40, background:'var(--surface)', border:'1px solid var(--rim-2)', marginTop:40 }}>
        <div style={{ display:'flex', alignItems:'center', gap:12, marginBottom:20 }}>
          <div style={{ width:40, height:40, background:'rgba(220,38,38,0.1)', display:'flex', alignItems:'center', justifyContent:'center', border:'1px solid var(--red)' }}>
            <svg viewBox="0 0 16 16" fill="none" stroke="var(--red)" strokeWidth="1.5" style={{ width:20, height:20 }}>
              <rect x="3" y="11" width="10" height="8" rx="1"/>
              <path d="M5 11V7a3 3 0 016 0v4"/>
            </svg>
          </div>
          <div>
            <h2 style={{ fontFamily:"'Syne',sans-serif", fontWeight:800, fontSize:22, color:'var(--red)', margin:0 }}>
              ACCESS RESTRICTED
            </h2>
            <div className="coord" style={{ color:'var(--text-3)', marginTop:4 }}>
              CLEARANCE LEVEL INSUFFICIENT
            </div>
          </div>
        </div>
        <p style={{ fontFamily:"'Space Mono',monospace", fontSize:13, color:'var(--text-2)', lineHeight:1.8, marginBottom:24 }}>
          MoSPI Data Ingestion controls are restricted to the Administrator role only. Your current clearance tier ({user?.scope?.toUpperCase() || 'PUBLIC'}) does not permit manual dataset modifications.
        </p>
        <button onClick={() => navigate('/dashboard')} className="iris-btn iris-btn-cyan">
          RETURN TO DASHBOARD
        </button>
      </div>
    )
  }

  const processFile = async (file) => {
    if (!file) return
    const name = file.name.toLowerCase()
    const ok   = ACCEPTED.some(ext => name.endsWith(ext))
    if (!ok) { setError(`File type not supported. Use: ${ACCEPTED.join(', ')}`); return }

    // ZIP file handling — use SSE endpoint
    if (name.endsWith('.zip')) {
      setZipMode(true)
      setZipFiles([])
      setUploading(true)
      setError('')
      setProgress(0)

      const formData = new FormData()
      formData.append('file', file)

      try {
        const response = await fetch('/v1/upload/zip', {
          method: 'POST',
          body: formData,
          credentials: 'include',
        })

        if (!response.ok) {
          const errData = await response.json().catch(() => ({ detail: 'Upload failed' }))
          throw new Error(errData.detail || `HTTP ${response.status}`)
        }

        const reader = response.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ''

        while (true) {
          const { done: readerDone, value } = await reader.read()
          if (readerDone) break
          buffer += decoder.decode(value, { stream: true })

          const lines = buffer.split('\n\n')
          buffer = lines.pop() || ''

          for (const line of lines) {
            const dataLine = line.replace(/^data: /, '')
            if (!dataLine) continue
            try {
              const event = JSON.parse(dataLine)
              if (event.status === 'complete') {
                setProgress(100)
              } else if (event.file || event.filename) {
                const fName = event.file || event.filename
                setZipFiles(prev => {
                  const existing = prev.findIndex(f => f.name === fName)
                  const entry = {
                    name: fName,
                    status: event.status,
                    rows: event.row_count || event.rows || 0,
                    message: event.message || event.error || '',
                    duplicate: event.duplicate || false,
                  }
                  if (existing >= 0) {
                    const updated = [...prev]
                    updated[existing] = entry
                    return updated
                  }
                  return [...prev, entry]
                })
                if (event.total) {
                  setProgress(Math.round((event.index / event.total) * 100))
                }
              }
            } catch (e) { /* skip malformed SSE */ }
          }
        }

        await new Promise(r => setTimeout(r, 500))
        setDone(true)
      } catch (err) {
        setError(err.message || 'ZIP upload failed')
      } finally {
        setUploading(false)
      }
      return
    }

    // Single file handling (existing behavior)
    setZipMode(false)
    setError(''); setUploading(true); setProgress(0)

    const iv = setInterval(() => setProgress(p => p >= 88 ? (clearInterval(iv), 88) : p + 10), 110)
    try {
      const result = await uploadDataset(file)
      clearInterval(iv); setProgress(100)
      await new Promise(r => setTimeout(r, 300))
      setDataset(result); setDone(true)
    } catch (err) {
      clearInterval(iv)
      const msg = err.message || 'Upload failed. Please check the file and try again.'
      setError(msg)
    } finally { setUploading(false) }
  }

  return (
    <div style={{ maxWidth:900, display:'flex', flexDirection:'column', gap:20 }}>

      {/* Header */}
      <div className="a-iris">
        <div className="coord" style={{ color:'var(--amber)', marginBottom:6 }}>// {t('nav_ingest').toUpperCase()}</div>
        <h1 style={{ fontFamily:"'Syne',sans-serif", fontWeight:800, fontSize:26, color:'var(--text-0)' }}>
          {t('ingest_title')}
        </h1>
        <div className="label-xs" style={{ marginTop:4, color:'var(--text-3)' }}>
          {t('ingest_subtitle')}
        </div>
      </div>

      {/* Upload zone */}
      {(!done || zipMode) && (
        <div className="panel a-iris d1" style={{ overflow:'hidden' }}>
          <div style={{ padding:'14px 20px', borderBottom:'1px solid var(--rim-2)', display:'flex', alignItems:'center', gap:10 }}>
            <div style={{ width:3, height:16, background: done ? 'var(--green)' : 'var(--amber)' }}></div>
            <span className="label-sm" style={{ fontSize:12 }}>
              {done ? 'BATCH INGESTION COMPLETE' : 'UPLOAD SURVEY DATASET'}
            </span>
          </div>

          <div style={{ padding:24 }}>
            {/* Drop zone */}
            {!done && (
            <div
              onClick={() => !uploading && inputRef.current.click()}
              onDrop={e => { e.preventDefault(); setDragging(false); processFile(e.dataTransfer.files[0]) }}
              onDragOver={e => { e.preventDefault(); setDragging(true) }}
              onDragLeave={() => setDragging(false)}
              style={{
                border:`2px dashed ${dragging ? 'var(--amber)' : 'var(--rim-2)'}`,
                background: dragging ? 'var(--amber-glow)' : 'var(--ink-2)',
                padding:'52px 24px', textAlign:'center',
                cursor: uploading ? 'not-allowed' : 'pointer',
                transition:'all 0.2s', marginBottom:20,
              }}
            >
              <div style={{ marginBottom:16, opacity: dragging ? 1 : 0.4 }}>
                <svg viewBox="0 0 48 48" fill="none" stroke="var(--amber)" strokeWidth="1.2" style={{ width:48, height:48, margin:'0 auto' }}>
                  <path d="M24 4L4 14v20l20 10 20-10V14L24 4z"/>
                  <path d="M24 4v30M4 14l20 10 20-10"/>
                </svg>
              </div>

              {uploading ? (
                <div className="label-xs" style={{ color:'var(--amber)', fontSize:12 }}>
                  Uploading and parsing dataset...
                </div>
              ) : (
                <>
                  <div style={{ fontFamily:"'Syne',sans-serif", fontWeight:700, fontSize:18, color:'var(--text-0)', marginBottom:8 }}>
                    {t('ingest_drop')}
                  </div>
                  <div className="coord" style={{ marginBottom:20, color:'var(--text-3)', fontSize:10 }}>
                    or click to browse your files
                  </div>
                  <div style={{ display:'flex', flexWrap:'wrap', justifyContent:'center', gap:8, marginBottom:20 }}>
                    {['CSV','XLSX','XLS','SPSS (.sav)','Stata (.dta)','FWF (.txt)','ZIP'].map(fmt => (
                    <span key={fmt} className="tag tag-dim" style={{ fontSize:10 }}>{fmt}</span>
                  ))}
                  </div>
                  <button className="iris-btn iris-btn-cyan" style={{ fontSize:12 }}>
                    {t('ingest_browse').toUpperCase()}
                  </button>
                </>
              )}
            </div>
            )}

            {/* Progress */}
            {uploading && (
              <div style={{ marginBottom:16 }}>
                <div style={{ display:'flex', justifyContent:'space-between', marginBottom:8 }}>
                  <span className="coord" style={{ color:'var(--text-2)', fontSize:10 }}>
                    Detecting schema · Extracting metadata · Building index
                  </span>
                  <span className="coord" style={{ color:'var(--amber)', fontSize:10 }}>{progress}%</span>
                </div>
                <div className="iris-bar-track">
                  <div className="iris-bar-fill" style={{ width:`${progress}%`, transition:'width 0.15s' }}></div>
                </div>
              </div>
            )}

            {/* Error */}
            {error && (
              <div style={{
                background:'rgba(220,38,38,0.06)', border:'1px solid rgba(220,38,38,0.25)',
                borderLeft:'3px solid var(--red)', padding:'12px 16px',
              }}>
                <span style={{ fontFamily:"'Space Mono',monospace", fontSize:12, color:'var(--red)' }}>
                  // ERROR: {error}
                </span>
              </div>
            )}

            <input ref={inputRef} type="file" accept={ACCEPTED.join(',')} style={{ display:'none' }}
              onChange={e => processFile(e.target.files[0])} />

            {/* ZIP multi-file status */}
            {zipMode && zipFiles.length > 0 && (
              <div style={{ marginTop: 16, border: '1px solid var(--rim-2)', background: 'var(--ink-2)' }}>
                <div style={{ padding: '10px 14px', borderBottom: '1px solid var(--rim)', display: 'flex', alignItems: 'center', gap: 8 }}>
                  <div style={{ width: 2, height: 12, background: 'var(--amber)' }}></div>
                  <span className="label-xs" style={{ fontSize: 10 }}>EXTRACTED FILES</span>
                  <span className="tag tag-dim" style={{ marginLeft: 'auto', fontSize: 9 }}>{zipFiles.length} FILES</span>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column' }}>
                  {zipFiles.map((zf, i) => {
                    const statusIcon = zf.status === 'success' ? '✅'
                      : zf.status === 'duplicate' ? '⚠️'
                      : zf.status === 'error' ? '❌'
                      : zf.status === 'processing' ? '🔄' : '⏳'
                    const statusColor = zf.status === 'success' ? 'var(--green)'
                      : zf.status === 'duplicate' ? 'var(--amber)'
                      : zf.status === 'error' ? 'var(--red)'
                      : 'var(--text-3)'
                    return (
                      <div key={zf.name + i} style={{
                        display: 'flex', alignItems: 'center', gap: 12,
                        padding: '10px 14px',
                        borderBottom: i < zipFiles.length - 1 ? '1px solid var(--rim)' : 'none',
                        background: zf.status === 'error' ? 'rgba(220,38,38,0.03)'
                          : zf.status === 'duplicate' ? 'rgba(245,158,11,0.03)'
                          : zf.status === 'success' ? 'rgba(16,185,129,0.03)'
                          : 'transparent',
                      }}>
                        <span style={{ fontSize: 14, width: 20, textAlign: 'center' }}>{statusIcon}</span>
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ fontFamily: "'Space Mono',monospace", fontSize: 12, color: 'var(--text-0)', marginBottom: 2 }}>
                            {zf.name}
                          </div>
                          {zf.message && (
                            <div className="coord" style={{ fontSize: 9, color: statusColor }}>
                              {zf.message}
                            </div>
                          )}
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
                          {zf.rows > 0 && (
                            <span className="tag tag-dim" style={{ fontSize: 9 }}>{zf.rows.toLocaleString()} ROWS</span>
                          )}
                          <span style={{
                            padding: '2px 8px', fontSize: 9, fontWeight: 700,
                            fontFamily: "'Space Mono',monospace", letterSpacing: '0.06em',
                            border: `1px solid ${statusColor}`,
                            color: statusColor, textTransform: 'uppercase',
                          }}>
                            {zf.status === 'success' ? 'STORED' : zf.status?.toUpperCase() || 'PENDING'}
                          </span>
                        </div>
                      </div>
                    )
                  })}
                </div>
                {/* Summary bar */}
                {!uploading && zipFiles.length > 0 && (
                  <div style={{
                    padding: '10px 14px', borderTop: '1px solid var(--rim)',
                    display: 'flex', gap: 16, background: 'var(--ink-3)',
                  }}>
                    <span className="coord" style={{ color: 'var(--green)', fontSize: 10 }}>
                      ✅ {zipFiles.filter(f => f.status === 'success').length} stored
                    </span>
                    <span className="coord" style={{ color: 'var(--amber)', fontSize: 10 }}>
                      ⚠️ {zipFiles.filter(f => f.status === 'duplicate').length} duplicates skipped
                    </span>
                    <span className="coord" style={{ color: 'var(--red)', fontSize: 10 }}>
                      ❌ {zipFiles.filter(f => f.status === 'error').length} errors
                    </span>
                  </div>
                )}
              </div>
            )}

            {/* Post-ZIP actions */}
            {done && zipMode && (
              <div style={{ marginTop: 24, display: 'flex', gap: 12 }}>
                <button onClick={() => { setDone(false); setZipMode(false); setZipFiles([]); setError(''); }} className="iris-btn iris-btn-ghost">
                  UPLOAD ANOTHER BATCH
                </button>
                <button onClick={() => navigate('/admin/datasets')} className="iris-btn iris-btn-cyan">
                  VIEW IN DATASETS REGISTRY
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Success card (Single file only) */}
      {done && !zipMode && (
        <div className="panel a-iris d1" style={{ overflow:'hidden' }}>

          {/* Green header */}
          <div style={{
            padding:'16px 20px',
            background:'var(--green-glow)',
            borderBottom:'1px solid rgba(5,150,105,0.3)',
            display:'flex', alignItems:'center', justifyContent:'space-between',
          }}>
            <div style={{ display:'flex', alignItems:'center', gap:12 }}>
              <div style={{ width:36, height:36, background:'var(--green)', display:'flex', alignItems:'center', justifyContent:'center' }}>
                <svg viewBox="0 0 16 16" fill="none" stroke="white" strokeWidth="2" style={{ width:16, height:16 }}>
                  <polyline points="2 8 6 12 14 4"/>
                </svg>
              </div>
              <div>
                <div style={{ fontFamily:"'Syne',sans-serif", fontWeight:700, fontSize:16, color:'var(--green)' }}>
                  {t('ingest_success')}
                </div>
                <div className="coord" style={{ color:'var(--text-3)', marginTop:2 }}>
                  {t('ingest_ready')}
                </div>
              </div>
            </div>
            <span className="tag tag-green">{t('active_dataset').toUpperCase()}</span>
          </div>

          <div style={{ padding:24 }}>

            {/* Info grid */}
            <div style={{ display:'grid', gridTemplateColumns:'repeat(3,1fr)', gap:10, marginBottom:24 }}>
              {[
                { label:'Dataset Name',  value: filename  },
                { label:'Table (DB)',    value: datasetId },
                { label:'File Type',     value: fileType  },
                { label:'Total Records', value: rowCount?.toLocaleString() },
                { label:'Columns',       value: columns?.length },
                { label:'Uploaded At',   value: uploadTime },
              ].map(item => (
                <div key={item.label} style={{ background:'var(--ink-2)', border:'1px solid var(--rim-2)', padding:'14px 16px' }}>
                  <div className="coord" style={{ color:'var(--text-4)', marginBottom:6, fontSize:9 }}>
                    {item.label.toUpperCase()}
                  </div>
                  <div className="data-val" style={{ fontSize:14, color:'var(--text-0)', wordBreak:'break-all' }}>
                    {item.value}
                  </div>
                </div>
              ))}
            </div>

            {/* Detected columns */}
            <div style={{ marginBottom:24 }}>
              <div className="label-xs" style={{ color:'var(--text-3)', marginBottom:12, fontSize:10 }}>
                // {t('ingest_columns').toUpperCase()} ({columns?.length})
              </div>
              <div style={{ display:'flex', flexWrap:'wrap', gap:8 }}>
                {columns?.map(col => (
                  <span key={col} className="tag tag-cyan" style={{ fontSize:10, fontFamily:"'DM Mono',monospace" }}>{col}</span>
                ))}
              </div>
            </div>

            {/* Preview table */}
            <div style={{ marginBottom:24 }}>
              <div className="label-xs" style={{ color:'var(--text-3)', marginBottom:12, fontSize:10 }}>
                // {t('ingest_preview').toUpperCase()}
              </div>
              <div style={{ overflowX:'auto', border:'1px solid var(--rim-2)' }}>
                <table style={{ width:'100%', borderCollapse:'collapse', fontSize:13 }}>
                  <thead>
                    <tr style={{ background:'var(--ink-3)' }}>
                      {previewRows?.[0] && Object.keys(previewRows[0]).map(col => (
                        <th key={col} style={{
                          textAlign:'left', padding:'10px 14px',
                          fontFamily:"'Space Mono',monospace", fontSize:10,
                          color:'var(--text-2)', fontWeight:700,
                          letterSpacing:'0.08em', textTransform:'uppercase',
                          borderBottom:'1px solid var(--rim-2)',
                          whiteSpace:'nowrap',
                        }}>
                          {col}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {previewRows?.map((row, i) => (
                      <tr key={i} style={{ background: i%2===0 ? 'var(--surface)' : 'var(--ink-2)' }}>
                        {Object.values(row).map((val, j) => (
                          <td key={j} style={{
                            padding:'10px 14px',
                            fontFamily:"'DM Mono',monospace", fontSize:13,
                            color:'var(--text-1)',
                            borderBottom:'1px solid var(--rim)',
                            whiteSpace:'nowrap',
                          }}>
                            {val}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Actions */}
            <div style={{ display:'flex', gap:12, flexWrap:'wrap' }}>
              <button
                onClick={() => navigate(`/datasets/${encodeURIComponent(datasetId)}/explore`)}
                className="iris-btn iris-btn-cyan"
                style={{ flex:1, fontSize:13, padding:'13px' }}
              >
                🔍 EXPLORE DATASET METADATA
              </button>
              <button
                onClick={() => navigate('/query')}
                className="iris-btn iris-btn-primary"
                style={{ flex:1, fontSize:13, padding:'13px' }}
              >
                {t('ingest_start').toUpperCase()} →
              </button>
              <button
                onClick={() => { clearDataset(); setDone(false); setProgress(0) }}
                className="iris-btn iris-btn-ghost"
                style={{ padding:'13px 20px', fontSize:12 }}
              >
                {t('ingest_replace').toUpperCase()}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Governance notice */}
      <div style={{
        background:'var(--amber-glow)',
        border:'1px solid rgba(217,119,6,0.3)',
        borderLeft:'4px solid var(--amber)',
        padding:'16px 20px',
        display:'flex', alignItems:'flex-start', gap:14,
      }}>
        <svg viewBox="0 0 20 20" fill="none" stroke="var(--amber)" strokeWidth="1.5" style={{ width:22, height:22, flexShrink:0, marginTop:2 }}>
          <rect x="3" y="11" width="14" height="8" rx="1"/>
          <path d="M7 11V7a3 3 0 016 0v4"/>
        </svg>
        <div>
          <div className="label-xs" style={{ color:'var(--amber)', marginBottom:6, fontSize:10 }}>
            // DATA GOVERNANCE NOTICE
          </div>
          <p style={{ fontFamily:"'Space Mono',monospace", fontSize:13, color:'var(--text-1)', lineHeight:1.8, margin:0 }}>
            All queries will run exclusively on the active dataset.
            No external data sources are accessed.
            Results are aggregated only — no individual records are exposed.
            Compliant with DPDP Act 2023.
          </p>
        </div>
      </div>
    </div>
  )
}
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useSession } from '../hooks/useSession'
import { useLang } from '../hooks/useLang'
import { runNLQuery, runBuilderQuery } from '../services/api'
import { generateExplanation, getFormula } from '../utils/explainResult'
import EmptyState          from '../components/common/EmptyState'
import LoadingSpinner      from '../components/common/LoadingSpinner'
import ErrorCard           from '../components/common/ErrorCard'
import QueryBuilder        from '../components/query/QueryBuilder'
import ResultSummaryCard   from '../components/results/ResultSummaryCard'
import AIExplanationPanel  from '../components/results/AIExplanationPanel'
import TransparencyPanel   from '../components/results/TransparencyPanel'
import DataGovernancePanel from '../components/results/DataGovernancePanel'
import ResultsTable        from '../components/charts/ResultsTable'
import BarChartView        from '../components/charts/BarChartView'
import LineChartView       from '../components/charts/LineChartView'
import PieChartView        from '../components/charts/PieChartView'

const EXAMPLES_EN = [
  'Show unemployment rate among rural women in Tamil Nadu',
  'Compare employment trends across all states in 2024',
  'Labour force participation by sector and gender',
  'What is the LFPR for urban males aged 15–29?',
  'Show consumption expenditure trends 2020 to 2024',
]

const EXAMPLES_HI = [
  'तमिलनाडु में ग्रामीण महिलाओं की बेरोजगारी दर दिखाएं',
  '2024 में सभी राज्यों में रोजगार के रुझान की तुलना करें',
  'क्षेत्र और लिंग के अनुसार श्रम बल भागीदारी दिखाएं',
  '15-29 वर्ष के शहरी पुरुषों के लिए LFPR क्या है?',
  'राज्यों में बेरोजगारी दर की तुलना करें',
]

export default function QueryWorkspace() {
  const navigate  = useNavigate()
  const { t, lang } = useLang()
  const {
    sessionId, datasetReady, filename,
    setResult, setQuerying, setQueryError,
    lastResult, isQuerying, queryError, lastQuery,
  } = useSession()
  const user = useSession(state => state.user)

  const [activeTab,  setActiveTab]  = useState('nl')
  const [nlQuery,    setNlQuery]    = useState('')
  const [chartType,  setChartType]  = useState('bar')

  if (!datasetReady) {
    return (
      <EmptyState
        title={t('query_no_data')}
        message={t('query_upload_msg')}
        buttonLabel={t('query_go_upload')}
        buttonPath="/ingest"
      />
    )
  }

  const handleNLQuery = async () => {
    if (!nlQuery.trim()) return
    setQuerying(true)
    try {
      const result = await runNLQuery(sessionId, nlQuery)
      // Enrich with frontend-generated explanation if backend doesn't provide
      const explanation = result.explanation || generateExplanation(result.data, result.indicator_name, lang)
      const formula     = result.formula     || getFormula(result.indicator_name, lang)
      setResult({ ...result, explanation, formula }, nlQuery)
      setChartType('bar')
    } catch {
      setQueryError(lang === 'hi' ? 'प्रश्न विफल हुआ। कृपया पुनः प्रयास करें।' : 'Query failed. Please rephrase and try again.')
    }
  }

  const handleBuilderQuery = async (zones) => {
    setQuerying(true)
    const label = Object.values(zones).flat().map(f => f.label).join(' · ')
    try {
      const result = await runBuilderQuery(sessionId, zones)
      const explanation = result.explanation || generateExplanation(result.data, result.indicator_name, lang)
      const formula     = result.formula     || getFormula(result.indicator_name, lang)
      setResult({ ...result, explanation, formula }, label)
      setChartType('bar')
    } catch {
      setQueryError(lang === 'hi' ? 'प्रश्न विफल हुआ।' : 'Query failed. Please adjust your filters.')
    }
  }

  const examples = lang === 'hi' ? EXAMPLES_HI : EXAMPLES_EN
  const isFree = user?.scope === 'public'

  return (
    <div style={{ maxWidth:1000, display:'flex', flexDirection:'column', gap:20 }}>

      {/* Header */}
      <div className="a-iris" style={{ display:'flex', alignItems:'center', justifyContent:'space-between' }}>
        <div>
          <div className="coord" style={{ color:'var(--amber)', marginBottom:6 }}>
            // {t('nav_query').toUpperCase()}
          </div>
          <h1 style={{ fontFamily:"'Syne',sans-serif", fontWeight:800, fontSize:26, color:'var(--text-0)' }}>
            {t('query_title')}
          </h1>
          <div className="label-xs" style={{ marginTop:4, color:'var(--text-3)' }}>
            {t('query_scoped')}: <span style={{ color:'var(--cyan)' }}>{filename}</span>
          </div>
        </div>
        <div style={{ display:'flex', alignItems:'center', gap:8 }}>
          <span className="status-dot status-live"></span>
          <span className="label-xs" style={{ color:'var(--green)' }}>DATASET ACTIVE</span>
        </div>
      </div>

      {/* Mode tabs */}
      <div style={{ display:'flex', gap:2, background:'var(--ink-2)', padding:3, width:'fit-content' }} className="a-iris d1">
        {[
          { id:'nl',      label: lang === 'hi' ? '✦ सामान्य भाषा' : '✦ Natural Language' },
          { id:'builder', label: (lang === 'hi' ? '⊞ प्रश्न बिल्डर' : '⊞ Query Builder') + (isFree ? ' 🔒' : '') },
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => {
              if (tab.id === 'builder' && isFree) {
                alert('Visual Query Builder is a Premium Feature. Please upgrade to Premium Tier using the button in the sidebar to unlock advanced visual queries!')
                return
              }
              setActiveTab(tab.id)
            }}
            className="iris-btn"
            style={{
              padding:'8px 20px', fontSize:12,
              background: activeTab === tab.id ? 'var(--surface)' : 'transparent',
              borderColor: activeTab === tab.id ? 'var(--rim-2)' : 'transparent',
              color: activeTab === tab.id ? 'var(--amber)' : 'var(--text-3)',
              fontWeight: activeTab === tab.id ? 700 : 400,
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* NL Query panel */}
      {activeTab === 'nl' && (
        <div className="panel a-iris d1" style={{ overflow:'hidden' }}>
          <div style={{
            padding:'14px 20px',
            borderBottom:'1px solid var(--rim-2)',
            background:'var(--amber-glow)',
            display:'flex', alignItems:'center', gap:10,
          }}>
            <div style={{ width:3, height:20, background:'var(--amber)' }}></div>
            <div>
              <span className="label-sm" style={{ color:'var(--amber)', fontSize:12, display:'block' }}>
                {t('query_nl').toUpperCase()}
              </span>
              <span className="coord" style={{ color:'var(--text-3)', fontSize:9 }}>
                {lang === 'hi' ? 'हिंदी या अंग्रेजी में प्रश्न लिखें' : 'Type in English or Hindi'}
              </span>
            </div>
          </div>

          <div style={{ padding:24 }}>
            <div className="label-xs" style={{ color:'var(--text-3)', marginBottom:10, fontSize:10 }}>
              // {t('query_ask').toUpperCase()}
            </div>
            <div style={{ display:'flex', gap:10, marginBottom:20 }}>
              <input
                value={nlQuery}
                onChange={e => setNlQuery(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleNLQuery()}
                placeholder={t('query_placeholder')}
                className="iris-input"
                style={{ fontSize:15, padding:'13px 16px', flex:1 }}
              />
              <button
                onClick={handleNLQuery}
                disabled={isQuerying || !nlQuery.trim()}
                className="iris-btn iris-btn-primary"
                style={{ fontSize:13, padding:'13px 24px', whiteSpace:'nowrap' }}
              >
                {isQuerying ? t('query_running') : t('query_run')}
              </button>
            </div>

            {/* Examples */}
            <div>
              <div className="label-xs" style={{ color:'var(--text-4)', marginBottom:10, fontSize:9 }}>
                // {t('query_examples').toUpperCase()}
              </div>
              <div style={{ display:'flex', flexWrap:'wrap', gap:8 }}>
                {examples.map(ex => (
                  <button
                    key={ex}
                    onClick={() => setNlQuery(ex)}
                    style={{
                      fontFamily:"'Space Mono',monospace", fontSize:11,
                      color:'var(--text-2)', background:'var(--ink-2)',
                      border:'1px solid var(--rim-2)', padding:'6px 12px',
                      cursor:'pointer', transition:'all 0.15s',
                      borderRadius:2,
                    }}
                    onMouseEnter={e => { e.currentTarget.style.borderColor='var(--amber)'; e.currentTarget.style.color='var(--amber)' }}
                    onMouseLeave={e => { e.currentTarget.style.borderColor='var(--rim-2)';  e.currentTarget.style.color='var(--text-2)' }}
                  >
                    {ex}
                  </button>
                ))}
              </div>
            </div>

            {/* Dataset lock notice */}
            <div style={{
              marginTop:20,
              display:'flex', alignItems:'center', gap:10,
              background:'var(--amber-glow)',
              border:'1px solid rgba(217,119,6,0.25)',
              borderLeft:'3px solid var(--amber)',
              padding:'12px 16px',
            }}>
              <svg viewBox="0 0 16 16" fill="none" stroke="var(--amber)" strokeWidth="1.5" style={{ width:16, height:16, flexShrink:0 }}>
                <rect x="3" y="7" width="10" height="8" rx="1"/>
                <path d="M5 7V5a3 3 0 016 0v2"/>
              </svg>
              <p style={{ fontFamily:"'Space Mono',monospace", fontSize:12, color:'var(--amber)', margin:0 }}>
                {t('query_scoped')}: <strong>{filename}</strong>
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Builder tab */}
      {activeTab === 'builder' && (
        <div className="panel a-iris d1" style={{ overflow:'hidden' }}>
          <div style={{
            padding:'14px 20px', borderBottom:'1px solid var(--rim-2)',
            display:'flex', alignItems:'center', gap:10,
            background:'var(--ink-2)',
          }}>
            <div style={{ width:3, height:20, background:'var(--cyan)' }}></div>
            <div>
              <span className="label-sm" style={{ fontSize:12, display:'block' }}>
                {t('query_builder').toUpperCase()}
              </span>
              <span className="coord" style={{ fontSize:9, color:'var(--text-3)' }}>
                Drag fields from the panel into the canvas
              </span>
            </div>
          </div>
          <div style={{ padding:24 }}>
            <QueryBuilder onQuery={handleBuilderQuery} isQuerying={isQuerying} filename={filename} />
          </div>
        </div>
      )}

      {/* Loading */}
      {isQuerying && (
        <div className="panel a-iris">
          <LoadingSpinner />
        </div>
      )}

      {/* Error */}
      {queryError && !isQuerying && (
        <ErrorCard message={queryError} onRetry={() => setQuerying(false)} />
      )}

      {/* Results */}
      {lastResult && !isQuerying && (
        <div style={{ display:'flex', flexDirection:'column', gap:20 }} className="a-iris">

          {/* Divider */}
          <div style={{ display:'flex', alignItems:'center', gap:16 }}>
            <div style={{ flex:1, height:1, background:`linear-gradient(90deg, var(--amber), transparent)` }}></div>
            <span className="label-xs" style={{ color:'var(--amber)', letterSpacing:'0.2em' }}>
              // RESULTS
            </span>
            <div style={{ flex:1, height:1, background:`linear-gradient(270deg, var(--amber), transparent)` }}></div>
          </div>

          {/* Query echo */}
          <div style={{
            background:'var(--ink-2)', border:'1px solid var(--rim-2)',
            borderLeft:'3px solid var(--cyan)',
            padding:'12px 18px',
            display:'flex', alignItems:'center', gap:12,
          }}>
            <svg viewBox="0 0 16 16" fill="none" stroke="var(--cyan)" strokeWidth="1.5" style={{ width:16, height:16, flexShrink:0 }}>
              <circle cx="7" cy="7" r="5"/><path d="M14 14l-3-3"/>
            </svg>
            <span style={{ fontFamily:"'DM Mono',monospace", fontSize:14, color:'var(--text-1)', flex:1 }}>
              "{lastQuery}"
            </span>
            <span className="tag tag-green" style={{ fontSize:9 }}>{t('completed').toUpperCase()}</span>
          </div>

          <ResultSummaryCard result={lastResult} />

          {/* Chart panel */}
          <div className="panel" style={{ overflow:'hidden' }}>
            <div style={{
              padding:'12px 20px', borderBottom:'1px solid var(--rim-2)',
              display:'flex', alignItems:'center', justifyContent:'space-between',
            }}>
              <div>
                <div style={{ fontFamily:"'Syne',sans-serif", fontWeight:700, fontSize:16, color:'var(--text-0)' }}>
                  {lastResult.indicator_name}
                </div>
                <div className="coord" style={{ marginTop:3, color:'var(--text-3)', fontSize:9 }}>
                  {lastResult.records_analyzed?.toLocaleString()} records · {lastResult.dataset_used}
                </div>
              </div>
              <div style={{ display:'flex', gap:2, background:'var(--ink-2)', padding:3 }}>
                {[
                  { id:'bar',   icon:'▊', label:'Bar'   },
                  { id:'line',  icon:'↗', label:'Line'  },
                  { id:'pie',   icon:'◕', label:'Pie'   },
                  { id:'table', icon:'⊞', label:'Table' },
                ].map(ct => (
                  <button
                    key={ct.id}
                    onClick={() => setChartType(ct.id)}
                    className="iris-btn"
                    style={{
                      padding:'5px 12px', fontSize:10,
                      background: chartType === ct.id ? 'var(--surface)' : 'transparent',
                      borderColor: chartType === ct.id ? 'var(--rim-2)' : 'transparent',
                      color: chartType === ct.id ? 'var(--amber)' : 'var(--text-3)',
                    }}
                  >
                    {ct.icon} {ct.label}
                  </button>
                ))}
              </div>
            </div>
            <div style={{ padding:24 }}>
              {chartType === 'bar'   && <BarChartView  data={lastResult.data} />}
              {chartType === 'line'  && <LineChartView data={lastResult.data} />}
              {chartType === 'pie'   && <PieChartView  data={lastResult.data} />}
              {chartType === 'table' && <ResultsTable  data={lastResult.data} />}
            </div>
          </div>

          <AIExplanationPanel    result={lastResult} />
          <TransparencyPanel     result={lastResult} />
          <DataGovernancePanel   result={lastResult} />

          <div style={{ display:'flex', justifyContent:'flex-end', paddingBottom:8 }}>
            <button
              onClick={() => navigate('/exports')}
              className="iris-btn iris-btn-cyan"
              style={{ fontSize:12 }}
            >
              {t('result_export').toUpperCase()} →
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
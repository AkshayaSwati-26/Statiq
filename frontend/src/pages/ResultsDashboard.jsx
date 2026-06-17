import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useSession } from '../hooks/useSession'
import { useLang } from '../hooks/useLang'
import EmptyState          from '../components/common/EmptyState'
import BarChartView        from '../components/charts/BarChartView'
import LineChartView       from '../components/charts/LineChartView'
import PieChartView        from '../components/charts/PieChartView'
import ResultsTable        from '../components/charts/ResultsTable'
import AIExplanationPanel  from '../components/results/AIExplanationPanel'
import TransparencyPanel   from '../components/results/TransparencyPanel'
import DataGovernancePanel from '../components/results/DataGovernancePanel'
import ResultSummaryCard   from '../components/results/ResultSummaryCard'

export default function ResultsDashboard() {
  const navigate = useNavigate()
  const { lastResult, lastQuery, filename, datasetReady } = useSession()
  const { t } = useLang()
  const [chartType, setChartType] = useState('bar')

  if (!datasetReady || !lastResult) {
    return (
      <EmptyState
        title={t('no_results')}
        message={t('no_results_msg')}
        buttonLabel={t('go_query')}
        buttonPath="/query"
      />
    )
  }

  return (
    <div style={{ maxWidth:1000, display:'flex', flexDirection:'column', gap:20 }} className="a-iris">

      <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between' }}>
        <div>
          <div className="coord" style={{ color:'var(--amber)', marginBottom:6 }}>
            // {t('nav_results').toUpperCase()}
          </div>
          <h1 style={{ fontFamily:"'Syne',sans-serif", fontWeight:800, fontSize:26, color:'var(--text-0)' }}>
            {t('nav_results')} Dashboard
          </h1>
          <div className="label-xs" style={{ marginTop:4, color:'var(--text-3)' }}>
            {t('active_dataset')}: <span style={{ color:'var(--cyan)' }}>{filename}</span>
          </div>
        </div>
        <button onClick={() => navigate('/query')} className="iris-btn iris-btn-ghost" style={{ fontSize:11 }}>
          ← NEW QUERY
        </button>
      </div>

      {/* Last query */}
      <div style={{
        background:'var(--ink-2)', border:'1px solid var(--rim-2)',
        borderLeft:'3px solid var(--cyan)',
        padding:'13px 18px', display:'flex', alignItems:'center', gap:12,
      }}>
        <svg viewBox="0 0 16 16" fill="none" stroke="var(--cyan)" strokeWidth="1.5" style={{ width:16, height:16, flexShrink:0 }}>
          <circle cx="7" cy="7" r="5"/><path d="M14 14l-3-3"/>
        </svg>
        <span style={{ fontFamily:"'DM Mono',monospace", fontSize:15, color:'var(--text-1)', flex:1 }}>
          "{lastQuery}"
        </span>
        <span className="tag tag-green" style={{ fontSize:9 }}>
          {lastResult.confidence_score}% CONFIDENCE
        </span>
      </div>

      <ResultSummaryCard result={lastResult} />

      {/* Chart */}
      <div className="panel" style={{ overflow:'hidden' }}>
        <div style={{
          padding:'13px 20px', borderBottom:'1px solid var(--rim-2)',
          display:'flex', alignItems:'center', justifyContent:'space-between',
        }}>
          <div style={{ fontFamily:"'Syne',sans-serif", fontWeight:700, fontSize:16, color:'var(--text-0)' }}>
            {lastResult.indicator_name}
          </div>
          <div style={{ display:'flex', gap:2, background:'var(--ink-2)', padding:3 }}>
            {['bar','line','pie','table'].map(ct => (
              <button key={ct} onClick={() => setChartType(ct)} className="iris-btn" style={{
                padding:'5px 12px', fontSize:10, textTransform:'capitalize',
                background: chartType===ct ? 'var(--surface)' : 'transparent',
                borderColor: chartType===ct ? 'var(--rim-2)' : 'transparent',
                color: chartType===ct ? 'var(--amber)' : 'var(--text-3)',
              }}>
                {ct}
              </button>
            ))}
          </div>
        </div>
        <div style={{ padding:24 }}>
          {chartType==='bar'   && <BarChartView  data={lastResult.data} />}
          {chartType==='line'  && <LineChartView data={lastResult.data} />}
          {chartType==='pie'   && <PieChartView  data={lastResult.data} />}
          {chartType==='table' && <ResultsTable  data={lastResult.data} />}
        </div>
      </div>

      <AIExplanationPanel    result={lastResult} />
      <TransparencyPanel     result={lastResult} />
      <DataGovernancePanel   result={lastResult} />
    </div>
  )
}
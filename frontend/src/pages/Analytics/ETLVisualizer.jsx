import { useState, useEffect, useRef } from 'react'
import { analyticsApi } from '@/services/api'
import { PageLoader } from '@/components/shared/States'
import { 
  Database, ArrowRight, Cog, LayoutDashboard, DatabaseZap, 
  ShieldCheck, CheckCircle2, Play, AlertTriangle, Clock, RefreshCw 
} from 'lucide-react'

export default function ETLVisualizer() {
  const [data,     setData]     = useState(null)
  const [loading,  setLoading]  = useState(true)
  const [syncing,  setSyncing]  = useState(false)
  const [error,    setError]    = useState(null)
  const pollIntervalRef         = useRef(null)

  const fetchStatus = () => {
    analyticsApi.getETLStatus()
      .then(d => {
        setData(d)
        setLoading(false)
        // If it's running, set up polling if not already active
        if (d.last_run && d.last_run.status === 'Running') {
          startPolling()
        } else {
          stopPolling()
        }
      })
      .catch((err) => {
        console.error('Error fetching ETL status:', err)
        setLoading(false)
      })
  }

  const startPolling = () => {
    if (!pollIntervalRef.current) {
      pollIntervalRef.current = setInterval(() => {
        analyticsApi.getETLStatus()
          .then(d => {
            setData(d)
            if (!d.last_run || d.last_run.status !== 'Running') {
              stopPolling()
            }
          })
          .catch(() => stopPolling())
      }, 3000)
    }
  }

  const stopPolling = () => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current)
      pollIntervalRef.current = null
    }
  }

  useEffect(() => {
    fetchStatus()
    return () => stopPolling()
  }, [])

  const triggerSync = () => {
    setSyncing(true)
    setError(null)
    analyticsApi.triggerETLSync()
      .then(res => {
        setSyncing(false)
        fetchStatus() // refresh status to catch "Running" state
      })
      .catch(err => {
        setSyncing(false)
        const errMsg = err.response?.data?.message || 'Failed to start ETL pipeline.'
        setError(errMsg)
      })
  }

  if (loading) return <PageLoader />

  const lastRun = data?.last_run
  const isRunning = lastRun?.status === 'Running'

  const STAGES = [
    { 
      id: 'extract', 
      title: 'Extract Stage', 
      icon: DatabaseZap, 
      color: 'text-accent-sky', 
      border: 'border-accent-sky/20',
      bg: 'bg-accent-sky/5',
      desc: 'Pulling raw transactional database tables and Shopify export CSV files.',
      metrics: [
        `${data?.data_counts?.orders || 0} Sales Rows`, 
        `${data?.data_counts?.customers || 0} Customer Rows`
      ]
    },
    { 
      id: 'transform', 
      title: 'Transform Stage', 
      icon: Cog, 
      color: 'text-accent-violet', 
      border: 'border-accent-violet/20',
      bg: 'bg-accent-violet/5',
      desc: 'Resolving SKU drift, standardizing governorates, enforcing SCD Type 2 product timelines, and cost hierarchies.',
      metrics: [
        'SCD Type 2 Enabled', 
        'Hierarchical Costs'
      ]
    },
    { 
      id: 'load', 
      title: 'Load Stage', 
      icon: Database, 
      color: 'text-accent-amber', 
      border: 'border-accent-amber/20',
      bg: 'bg-accent-amber/5',
      desc: 'Bulk inserting clean dimensions and fact logs into the dedicated warehouse schema.',
      metrics: [
        '5 Dimensions Loaded', 
        '3 Facts Loaded'
      ]
    },
    { 
      id: 'analyze', 
      title: 'Analyze & Mining', 
      icon: LayoutDashboard, 
      color: 'text-accent-emerald', 
      border: 'border-accent-emerald/20',
      bg: 'bg-accent-emerald/5',
      desc: 'Re-evaluating RFM clusters, market basket rules, and sales demand forecasts.',
      metrics: [
        'RFM Clustering', 
        'Demand Forecasts'
      ]
    },
  ]

  return (
    <div className="space-y-8 py-4">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 pb-6 border-b border-border">
        <div className="space-y-2">
          <div className="inline-flex items-center gap-2 px-3 py-1 bg-brand-500/10 border border-brand-500/20 rounded-full text-brand-400 text-[10px] font-bold uppercase tracking-widest">
            Pipeline Control Panel
          </div>
          <h3 className="text-3xl font-extrabold text-text-primary tracking-tight">ETL Warehouse Visualizer</h3>
          <p className="text-sm text-text-muted max-w-xl">
            Orchestrate operational transaction processing (OLTP) and analytical database schema (OLAP) synchronization.
          </p>
        </div>
        
        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={fetchStatus}
            className="flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-lg bg-bg-card border border-border text-text-secondary hover:bg-bg-hover transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRunning ? 'animate-spin' : ''}`} />
            Refresh
          </button>
          <button
            onClick={triggerSync}
            disabled={isRunning || syncing}
            className="flex items-center gap-2 px-5 py-2.5 text-xs font-semibold rounded-lg bg-brand-500 text-white hover:bg-brand-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-lg shadow-brand-500/15"
          >
            {isRunning ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                Processing DW Sync...
              </>
            ) : (
              <>
                <Play className="w-4 h-4 fill-white" />
                Run ETL Pipeline
              </>
            )}
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-lg bg-accent-red/10 border border-accent-red/20 text-accent-red text-xs flex items-center gap-3">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          {error}
        </div>
      )}

      {/* Pipeline Status Banner */}
      {lastRun && (
        <div className={`p-6 rounded-xl border bg-gradient-to-r ${
          lastRun.status === 'Completed' ? 'from-accent-emerald/10 to-transparent border-accent-emerald/20' :
          lastRun.status === 'Running' ? 'from-accent-amber/10 to-transparent border-accent-amber/20 animate-pulse' :
          'from-accent-red/10 to-transparent border-accent-red/20'
        } flex flex-col md:flex-row md:items-center justify-between gap-6`}>
          <div className="flex items-start gap-4">
            <div className={`p-3 rounded-xl border ${
              lastRun.status === 'Completed' ? 'bg-accent-emerald/10 border-accent-emerald/20 text-accent-emerald' :
              lastRun.status === 'Running' ? 'bg-accent-amber/10 border-accent-amber/20 text-accent-amber' :
              'bg-accent-red/10 border-accent-red/20 text-accent-red'
            }`}>
              {lastRun.status === 'Completed' ? <CheckCircle2 className="w-6 h-6" /> :
               lastRun.status === 'Running' ? <RefreshCw className="w-6 h-6 animate-spin" /> :
               <AlertTriangle className="w-6 h-6" />}
            </div>
            <div className="space-y-1">
              <h4 className="font-bold text-text-primary text-sm flex items-center gap-2">
                Pipeline Status: <span className={
                  lastRun.status === 'Completed' ? 'text-accent-emerald' :
                  lastRun.status === 'Running' ? 'text-accent-amber' : 'text-accent-red'
                }>{lastRun.status}</span>
              </h4>
              <p className="text-xs text-text-secondary">
                {lastRun.status === 'Completed' ? `Loaded ${lastRun.rows_loaded} rows into analytical models.` :
                 lastRun.status === 'Running' ? 'Extracting source CSV files and converting dimensions in memory...' :
                 'Encountered database transaction exception during load stage.'}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-6 text-xs text-text-secondary border-t md:border-t-0 pt-4 md:pt-0 border-border">
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4 text-text-muted" />
              <div>
                <div className="text-[10px] text-text-muted font-bold uppercase">Duration</div>
                <div className="font-bold text-text-primary">{lastRun.duration_seconds || '--'}s</div>
              </div>
            </div>
            <div>
              <div className="text-[10px] text-text-muted font-bold uppercase">Last Run</div>
              <div className="font-bold text-text-primary">
                {new Date(lastRun.start_time).toLocaleString()}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Visual Flow Diagram */}
      <div className="relative flex flex-col lg:flex-row items-center justify-between gap-6 lg:gap-4 max-w-5xl mx-auto px-4 py-6">
        {/* Connecting Gradient Line */}
        <div className="absolute top-1/2 left-0 right-0 h-0.5 bg-gradient-to-r from-accent-sky via-accent-violet to-accent-emerald opacity-20 hidden lg:block -translate-y-1/2" />
        
        {STAGES.map((stage, idx) => (
          <div key={stage.id} className="relative z-10 w-full lg:w-48 xl:w-56 text-center group">
            <div className={`w-16 h-16 rounded-2xl mx-auto flex items-center justify-center bg-bg-card border ${stage.border} shadow-xl mb-4 bg-gradient-to-b from-transparent to-bg-hover/30 hover:scale-105 transition-all duration-300`}>
              <stage.icon className={`w-8 h-8 ${stage.color}`} />
            </div>
            
            <h4 className="font-bold text-text-primary mb-1 text-xs flex items-center justify-center gap-2">
              {stage.title}
              {idx < STAGES.length - 1 && <ArrowRight className="w-3.5 h-3.5 text-text-muted hidden lg:block" />}
            </h4>
            <p className="text-[10px] text-text-muted leading-relaxed mb-3 px-2">
              {stage.desc}
            </p>
            
            <div className="space-y-1">
              {stage.metrics.map(m => (
                <div key={m} className={`inline-block px-2 py-0.5 ${stage.bg} rounded-md text-[9px] font-bold ${stage.color} border ${stage.border} mx-0.5`}>
                  {m}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Diagnostic Errors Panel */}
      {lastRun?.status === 'Failed' && lastRun.errors && (
        <div className="max-w-5xl mx-auto rounded-lg border border-accent-red/20 bg-bg-card overflow-hidden">
          <div className="px-4 py-3 bg-accent-red/5 border-b border-accent-red/10 flex items-center gap-2 text-accent-red font-bold text-xs">
            <AlertTriangle className="w-4 h-4" />
            Execution Failure Diagnostics (Stack Trace)
          </div>
          <pre className="p-4 text-[10px] font-mono text-accent-red bg-bg-hover overflow-x-auto whitespace-pre leading-relaxed">
            {lastRun.errors}
          </pre>
        </div>
      )}

      {/* Architecture Features Info */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-5xl mx-auto pt-4">
        <div className="glass-card p-6 flex items-start gap-4">
          <div className="p-3 rounded-xl bg-accent-sky/10 border border-accent-sky/20">
            <ShieldCheck className="w-6 h-6 text-accent-sky" />
          </div>
          <div>
            <h4 className="font-bold text-text-primary mb-1 text-sm">PostgreSQL Dual-Schema Architecture</h4>
            <p className="text-xs text-text-secondary leading-relaxed">
              Separates transaction processing (`operational` schema) from reporting (`warehouse` schema). Analytics run exclusively on the dimensional model, guaranteeing storefront speed.
            </p>
          </div>
        </div>
        <div className="glass-card p-6 flex items-start gap-4">
          <div className="p-3 rounded-xl bg-brand-500/10 border border-brand-500/20">
            <DatabaseZap className="w-6 h-6 text-brand-400" />
          </div>
          <div>
            <h4 className="font-bold text-text-primary mb-1 text-sm">SCD Type 2 Product Dimensioning</h4>
            <p className="text-xs text-text-secondary leading-relaxed">
              Captures product price and cost alterations over time. Historical orders continue pointing to the actual values active at sale time, preventing profitability skew.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

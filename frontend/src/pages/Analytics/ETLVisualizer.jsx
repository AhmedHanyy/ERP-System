import { useState, useEffect } from 'react'
import { analyticsApi } from '@/services/api'
import { PageLoader } from '@/components/shared/States'
import { Database, ArrowRight, Cog, LayoutDashboard, DatabaseZap, ShieldCheck, CheckCircle2 } from 'lucide-react'

export default function ETLVisualizer() {
  const [data,     setData]     = useState(null)
  const [loading,  setLoading]  = useState(true)

  useEffect(() => {
    analyticsApi.getETLStatus()
      .then(d => { setData(d); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  if (loading) return <PageLoader />

  const STAGES = [
    { 
      id: 'extract', 
      title: 'Extract', 
      icon: DatabaseZap, 
      color: 'text-accent-sky', 
      desc: 'Raw transactional data from PostgreSQL/SQLite.',
      metrics: [`${data.data_counts.orders} Orders`, `${data.data_counts.customers} Customers`]
    },
    { 
      id: 'transform', 
      title: 'Transform', 
      icon: Cog, 
      color: 'text-accent-violet', 
      desc: 'Cleaning, normalization & date enrichment via pandas.',
      metrics: ['Missing Values Fixed', 'Feature Engineering']
    },
    { 
      id: 'load', 
      title: 'Load', 
      icon: Database, 
      color: 'text-accent-amber', 
      desc: 'Analytical schema (OLAP) prepared for mining.',
      metrics: ['Daily Aggregates', 'Product Performance']
    },
    { 
      id: 'analyze', 
      title: 'Analyze', 
      icon: LayoutDashboard, 
      color: 'text-accent-emerald', 
      desc: 'Forecasting, RFM Clustering & Basket Rule Mining.',
      metrics: ['Predictive Insights', 'Customer Segments']
    },
  ]

  return (
    <div className="space-y-8 py-4">
      <div className="text-center max-w-2xl mx-auto space-y-3">
        <div className="inline-flex items-center gap-2 px-3 py-1 bg-brand-500/10 border border-brand-500/20 rounded-full text-brand-400 text-[10px] font-bold uppercase tracking-widest">
           System Intelligence
        </div>
        <h3 className="text-2xl font-bold text-text-primary">Operational-to-Analytical Pipeline</h3>
        <p className="text-sm text-text-muted">
           SmartERP separates operational transaction processing (OLTP) from analytical processing (OLAP) 
           to ensure system performance and valid decision support.
        </p>
      </div>

      {/* Visual Flow */}
      <div className="relative flex flex-col md:flex-row items-center justify-between gap-4 md:gap-0 max-w-5xl mx-auto px-4">
        {/* Connection Line */}
        <div className="absolute top-1/2 left-0 right-0 h-0.5 bg-gradient-to-r from-accent-sky via-accent-violet to-accent-emerald opacity-20 hidden md:block" />
        
        {STAGES.map((stage, idx) => (
          <div key={stage.id} className="relative z-10 w-full md:w-48 lg:w-56 text-center group">
            <div className={`w-16 h-16 rounded-2xl mx-auto flex items-center justify-center bg-bg-card border border-border group-hover:border-${stage.color.split('-')[1]} transition-all duration-500 shadow-xl group-hover:shadow-${stage.color.split('-')[1]}/20 mb-6 bg-gradient-to-b from-transparent to-bg-hover/30`}>
              <stage.icon className={`w-8 h-8 ${stage.color}`} />
              <div className="absolute -top-1 -right-1">
                 <CheckCircle2 className="w-5 h-5 text-accent-emerald fill-bg-primary" />
              </div>
            </div>
            
            <h4 className="font-bold text-text-primary mb-2 flex items-center justify-center gap-2">
               {stage.title}
               {idx < STAGES.length - 1 && <ArrowRight className="w-3 h-3 text-text-muted hidden md:block" />}
            </h4>
            <p className="text-[11px] text-text-muted leading-relaxed mb-4 px-2">
               {stage.desc}
            </p>
            
            <div className="space-y-1">
               {stage.metrics.map(m => (
                 <div key={m} className="inline-block px-2 py-0.5 bg-bg-hover rounded-md text-[9px] font-bold text-text-secondary border border-border mx-0.5">
                   {m}
                 </div>
               ))}
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-5xl mx-auto pt-8">
         <div className="glass-card p-6 flex items-start gap-4">
            <div className="p-3 rounded-xl bg-accent-sky/10 border border-accent-sky/20">
               <ShieldCheck className="w-6 h-6 text-accent-sky" />
            </div>
            <div>
               <h4 className="font-bold text-text-primary mb-1 text-sm">Data Integrity Layer</h4>
               <p className="text-xs text-text-secondary leading-relaxed">
                  Automated background sync validates all relational constraints, ensuring that analytics 
                  are always computed on verified transactional snapshots.
               </p>
            </div>
         </div>
         <div className="glass-card p-6 flex items-start gap-4">
            <div className="p-3 rounded-xl bg-brand-500/10 border border-brand-500/20">
               <DatabaseZap className="w-6 h-6 text-brand-400" />
            </div>
            <div>
               <h4 className="font-bold text-text-primary mb-1 text-sm">Real-time Computation</h4>
               <p className="text-xs text-text-secondary leading-relaxed">
                  Mining algorithms (Apriori, K-Means) are triggered on-demand to provide fresh insights 
                  without the overhead of persistent analytical storage.
               </p>
            </div>
         </div>
      </div>
    </div>
  )
}

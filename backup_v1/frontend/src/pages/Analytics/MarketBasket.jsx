import { useState, useEffect } from 'react'
import { analyticsApi } from '@/services/api'
import { PageLoader, ErrorState, EmptyState } from '@/components/shared/States'
import { ShoppingCart, ArrowRight, Info, Filter, Zap } from 'lucide-react'

export default function MarketBasket() {
  const [data,     setData]     = useState(null)
  const [loading,  setLoading]  = useState(true)
  const [error,    setError]    = useState(null)
  
  const [minSupport, setMinSupport] = useState(0.02)
  const [minConf, setMinConf] = useState(0.3)

  const load = async () => {
    setLoading(true)
    analyticsApi.getMarketBasket({ min_support: minSupport, min_confidence: minConf })
      .then(d => { setData(d); setLoading(false) })
      .catch(() => { setError('Failed to run Apriori mining'); setLoading(false) })
  }

  useEffect(() => { load() }, [])

  if (loading) return <PageLoader />
  if (error)   return <ErrorState message={error} onRetry={load} />

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        
        {/* Left: Tuning Controls */}
        <div className="space-y-4">
           <div className="glass-card p-5 border-l-4 border-accent-sky">
              <h4 className="text-sm font-bold text-text-primary mb-4 flex items-center gap-2">
                 <Filter className="w-4 h-4 text-accent-sky" /> Algorithm Tuning
              </h4>
              <div className="space-y-5">
                 <div>
                    <div className="flex justify-between mb-1.5">
                       <label className="text-[10px] font-bold text-text-muted uppercase">Min Support</label>
                       <span className="text-[10px] font-mono text-accent-sky">{(minSupport * 100).toFixed(1)}%</span>
                    </div>
                    <input 
                      type="range" min="0.01" max="0.1" step="0.01" 
                      className="w-full h-1.5 bg-bg-primary rounded-lg appearance-none cursor-pointer accent-accent-sky"
                      value={minSupport}
                      onChange={e => setMinSupport(parseFloat(e.target.value))}
                    />
                 </div>
                 <div>
                    <div className="flex justify-between mb-1.5">
                       <label className="text-[10px] font-bold text-text-muted uppercase">Min Confidence</label>
                       <span className="text-[10px] font-mono text-accent-sky">{(minConf * 100).toFixed(0)}%</span>
                    </div>
                    <input 
                      type="range" min="0.1" max="0.8" step="0.1" 
                      className="w-full h-1.5 bg-bg-primary rounded-lg appearance-none cursor-pointer accent-accent-sky"
                      value={minConf}
                      onChange={e => setMinConf(parseFloat(e.target.value))}
                    />
                 </div>
                 <button onClick={load} className="w-full btn-primary bg-accent-sky hover:bg-sky-600 shadow-glow-sky text-xs py-2">
                   Apply & Re-mine
                 </button>
              </div>
           </div>

           <div className="glass-card p-5 text-[11px] leading-relaxed text-text-secondary space-y-3">
              <div className="flex items-center gap-2 text-text-primary font-bold mb-1">
                 <Info className="w-3.5 h-3.5 text-accent-sky" /> Understanding Metrics
              </div>
              <p><span className="text-accent-sky font-bold">Support:</span> Popularity of the itemset in overall transactions.</p>
              <p><span className="text-accent-sky font-bold">Confidence:</span> Likelihood that product B is purchased when product A is purchased.</p>
              <p><span className="text-accent-sky font-bold">Lift:</span> Increase in the ratio of sale of B when A is sold (Lift {'>'} 1 = strong association).</p>
           </div>
        </div>

        {/* Right: Association Rules List */}
        <div className="lg:col-span-3 space-y-4">
           <div className="flex items-center justify-between mb-2">
              <h3 className="section-title mb-0">Discovered Association Rules</h3>
              <div className="badge-info text-[10px]">{data?.rules?.length || 0} strong rules found</div>
           </div>
 
           {(!data?.rules || data.rules.length === 0) ? (
             <EmptyState title="No association rules found" subtitle="Try lowering the Support or Confidence thresholds." icon={ShoppingCart} />
           ) : (
             <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
               {data.rules.map((rule, idx) => (
                 <div key={idx} className="glass-card p-5 group hover:border-accent-sky/30 transition-all duration-300">
                    <div className="flex items-center gap-3 mb-4">
                       <div className="flex-1 space-y-1">
                          <p className="text-[10px] font-bold text-text-muted uppercase tracking-wider">Frequently bought together</p>
                          <div className="flex items-center gap-2">
                             <span className="text-xs font-bold text-text-primary">{rule.antecedents?.join(' + ') || '---'}</span>
                             <ArrowRight className="w-4 h-4 text-accent-sky group-hover:translate-x-1 transition-transform" />
                             <span className="text-xs font-bold text-accent-sky">{rule.consequents?.join(' + ') || '---'}</span>
                          </div>
                       </div>
                       <div className="w-10 h-10 rounded-xl bg-accent-sky/10 border border-accent-sky/20 flex items-center justify-center">
                          <Zap className="w-5 h-5 text-accent-sky" />
                       </div>
                    </div>
 
                    <div className="space-y-3">
                       <p className="text-[11px] text-text-secondary leading-normal bg-bg-hover/50 p-2.5 rounded-lg border border-border border-dashed">
                          {rule.interpretation}
                       </p>
                       <div className="flex gap-4 p-1">
                          <div>
                            <p className="text-[9px] text-text-muted uppercase font-bold">Confidence</p>
                            <p className="text-xs font-bold text-text-primary">{(rule.confidence * 100).toFixed(1)}%</p>
                          </div>
                          <div>
                            <p className="text-[9px] text-text-muted uppercase font-bold">Lift</p>
                            <p className="text-xs font-bold text-accent-sky">{rule.lift?.toFixed(2) || 0}x</p>
                          </div>
                       </div>
                    </div>
                 </div>
               ))}
             </div>
           )}
        </div>
      </div>
    </div>
  )
}

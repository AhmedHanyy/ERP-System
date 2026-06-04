import { useState, useEffect } from 'react'
import { analyticsApi } from '@/services/api'
import { PageLoader, ErrorState } from '@/components/shared/States'
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  LineChart, Line, ComposedChart, Area, Cell, PieChart, Pie, Legend
} from 'recharts'
import { 
  BarChart3, TrendingUp, Award, Layers, Target, 
  DollarSign, Globe, ArrowUpRight, TrendingDown, BookOpen, ShieldCheck, Zap
} from 'lucide-react'

const COLORS = ['#6366F1', '#8B5CF6', '#10B981', '#F59E0B', '#F43F5E', '#0EA5E9']

export default function BIReports() {
  const [data,     setData]     = useState(null)
  const [loading,  setLoading]  = useState(true)
  const [error,    setError]    = useState(null)
  const [activeTab, setActiveTab] = useState('financials')

  useEffect(() => {
    analyticsApi.getBIReport()
      .then(d => { setData(d); setLoading(false) })
      .catch(() => { setError('Failed to load BI data'); setLoading(false) })
  }, [])

  if (loading) return <PageLoader />
  if (error)   return <ErrorState message={error} />

  const fin = data?.financial_summary || {}

  return (
    <div className="space-y-6">
      {/* Tab Selector */}
      <div className="flex gap-2 p-1 border border-border rounded-xl w-fit" style={{ backgroundColor: 'var(--bg-surface)' }}>
         {['financials', 'products', 'supply-chain'].map(t => (
           <button 
             key={t}
             onClick={() => setActiveTab(t)}
             className={`px-4 py-2 rounded-lg text-xs font-bold transition-all ${
               activeTab === t ? 'bg-brand-50 dark:bg-blue-950/40 text-brand-600 dark:text-blue-400 shadow-sm' : 'text-text-muted hover:bg-bg-hover'
             }`}
           >
             {t === 'financials' ? 'Financial Intelligence' : t === 'products' ? 'Top Products' : 'Advanced Supply Chain'}
           </button>
         ))}
      </div>

      {activeTab === 'financials' ? (
         <div className="space-y-6 animate-fade-in">
             {/* 1. High-Level Financial Suite */}
             <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <FinancialCard label="Total Revenue" value={`EGP ${(fin.total_revenue || 0).toLocaleString()}`} trend="+12.4%" icon={DollarSign} color="text-brand-500 dark:text-blue-400" bg="bg-brand-50 dark:bg-blue-950/40" />
                <FinancialCard label="COGS" value={`EGP ${(fin.total_cogs || 0).toLocaleString()}`} trend="Optimized" icon={BookOpen} color="text-rose-500 dark:text-rose-400" bg="bg-rose-50 dark:bg-rose-950/40" />
                <FinancialCard label="Gross Profit" value={`EGP ${(fin.gross_profit || 0).toLocaleString()}`} trend="+8.2%" icon={TrendingUp} color="text-emerald-500 dark:text-emerald-400" bg="bg-emerald-50 dark:bg-emerald-950/40" />
                <FinancialCard label="Gross Margin" value={`${fin.gross_margin_pct || 0}%`} trend="Stable" icon={BarChart3} color="text-accent-violet dark:text-purple-400" bg="bg-accent-violet/10 dark:bg-purple-950/40" />
             </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
               <div className="lg:col-span-2 glass-card p-6">
                  <h3 className="section-title flex items-center gap-2 mb-6"><TrendingUp className="w-4 h-4 text-brand-500" /> Revenue vs Activity Trends</h3>
                  <div className="h-[300px]">
                     <ResponsiveContainer width="100%" height="100%">
                        <ComposedChart data={data?.monthly_revenue || []}>
                           <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" vertical={false} />
                           <XAxis dataKey="month" tick={{ fill: '#94A3B8', fontSize: 10 }} axisLine={false} tickLine={false} />
                           <YAxis tick={{ fill: '#94A3B8', fontSize: 10 }} axisLine={false} tickLine={false} tickFormatter={(v) => `${v/1000}K`} />
                           <Tooltip contentStyle={{ backgroundColor: 'var(--bg-surface)', border: '1px solid var(--border-main)', borderRadius: 12, fontSize: 12, color: 'var(--text-primary)' }} labelStyle={{ color: 'var(--text-secondary)' }} />
                           <Area type="monotone" dataKey="revenue" fill="#6366F1" fillOpacity={0.05} stroke="none" />
                           <Bar dataKey="orders" barSize={30} fill="#818CF8" radius={[4, 4, 0, 0]} opacity={0.3} />
                           <Line type="monotone" dataKey="revenue" stroke="#6366F1" strokeWidth={3} dot={{ r: 4 }} />
                        </ComposedChart>
                     </ResponsiveContainer>
                  </div>
               </div>

               <div className="glass-card p-6">
                  <h3 className="section-title flex items-center gap-2 mb-6"><Globe className="w-4 h-4 text-accent-sky" /> Top Regions (Sales)</h3>
                  <div className="space-y-5">
                     {(data?.region_distribution || []).slice(0, 5).map((r, i) => {
                        const totalRev = fin.total_revenue || 1;
                        const pct = Math.min(100, Math.max(0, ((r.revenue || 0) / totalRev) * 100));
                        return (
                           <div key={r.city || i} className="space-y-1.5">
                              <div className="flex justify-between text-xs"><span className="text-text-primary font-bold">{r.city || 'Unknown'}</span><span className="text-text-muted">EGP {(r.revenue || 0).toLocaleString()}</span></div>
                              <div className="w-full bg-bg-primary rounded-full h-1.5 overflow-hidden"><div className="h-full bg-accent-sky transition-all duration-1000" style={{ width: `${pct}%` }} /></div>
                           </div>
                        );
                     })}
                  </div>
               </div>
            </div>
         </div>
      ) : activeTab === 'products' ? (
         <div className="space-y-6 animate-fade-in">
           {/* Top 20 Products */}
           <div className="glass-card p-6">
             <h3 className="section-title flex items-center gap-2 mb-2"><Award className="w-4 h-4 text-brand-500" /> Top 20 Products — All Time</h3>
             <p className="text-[10px] text-text-muted mb-4">Ranked by net revenue. Historical Unmapped Product excluded.</p>
             <div className="overflow-x-auto">
               <table className="data-table">
                 <thead><tr><th>#</th><th>Product</th><th>Units</th><th>Revenue (EGP)</th><th>Profit (EGP)</th></tr></thead>
                 <tbody>
                   {(data?.top_20_products || []).map((p, i) => (
                     <tr key={i}>
                       <td className="text-xs text-text-muted font-bold">{i + 1}</td>
                       <td className="text-xs font-medium text-text-primary max-w-[280px] truncate">{p.name}</td>
                       <td className="text-xs text-center">{p.units.toLocaleString()}</td>
                       <td className="text-xs font-bold text-emerald-600 dark:text-emerald-400">{p.revenue.toLocaleString()}</td>
                       <td className="text-xs font-bold text-brand-600 dark:text-blue-400">{p.profit.toLocaleString()}</td>
                     </tr>
                   ))}
                 </tbody>
               </table>
             </div>
           </div>

           {/* Top 20 Variants */}
           <div className="glass-card p-6">
             <h3 className="section-title flex items-center gap-2 mb-2"><Layers className="w-4 h-4 text-accent-violet" /> Top 20 Variants — All Time</h3>
             <p className="text-[10px] text-text-muted mb-4">Individual SKU performance by color and size.</p>
             <div className="overflow-x-auto">
               <table className="data-table">
                 <thead><tr><th>#</th><th>SKU</th><th>Color</th><th>Size</th><th>Units</th><th>Revenue (EGP)</th><th>Profit (EGP)</th></tr></thead>
                 <tbody>
                   {(data?.top_20_variants || []).map((v, i) => (
                     <tr key={i}>
                       <td className="text-xs text-text-muted font-bold">{i + 1}</td>
                       <td className="text-xs font-mono text-text-secondary">{v.sku}</td>
                       <td className="text-xs">{v.color}</td>
                       <td className="text-xs">{v.size}</td>
                       <td className="text-xs text-center">{v.units.toLocaleString()}</td>
                       <td className="text-xs font-bold text-emerald-600 dark:text-emerald-400">{v.revenue.toLocaleString()}</td>
                       <td className="text-xs font-bold text-brand-600 dark:text-blue-400">{v.profit.toLocaleString()}</td>
                     </tr>
                   ))}
                 </tbody>
               </table>
             </div>
           </div>
         </div>
      ) : (
         <div className="space-y-6 animate-fade-in">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
               {/* ABC Analysis */}
               <div className="glass-card p-6">
                  <h3 className="section-title flex items-center gap-2 mb-4"><Zap className="w-4 h-4 text-accent-amber" /> ABC Financial Classification</h3>
                  <p className="text-[10px] text-text-muted mb-6">Grouping products by their cumulative revenue contribution (80/15/5 rule).</p>
                  <div className="space-y-2">
                     {(data?.abc_analysis || []).slice(0, 8).map(p => {
                        const abcClass = p.abc_class || 'C';
                        return (
                           <div key={p.product_id} className="flex justify-between items-center p-3 bg-bg-hover/30 rounded-xl border border-border">
                              <div>
                                 <p className="text-xs font-bold text-text-primary">{p.product_name || 'Unknown Product'}</p>
                                 <p className="text-[9px] text-text-muted">Rev: EGP {(p.revenue || 0).toLocaleString()}</p>
                              </div>
                              <span className={`px-2 py-1 rounded-full text-[9px] font-bold ${
                                 abcClass.startsWith('A') ? 'bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 dark:text-emerald-400' :
                                 abcClass.startsWith('B') ? 'bg-brand-50 dark:bg-blue-950/40 text-brand-600 dark:text-blue-400' :
                                 'bg-rose-50 dark:bg-rose-950/40 text-rose-600 dark:text-rose-400'
                              }`}>
                                 Class {abcClass}
                              </span>
                           </div>
                        );
                     })}
                  </div>
               </div>

               {/* Safety Stock Analysis */}
               <div className="glass-card p-6">
                  <h3 className="section-title flex items-center gap-2 mb-4"><ShieldCheck className="w-4 h-4 text-emerald-500" /> Safety Stock & Risk Analysis</h3>
                  <p className="text-[10px] text-text-muted mb-6">Statistical safety stock levels targeting a 95% service level confidence.</p>
                  <div className="overflow-x-auto">
                     <table className="data-table">
                        <thead>
                           <tr><th>Item</th><th>Actual</th><th>Safety</th><th>Status</th></tr>
                        </thead>
                        <tbody>
                           {(data?.safety_stock_report || []).slice(0, 8).map(s => {
                              const status = s.status || 'Unknown';
                              return (
                                 <tr key={s.product_id}>
                                    <td className="text-xs font-medium">{s.name || 'Unknown'}</td>
                                    <td className="text-xs">{s.current_stock || 0}</td>
                                    <td className="text-xs font-bold text-brand-600">{s.safety_stock || 0}</td>
                                    <td>
                                       <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold uppercase ${status === 'Healthy' ? 'bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 dark:text-emerald-400' : 'bg-rose-50 dark:bg-rose-950/40 text-rose-600 dark:text-rose-400 animate-pulse'}`}>
                                          {status}
                                       </span>
                                    </td>
                                 </tr>
                              );
                           })}
                        </tbody>
                     </table>
                  </div>
               </div>
            </div>
         </div>
      )}
    </div>
  )
}

function FinancialCard({ label, value, trend, icon: Icon, color, bg }) {
  return (
    <div className="glass-card p-5 relative overflow-hidden transition-all hover:translate-y-[-2px] hover:shadow-xl">
       <div className={`absolute top-0 right-0 p-4 opacity-10 ${color}`}><Icon className="w-12 h-12" /></div>
       <div className="relative z-10">
          <div className="flex items-center gap-2 mb-3"><div className={`p-1.5 rounded-lg ${bg} ${color}`}><Icon className="w-4 h-4" /></div><p className="text-[10px] font-bold text-text-muted uppercase tracking-wider">{label}</p></div>
          <p className="text-xl font-bold text-text-primary tracking-tight">{value}</p>
          <div className="flex items-center gap-1 mt-1 text-[10px] font-medium text-emerald-600"><ArrowUpRight className="w-3 h-3" /><span>{trend}</span></div>
       </div>
    </div>
  )
}

function DetailRow({ icon: Icon, label, value }) {
  return (
    <div className="flex items-center gap-3"><Icon className="w-4 h-4 text-text-muted shrink-0" /><div><p className="text-[9px] text-text-muted font-bold uppercase leading-none">{label}</p><p className="text-xs text-text-secondary mt-0.5">{value}</p></div></div>
  )
}

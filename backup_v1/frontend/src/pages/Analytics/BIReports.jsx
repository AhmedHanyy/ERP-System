import { useState, useEffect } from 'react'
import { analyticsApi } from '@/services/api'
import { PageLoader, ErrorState } from '@/components/shared/States'
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  LineChart, Line, ComposedChart, Area, Cell, PieChart, Pie
} from 'recharts'
import { BarChart3, TrendingUp, Award, Layers, Target } from 'lucide-react'
import StatusBadge from '@/components/shared/StatusBadge'

const COLORS = ['#6366F1', '#8B5CF6', '#10B981', '#F59E0B', '#F43F5E', '#0EA5E9']

export default function BIReports() {
  const [data,     setData]     = useState(null)
  const [loading,  setLoading]  = useState(true)
  const [error,    setError]    = useState(null)

  useEffect(() => {
    analyticsApi.getBIReport()
      .then(d => { setData(d); setLoading(false) })
      .catch(() => { setError('Failed to load BI data'); setLoading(false) })
  }, [])

  if (loading) return <PageLoader />
  if (error)   return <ErrorState message={error} />

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* Monthly Performance Trend */}
        <div className="glass-card p-6">
           <h3 className="section-title flex items-center gap-2 mb-6">
             <TrendingUp className="w-4 h-4 text-brand-400" />
             Yearly Revenue Performance
           </h3>
           <div className="h-[280px]">
             <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={data?.monthly_revenue || []}>
                   <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" vertical={false} />
                   <XAxis dataKey="month" tick={{ fill: '#94A3B8', fontSize: 10 }} axisLine={false} tickLine={false} />
                   <YAxis tick={{ fill: '#94A3B8', fontSize: 10 }} axisLine={false} tickLine={false} tickFormatter={(v) => `${v/1000}K`} />
                   <Tooltip 
                     contentStyle={{ background: '#FFFFFF', border: '1px solid #E2E8F0', borderRadius: 12, fontSize: 12, boxShadow: '0 4px 12px rgba(0,0,0,0.05)' }}
                   />
                   <Area type="monotone" dataKey="revenue" fill="#6366F1" fillOpacity={0.1} stroke="none" />
                   <Bar dataKey="orders" barSize={20} fill="#8B5CF6" radius={[4, 4, 0, 0]} opacity={0.6} />
                   <Line type="monotone" dataKey="revenue" stroke="#6366F1" strokeWidth={3} dot={{ r: 3, fill: '#6366F1' }} />
                </ComposedChart>
             </ResponsiveContainer>
           </div>
        </div>

        {/* Category Share */}
        <div className="glass-card p-6">
           <h3 className="section-title flex items-center gap-2 mb-6">
             <Layers className="w-4 h-4 text-accent-sky" />
             Revenue by Category
           </h3>
           <div className="h-[280px]">
             <ResponsiveContainer width="100%" height="100%">
               <PieChart>
                  <Pie
                    data={data?.category_revenue || []} dataKey="revenue" nameKey="category_id"
                    cx="50%" cy="50%" innerRadius={60} outerRadius={100} paddingAngle={5}
                  >
                    {(data?.category_revenue || []).map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={{ background: '#FFFFFF', border: '1px solid #E2E8F0', borderRadius: 12, fontSize: 12, boxShadow: '0 4px 12px rgba(0,0,0,0.05)' }} />
               </PieChart>
             </ResponsiveContainer>
           </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
         {/* Pareto Analysis (Top Products Contribution) */}
         <div className="lg:col-span-1 glass-card p-6">
            <h3 className="section-title flex items-center gap-2 mb-4">
              <Target className="w-4 h-4 text-accent-rose" />
              Pareto Analysis (80/20)
            </h3>
            <p className="text-[10px] text-text-muted mb-6 leading-relaxed">
              Analyzing the top 20 products and their cumulative contribution to overall revenue.
            </p>
            <div className="space-y-4">
               {(data?.pareto_analysis || []).slice(0, 5).map((p, i) => (
                 <div key={p.product_id} className="space-y-1.5">
                    <div className="flex justify-between text-xs">
                       <span className="text-text-primary font-medium truncate max-w-[140px]">{p.product_name}</span>
                       <span className="text-text-muted">{p.cum_revenue_pct}%</span>
                    </div>
                    <div className="w-full bg-bg-primary rounded-full h-1.5 overflow-hidden">
                       <div 
                         className="h-full bg-gradient-brand transition-all duration-1000" 
                         style={{ width: `${p.cum_revenue_pct}%` }} 
                       />
                    </div>
                 </div>
               ))}
               <div className="pt-4 border-t border-border flex items-center justify-between">
                  <p className="text-[10px] font-bold text-text-muted uppercase">Top 5 Revenue Share</p>
                  <p className="text-sm font-bold text-accent-emerald">{data?.pareto_analysis?.[4]?.cum_revenue_pct || 0}%</p>
               </div>
            </div>
         </div>

         {/* Supplier Performance */}
         <div className="lg:col-span-2 glass-card overflow-hidden">
            <div className="p-4 border-b border-border bg-bg-hover/20 flex items-center justify-between">
               <h3 className="text-xs font-bold text-text-muted uppercase tracking-wider flex items-center gap-2">
                 <Award className="w-4 h-4 text-accent-amber" />
                 Supplier Performance
               </h3>
               <span className="text-[10px] text-text-muted">Procurement Analytics</span>
            </div>
            <div className="overflow-x-auto">
               <table className="data-table">
                  <thead>
                     <tr>
                        <th>Supplier</th><th>Rating</th><th>Purchase Orders</th><th>Total Value</th>
                     </tr>
                  </thead>
                  <tbody>
                    {(data?.supplier_performance || []).map(s => (
                       <tr key={s.id}>
                          <td className="text-sm font-medium">{s.name}</td>
                          <td>
                             <div className="flex items-center gap-1">
                                <span className="text-xs font-bold text-accent-amber">{s.rating}</span>
                                <div className="flex">
                                  {[1,2,3,4,5].map(i => (
                                    <div key={i} className={`w-1.5 h-1.5 rounded-full mx-0.5 ${i <= s.rating ? 'bg-accent-amber' : 'bg-bg-hover'}`} />
                                  ))}
                                </div>
                             </div>
                          </td>
                          <td className="text-xs text-text-secondary">{s.total_orders} requests</td>
                          <td className="text-xs font-bold text-text-primary">EGP {s.total_value?.toLocaleString()}</td>
                       </tr>
                    ))}
                  </tbody>
               </table>
            </div>
         </div>
      </div>
    </div>
  )
}

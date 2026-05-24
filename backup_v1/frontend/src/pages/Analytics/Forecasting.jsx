import { useState, useEffect } from 'react'
import { analyticsApi } from '@/services/api'
import { PageLoader, ErrorState } from '@/components/shared/States'
import { 
  ComposedChart, Line, Area, XAxis, YAxis, CartesianGrid, 
  Tooltip, ResponsiveContainer, Legend 
} from 'recharts'
import { Sparkles, TrendingUp, Calendar, Info } from 'lucide-react'

export default function Forecasting() {
  const [data,     setData]     = useState(null)
  const [loading,  setLoading]  = useState(true)
  const [error,    setError]    = useState(null)
  const [days,     setDays]     = useState(30)

  useEffect(() => {
    setLoading(true)
    analyticsApi.getForecast(days)
      .then(d => { setData(d); setLoading(false) })
      .catch(() => { setError('Failed to generate forecast'); setLoading(false) })
  }, [days])

  if (loading) return <PageLoader />
  if (error)   return <ErrorState message={error} />

  // Combine historical and forecast for the chart
  const historical = data.historical.map(d => ({ ...d, type: 'historical' }))
  const forecast   = data.forecast.map(d => ({ ...d, type: 'forecast' }))
  const chartData  = [...historical, ...forecast]

  return (
    <div className="space-y-6">
      {/* Forecasting logic info */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        <div className="lg:col-span-3 glass-card p-6 relative overflow-hidden">
           <div className="absolute top-0 right-0 p-8 opacity-5">
              <Sparkles className="w-32 h-32 text-accent-violet" />
           </div>
           
           <h3 className="section-title flex items-center gap-2">
             <TrendingUp className="w-4 h-4 text-accent-violet" />
             Revenue Demand Forecast
           </h3>
           
           <div className="h-[350px] w-full mt-6">
             <ResponsiveContainer width="100%" height="100%">
               <ComposedChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" vertical={false} />
                  <XAxis 
                    dataKey="date" 
                    tick={{ fill: '#94A3B8', fontSize: 10 }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <YAxis 
                    tick={{ fill: '#94A3B8', fontSize: 10 }}
                    tickFormatter={(v) => `EGP ${v/1000}K`}
                    axisLine={false}
                    tickLine={false}
                  />
                  <Tooltip 
                    contentStyle={{ background: '#FFFFFF', border: '1px solid #E2E8F0', borderRadius: 12, boxShadow: '0 4px 12px rgba(0,0,0,0.05)' }}
                    itemStyle={{ fontSize: 12 }}
                  />
                 <Legend verticalAlign="top" height={36} iconType="circle" />
                 
                 {/* Historical actuals */}
                 <Line 
                   type="monotone" dataKey="actual" 
                   stroke="#6366F1" strokeWidth={3} 
                   dot={false} name="Historical Revenue"
                   activeDot={{ r: 4, fill: '#6366F1' }}
                 />
                 
                 {/* Fitted curve */}
                 <Line 
                   type="monotone" dataKey="fitted" 
                   stroke="#818CF8" strokeDasharray="5 5" 
                   strokeWidth={1} dot={false} name="Model Fit"
                 />
                 
                 {/* Forecast line */}
                 <Line 
                   type="monotone" dataKey="forecast" 
                   stroke="#8B5CF6" strokeWidth={3} 
                   dot={false} name="Predicted Trend"
                   connectNulls
                 />
                 
                 {/* Confidence Interval */}
                 <Area 
                   type="monotone" dataKey="upper_bound" 
                   stroke="none" fill="#8B5CF6" fillOpacity={0.1} 
                   connectNulls
                 />
                 <Area 
                   type="monotone" dataKey="lower_bound" 
                   stroke="none" fill="#8B5CF6" fillOpacity={0.1}
                   connectNulls
                 />
               </ComposedChart>
             </ResponsiveContainer>
           </div>
        </div>

        <div className="space-y-4">
           {/* Model Info */}
           <div className="glass-card p-5 border-l-4 border-accent-violet">
              <p className="text-[10px] font-bold text-accent-violet uppercase tracking-widest mb-1">Model: {data.model_info.type}</p>
              <div className="flex items-center justify-between mb-4">
                 <h4 className="text-sm font-bold text-text-primary">Decision Support</h4>
                 <div className="badge-info text-[10px]">R² Score: {data.model_info.r2_score}</div>
              </div>
              <div className="space-y-3">
                 <div className="p-3 bg-bg-hover/40 rounded-xl">
                    <p className="text-xs text-text-muted mb-1">Growth Trend (Daily)</p>
                    <p className="text-lg font-bold text-text-primary">
                       {data.model_info.slope > 0 ? '+' : ''}{data.model_info.slope.toFixed(2)} 
                       <span className="text-[10px] text-text-muted font-normal ml-1">EGP/day</span>
                    </p>
                 </div>
                 <div className="flex gap-2 p-2 bg-accent-violet/5 rounded-xl text-accent-violet">
                    <Info className="w-4 h-4 shrink-0 mt-0.5" />
                    <p className="text-[10px] leading-relaxed font-medium">Predicted upward trend identified. Suggesting 15% inventory buffer for next 30 days.</p>
                 </div>
              </div>
           </div>

           {/* Controls */}
           <div className="glass-card p-5">
              <h4 className="text-sm font-bold text-text-primary mb-4 flex items-center gap-2">
                 <Calendar className="w-4 h-4 text-text-muted" /> Parametric Controls
              </h4>
              <div className="space-y-4">
                 <div>
                    <label className="text-[10px] font-bold text-text-muted uppercase block mb-2">Forecast Horizon (Days)</label>
                    <div className="flex gap-2">
                       {[30, 60, 90].map(d => (
                         <button 
                           key={d} 
                           onClick={() => setDays(d)}
                           className={`flex-1 py-2 rounded-lg text-xs font-bold transition-all ${
                             days === d ? 'bg-accent-violet text-white shadow-lg' : 'bg-bg-hover text-text-muted hover:text-text-primary'
                           }`}
                         >
                           {d}d
                         </button>
                       ))}
                    </div>
                 </div>
                 <p className="text-[10px] text-text-muted italic border-t border-border pt-4">
                    Uses Least Squares Regression on daily sales aggregates from OLAP layer.
                 </p>
              </div>
           </div>
        </div>
      </div>
    </div>
  )
}

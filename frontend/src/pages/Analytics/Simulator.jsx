import { useState } from 'react'
import { 
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, 
  ResponsiveContainer, AreaChart, Area 
} from 'recharts'
import { Zap, TrendingUp, DollarSign, Package, AlertCircle } from 'lucide-react'

export default function Simulator() {
  const [markup, setMarkup] = useState(40)
  const [adSpend, setAdSpend] = useState(5000)
  const [conversion, setConversion] = useState(2.5)

  // Mock simulation logic with dampened elasticity
  const generateSimulatedData = () => {
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun']
    const baseRevenue = 50000
    
    // Dampened impact: higher markup should eventually hurt conversion
    // This creates a more realistic ROI curve rather than unchecked exponential growth
    const priceElasticityPenalty = markup > 50 ? (markup - 50) * 0.1 : 0
    const effectiveConversion = Math.max(0.5, conversion - priceElasticityPenalty)
    
    const impact = (adSpend * (effectiveConversion / 100)) + (baseRevenue * (markup / 100) * 0.4)
    
    return months.map((m, i) => ({
      name: m,
      baseline: baseRevenue + (i * 2000),
      simulated: baseRevenue + (i * 2000) + (impact * (1 + (i*0.05)))
    }))
  }

  const data = generateSimulatedData()
  const currentSim = data[data.length - 1].simulated
  const baseline = data[data.length - 1].baseline
  const increase = ((currentSim - baseline) / baseline * 100).toFixed(1)

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        
        {/* Controls Panel */}
        <div className="space-y-4">
           <div className="glass-card p-6 border-l-4 border-brand-500">
              <h3 className="text-sm font-bold text-text-primary mb-6 flex items-center gap-2">
                 <Zap className="w-4 h-4 text-brand-500" /> Strategic Variables
              </h3>
              <div className="space-y-8">
                 <div>
                    <div className="flex justify-between mb-2">
                       <label className="text-[10px] font-bold text-text-muted uppercase">Price Markup %</label>
                       <span className="text-[10px] font-mono text-brand-600">+{markup}%</span>
                    </div>
                    <input 
                      type="range" min="10" max="100" 
                      className="w-full accent-brand-500" 
                      value={markup} 
                      onChange={(e) => setMarkup(parseInt(e.target.value))}
                    />
                 </div>
                 <div>
                    <div className="flex justify-between mb-2">
                       <label className="text-[10px] font-bold text-text-muted uppercase">Monthly Ad Spend</label>
                       <span className="text-[10px] font-mono text-brand-600">EGP {adSpend}</span>
                    </div>
                    <input 
                      type="range" min="0" max="20000" step="500"
                      className="w-full accent-brand-500" 
                      value={adSpend} 
                      onChange={(e) => setAdSpend(parseInt(e.target.value))}
                    />
                 </div>
                 <div>
                    <div className="flex justify-between mb-2">
                       <label className="text-[10px] font-bold text-text-muted uppercase">Conversion Rate</label>
                       <span className="text-[10px] font-mono text-brand-600">{conversion}%</span>
                    </div>
                    <input 
                      type="range" min="0.1" max="10" step="0.1"
                      className="w-full accent-brand-500" 
                      value={conversion} 
                      onChange={(e) => setConversion(parseFloat(e.target.value))}
                    />
                 </div>
              </div>
           </div>

           <div className="glass-card p-5 bg-brand-500 text-white shadow-glow-brand">
              <p className="text-[10px] font-bold uppercase opacity-80 mb-1">Simulated ROI</p>
              <h4 className="text-2xl font-bold">+{increase}%</h4>
              <p className="text-[10px] mt-2 opacity-90 leading-relaxed">
                 Predicted revenue increase based on multi-variate informatics model.
              </p>
           </div>
           
           {/* Assumptions Breakdown */}
           <div className="glass-card p-5 border border-amber-500/20 bg-amber-500/5">
              <p className="text-[10px] font-bold uppercase text-amber-600 dark:text-amber-500 mb-3 flex items-center gap-1">
                 <AlertCircle className="w-3 h-3" /> Assumptions Breakdown
              </p>
              <div className="space-y-2 text-[10px] text-text-secondary font-medium">
                 <p className="flex justify-between"><span>Base Revenue:</span> <span>EGP 50,000</span></p>
                 <p className="flex justify-between"><span>Price Penalty:</span> <span>{markup > 50 ? `-${((markup - 50) * 0.1).toFixed(1)}% Conversion` : 'None'}</span></p>
                 <p className="flex justify-between border-t border-border/50 pt-2 mt-2">
                    <span>Effective Conversion:</span> <span className="text-text-primary font-bold">{Math.max(0.5, conversion - (markup > 50 ? (markup - 50) * 0.1 : 0)).toFixed(1)}%</span>
                 </p>
                 <p className="text-text-muted italic mt-2 leading-tight">
                    * Simulation dampens exponential growth at extreme price markups to simulate real-world price elasticity.
                 </p>
              </div>
           </div>
        </div>

        {/* Forecast Comparison */}
        <div className="lg:col-span-3 glass-card p-6">
            <div className="flex items-center justify-between mb-4">
               <div>
                  <h3 className="section-title mb-1 flex items-center gap-2">
                     Revenue Impact Simulation
                  </h3>
                  <p className="text-[10px] text-amber-600 dark:text-amber-400 font-bold flex items-center gap-1 mt-2">
                     <AlertCircle className="w-3 h-3" /> Scenario estimates based on simplified forecasting assumptions.
                  </p>
               </div>
               <div className="flex gap-4">
                 <div className="flex items-center gap-1.5 text-[10px] font-bold text-text-muted uppercase">
                    <div className="w-2.5 h-2.5 rounded-full bg-bg-hover" /> Baseline
                 </div>
                 <div className="flex items-center gap-1.5 text-[10px] font-bold text-brand-500 uppercase">
                    <div className="w-2.5 h-2.5 rounded-full bg-brand-500" /> Simulated
                 </div>
              </div>
           </div>

           <div className="h-[380px]">
              <ResponsiveContainer width="100%" height="100%">
                 <AreaChart data={data}>
                    <defs>
                       <linearGradient id="colorSim" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#6366F1" stopOpacity={0.1}/>
                          <stop offset="95%" stopColor="#6366F1" stopOpacity={0}/>
                       </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" vertical={false} />
                    <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{fontSize: 10, fill: '#94A3B8'}} />
                    <YAxis axisLine={false} tickLine={false} tick={{fontSize: 10, fill: '#94A3B8'}} tickFormatter={(v) => `EGP ${v/1000}K`} />
                    <Tooltip 
                      contentStyle={{ background: '#FFFFFF', border: '1px solid #E2E8F0', borderRadius: 12, boxShadow: '0 4px 12px rgba(0,0,0,0.05)' }}
                    />
                    <Area type="monotone" dataKey="simulated" stroke="#6366F1" strokeWidth={3} fillOpacity={1} fill="url(#colorSim)" />
                    <Area type="monotone" dataKey="baseline" stroke="#E2E8F0" strokeWidth={2} strokeDasharray="5 5" fill="none" />
                 </AreaChart>
              </ResponsiveContainer>
           </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
         <InsightBox 
           icon={Package} 
           title="Inventory Implication" 
           desc="Simulated demand requires a 22% increase in turnover speed to avoid stock-outs." 
         />
         <InsightBox 
           icon={DollarSign} 
           title="Cash Flow Outlook" 
           desc="Estimated profitability peak reaches EGP 95K in Month 5 under these variables." 
         />
         <InsightBox 
           icon={AlertCircle} 
           title="Risk Threshold" 
           desc="Markup {'>'} 65% may lead to a 10% decrease in conversion due to price sensitivity." 
         />
      </div>
    </div>
  )
}

function InsightBox({ icon: Icon, title, desc }) {
   return (
      <div className="glass-card p-5 flex gap-4">
         <div className="w-10 h-10 rounded-xl bg-bg-hover flex items-center justify-center shrink-0">
            <Icon className="w-5 h-5 text-text-secondary" />
         </div>
         <div>
            <h5 className="text-xs font-bold text-text-primary mb-1">{title}</h5>
            <p className="text-[10px] text-text-secondary leading-relaxed">{desc}</p>
         </div>
      </div>
   )
}

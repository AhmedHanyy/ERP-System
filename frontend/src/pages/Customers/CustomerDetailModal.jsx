import { useState, useEffect } from 'react'
import { customersApi } from '@/services/api'
import { PageLoader } from '@/components/shared/States'
import StatusBadge from '@/components/shared/StatusBadge'
import { X, Mail, Phone, MapPin, Calendar, ShoppingBag, Target, PieChart, TrendingUp } from 'lucide-react'
import { format } from 'date-fns'

export default function CustomerDetailModal({ customerId, onClose }) {
  const [customer, setCustomer] = useState(null)
  const [insights, setInsights] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetch = async () => {
       try {
          const cust = await customersApi.get(customerId)
          setCustomer(cust)
          
          // Separate try-catch for insights so they don't break the main profile
          try {
             const ins = await customersApi.getInsights(customerId)
             setInsights(ins)
          } catch (e) {
             console.error("Insights error:", e)
          }
       } catch (e) {
          console.error("Customer load error:", e)
       } finally {
          setLoading(false)
       }
    }
    fetch()
  }, [customerId])

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-bg-primary/90 backdrop-blur-md p-4" onClick={onClose}>
      <div
        className="w-full max-w-4xl max-h-[90vh] bg-bg-secondary rounded-3xl border border-border overflow-hidden animate-scale-in shadow-2xl flex flex-col"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-6 border-b border-border flex items-center justify-between" style={{ backgroundColor: 'var(--bg-surface)' }}>
          <div className="flex items-center gap-3">
             <Target className="w-5 h-5 text-brand-500" />
             <h2 className="text-lg font-bold text-text-primary">Informatics Customer Profile</h2>
          </div>
          <button onClick={onClose} className="p-2 rounded-xl hover:bg-bg-hover transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        {loading ? <div className="p-20"><PageLoader /></div> : !customer ? (
          <div className="p-20 text-center text-text-muted">Customer data unavailable</div>
        ) : (
          <div className="overflow-y-auto flex-1 p-8 space-y-10">
            
            {/* Top Section: Hero & Key Metrics */}
            <div className="flex flex-col md:flex-row gap-8 items-start">
               <div className="relative shrink-0">
                  <div className="w-24 h-24 rounded-[2rem] bg-gradient-brand flex items-center justify-center text-white text-4xl font-black border-4 border-white shadow-xl">
                     {customer.name?.charAt(0).toUpperCase()}
                  </div>
                  <div className="absolute -bottom-1 -right-1 w-8 h-8 rounded-xl bg-emerald-500 border-4 border-white flex items-center justify-center">
                     <div className="w-2 h-2 rounded-full bg-white animate-pulse" />
                  </div>
               </div>

               <div className="flex-1 space-y-1">
                  <h3 className="text-3xl font-black text-text-primary tracking-tight">{customer.name}</h3>
                  <div className="flex items-center gap-4 py-2">
                     <StatusBadge status={customer.segment} />
                     <span className="text-[10px] font-bold text-text-muted uppercase tracking-widest">Global ID: #{customer.id}</span>
                  </div>
                  <div className="flex flex-wrap gap-6 pt-4 text-sm">
                     <DetailRow icon={Mail} value={customer.email} />
                     <DetailRow icon={Phone} value={customer.phone || 'No Phone Registered'} />
                     <DetailRow icon={MapPin} value={`${customer.city}, ${customer.country}`} />
                  </div>
               </div>

                <div className="w-full md:w-64 space-y-3">
                  <div className="glass-card p-4 bg-brand-50/50 dark:bg-blue-950/20 border-brand-100 dark:border-blue-900/30">
                     <p className="text-[9px] font-bold text-brand-600 dark:text-blue-400 uppercase">Lifetime Rev</p>
                     <p className="text-xl font-black text-brand-600 dark:text-blue-400">EGP {customer.lifetime_value?.toLocaleString()}</p>
                  </div>
               </div>
            </div>

            {/* Behavioral Intelligence Section */}
            <div className="space-y-4">
               <h4 className="text-xs font-bold text-text-muted uppercase tracking-widest px-1">Behavioral Informatics</h4>
               <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <InsightCard 
                    title="Order Consistency" 
                    value={insights?.behavior_report?.order_consistency || 'Analyzing...'} 
                    desc="Historical regularity index"
                    icon={TrendingUp}
                    color="text-brand-500 dark:text-blue-400"
                    bg="bg-brand-50 dark:bg-blue-950/40"
                  />
                  <InsightCard 
                    title="Average Basket" 
                    value={`EGP ${insights?.behavior_report?.avg_basket_value?.toLocaleString() || 0}`} 
                    desc="Mean Transaction Value"
                    icon={ShoppingBag}
                    color="text-emerald-500 dark:text-emerald-400"
                    bg="bg-emerald-50 dark:bg-emerald-950/40"
                  />
                  <InsightCard 
                    title="AI Prediction" 
                    value={insights?.behavior_report?.prediction || 'Pending...'} 
                    desc="Projected Brand Loyalty"
                    icon={Target}
                    color="text-accent-violet dark:text-purple-400"
                    bg="bg-accent-violet/10 dark:bg-purple-950/40"
                  />
               </div>
            </div>

            {/* Bottom Grid: Products & Ledger */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
               <div className="space-y-4">
                  <h4 className="text-xs font-bold text-text-muted uppercase tracking-widest">Top Product Affinity</h4>
                  <div className="space-y-3">
                     {(insights?.top_products || []).slice(0, 5).map(p => (
                       <div key={p.name} className="flex justify-between items-center p-3 bg-bg-hover rounded-2xl border border-border/50">
                          <span className="text-sm font-bold text-text-primary">{p.name}</span>
                          <div className="text-right">
                             <p className="text-[10px] font-bold text-emerald-600">{p.qty} Total Units</p>
                             <p className="text-[9px] text-text-muted">EGP {p.spend?.toLocaleString()}</p>
                          </div>
                       </div>
                     ))}
                     {(!insights?.top_products?.length) && <p className="text-xs text-text-muted italic py-4">No product data available yet.</p>}
                  </div>
               </div>

               <div className="space-y-4">
                  <h4 className="text-xs font-bold text-text-muted uppercase tracking-widest">Transaction Ledger</h4>
                  <div className="space-y-3 max-h-[300px] overflow-y-auto pr-2 custom-scrollbar">
                      {(customer.orders || []).map(order => (
                       <div key={order.id} className="p-4 rounded-2xl border border-border flex items-center justify-between shadow-sm hover:shadow-md transition-all" style={{ backgroundColor: 'var(--bg-surface)' }}>
                          <div>
                             <p className="text-sm font-black text-brand-500">{order.order_number}</p>
                             <p className="text-[10px] text-text-muted">{format(new Date(order.created_at), 'MMM d, yyyy')}</p>
                          </div>
                          <div className="text-right">
                             <p className="text-sm font-bold text-text-primary">EGP {order.total_amount?.toLocaleString()}</p>
                             <StatusBadge status={order.status} showDot={false} />
                          </div>
                       </div>
                     ))}
                  </div>
               </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function InsightCard({ title, value, desc, icon: Icon, color, bg }) {
  return (
    <div className="glass-card p-6 shadow-sm border-border/50">
       <div className="flex items-center gap-3 mb-4">
          <div className={`p-2 rounded-xl ${bg} ${color}`}>
             <Icon className="w-5 h-5" />
          </div>
          <p className="text-[10px] font-bold text-text-muted uppercase tracking-widest">{title}</p>
       </div>
       <p className="text-lg font-black text-text-primary mb-1">{value}</p>
       <p className="text-[10px] text-text-muted font-medium italic">{desc}</p>
    </div>
  )
}

function DetailRow({ icon: Icon, value }) {
  return (
    <div className="flex items-center gap-2">
       <Icon className="w-4 h-4 text-text-muted" />
       <span className="font-medium text-text-secondary">{value}</span>
    </div>
  )
}

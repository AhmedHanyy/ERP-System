import { useState, useEffect } from 'react'
import { customersApi } from '@/services/api'
import { PageLoader } from '@/components/shared/States'
import StatusBadge from '@/components/shared/StatusBadge'
import { X, Mail, Phone, MapPin, Calendar, ShoppingBag } from 'lucide-react'
import { format } from 'date-fns'

export default function CustomerDetailModal({ customerId, onClose }) {
  const [customer, setCustomer] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    customersApi.get(customerId)
      .then(d => { setCustomer(d); setLoading(false) })
      .catch(() => setLoading(false))
  }, [customerId])

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-end bg-bg-primary/80 backdrop-blur-sm" onClick={onClose}>
      <div
        className="w-full max-w-xl h-full bg-bg-secondary border-l border-border overflow-y-auto animate-slide-in"
        onClick={e => e.stopPropagation()}
      >
        <div className="p-6 border-b border-border flex items-center justify-between">
          <h2 className="text-lg font-semibold">Customer Profile</h2>
          <button onClick={onClose} className="p-2 rounded-xl hover:bg-bg-hover transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>

        {loading ? <div className="p-8"><PageLoader /></div> : !customer ? (
          <div className="p-8 text-center text-text-muted">Customer not found</div>
        ) : (
          <div className="p-6 space-y-6">
            {/* Header / Avatar */}
            <div className="flex items-center gap-4">
              <div className="w-16 h-16 rounded-2xl bg-gradient-brand flex items-center justify-center text-white text-2xl font-bold border border-white/10">
                {customer.name?.charAt(0).toUpperCase()}
              </div>
              <div>
                <h3 className="text-xl font-bold text-text-primary">{customer.name}</h3>
                <div className="flex items-center gap-2 mt-1">
                  <StatusBadge status={customer.segment} />
                  <span className="text-xs text-text-muted">ID: {customer.id}</span>
                </div>
              </div>
            </div>

            {/* Stats Grid */}
            <div className="grid grid-cols-2 gap-4">
              <div className="glass-card p-4">
                <p className="text-xs text-text-muted uppercase mb-1">Lifetime Value</p>
                <p className="text-lg font-bold text-accent-emerald">EGP {customer.lifetime_value?.toLocaleString()}</p>
              </div>
              <div className="glass-card p-4">
                <p className="text-xs text-text-muted uppercase mb-1">Total Orders</p>
                <p className="text-lg font-bold text-text-primary">{customer.total_orders}</p>
              </div>
            </div>

            {/* Info List */}
            <div className="glass-card overflow-hidden">
               <div className="p-4 border-b border-border bg-bg-hover/30">
                 <p className="text-xs font-semibold text-text-muted uppercase tracking-wider">Contact Info</p>
               </div>
               <div className="p-4 space-y-3">
                 <div className="flex items-center gap-3 text-sm">
                   <Mail className="w-4 h-4 text-text-muted" />
                   <span className="text-text-secondary">{customer.email}</span>
                 </div>
                 <div className="flex items-center gap-3 text-sm">
                   <Phone className="w-4 h-4 text-text-muted" />
                   <span className="text-text-secondary">{customer.phone || 'N/A'}</span>
                 </div>
                 <div className="flex items-center gap-3 text-sm">
                   <MapPin className="w-4 h-4 text-text-muted" />
                   <span className="text-text-secondary">{customer.city}, {customer.country}</span>
                 </div>
                 <div className="flex items-center gap-3 text-sm">
                   <Calendar className="w-4 h-4 text-text-muted" />
                   <span className="text-text-secondary">Joined {format(new Date(customer.created_at), 'PPP')}</span>
                 </div>
               </div>
            </div>

            {/* Recent Orders */}
            <div>
              <div className="flex items-center justify-between mb-3">
                <p className="text-xs font-semibold text-text-muted uppercase tracking-wider">Recent Orders</p>
                <div className="bg-bg-hover px-2 py-0.5 rounded text-[10px] text-text-secondary uppercase">Last 20</div>
              </div>
              <div className="space-y-2">
                {(customer.orders || []).map(order => (
                  <div key={order.id} className="bg-bg-hover/50 hover:bg-bg-hover rounded-xl p-3 border border-border border-dashed transition-colors flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-lg bg-bg-card flex items-center justify-center">
                        <ShoppingBag className="w-4 h-4 text-text-muted" />
                      </div>
                      <div>
                        <p className="text-sm font-mono text-brand-400">{order.order_number}</p>
                        <p className="text-[10px] text-text-muted">{format(new Date(order.created_at), 'MMM d, yyyy')}</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-bold text-text-primary">EGP {order.total_amount?.toLocaleString()}</p>
                      <StatusBadge status={order.status} showDot={false} />
                    </div>
                  </div>
                ))}
                {(!customer.orders || customer.orders.length === 0) && (
                  <p className="text-center py-4 text-xs text-text-muted">No orders found</p>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

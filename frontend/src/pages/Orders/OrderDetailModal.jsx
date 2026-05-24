import { useState, useEffect } from 'react'
import { ordersApi } from '@/services/api'
import { PageLoader } from '@/components/shared/States'
import StatusBadge from '@/components/shared/StatusBadge'
import { X, Package } from 'lucide-react'
import { format } from 'date-fns'
import toast from 'react-hot-toast'

export default function OrderDetailModal({ orderId, onClose, onStatusUpdate }) {
  const [order,   setOrder]   = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    ordersApi.get(orderId)
      .then(d => { setOrder(d); setLoading(false) })
      .catch(() => setLoading(false))
  }, [orderId])

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-end bg-bg-primary/80 backdrop-blur-sm" onClick={onClose}>
      <div
        className="w-full max-w-xl h-full bg-bg-secondary border-l border-border overflow-y-auto animate-slide-in"
        onClick={e => e.stopPropagation()}
      >
        <div className="p-6 border-b border-border flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold">Order Details</h2>
            {order && <p className="text-xs text-brand-400 font-mono">{order.order_number}</p>}
          </div>
          <button onClick={onClose} className="p-2 rounded-xl hover:bg-bg-hover transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>

        {loading ? <div className="p-8"><PageLoader /></div> : !order ? (
          <div className="p-8 text-center text-text-muted">Order not found</div>
        ) : (
          <div className="p-6 space-y-6">
            {/* Customer */}
            <div className="glass-card p-4">
              <p className="text-xs text-text-muted uppercase tracking-wider mb-3">Customer</p>
              <p className="font-semibold">{order.customer_name}</p>
              <p className="text-sm text-text-secondary">{order.customer_email}</p>
            </div>

            {/* Status */}
            <div className="glass-card p-4">
              <p className="text-xs text-text-muted uppercase tracking-wider mb-3">Status</p>
              <div className="flex items-center gap-3">
                <StatusBadge status={order.status} />
                <select
                  className="input text-xs py-1.5 flex-1"
                  value={order.status}
                  onChange={e => { onStatusUpdate(order.id, e.target.value); setOrder({...order, status: e.target.value}) }}
                >
                  {['Pending','Preparing','Shipped','Delivered','Cancelled'].map(s =>
                    <option key={s} value={s}>{s}</option>
                  )}
                </select>
              </div>
            </div>

            {/* Items */}
            <div>
              <p className="text-xs text-text-muted uppercase tracking-wider mb-3">Order Items</p>
              <div className="space-y-2">
                {(order.items || []).map(item => (
                  <div key={item.id} className="bg-bg-hover rounded-xl p-3 flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-brand-500/10 flex items-center justify-center shrink-0">
                      <Package className="w-4 h-4 text-brand-400" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">{item.product_name}</p>
                      <p className="text-xs text-text-muted">{item.product_sku} × {item.quantity}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-semibold">EGP {item.subtotal?.toLocaleString()}</p>
                      <p className="text-xs text-text-muted">@ {item.unit_price}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Totals */}
            <div className="glass-card p-4 space-y-2 text-sm">
              <div className="flex justify-between text-text-secondary">
                <span>Subtotal</span>
                <span>EGP {(order.total_amount - order.shipping_fee + order.discount).toLocaleString()}</span>
              </div>
              {order.discount > 0 && (
                <div className="flex justify-between text-accent-emerald">
                  <span>Discount</span>
                  <span>- EGP {order.discount}</span>
                </div>
              )}
              <div className="flex justify-between text-text-secondary">
                <span>Shipping</span>
                <span>EGP {order.shipping_fee}</span>
              </div>
              <div className="flex justify-between font-bold border-t border-border pt-2 text-text-primary">
                <span>Total</span>
                <span>EGP {order.total_amount?.toLocaleString()}</span>
              </div>
              <div className="flex justify-between text-accent-emerald">
                <span>Profit</span>
                <span>EGP {order.profit?.toLocaleString()}</span>
              </div>
            </div>

            <p className="text-xs text-text-muted text-center">
              Created {format(new Date(order.created_at), 'PPP')}
            </p>
          </div>
        )}
      </div>
    </div>
  )
}

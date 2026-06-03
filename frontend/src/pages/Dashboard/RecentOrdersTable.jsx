import { useState, useEffect } from 'react'
import { dashboardApi } from '@/services/api'
import { PageLoader } from '@/components/shared/States'
import StatusBadge from '@/components/shared/StatusBadge'
import { useNavigate } from 'react-router-dom'
import clsx from 'clsx'

export default function RecentOrdersTable() {
  const [orders,  setOrders]  = useState([])
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    dashboardApi.getRecentOrders()
      .then(d => { setOrders(d.slice(0, 4)); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  return (
    <div className="glass-card p-6 h-full">
      <div className="flex items-center justify-between mb-6">
        <h3 className="section-title mb-0">Recent Orders</h3>
        <button onClick={() => navigate('/orders')} className="text-brand-600 text-[11px] font-bold hover:underline">
          View All
        </button>
      </div>

      {loading ? <PageLoader /> : (
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="text-[10px] font-bold text-text-muted uppercase tracking-wider">
                <th className="pb-3 pr-2">Order No.</th>
                <th className="pb-3 pr-2">Customer</th>
                <th className="pb-3 pr-2">Status</th>
                <th className="pb-3 pr-2">Revenue</th>
                <th className="pb-3">Net Profit</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {orders.map((o, idx) => (
                <tr key={o.id} className="group cursor-pointer hover:bg-bg-hover" onClick={() => navigate('/orders')}>
                  <td className="py-4">
                    <span className="text-[13px] font-bold text-brand-600">#{o.order_number?.substring(0, 6) || '---'}</span>
                  </td>
                  <td className="py-4">
                    <div className="flex items-center gap-2">
                       <div className={clsx("w-7 h-7 rounded-full flex items-center justify-center text-[10px] font-bold", {
                         'bg-brand-100 text-brand-600': idx % 3 === 0,
                         'bg-accent-emerald/10 text-accent-emerald': idx % 3 === 1,
                         'bg-accent-rose/10 text-accent-rose': idx % 3 === 2,
                       })}>
                          {o.customer_name?.split(' ').map(n => n[0]).join('') || '?'}
                       </div>
                       <span className="text-[13px] font-medium text-text-primary whitespace-nowrap">{o.customer_name || 'Generic Customer'}</span>
                    </div>
                  </td>
                  <td className="py-4"><StatusBadge status={o.status} showDot={false} /></td>
                  <td className="py-4 text-[13px] font-medium text-text-primary">EGP {o.total_amount?.toLocaleString()}</td>
                  <td className="py-4 text-[13px] font-bold text-accent-emerald">+EGP {o.profit?.toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

import { useState, useEffect } from 'react'
import { dashboardApi } from '@/services/api'
import { PageLoader } from '@/components/shared/States'
import StatusBadge from '@/components/shared/StatusBadge'
import { AlertTriangle } from 'lucide-react'

export default function InventoryAlerts() {
  const [items,   setItems]   = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    dashboardApi.getInventoryAlerts()
      .then(d => { setItems(d); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  if (!loading && items.length === 0) return null

  return (
    <div className="glass-card p-6">
      <div className="flex items-center gap-2 mb-4">
        <div className="p-1.5 rounded-lg bg-accent-amber/10">
          <AlertTriangle className="w-4 h-4 text-accent-amber" />
        </div>
        <h3 className="section-title mb-0">Inventory Alerts</h3>
        <span className="badge-warning ml-auto">{items.length} products need attention</span>
      </div>

      {loading ? <PageLoader /> : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {items.map(item => (
            <div key={item.id} className="bg-bg-hover rounded-xl p-4 border border-border hover:border-accent-amber/30 transition-colors">
              <div className="flex items-start justify-between mb-2">
                <p className="text-sm font-medium text-text-primary leading-tight">{item.name}</p>
                <StatusBadge status={item.inventory?.status} />
              </div>
              <p className="text-xs text-text-muted mb-3">{item.sku}</p>
              <div className="space-y-1.5">
                <div className="flex justify-between text-xs">
                  <span className="text-text-muted">Stock</span>
                  <span className={`font-semibold ${item.inventory?.quantity === 0 ? 'text-accent-rose' : 'text-accent-amber'}`}>
                    {item.inventory?.quantity} units
                  </span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-text-muted">Reorder at</span>
                  <span className="text-text-secondary">{item.inventory?.reorder_point} units</span>
                </div>
                {/* Stock bar */}
                <div className="w-full bg-bg-primary rounded-full h-1.5 mt-2">
                  <div
                    className="h-1.5 rounded-full transition-all"
                    style={{
                      width: `${Math.min(100, (item.inventory?.quantity / item.inventory?.reorder_point) * 50)}%`,
                      background: item.inventory?.quantity === 0 ? '#F43F5E' : '#F59E0B'
                    }}
                  />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

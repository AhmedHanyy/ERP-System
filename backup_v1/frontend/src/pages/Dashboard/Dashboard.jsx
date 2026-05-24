import { useState, useEffect } from 'react'
import { ShoppingBag, DollarSign, Truck, BarChart2, Plus, Calendar } from 'lucide-react'
import { dashboardApi } from '@/services/api'
import KPICard  from '@/components/shared/KPICard'
import { PageLoader, ErrorState } from '@/components/shared/States'
import SalesPerformanceChart from './SalesPerformanceChart'
import TopSKUProgress        from './TopSKUProgress'
import RecentOrdersTable     from './RecentOrdersTable'
import CustomerInsights      from './CustomerInsights'
import ProcurementTimeline   from './ProcurementTimeline'

export default function Dashboard() {
  const [kpis,    setKpis]    = useState(null)
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState(null)

  const loadKPIs = async () => {
    try {
      setLoading(true)
      const data = await dashboardApi.getKPIs()
      setKpis(data)
    } catch { setError('Failed to load dashboard') }
    finally { setLoading(false) }
  }

  useEffect(() => { loadKPIs() }, [])

  if (loading) return <PageLoader />
  if (error)   return <ErrorState message={error} onRetry={loadKPIs} />

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 py-2">
        <div>
          <h2 className="text-2xl font-bold text-text-primary tracking-tight">Operations Overview Dashboard</h2>
          <p className="text-sm text-text-muted">Real-time performance metrics.</p>
        </div>
        <div className="flex gap-3">
          <button className="btn-secondary">
            <Calendar className="w-4 h-4" /> Current Period
          </button>
          <button className="btn-primary">
            <Plus className="w-4 h-4" /> Create Order
          </button>
        </div>
      </div>

      {/* KPI Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-6">
        <KPICard
          title="Total Order Volume"
          value={kpis?.total_orders?.value || 0}
          change={12.5}
          icon={ShoppingBag}
          color="brand"
        />
        <KPICard
          title="Gross Revenue"
          value={kpis?.revenue?.value || 0}
          change={8.2}
          prefix="EGP "
          icon={DollarSign}
          color="emerald"
        />
        <KPICard
          title="Procurement Active"
          value={12}
          suffix=" Req."
          change={-3}
          icon={Truck}
          color="sky"
        />
        <KPICard
          title="Inventory Turnover"
          value={4.2}
          suffix="x"
          change={5}
          icon={BarChart2}
          color="amber"
          label="Optimal ratio"
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-3 glass-card p-6">
          <SalesPerformanceChart />
        </div>
      </div>

      {/* Progress & Bottom Row */}
      <div className="grid grid-cols-1 xl:grid-cols-4 gap-6">
         <div className="xl:col-span-4">
            <TopSKUProgress />
         </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
          <div className="xl:col-span-1">
             <RecentOrdersTable compact />
          </div>
          <div className="xl:col-span-1">
             <CustomerInsights />
          </div>
          <div className="xl:col-span-1">
             <ProcurementTimeline />
          </div>
      </div>
    </div>
  )
}

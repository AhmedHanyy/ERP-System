import { useState, useEffect } from 'react'
import { ShoppingBag, DollarSign, Truck, BarChart2, Calendar, Target, AlertTriangle, Users } from 'lucide-react'
import { dashboardApi } from '@/services/api'
import { useAuth } from '@/context/AuthContext'
import KPICard  from '@/components/shared/KPICard'
import { PageLoader, ErrorState } from '@/components/shared/States'
import SalesPerformanceChart from './SalesPerformanceChart'
import TopSKUProgress        from './TopSKUProgress'
import RecentOrdersTable     from './RecentOrdersTable'
import CustomerInsights      from './CustomerInsights'
import ProcurementTimeline   from './ProcurementTimeline'

export default function Dashboard() {
  const { user } = useAuth()
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

  // Role-Based Views Logic
  const role = user?.role || 'Admin'

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      {/* Dynamic Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-extrabold text-slate-900 tracking-tight">{role} Performance Hub</h2>
          <p className="text-slate-500 mt-1">Unified command center for SmartERP operations.</p>
        </div>
        <div className="hidden md:flex items-center gap-4 bg-white p-1.5 rounded-2xl shadow-sm border border-slate-100">
            <span className="px-4 py-2 text-sm font-semibold text-slate-600 bg-slate-50 rounded-xl flex items-center gap-2">
                <Calendar className="w-4 h-4 text-slate-400" /> Fiscal Q3
            </span>
        </div>
      </div>

      {/* KPI Section - Personalized by Role */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        {role === 'Admin' && (
            <>
                <KPICard title="Revenue" value={kpis?.revenue?.value || 0} prefix="EGP " icon={DollarSign} color="emerald" change={8.2} />
                <KPICard title="Orders" value={kpis?.total_orders?.value || 0} icon={ShoppingBag} color="brand" change={12} />
                <KPICard title="Customer LTV" value={8400} prefix="EGP " icon={Users} color="sky" label="Avg. per segment" />
                <KPICard title="Growth Target" value={92} suffix="%" icon={Target} color="amber" label="On track for Q4" />
            </>
        )}
        {role === 'Procurement Staff' && (
            <>
                <KPICard title="Critical Reorders" value={5} icon={AlertTriangle} color="rose" label="Action required" />
                <KPICard title="Active Requests" value={12} icon={Truck} color="brand" />
                <KPICard title="Lead Time Avg." value={4.2} suffix=" Days" icon={Calendar} color="sky" />
                <KPICard title="Budget Utilized" value={65} suffix="%" icon={DollarSign} color="amber" />
            </>
        )}
        {(role === 'Operations Manager' || role === 'Customer Service') && (
            <>
                <KPICard title="Daily Orders" value={42} icon={ShoppingBag} color="emerald" change={15} />
                <KPICard title="Fulfillment Rate" value={98.5} suffix="%" icon={Target} color="brand" />
                <KPICard title="Active Returns" value={3} icon={AlertTriangle} color="amber" />
                <KPICard title="Customer Rating" value={4.9} suffix="/5" icon={Target} color="sky" />
            </>
        )}
      </div>

      {/* Layout Grid - Strategic vs Operational */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-8">
        {/* Main Strategic Section */}
        <div className="xl:col-span-8 space-y-8">
          {(role === 'Admin' || role === 'Analytics Manager') && (
            <div className="glass-card p-6 shadow-sm border-slate-100/50">
               <SalesPerformanceChart />
            </div>
          )}
          
          <div className="glass-card p-0 overflow-hidden shadow-sm border-slate-100/50">
             <RecentOrdersTable compact />
          </div>
        </div>

        {/* Side Operational Section */}
        <div className="xl:col-span-4 space-y-8">
          <div className="glass-card p-6 shadow-sm border-slate-100/50">
             <TopSKUProgress />
          </div>
          
          {role === 'Procurement Staff' ? <ProcurementTimeline hideFull /> : <CustomerInsights />}
        </div>
      </div>
    </div>
  )
}
